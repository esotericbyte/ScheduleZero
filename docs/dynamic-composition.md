# Dynamic Microsite Composition

## Concept

**Dynamic Composition** allows microsites to be discovered, downloaded, and integrated at runtime without redeploying the portal. This enables:

- 🛒 **Plugin Marketplaces** - Users install microsites from a catalog
- 🏢 **Multi-tenant Customization** - Customers add their own microsites
- 🌐 **Distributed Registries** - Microsites can be hosted anywhere
- 🔌 **Runtime Extensibility** - No redeployment needed

## Architecture

### Traditional Static Composition

```yaml
# portal_config.yaml (static, deployed with portal)
microsites:
  - id: "sz_dash"
    path: "/dash"
    enabled: true
```

Portal reads config at startup, microsites are fixed.

### Dynamic Composition

```yaml
# portal_config.yaml (base configuration)
microsites:
  - id: "sz_dash"
    path: "/dash"
    enabled: true
    
  # Special microsite that can add more microsites
  - id: "sz_marketplace"
    name: "Marketplace"
    path: "/marketplace"
    microsite_type: "htmx"
    capabilities:
      - "microsite:install"    # Can install new microsites
      - "microsite:discover"   # Can query microsite registry
```

**At runtime:**
1. User browses marketplace microsite
2. User clicks "Install LogStream Analytics"
3. Marketplace microsite calls portal API
4. Portal downloads, validates, and activates new microsite
5. Navigation updates automatically (no restart)

## Implementation Layers

### Layer 1: Microsite Registry (Discovery)

**Centralized Registry API:**
```python
# External service or built into portal
class MicrositeRegistry:
    def search(self, query: str) -> List[MicrositeDescriptor]:
        """Search available microsites"""
        
    def get_manifest(self, microsite_id: str) -> MicrositeManifest:
        """Get microsite metadata and installation info"""
        
    def download_package(self, microsite_id: str, version: str) -> bytes:
        """Download microsite package (zip/tar.gz)"""
```

**Microsite Manifest:**
```yaml
# microsite_manifest.yaml (embedded in each microsite package)
manifest_version: "1.0"
microsite:
  id: "logstream_analytics"
  name: "LogStream Analytics"
  version: "2.1.0"
  author: "LogStream Inc."
  license: "MIT"
  
  # What this microsite provides
  type: "htmx"
  icon: "📊"
  path: "/logstream"
  description: "Real-time log analytics and visualization"
  
  # Dependencies
  requires:
    platform_version: ">=1.0.0"
    component_libraries:
      - htmx: ">=1.9.0"
      - web-components: ">=1.0.0"
    microsites:
      - sz_schedules: ">=1.0.0"  # Depends on schedules microsite
  
  # Capabilities this microsite needs
  permissions:
    - "api:schedules:read"
    - "api:handlers:write"
    - "storage:100gb"
  
  # Files in package
  files:
    handlers: "handlers/"
    templates: "templates/"
    static: "static/"
    migrations: "migrations/"
    
  # Configuration schema
  config_schema:
    type: object
    properties:
      retention_days:
        type: integer
        default: 30
      max_log_size_mb:
        type: integer
        default: 100
```

### Layer 2: Portal Framework Support

**Portal API Endpoints:**
```python
# POST /api/portal/microsites/install
class InstallMicrositeHandler(RequestHandler):
    async def post(self):
        manifest = self.get_json_argument('manifest')
        package_url = self.get_json_argument('package_url')
        
        # 1. Validate permissions
        if not self.current_user.has_permission('microsite:install'):
            raise HTTPError(403)
        
        # 2. Download and verify package
        package = await self.download_package(package_url)
        if not self.verify_signature(package, manifest['signature']):
            raise HTTPError(400, "Invalid package signature")
        
        # 3. Check dependencies
        if not self.check_dependencies(manifest['requires']):
            raise HTTPError(400, "Dependency check failed")
        
        # 4. Extract and install
        install_path = f"microsites/{manifest['microsite']['id']}"
        self.extract_package(package, install_path)
        
        # 5. Run migrations
        await self.run_migrations(install_path)
        
        # 6. Update portal config
        self.add_to_config(manifest['microsite'])
        
        # 7. Hot-reload portal (no restart!)
        await self.portal.reload_microsites()
        
        self.write({
            'status': 'installed',
            'microsite_id': manifest['microsite']['id']
        })

# GET /api/portal/microsites/available
class AvailableMicrositesHandler(RequestHandler):
    async def get(self):
        registry_url = self.application.config.get('microsite_registry')
        available = await self.fetch_from_registry(registry_url)
        installed = self.get_installed_microsites()
        
        self.write({
            'available': available,
            'installed': installed
        })

# DELETE /api/portal/microsites/{id}
class UninstallMicrositeHandler(RequestHandler):
    async def delete(self, microsite_id: str):
        # 1. Check if other microsites depend on this
        if self.has_dependents(microsite_id):
            raise HTTPError(400, "Other microsites depend on this")
        
        # 2. Remove from config
        self.remove_from_config(microsite_id)
        
        # 3. Hot-reload
        await self.portal.reload_microsites()
        
        # 4. Optionally keep files for rollback
        self.archive_microsite(microsite_id)
        
        self.write({'status': 'uninstalled'})
```

### Layer 3: Marketplace Microsite

**UI for browsing and installing:**

```html
<!-- templates/marketplace.html -->
<div class="marketplace">
  <h1>Microsite Marketplace</h1>
  
  <!-- Search -->
  <input type="text" 
         hx-get="/marketplace/search" 
         hx-trigger="keyup changed delay:500ms"
         hx-target="#results"
         placeholder="Search microsites...">
  
  <!-- Results -->
  <div id="results">
    {% for microsite in available_microsites %}
    <div class="microsite-card">
      <h3>{{ microsite.icon }} {{ microsite.name }}</h3>
      <p>{{ microsite.description }}</p>
      <span class="version">v{{ microsite.version }}</span>
      
      {% if microsite.id in installed %}
        <button disabled>✓ Installed</button>
      {% else %}
        <button hx-post="/marketplace/install"
                hx-vals='{"microsite_id": "{{ microsite.id }}"}'
                hx-target="this"
                hx-swap="outerHTML">
          Install
        </button>
      {% endif %}
    </div>
    {% endfor %}
  </div>
</div>
```

**Marketplace Handler:**
```python
class MarketplaceHandler(RequestHandler):
    async def get(self):
        # Fetch from registry
        registry = MicrositeRegistry(self.application.config['registry_url'])
        available = await registry.search("")
        installed = self.get_installed_microsite_ids()
        
        self.render('marketplace.html', 
                   available_microsites=available,
                   installed=installed)

class MarketplaceInstallHandler(RequestHandler):
    async def post(self):
        microsite_id = self.get_argument('microsite_id')
        
        # Fetch manifest
        registry = MicrositeRegistry(self.application.config['registry_url'])
        manifest = await registry.get_manifest(microsite_id)
        
        # Call portal install API
        response = await self.http_client.fetch(
            f"{self.portal_url}/api/portal/microsites/install",
            method='POST',
            body=json.dumps({
                'manifest': manifest,
                'package_url': manifest['package_url']
            })
        )
        
        if response.code == 200:
            # Trigger navigation refresh
            self.write("""
                <button disabled class="success">✓ Installed</button>
                <script>
                    // Tell sz-nav to reload config
                    document.querySelector('sz-nav').refresh();
                </script>
            """)
        else:
            self.write(f"""
                <button class="error">Installation Failed</button>
                <div class="error">{response.body}</div>
            """)
```

### Layer 4: Hot-Reload Navigation

**sz-nav component needs refresh capability:**

```typescript
// src/components/sz-nav.ts
class SzNav extends HTMLElement {
  private config?: PortalConfig;
  
  async connectedCallback() {
    await this.loadConfig();
    this.render();
    
    // Listen for microsite changes
    this.listenForChanges();
  }
  
  private listenForChanges() {
    // WebSocket or Server-Sent Events
    const ws = new WebSocket(`ws://${location.host}/api/portal/events`);
    
    ws.addEventListener('message', (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'microsite:installed' || 
          data.type === 'microsite:uninstalled') {
        this.refresh();
      }
    });
  }
  
  public async refresh() {
    await this.loadConfig();
    this.render();
    this.dispatchEvent(new CustomEvent('nav:refreshed', { bubbles: true }));
  }
}
```

## Portal Configuration

**Enable dynamic composition:**

```yaml
# portal_config.yaml
portal:
  name: "ScheduleZero"
  version: "1.0.0"
  
# Dynamic microsite support
dynamic_microsites:
  enabled: true
  registry_url: "https://registry.schedulezero.io"
  # OR for distributed registries:
  registries:
    - url: "https://registry.schedulezero.io"
      name: "Official Registry"
    - url: "https://marketplace.mycompany.com"
      name: "Company Registry"
  
  # Security settings
  allow_unsigned: false  # Require signed packages
  auto_update: false     # Don't auto-update microsites
  
  # Installation limits (multi-tenant)
  max_microsites_per_tenant: 10
  max_storage_per_tenant: "10GB"

# Static microsites (always available)
microsites:
  - id: "sz_dash"
    path: "/dash"
    microsite_type: "htmx"
    
  # Marketplace microsite (has special capabilities)
  - id: "sz_marketplace"
    name: "Marketplace"
    icon: "🛒"
    path: "/marketplace"
    microsite_type: "htmx"
    capabilities:
      - "microsite:install"
      - "microsite:uninstall"
      - "microsite:discover"

# Dynamically installed microsites stored separately
# (managed at runtime, not in this file)
```

## Security Considerations

### 1. Package Signing
```python
# All packages must be signed
def verify_signature(package: bytes, signature: str) -> bool:
    public_key = load_public_key_from_registry()
    return crypto.verify(public_key, package, signature)
```

### 2. Permission System
```yaml
# microsite_manifest.yaml
permissions:
  - "api:schedules:read"      # Read schedules
  - "api:handlers:write"      # Register handlers
  - "storage:100gb"           # Storage quota
  - "network:outbound"        # Make external requests
```

User must approve permissions before installation.

### 3. Sandboxing
```python
# Run microsites in isolated contexts
class MicrositeSandbox:
    def __init__(self, microsite_id: str):
        self.microsite_id = microsite_id
        self.allowed_apis = self.load_permissions(microsite_id)
    
    def check_api_access(self, endpoint: str):
        if not self.has_permission(endpoint):
            raise PermissionDenied(f"{self.microsite_id} cannot access {endpoint}")
```

### 4. Resource Limits
```python
# Enforce resource quotas
class ResourceManager:
    def check_quota(self, tenant_id: str, resource: str, amount: int):
        usage = self.get_current_usage(tenant_id, resource)
        limit = self.get_limit(tenant_id, resource)
        
        if usage + amount > limit:
            raise QuotaExceeded(f"{resource} quota exceeded")
```

## Use Cases

### Use Case 1: Plugin Marketplace

**Official ScheduleZero marketplace:**
```
https://marketplace.schedulezero.io

Available Microsites:
- Grafana Integration    [Install]
- Slack Notifications     [Install]
- Datadog Monitoring      [Install]
- Custom Report Builder   [Install]
```

Users browse and install microsites from web UI.

### Use Case 2: Multi-Tenant SaaS

**LogStream portal (multi-tenant):**
```python
# Each tenant can install custom microsites
tenant_a:
  installed_microsites:
    - core: [sz_dash, sz_schedules]
    - custom: [custom_dashboard, ml_pipeline]
    
tenant_b:
  installed_microsites:
    - core: [sz_dash, sz_schedules]
    - custom: [billing_integration, api_gateway]
```

Tenants get isolated microsite environments.

### Use Case 3: Distributed Development

**Company has internal registry:**
```yaml
registries:
  - url: "https://registry.schedulezero.io"
    name: "Official"
  - url: "https://registry.acmecorp.internal"
    name: "ACME Corp Internal"
```

Teams publish microsites to internal registry, others discover and install.

### Use Case 4: Microsite Can Install Microsites

**Handler Hub microsite installs language-specific handlers:**

```yaml
# handler_hub microsite can install other microsites
- id: "handler_hub"
  name: "Handler Hub"
  capabilities:
    - "microsite:install"  # Can install handler microsites

# User installs "Python Handlers" from Handler Hub
# Handler Hub calls: POST /api/portal/microsites/install
# Portal installs "sz_handlers_python" microsite
```

This creates a **compositional hierarchy**:
```
Portal
  ├─ sz_marketplace (can install microsites)
  │   └─ Installs: handler_hub
  │
  └─ handler_hub (can install handler microsites)
      ├─ Installs: sz_handlers_python
      ├─ Installs: sz_handlers_rust
      └─ Installs: sz_handlers_go
```

## Implementation Roadmap

### Phase 1: Registry & Manifest
- Design microsite manifest schema
- Build microsite registry service
- Package signing infrastructure

### Phase 2: Portal Framework
- Install/uninstall API endpoints
- Hot-reload support (no restart)
- Permission system

### Phase 3: Marketplace Microsite
- Browse available microsites
- Install/uninstall UI
- Dependency resolution

### Phase 4: Advanced Features
- Auto-updates
- Version management
- Rollback support
- Multi-registry federation

## Technical Challenges

### Challenge 1: Route Conflicts
**Problem:** Newly installed microsite might conflict with existing routes

**Solution:** Route validation before installation
```python
def check_route_conflicts(new_microsite):
    existing_routes = self.get_all_routes()
    new_routes = new_microsite.get_routes()
    
    conflicts = set(existing_routes) & set(new_routes)
    if conflicts:
        raise RouteConflictError(f"Routes already exist: {conflicts}")
```

### Challenge 2: Database Migrations
**Problem:** Microsite needs database tables

**Solution:** Include migrations in package, run during installation
```python
def run_migrations(microsite_id: str):
    migration_dir = f"microsites/{microsite_id}/migrations"
    alembic.upgrade(migration_dir, "head")
```

### Challenge 3: Dependency Resolution
**Problem:** Microsite A requires Microsite B

**Solution:** Dependency graph and installation order
```python
def resolve_dependencies(microsite_id: str) -> List[str]:
    manifest = get_manifest(microsite_id)
    deps = manifest['requires']['microsites']
    
    install_order = []
    for dep_id, dep_version in deps.items():
        if not is_installed(dep_id, dep_version):
            install_order.extend(resolve_dependencies(dep_id))
            install_order.append(dep_id)
    
    return install_order
```

### Challenge 4: Hot-Reload
**Problem:** Add microsite without restarting Tornado

**Solution:** Dynamic handler registration
```python
class DynamicApplication(Application):
    def add_microsite(self, microsite: Microsite):
        # Add handlers dynamically
        for route, handler in microsite.get_handlers():
            self.add_handlers(r".*", [(route, handler)])
        
        # Notify connected clients
        self.broadcast_event({
            'type': 'microsite:installed',
            'microsite_id': microsite.id
        })
```

## Benefits

✅ **Extensibility** - Users extend portal without touching code  
✅ **Marketplace Economy** - Third parties can publish microsites  
✅ **Multi-tenancy** - Each tenant customizes their portal  
✅ **Rapid Innovation** - Deploy new features without portal updates  
✅ **Distributed Development** - Teams work independently, integrate seamlessly

This makes ScheduleZero a true **platform** - not just an application! 🚀
