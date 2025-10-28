# Do NOT use gevent monkey patching - it breaks asyncio/anyio in APScheduler 4.x
# Instead, we'll ensure the zerorpc server thread properly runs its gevent loop

import asyncio
import logging
import threading
import gevent
import time
import random
import json
import os
import yaml
from datetime import datetime, timezone, timedelta
import dateutil.parser

import tornado.ioloop
import tornado.web
import zerorpc

from apscheduler import AsyncScheduler, ConflictingIdError, TaskLookupError, RunState
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import create_engine

# --- Configuration ---
# Consider changing these paths for production deployments (e.g., /etc/schedule-zero/)
CONFIG_FILE_PATH = "config.yaml"
README_FILE_PATH = "README.md"
REGISTRY_FILE_PATH = "handler_registry.yaml"
DATABASE_URL = "sqlite:///schedulezero_jobs.db" # Can also be overridden by environment variable

# Network Configuration (Defaults to localhost)
TORNADO_ADDRESS = os.environ.get("SCHEDULEZERO_TORNADO_ADDR", "127.0.0.1")
TORNADO_PORT = int(os.environ.get("SCHEDULEZERO_TORNADO_PORT", 8888))
ZRPC_SERVER_HOST = os.environ.get("SCHEDULEZERO_ZRPC_HOST", "127.0.0.1") # Changed from 0.0.0.0
ZRPC_SERVER_PORT = int(os.environ.get("SCHEDULEZERO_ZRPC_PORT", 4242))
ZRPC_SERVER_ADDRESS = f"tcp://{ZRPC_SERVER_HOST}:{ZRPC_SERVER_PORT}" # Use localhost default

# RPC Client Configuration
HEARTBEAT_INTERVAL = 5
RPC_TIMEOUT = 10

# API Defaults
DEFAULT_PAGE_LIMIT = 50

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Global Variables / State ---
scheduler: AsyncScheduler | None = None
registered_handlers = {}
zrpc_server_thread = None
zrpc_server = None  # Reference to zerorpc.Server for clean shutdown
shutdown_event = threading.Event()
app_config = {}
registry_lock = threading.Lock() # Lock for accessing registry file/dict

# --- Config Loading ---
def load_config():
    global app_config
    config_path = os.environ.get("SCHEDULEZERO_CONFIG_PATH", CONFIG_FILE_PATH)
    try:
        with open(config_path, 'r') as f: app_config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
    except FileNotFoundError: logger.warning(f"Config file '{config_path}' not found. Using defaults."); app_config = {"instance_name": "ScheduleZero (Default)", "description": "Config file not found.", "admin_contact": "N/A", "version": "N/A"}
    except yaml.YAMLError as e: logger.error(f"Error parsing {config_path}: {e}"); app_config = {"error": f"Failed to load config: {e}"}

# --- Handler Registry Persistence (YAML) ---
def get_registry_path():
    return os.environ.get("SCHEDULEZERO_REGISTRY_PATH", REGISTRY_FILE_PATH)

def save_registry():
    """Saves the current handler registry to a YAML file."""
    registry_path = get_registry_path()
    with registry_lock:
        try:
            # Create a copy without the non-serializable client objects
            registry_to_save = {}
            for handler_id, info in registered_handlers.items():
                registry_to_save[handler_id] = {
                    "address": info.get("address"),
                    "methods": info.get("methods", [])
                }
            # Only create directory if path includes a directory component
            dir_name = os.path.dirname(registry_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            with open(registry_path, 'w') as f:
                yaml.dump(registry_to_save, f, default_flow_style=False)
            logger.debug(f"Saved handler registry to {registry_path}")
        except Exception as e:
            logger.error(f"Error saving handler registry to {registry_path}: {e}", exc_info=True)

def load_registry():
    """Loads the handler registry from a YAML file."""
    global registered_handlers
    registry_path = get_registry_path()
    if os.path.exists(registry_path):
        with registry_lock:
            try:
                with open(registry_path, 'r') as f:
                    loaded_registry = yaml.safe_load(f)
                validated_registry = {}
                if isinstance(loaded_registry, dict):
                    for handler_id, info in loaded_registry.items():
                         if isinstance(info, dict) and "address" in info and "methods" in info:
                             methods = info["methods"] if isinstance(info["methods"], list) else []
                             validated_registry[handler_id] = {
                                 "address": info["address"],
                                 "methods": sorted([str(m) for m in methods]),
                                 "client": None
                             }
                         else: logger.warning(f"Skipping invalid entry in registry file '{registry_path}' for key: {handler_id}")
                    registered_handlers = validated_registry
                    logger.info(f"Loaded handler registry from {registry_path}. Found {len(registered_handlers)} handlers.")
                elif loaded_registry is None:
                    logger.info(f"Registry file '{registry_path}' is empty. Starting fresh.")
                    registered_handlers = {}
                else:
                    logger.error(f"Registry file '{registry_path}' did not contain a dictionary. Starting fresh.")
                    registered_handlers = {}
            except (yaml.YAMLError, Exception) as e:
                logger.error(f"Error loading handler registry from {registry_path}: {e}. Starting with an empty registry.", exc_info=True)
                registered_handlers = {}
    else:
        logger.info(f"Registry file '{registry_path}' not found. Starting with an empty registry.")
        registered_handlers = {}

# --- zerorpc Server for Registration ---
class RegistrationService:
    """zerorpc service exposed by the main server for handlers to register/update."""
    def register_handler(self, handler_id: str, address: str, methods: list[str]) -> bool:
        """Registers or updates a remote job handler and persists the registry."""
        # Basic validation
        if not isinstance(handler_id, str) or not handler_id:
            logger.error("Registration failed: Invalid handler_id.")
            return False
        if not isinstance(address, str) or not address.startswith("tcp://"): # Basic check
             logger.error(f"Registration failed for '{handler_id}': Invalid address format '{address}'. Expected tcp://host:port.")
             return False
        if not isinstance(methods, list):
             logger.error(f"Registration failed for '{handler_id}': Methods must be a list.")
             return False

        with registry_lock:
            if handler_id in registered_handlers:
                logger.info(f"Handler '{handler_id}' re-registering/updating.")
                if registered_handlers[handler_id].get('address') != address:
                    logger.info(f"Address changed for {handler_id}. Invalidating client.")
                    old_client = registered_handlers[handler_id].get('client')
                    if old_client:
                        try: old_client.close()
                        except Exception as e: logger.warning(f"Non-critical error closing old client for {handler_id}: {e}")
                    registered_handlers[handler_id]['client'] = None
                registered_handlers[handler_id]['address'] = address
                registered_handlers[handler_id]['methods'] = sorted(list(set(map(str, methods)))) # Ensure strings
            else:
                logger.info(f"Registering new handler '{handler_id}' at {address} with methods: {methods}")
                registered_handlers[handler_id] = {
                    "address": address,
                    "methods": sorted(list(set(map(str, methods)))), # Ensure strings
                    "client": None
                }
        save_registry()
        return True

    def report_status(self, handler_id: str, status: str) -> bool:
        """Allows handlers to report status (e.g., 'offline', 'online'). Currently informational."""
        with registry_lock:
             if handler_id in registered_handlers:
                 logger.info(f"Handler '{handler_id}' reported status: {status}")
                 # You could store this in memory for the UI if needed
                 # registered_handlers[handler_id]['last_status'] = status
                 # registered_handlers[handler_id]['last_status_time'] = datetime.now(timezone.utc)
                 return True
             else:
                 logger.warning(f"Status report from unknown handler '{handler_id}'")
                 return False

    def unregister_handler_persistent(self, handler_id: str) -> bool:
        """Explicitly unregisters a handler and persists the change."""
        success = False
        with registry_lock:
            if handler_id in registered_handlers:
                logger.info(f"Persistently unregistering handler '{handler_id}'")
                client = registered_handlers[handler_id].get('client')
                if client:
                    try: client.close()
                    except Exception as e: logger.warning(f"Non-critical error closing client for unregistered handler {handler_id}: {e}")
                del registered_handlers[handler_id]
                success = True
            else:
                logger.warning(f"Attempted to unregister unknown handler '{handler_id}'")
                success = False
        if success:
            save_registry()
        return success

    def ping(self) -> str: return "pong"

def run_zrpc_server():
    """Run zerorpc server in a thread following zerorpc documentation pattern."""
    global zrpc_server
    s = None
    try:
        s = zerorpc.Server(RegistrationService())
        zrpc_server = s  # Store global reference for shutdown
        s.bind(ZRPC_SERVER_ADDRESS)
        logger.info(f"zerorpc Registration/Status Server listening on {ZRPC_SERVER_ADDRESS}")
        
        # Just run it - this is the documented way per zerorpc docs
        # It will block until s.close() is called from another thread
        s.run()
        
    except Exception as e:
         logger.error(f"Failed to bind or run zerorpc server on {ZRPC_SERVER_ADDRESS}: {e}", exc_info=True)
    finally:
        logger.info("zerorpc Server shutting down.")
        if s:
            try:
                s.close()
            except Exception as e:
                logger.error(f"Error closing zerorpc server: {e}")

# --- zerorpc Client Management ---
# (get_handler_client remains the same)
def get_handler_client(handler_id: str) -> zerorpc.Client | None:
    with registry_lock:
        handler_info = registered_handlers.get(handler_id)

    if not handler_info:
        logger.error(f"Attempted to get client for unknown handler '{handler_id}'")
        return None

    client = handler_info.get('client')
    if client:
        try:
             loop = asyncio.get_running_loop()
             pong_future = loop.run_in_executor(None, lambda: client.ping(timeout=2))
             asyncio.run_coroutine_threadsafe(pong_future, loop).result(timeout=3)
             logger.debug(f"Ping successful for handler {handler_id}")
             return client
        except Exception as e:
             logger.warning(f"Ping failed for handler {handler_id} at {handler_info['address']}: {e}. Invalidating client.")
             with registry_lock:
                 if handler_id in registered_handlers and registered_handlers[handler_id].get('client') == client:
                     try: client.close()
                     except Exception: pass
                     registered_handlers[handler_id]['client'] = None
             client = None

    if client is None:
        with registry_lock:
            handler_info = registered_handlers.get(handler_id)
            if not handler_info: return None
            if handler_info.get('client') is not None:
                return handler_info['client']

            try:
                logger.info(f"Creating/Recreating zerorpc client for handler '{handler_id}' at {handler_info['address']}")
                loop = asyncio.get_running_loop()
                def connect_sync():
                    # Set timeout for the initial connection attempt itself via ZMQ socket option
                    # Note: zerorpc doesn't directly expose zmq socket options easily here.
                    # We rely on the ping timeout during creation instead.
                    new_client = zerorpc.Client(heartbeat=HEARTBEAT_INTERVAL, timeout=RPC_TIMEOUT)
                    new_client.connect(handler_info['address'])
                    new_client.ping(timeout=5) # Verify connection during creation
                    return new_client

                client_future = loop.run_in_executor(None, connect_sync)
                new_client = asyncio.run_coroutine_threadsafe(client_future, loop).result(timeout=15)

                registered_handlers[handler_id]['client'] = new_client
                logger.info(f"Successfully connected client for handler '{handler_id}'")
                return new_client
            except (asyncio.TimeoutError, zerorpc.TimeoutExpired, Exception) as e:
                logger.error(f"Failed to connect client for handler '{handler_id}': {e}")
                if handler_id in registered_handlers: registered_handlers[handler_id]['client'] = None
                return None
    return None

# --- APScheduler Job Function Example with Retries ---
# (call_remote_handler_job remains the same)
async def call_remote_handler_job(handler_id: str, method_name: str, job_params: dict):
    logger.info(f"Job triggered: Call {handler_id}.{method_name} with params: {job_params}")
    retries, max_retries, current_delay = 0, 5, 2.0
    backoff_factor, jitter_factor = 2.0, 0.5
    loop = asyncio.get_running_loop()
    while retries < max_retries:
        client = get_handler_client(handler_id)
        if not client:
            logger.error(f"Cannot execute job: No valid client for handler '{handler_id}'.")
            retries += 1
            if retries >= max_retries: raise Exception(f"Job failed for {handler_id}: Could not connect after {max_retries} attempts.")
            wait_time = max(0.1, current_delay + random.uniform(-jitter_factor, jitter_factor) * current_delay)
            logger.warning(f"Handler '{handler_id}' unreachable. Retrying connection in {wait_time:.2f}s...")
            await asyncio.sleep(wait_time)
            current_delay *= backoff_factor
            continue
        try:
            logger.info(f"Attempt {retries + 1}/{max_retries}: Calling {handler_id}.{method_name}...")
            # Run the potentially blocking zerorpc call in an executor thread
            def rpc_call_sync(): return client.call(method_name, job_params)
            result_future = loop.run_in_executor(None, rpc_call_sync)
            # Wait for the result with a timeout slightly longer than the RPC timeout
            result = await asyncio.wait_for(result_future, timeout=RPC_TIMEOUT + 5)
            logger.info(f"Job successful: {handler_id}.{method_name} returned: {result}")
            return # Success!
        except (zerorpc.TimeoutExpired, zerorpc.LostRemote, asyncio.TimeoutError) as e:
             # Handle failures specific to communication/timeout
             retries += 1
             logger.warning(f"Attempt {retries}/{max_retries} failed for {handler_id}.{method_name}: {e}")
             logger.info(f"Invalidating client connection for {handler_id} due to error.")
             # Safely close and remove the client reference from the shared registry
             with registry_lock:
                 if handler_id in registered_handlers and registered_handlers[handler_id].get('client') == client:
                     try: client.close()
                     except Exception: pass
                     registered_handlers[handler_id]['client'] = None
             # Check if max retries reached
             if retries >= max_retries:
                logger.error(f"Max retries reached for {handler_id}.{method_name}. Job failed.")
                raise Exception(f"Job failed for {handler_id}.{method_name} after {max_retries} retries.") from e
             # Calculate wait time with jitter for the next retry
             jitter = random.uniform(-jitter_factor, jitter_factor) * current_delay
             wait_time = max(0.1, current_delay + jitter)
             logger.info(f"Waiting {wait_time:.2f} seconds before next retry...")
             await asyncio.sleep(wait_time)
             # Increase delay for subsequent retries
             current_delay *= backoff_factor
        except Exception as e:
            # Handle unexpected errors during the RPC call itself
            logger.error(f"Unexpected error during job execution for {handler_id}.{method_name}: {e}", exc_info=True)
            # Re-raise to let APScheduler know the job run failed
            raise

# --- Tornado Web Handlers ---
class BaseAPIHandler(tornado.web.RequestHandler):
    def prepare(self):
        # Allow CORS for development (restrict in production)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        if self.request.method == 'OPTIONS':
            self.set_status(204)
            self.finish()
            return

        # Existing prepare logic
        if self.request.headers.get("Content-Type", "").startswith("application/json") and self.request.body:
            try: self.json_args = json.loads(self.request.body)
            except json.JSONDecodeError: self.send_error(400, reason="Invalid JSON body"); self.json_args = None; return
        else: self.json_args = None
        try: self.limit = int(self.get_query_argument("limit", DEFAULT_PAGE_LIMIT)); self.limit = max(1, self.limit)
        except ValueError: self.limit = DEFAULT_PAGE_LIMIT
        try: self.offset = int(self.get_query_argument("offset", 0)); self.offset = max(0, self.offset)
        except ValueError: self.offset = 0

    def write_error(self, status_code, **kwargs):
        self.set_header('Content-Type', 'application/json')
        reason = kwargs.get('reason', getattr(self, '_reason', 'Unknown Error'))
        exc_info = kwargs.get('exc_info')
        message = reason
        if exc_info:
            # In debug mode, potentially add more detail
            # message = f"{reason} - {exc_info[1]}"
            pass
        body = {'error': {'code': status_code, 'message': message}}
        self.finish(json.dumps(body))

    def write_json(self, data, status_code=200):
        self.set_status(status_code)
        self.set_header('Content-Type', 'application/json')
        self.finish(json.dumps(data, default=str)) # Use default=str for datetime etc.

    def options(self, *args, **kwargs):
        # Handle CORS preflight requests
        self.set_status(204)
        self.finish()


class ListHandlersHandler(BaseAPIHandler):
    async def get(self):
        with registry_lock:
            # Create a serializable copy of the handler data
            handler_data = []
            now = datetime.now(timezone.utc)
            for hid, info in registered_handlers.items():
                status = "Unknown"
                # Check if client exists and maybe add last ping time?
                # For simplicity, just use presence of client object for now
                if info.get('client'):
                    status = "Connected (Assumed)" # Needs actual ping/heartbeat status ideally
                else:
                    status = "Disconnected"

                handler_data.append({
                    "id": hid,
                    "address": info["address"],
                    "methods": info["methods"],
                    "status": status
                    # "last_seen": info.get('last_status_time') # If you add status reporting
                })
        self.write_json({"handlers": handler_data})


class ScheduleJobHandler(BaseAPIHandler):
    async def post(self):
        if not self.json_args: return self.send_error(400, reason="JSON body required.")
        required = ["handler_id", "method_name", "trigger_config", "job_params"]
        if not all(f in self.json_args for f in required): return self.send_error(400, reason=f"Missing fields. Expected: {required}.")
        handler_id, method_name, trigger_config, job_params = (self.json_args[f] for f in required)
        schedule_id = self.json_args.get("schedule_id") # Optional

        # Validate handler and method
        with registry_lock: handler_info = registered_handlers.get(handler_id)
        if not handler_info: return self.send_error(404, reason=f"Handler '{handler_id}' not registered.")
        if method_name not in handler_info["methods"]: return self.send_error(400, reason=f"Method '{method_name}' not exposed by handler '{handler_id}'.")
        if not isinstance(job_params, dict): return self.send_error(400, reason="'job_params' must be a dictionary/object.")

        # Parse trigger
        try:
            trigger_type = trigger_config.get("type", "").lower()
            trigger_args = {k: v for k, v in trigger_config.items() if k != "type"}

            if trigger_type == "date":
                run_date_str = trigger_args.get("run_date")
                if not run_date_str: raise ValueError("'run_date' is required for date trigger")
                run_date = dateutil.parser.isoparse(run_date_str)
                trigger = DateTrigger(run_time=run_date)  # APScheduler 4.x uses 'run_time' not 'run_date'
            elif trigger_type == "interval":
                # Convert interval units like 'seconds', 'minutes' etc. to integers/floats
                for key in ['weeks', 'days', 'hours', 'minutes', 'seconds']:
                    if key in trigger_args: trigger_args[key] = float(trigger_args[key])
                trigger = IntervalTrigger(**trigger_args)
            elif trigger_type == "cron":
                # APScheduler's CronTrigger takes string or int arguments directly
                trigger = CronTrigger(**trigger_args)
            else:
                return self.send_error(400, reason=f"Unsupported trigger type: '{trigger_type}'. Use 'date', 'interval', or 'cron'.")
        except (ValueError, TypeError, KeyError, dateutil.parser.ParserError) as e:
            logger.error(f"Invalid trigger config received: {trigger_config} - Error: {e}", exc_info=True)
            return self.send_error(400, reason=f"Invalid trigger configuration: {e}")
        except Exception as e:
             logger.error(f"Unexpected error parsing trigger: {e}", exc_info=True)
             return self.send_error(500, reason=f"Internal error parsing trigger: {e}")


        # Add schedule to APScheduler
        try:
            # Note: APScheduler requires args to be a list/tuple. We pass the dict as the third element.
            schedule_options = {
                "id": schedule_id,
                "args": [handler_id, method_name, job_params],
                "replace_existing": True, # Overwrite if ID exists
                "misfire_grace_time": self.json_args.get("misfire_grace_time", 60) # Allow some delay
                # Add other APScheduler options as needed (e.g., coalesce, max_instances from API?)
            }
            # Remove None ID if not provided, so APScheduler generates one
            if schedule_id is None: del schedule_options["id"]

            schedule = await scheduler.add_schedule(call_remote_handler_job, trigger=trigger, **schedule_options)
            logger.info(f"Scheduled job via API: ID={schedule.id}, Handler={handler_id}, Method={method_name}")
            self.write_json({"status": "success", "schedule_id": schedule.id}, 201) # 201 Created
        except ConflictingIdError:
            return self.send_error(409, reason=f"Schedule ID '{schedule_id}' already exists and replace_existing=False (or implicit default).")
        except TaskLookupError:
             # This shouldn't happen if call_remote_handler_job is defined
             logger.error("TaskLookupError: 'call_remote_handler_job' not found?", exc_info=True)
             return self.send_error(500, reason="Internal error: Target task function not found.")
        except Exception as e:
            logger.error(f"API schedule add failed: {e}", exc_info=True)
            return self.send_error(500, reason=f"Internal error adding schedule: {e}")


class RunNowHandler(BaseAPIHandler):
     async def post(self):
        if not self.json_args: return self.send_error(400, reason="JSON body required.")
        required = ["handler_id", "method_name", "job_params"]
        if not all(f in self.json_args for f in required): return self.send_error(400, reason=f"Missing fields. Expected: {required}.")
        handler_id, method_name, job_params = (self.json_args[f] for f in required)

        # Validate handler and method
        with registry_lock: handler_info = registered_handlers.get(handler_id)
        if not handler_info: return self.send_error(404, reason=f"Handler '{handler_id}' not registered.")
        if method_name not in handler_info["methods"]: return self.send_error(400, reason=f"Method '{method_name}' not exposed by handler '{handler_id}'.")
        if not isinstance(job_params, dict): return self.send_error(400, reason="'job_params' must be a dictionary/object.")

        # Add job to APScheduler's queue
        try:
            # Pass args=[handler_id, method_name, job_params]
            job = await scheduler.add_job(call_remote_handler_job, args=[handler_id, method_name, job_params])
            logger.info(f"Added job to run now via API: ID={job.id}, Handler={handler_id}, Method={method_name}")
            # Return 202 Accepted as it's queued, not necessarily executed yet
            self.write_json({"status": "success - job queued", "job_id": str(job.id)}, 202)
        except TaskLookupError:
             logger.error("TaskLookupError: 'call_remote_handler_job' not found?", exc_info=True)
             return self.send_error(500, reason="Internal error: Target task function not found.")
        except Exception as e:
            logger.error(f"API run now failed: {e}", exc_info=True)
            return self.send_error(500, reason=f"Internal error queuing job: {e}")


class ListSchedulesHandler(BaseAPIHandler):
    async def get(self):
        if not scheduler: return self.send_error(503, reason="Scheduler unavailable.")
        start_str, end_str = self.get_query_argument("start_time", None), self.get_query_argument("end_time", None)
        start_dt, end_dt = None, None
        try:
            # Parse ISO 8601 strings, make timezone-aware (assume UTC if none specified)
            if start_str: start_dt = dateutil.parser.isoparse(start_str); start_dt = start_dt.astimezone(timezone.utc) if start_dt.tzinfo else start_dt.replace(tzinfo=timezone.utc)
            if end_str: end_dt = dateutil.parser.isoparse(end_str); end_dt = end_dt.astimezone(timezone.utc) if end_dt.tzinfo else end_dt.replace(tzinfo=timezone.utc)
        except ValueError as e: return self.send_error(400, reason=f"Invalid date format (ISO 8601 expected): {e}")

        try:
            all_schedules = await scheduler.get_schedules()
            filtered = []
            for s in all_schedules:
                next_fire = None
                if s.next_fire_time:
                    # Ensure next_fire_time is timezone-aware for comparison
                    next_fire = s.next_fire_time.astimezone(timezone.utc) if s.next_fire_time.tzinfo else s.next_fire_time.replace(tzinfo=timezone.utc)

                # Filtering logic
                if next_fire:
                     passes_start = (start_dt is None or next_fire >= start_dt)
                     passes_end = (end_dt is None or next_fire <= end_dt)
                     if passes_start and passes_end:
                         filtered.append(s)
                elif start_dt is None and end_dt is None:
                    # Include schedules with no next fire time only if no time filter is applied
                    filtered.append(s)

            total = len(filtered)
            # Sort by next_fire_time (handle None by putting them last)
            filtered.sort(key=lambda s: s.next_fire_time if s.next_fire_time else datetime.max.replace(tzinfo=timezone.utc))

            # Apply pagination
            paginated = filtered[self.offset : self.offset + self.limit]

            # Format output
            output = []
            for s in paginated:
                 args = getattr(s, 'args', [])
                 # Safely extract args, assuming format [handler_id, method_name, job_params_dict]
                 hid = args[0] if len(args) > 0 and isinstance(args[0], str) else "?"
                 mname = args[1] if len(args) > 1 and isinstance(args[1], str) else "?"
                 params = args[2] if len(args) > 2 and isinstance(args[2], dict) else {}
                 misfire = s.misfire_grace_time
                 paused_until_iso = s.paused_until.isoformat() if s.paused_until else None
                 next_fire_iso = s.next_fire_time.isoformat() if s.next_fire_time else None

                 output.append({
                     "id": s.id,
                     "task_id": s.task_id, # Usually matches the function name
                     "trigger": str(s.trigger),
                     "next_fire_time": next_fire_iso,
                     "handler_id": hid,
                     "method_name": mname,
                     "job_params": params,
                     "paused": paused_until_iso is not None,
                     "paused_until": paused_until_iso,
                     "misfire_grace_time": misfire.total_seconds() if isinstance(misfire, timedelta) else misfire, # Could be None or int
                     "coalesce": s.coalesce.name, # e.g., 'latest', 'earliest', 'all'
                     "max_jitter": s.max_jitter.total_seconds() if s.max_jitter else None
                 })

            response = {
                "pagination": {"offset": self.offset, "limit": self.limit, "total": total},
                "schedules": output
            }
            self.write_json(response)
        except Exception as e:
            logger.error(f"Error listing schedules: {e}", exc_info=True)
            self.send_error(500, reason="Internal error retrieving schedules.")


class ConfigHandler(BaseAPIHandler):
     async def get(self): self.write_json(app_config)


class ReadmeHandler(BaseAPIHandler):
    async def get(self):
        readme_path = os.environ.get("SCHEDULEZERO_README_PATH", README_FILE_PATH)
        try:
            # Ensure path is safe if coming from env var? For now, assume it's controlled.
            with open(readme_path, 'r', encoding='utf-8') as f: content = f.read()
            self.write_json({"readme_content": content})
        except FileNotFoundError: self.send_error(404, reason=f"README file '{readme_path}' not found.")
        except Exception as e: logger.error(f"Error reading README from '{readme_path}': {e}", exc_info=True); self.send_error(500, reason="Error reading README.")


class MainHandler(tornado.web.RequestHandler):
    async def get(self):
        # Render the SPA template, passing the instance name
        instance_name = app_config.get("instance_name", "ScheduleZero")
        self.render("index.html", title=instance_name)


def make_app():
    # Ensure template directory exists
    template_dir = "templates"
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)
        logger.info(f"Created template directory: {template_dir}")

    # Generate or update index.html template
    index_html_path = os.path.join(template_dir, "index.html")
    # Content is mostly the same JS/HTML/CSS for the SPA structure
    # Consider moving this to a separate static file if it gets large
    index_html_content = """
<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{{ title }}</title><script src="https://cdn.tailwindcss.com"></script><style>body { font-family: 'Inter', sans-serif; } nav a.active { font-weight: bold; text-decoration: underline; } .loader { border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 20px; height: 20px; animation: spin 1s linear infinite; display: inline-block; margin-left: 10px; vertical-align: middle;} @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } } th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; vertical-align: top; } th { background-color: #f2f2f2; } td pre { white-space: pre-wrap; word-break: break-all; max-height: 10em; overflow-y: auto; }</style><link rel="preconnect" href="https://rsms.me/"><link rel="stylesheet" href="https://rsms.me/inter/inter.css"></head><body class="bg-gray-100 text-gray-800"><div class="container mx-auto p-4"><header class="bg-blue-600 text-white p-4 rounded-lg shadow mb-6"><h1 class="text-2xl font-bold">{{ title }}</h1></header><nav class="bg-white p-3 rounded-lg shadow mb-6 flex space-x-4"><a href="#readme" class="text-blue-600 hover:text-blue-800">Home/Readme</a><a href="#about" class="text-blue-600 hover:text-blue-800">About</a><a href="#registrations" class="text-blue-600 hover:text-blue-800">Registrations</a><a href="#schedules" class="text-blue-600 hover:text-blue-800">Schedules</a></nav><main id="content" class="bg-white p-6 rounded-lg shadow min-h-[300px]"><p>Loading...</p></main><footer class="text-center text-gray-500 mt-6 text-sm">ScheduleZero - Powered by Tornado & APScheduler</footer></div><script> const contentEl=document.getElementById('content'),navLinks=document.querySelectorAll('nav a');let currentApiRequestController=null;async function fetchData(url){if(currentApiRequestController){try{currentApiRequestController.abort()}catch(e){console.warn("Could not abort previous request",e)}} currentApiRequestController=new AbortController();const signal=currentApiRequestController.signal;showLoading();try{const response=await fetch(url,{signal});if(!response.ok){let errorMsg=`HTTP error! Status: ${response.status}`;try{const errData=await response.json();errorMsg=errData?.error?.message||errorMsg}catch(e){} throw new Error(errorMsg)} return await response.json()}catch(error){if(error.name==='AbortError'){console.log('Fetch aborted');return null} console.error('Fetch error:',error);showError(`Failed to load data: ${error.message}`);return null}finally{if(signal===currentApiRequestController?.signal){currentApiRequestController=null}}} function showLoading(){contentEl.innerHTML='<p>Loading<span class="loader"></span></p>'} function showError(message){contentEl.innerHTML=`<p class="text-red-600 font-bold">Error:</p><p>${message}</p>`} function setActiveLink(hash){navLinks.forEach(link=>{if(link.getAttribute('href')===hash){link.classList.add('active')}else{link.classList.remove('active')}})} function escapeHtml(unsafe){return unsafe.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")} function renderReadme(data){if(!data)return;contentEl.innerHTML=`<h2 class="text-xl font-semibold mb-4">README</h2><pre class="bg-gray-50 p-4 rounded border text-sm whitespace-pre-wrap">${escapeHtml(data.readme_content||'Failed to load README.')}</pre>`} function renderAbout(data){if(!data)return;let content='<h2 class="text-xl font-semibold mb-4">About This Instance</h2>';if(data.error){content+=`<p class="text-red-500">${escapeHtml(data.error)}</p>`}else{content+='<ul class="list-disc pl-5 space-y-1">';for(const key in data){content+=`<li><strong>${escapeHtml(key.replace(/_/g,' ').replace(/\\b\\w/g,l=>l.toUpperCase()))}:</strong> ${escapeHtml(String(data[key]))}</li>`} content+='</ul>'} contentEl.innerHTML=content} function renderRegistrations(data){if(!data)return;let tableHtml='<h2 class="text-xl font-semibold mb-4">Registered Handlers</h2>';if(!data.handlers||data.handlers.length===0){tableHtml+='<p>No handlers are currently registered.</p>'}else{tableHtml+='<div class="overflow-x-auto"><table class="w-full min-w-[600px]"><thead><tr><th>ID</th><th>Address</th><th>Status</th><th>Methods</th></tr></thead><tbody>';data.handlers.forEach(h=>{tableHtml+=`<tr><td>${escapeHtml(h.id)}</td><td>${escapeHtml(h.address)}</td><td class="${h.status.startsWith('Connected')?'text-green-600':'text-red-600'}">${escapeHtml(h.status)}</td><td>${escapeHtml(h.methods.join(', '))}</td></tr>`});tableHtml+='</tbody></table></div>'} contentEl.innerHTML=tableHtml} function renderSchedules(data){if(!data)return;const{schedules,pagination}=data;let contentHtml=`<h2 class="text-xl font-semibold mb-4">Scheduled Jobs</h2><div class="mb-4 flex flex-wrap items-center gap-4"><div><label for="start_time" class="mr-2">Start (UTC):</label><input type="datetime-local" id="start_time" class="border rounded p-1"></div><div><label for="end_time" class="mr-2">End (UTC):</label><input type="datetime-local" id="end_time" class="border rounded p-1"></div><button id="filter_button" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-1 px-3 rounded">Filter List</button><span class="text-sm text-gray-600">(Default: Next 7 days)</span></div>`;if(!schedules||schedules.length===0){contentHtml+='<p>No schedules found matching the criteria.</p>'}else{contentHtml+=`<p class="text-sm mb-2">Showing ${pagination.offset+1}-${Math.min(pagination.offset+pagination.limit,pagination.total)} of ${pagination.total} schedules.</p><div class="overflow-x-auto"><table class="w-full text-sm min-w-[800px]"><thead><tr><th>ID</th><th>Next Fire Time (UTC)</th><th>Handler</th><th>Method</th><th>Params</th><th>Trigger</th><th>Status</th></tr></thead><tbody>`;schedules.forEach(s=>{const nextFire=s.next_fire_time?new Date(s.next_fire_time).toISOString().replace('T',' ').substring(0,19):'N/A';const status=s.paused?`Paused until ${new Date(s.paused_until).toISOString().substring(0,10)}`:'Active';contentHtml+=`<tr><td class="break-all">${escapeHtml(s.id)}</td><td>${escapeHtml(nextFire)}</td><td>${escapeHtml(s.handler_id)}</td><td>${escapeHtml(s.method_name)}</td><td><pre class="text-xs bg-gray-50 p-1 rounded">${escapeHtml(JSON.stringify(s.job_params,null,2))}</pre></td><td class="text-xs">${escapeHtml(s.trigger)}</td><td class="${s.paused?'text-orange-600':'text-green-600'}">${escapeHtml(status)}</td></tr>`});contentHtml+='</tbody></table></div>';contentHtml+='<div class="mt-4 flex justify-between items-center">';const canPrev=pagination.offset>0;const canNext=(pagination.offset+pagination.limit)<pagination.total;contentHtml+=`<button id="prev_page" class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-1 px-3 rounded ${!canPrev?'opacity-50 cursor-not-allowed':''}" ${!canPrev?'disabled':''}>&lt; Previous</button>`;contentHtml+=`<span class="text-sm">Page ${Math.floor(pagination.offset/pagination.limit)+1} of ${Math.ceil(pagination.total/pagination.limit)}</span>`;contentHtml+=`<button id="next_page" class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-1 px-3 rounded ${!canNext?'opacity-50 cursor-not-allowed':''}" ${!canNext?'disabled':''}>Next &gt;</button>`;contentHtml+='</div>'} contentEl.innerHTML=contentHtml;document.getElementById('filter_button')?.addEventListener('click',()=>loadSchedules(0));document.getElementById('prev_page')?.addEventListener('click',()=>loadSchedules(pagination.offset-pagination.limit));document.getElementById('next_page')?.addEventListener('click',()=>loadSchedules(pagination.offset+pagination.limit));const currentSearchParams=new URLSearchParams(window.location.search);const currentStartTime=currentSearchParams.get('start_time');const currentEndTime=currentSearchParams.get('end_time');const startInput=document.getElementById('start_time');const endInput=document.getElementById('end_time');if(startInput&&currentStartTime)startInput.value=localDatetimeFromISO(currentStartTime);if(endInput&&currentEndTime)endInput.value=localDatetimeFromISO(currentEndTime)} function localDatetimeFromISO(isoString){if(!isoString)return '';try{const date=new Date(isoString);if(isNaN(date.getTime()))return '';const offset=date.getTimezoneOffset()*60000;const localISOTime=(new Date(date.getTime()-offset)).toISOString().slice(0,16);return localISOTime}catch(e){console.error("Error parsing date for input:",e);return ''}} function isoStringFromLocalInput(elementId){const input=document.getElementById(elementId);if(!input||!input.value)return null;try{const localDate=new Date(input.value);if(isNaN(localDate.getTime()))return null;return localDate.toISOString()}catch(e){console.error("Error creating ISO string from input:",e);return null}} async function loadReadme(){const data=await fetchData('/api/readme');renderReadme(data)} async function loadAbout(){const data=await fetchData('/api/config');renderAbout(data)} async function loadRegistrations(){const data=await fetchData('/api/handlers');renderRegistrations(data)} async function loadSchedules(requestedOffset=0){const limitParam=new URLSearchParams(window.location.search).get('limit');const limit=parseInt(limitParam||'50',10);let offset=Math.max(0,requestedOffset);let startTimeISO=isoStringFromLocalInput('start_time');let endTimeISO=isoStringFromLocalInput('end_time');const params=new URLSearchParams(window.location.search);const navigatedFromOtherPage=!params.has('start_time')&&!params.has('end_time')&&!document.getElementById('start_time');if(navigatedFromOtherPage&&!startTimeISO&&!endTimeISO){const now=new Date();const nextWeek=new Date(now.getTime()+7*24*60*60*1000);startTimeISO=now.toISOString();endTimeISO=nextWeek.toISOString()} const url=new URL('/api/schedules',window.location.origin);url.searchParams.set('limit',limit);url.searchParams.set('offset',offset);if(startTimeISO)url.searchParams.set('start_time',startTimeISO);if(endTimeISO)url.searchParams.set('end_time',endTimeISO);const historyUrl=new URL(window.location);historyUrl.hash='#schedules';historyUrl.searchParams.set('limit',limit);historyUrl.searchParams.set('offset',offset);if(startTimeISO)historyUrl.searchParams.set('start_time',startTimeISO);else historyUrl.searchParams.delete('start_time');if(endTimeISO)historyUrl.searchParams.set('end_time',endTimeISO);else historyUrl.searchParams.delete('end_time');history.replaceState(null,'',historyUrl);const data=await fetchData(url.toString());renderSchedules(data)} function router(){const hash=window.location.hash||'#readme';setActiveLink(hash);switch(hash){case'#readme':loadReadme();break;case'#about':loadAbout();break;case'#registrations':loadRegistrations();break;case'#schedules':const params=new URLSearchParams(window.location.search);const offset=parseInt(params.get('offset')||'0',10);loadSchedules(offset);break;default:contentEl.innerHTML='<p>Page not found.</p>';setActiveLink('')}} window.addEventListener('hashchange',router);window.addEventListener('load',router); </script></body></html>
    """
    try:
        # Check if content needs update or file doesn't exist
        needs_update = True
        if os.path.exists(index_html_path):
            with open(index_html_path, "r") as f:
                current_content = f.read()
            if current_content == index_html_content:
                needs_update = False

        if needs_update:
            with open(index_html_path, "w") as f:
                f.write(index_html_content)
            logger.info(f"Generated/Updated template: {index_html_path}")

    except Exception as e:
         logger.error(f"Error writing template file {index_html_path}: {e}")
         # Continue without template if writing fails? Or raise error?

    settings = {
        "template_path": template_dir,
        "debug": True # Enable debug mode for auto-reloading and easier development
    }
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/handlers", ListHandlersHandler),
        (r"/api/schedule", ScheduleJobHandler),
        (r"/api/run_now", RunNowHandler),
        (r"/api/schedules", ListSchedulesHandler),
        (r"/api/config", ConfigHandler),
        (r"/api/readme", ReadmeHandler),
    ], **settings)


# --- Main Application Start / Stop ---
async def main():
    global scheduler, zrpc_server_thread
    load_config()
    load_registry() # Load registry on startup

    # Allow overriding database URL via environment variable
    db_url = os.environ.get("SCHEDULEZERO_DATABASE_URL", DATABASE_URL)
    logger.info(f"Using database URL: {db_url}")
    try:
        data_store = SQLAlchemyDataStore(db_url)
    except Exception as e:
        logger.critical(f"Failed to create SQLAlchemy engine/datastore for {db_url}: {e}", exc_info=True)
        return # Cannot continue without datastore

    scheduler = AsyncScheduler(data_store=data_store)

    logger.info("Starting zerorpc server thread...")
    zrpc_server_thread = threading.Thread(target=run_zrpc_server, daemon=True)
    zrpc_server_thread.start()
    # Check if thread started successfully? Difficult directly. Give it a moment.
    await asyncio.sleep(1.5)
    if not zrpc_server_thread.is_alive():
         logger.critical("zerorpc server thread failed to start. Check logs. Exiting.")
         return

    # Use scheduler as async context manager
    async with scheduler:
        logger.info("APScheduler started.")

        # Example job addition removed - should be done via API

        try:
            app = make_app()
            app.listen(TORNADO_PORT, address=TORNADO_ADDRESS)
            logger.info(f"Tornado server listening on http://{TORNADO_ADDRESS}:{TORNADO_PORT}")
        except Exception as e:
            logger.critical(f"Failed to start Tornado server: {e}", exc_info=True)
            return

        await asyncio.Event().wait() # Keep running until interrupted

async def shutdown():
    logger.info("Initiating shutdown...")
    
    # Signal zerorpc server to stop via shutdown_event (it monitors this)
    logger.info("Signaling zerorpc server to shut down...")
    shutdown_event.set()
    
    if scheduler and scheduler.state == RunState.started:
        logger.info("Shutting down APScheduler...")
        try:
            await scheduler.stop()
            await scheduler.wait_until_stopped()
            logger.info("APScheduler stopped.")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}", exc_info=True)

    if zrpc_server_thread and zrpc_server_thread.is_alive():
        logger.info("Waiting for zerorpc server thread to exit...")
        zrpc_server_thread.join(timeout=5)
        if zrpc_server_thread.is_alive():
            logger.warning("zerorpc server thread did not exit cleanly after 5 seconds.")
        else:
            logger.info("zerorpc server thread exited cleanly.")

    logger.info("Closing handler clients...")
    loop = asyncio.get_running_loop()
    clients_to_close = []
    with registry_lock:
        clients_to_close = [(hid, info['client']) for hid, info in registered_handlers.items() if info.get('client')]
        # Clear clients immediately inside lock
        for hid, _ in clients_to_close:
            if hid in registered_handlers: registered_handlers[hid]['client'] = None

    close_tasks = []
    for handler_id, client in clients_to_close:
         logger.info(f"Closing client for {handler_id}")
         # Run close in executor as it might block
         close_tasks.append(loop.run_in_executor(None, client.close))

    if close_tasks:
        try:
            # Wait for close operations to finish, with a timeout
            await asyncio.wait_for(asyncio.gather(*close_tasks, return_exceptions=True), timeout=10.0)
            logger.info("Finished closing client connections.")
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for some clients to close.")
        except Exception as e:
             logger.error(f"Error during bulk client close: {e}", exc_info=True)

    logger.info("Shutdown sequence complete.")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    main_task = None
    try:
        main_task = loop.create_task(main())
        loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received.")
    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    except Exception as e:
         logger.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
    finally:
        logger.info("Starting final shutdown...")
        # Ensure main task is cancelled if it's still running
        if main_task and not main_task.done():
             logger.info("Cancelling main task...")
             main_task.cancel()
             try:
                 # Give cancellation a moment to propagate within the loop's handling
                 loop.run_until_complete(asyncio.sleep(0.1))
             except asyncio.CancelledError: pass # Loop might be stopping

        # Run the defined shutdown procedure
        shutdown_task = loop.create_task(shutdown())
        try:
            loop.run_until_complete(shutdown_task)
        except asyncio.CancelledError:
            logger.info("Shutdown task itself was cancelled.")
        except Exception as e:
             logger.error(f"Error during final shutdown execution: {e}", exc_info=True)

        logger.info("Attempting to close loop...")
        try:
            # Gather remaining tasks, cancel them, and wait briefly
            tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]
            if tasks:
                logger.warning(f"Found {len(tasks)} outstanding tasks during final close.")
                for task in tasks: task.cancel()
                try:
                    # Wait for cancellations to be processed
                    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                except asyncio.CancelledError: pass # Expected if loop is stopping
                except Exception as e: logger.error(f"Error gathering cancelled tasks: {e}", exc_info=True)

            # Standard loop closing procedure
            loop.call_soon(loop.stop)
            loop.run_forever() # Allow loop to process stop()
        except Exception as e:
            logger.error(f"Exception during loop cleanup: {e}", exc_info=True)
        finally:
             if not loop.is_closed():
                 loop.close()
                 logger.info("Loop closed.")
             else:
                  logger.info("Loop was already closed.")

