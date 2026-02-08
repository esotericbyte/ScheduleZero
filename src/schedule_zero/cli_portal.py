#!/usr/bin/env python3
"""
ScheduleZero Portal CLI

Commands for managing deployments and the portal server.
"""
import sys
import argparse
import subprocess
from pathlib import Path
from .deployment_config import get_deployment_config, DEPLOYMENTS


def cmd_list_deployments():
    """List all available deployments."""
    print("\nAvailable Deployments:")
    print("=" * 60)
    
    # Get all deployment directories with config files
    deployments_dir = Path("deployments")
    yaml_configs = set()
    if deployments_dir.exists():
        for config_file in deployments_dir.glob("*/config.yaml"):
            yaml_configs.add(config_file.parent.name)
    
    # Combine hardcoded and YAML-based deployments
    all_deployments = set(DEPLOYMENTS.keys()) | yaml_configs
    
    for name in sorted(all_deployments):
        try:
            config = get_deployment_config(name)
            source = "YAML" if (Path(f"deployments/{name}/config.yaml").exists()) else "Built-in"
            print(f"\n  {name.upper():<12} ({source})")
            print(f"    Web:      {config.tornado_host}:{config.tornado_port}")
            print(f"    ZMQ:      {config.zmq_host}:{config.zmq_port}")
            print(f"    Database: {config.database_path}")
            if config.log_file:
                print(f"    Log:      {config.log_file}")
        except Exception as e:
            print(f"\n  {name.upper():<12} (ERROR: {e})")
    
    print()


def cmd_show_deployment(deployment_name: str):
    """Show detailed configuration for a deployment."""
    try:
        config = get_deployment_config(deployment_name)
        
        print(f"\nDeployment: {config.name.upper()}")
        print("=" * 60)
        print(f"  Host:         {config.tornado_host}")
        print(f"  HTTP Port:    {config.tornado_port}")
        print(f"  ZMQ Port:     {config.zmq_port}")
        print(f"  Database:     {config.database_path}")
        print(f"  Registry:     {config.registry_file}")
        print(f"  PID Dir:      {config.pid_dir}")
        print(f"  Log Level:    {config.log_level}")
        if config.log_file:
            print(f"  Log File:     {config.log_file}")
        print(f"  Auto-reload:  {config.auto_reload}")
        print(f"  Auth:         {'Enabled' if config.enable_auth else 'Disabled'}")
        print()
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_start_server(deployment_name: str = "default", foreground: bool = False):
    """Start a deployment server."""
    script = Path("scripts/start-server.sh")
    
    if not script.exists():
        print(f"Error: {script} not found", file=sys.stderr)
        sys.exit(1)
    
    if foreground:
        # Run in foreground (blocks)
        subprocess.run(["bash", str(script), deployment_name, "--foreground"], check=True)
    else:
        # Run in background
        subprocess.run(["bash", str(script), deployment_name], check=True)


def cmd_stop_server(deployment_name: str = "default"):
    """Stop a deployment server."""
    script = Path("scripts/stop-server.sh")
    
    if not script.exists():
        print(f"Error: {script} not found", file=sys.stderr)
        sys.exit(1)
    
    subprocess.run(["bash", str(script), deployment_name], check=True)


def cmd_restart_server(deployment_name: str = "default"):
    """Restart a deployment server."""
    cmd_stop_server(deployment_name)
    print("Waiting 2 seconds...")
    import time
    time.sleep(2)
    cmd_start_server(deployment_name)


def cmd_create_deployment(name: str):
    """Create a new deployment from template."""
    deployment_dir = Path(f"deployments/{name}")
    
    if deployment_dir.exists():
        print(f"Error: Deployment '{name}' already exists", file=sys.stderr)
        sys.exit(1)
    
    # Create directories
    deployment_dir.mkdir(parents=True)
    (deployment_dir / "pids").mkdir()
    (deployment_dir / "logs").mkdir()
    
    # Create config.yaml from template
    config_content = f"""# ScheduleZero Deployment Configuration: {name}
name: {name}

# Server Configuration
host: 127.0.0.1
http_port: 8888    # Change this to avoid conflicts
zmq_port: 4242     # Change this to avoid conflicts

# Database Configuration
database:
  type: sqlite
  path: deployments/{name}/schedulezero_jobs.db

# Paths
paths:
  pid_dir: deployments/{name}/pids
  log_dir: deployments/{name}/logs
  registry_file: deployments/{name}/handler_registry.yaml

# Logging
logging:
  level: INFO
  file: deployments/{name}/server.log

# Development Options
auto_reload: false

# Security
enable_auth: false
"""
    
    config_file = deployment_dir / "config.yaml"
    config_file.write_text(config_content)
    
    # Create empty registry
    registry_file = deployment_dir / "handler_registry.yaml"
    registry_file.write_text("handlers: []\n")
    
    print(f"✓ Created deployment: {name}")
    print(f"  Config: {config_file}")
    print(f"  Registry: {registry_file}")
    print(f"\nEdit {config_file} to configure ports and other settings.")
    print(f"Then start with: sz-portal start {name}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ScheduleZero Portal Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sz-portal list                    # List all deployments
  sz-portal show production         # Show production config
  sz-portal start                   # Start default deployment
  sz-portal start test              # Start test deployment
  sz-portal stop production         # Stop production deployment
  sz-portal restart default         # Restart default deployment
  sz-portal create staging          # Create new deployment
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # list command
    subparsers.add_parser("list", help="List all available deployments")
    
    # show command
    show_parser = subparsers.add_parser("show", help="Show deployment configuration")
    show_parser.add_argument("deployment", help="Deployment name")
    
    # start command
    start_parser = subparsers.add_parser("start", help="Start a deployment server")
    start_parser.add_argument("deployment", nargs="?", default="default", help="Deployment name (default: default)")
    start_parser.add_argument("-f", "--foreground", action="store_true", help="Run in foreground")
    
    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop a deployment server")
    stop_parser.add_argument("deployment", nargs="?", default="default", help="Deployment name (default: default)")
    
    # restart command
    restart_parser = subparsers.add_parser("restart", help="Restart a deployment server")
    restart_parser.add_argument("deployment", nargs="?", default="default", help="Deployment name (default: default)")
    
    # create command
    create_parser = subparsers.add_parser("create", help="Create a new deployment")
    create_parser.add_argument("name", help="Name for the new deployment")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Dispatch to command handlers
    if args.command == "list":
        cmd_list_deployments()
    elif args.command == "show":
        cmd_show_deployment(args.deployment)
    elif args.command == "start":
        cmd_start_server(args.deployment, args.foreground)
    elif args.command == "stop":
        cmd_stop_server(args.deployment)
    elif args.command == "restart":
        cmd_restart_server(args.deployment)
    elif args.command == "create":
        cmd_create_deployment(args.name)


if __name__ == "__main__":
    main()
