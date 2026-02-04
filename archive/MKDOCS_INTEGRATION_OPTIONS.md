# MkDocs Integration Options

ScheduleZero provides two ways to integrate MkDocs documentation:

## Current: External Link (Recommended) ✅

**File:** `microsites/mkdocs/routes.py`
**Navigation:** Opens in new tab with ↗ indicator

### Pros:
- ✅ MkDocs keeps its own navigation, search, and theme
- ✅ Cleaner separation of concerns (docs vs app)
- ✅ Users expect documentation to open separately
- ✅ No iframe complexity or security concerns
- ✅ Full MkDocs features (search, copy code, etc.)

### Cons:
- ❌ Opens in new tab (but this is actually preferred UX for docs)

### Current Implementation:
```html
<!-- In layout.html -->
<nav-item href="/docs/" icon="📖" name="docs" target="_blank">Docs ↗</nav-item>
```

Docs accessible at: `http://localhost:8888/docs/`

---

## Alternative: Integrated (iframe wrapper)

**File:** `microsites/mkdocs/routes_integrated.py`
**Navigation:** Embedded within SZ container

### Pros:
- ✅ Shows ScheduleZero navigation sidebar
- ✅ No new tab required
- ✅ Feels more "integrated"

### Cons:
- ❌ Iframe complexity (CORS, height management, etc.)
- ❌ MkDocs navigation conflicts with SZ navigation
- ❌ Some MkDocs features may not work properly in iframe
- ❌ Worse user experience for documentation

### To Switch to Integrated:

1. **Update tornado_app_server.py:**
```python
# Change from:
from .microsites import mkdocs

# To:
from .microsites.mkdocs import routes_integrated as mkdocs

# Also add content route:
app.add_handlers(".*$", [
    (r"/docs-content/(.*)", mkdocs.DocsContentHandler)
])
```

2. **Update layout.html:**
```html
<!-- Remove target="_blank" -->
<nav-item href="/docs/" icon="📖" name="docs">Docs</nav-item>
```

3. **Restart server**

---

## Recommendation

**Keep the current external link approach** because:

1. Documentation is a reference resource, not an application feature
2. Users commonly keep docs open while working in the app
3. MkDocs Material theme is highly polished - let it shine
4. Avoids iframe complexity and security concerns
5. Industry standard (GitHub, GitLab, etc. all open docs in new tabs)

The "↗" symbol clearly indicates it's an external link, which sets proper expectations.

---

## Future Enhancement: Docs Search API

If you want deeper integration, consider building a docs search API that queries the MkDocs search index and shows results in the ScheduleZero UI. This gives you:

- Contextual help search within the app
- Link to specific doc pages
- No iframe complexity
- Best of both worlds

This could be implemented as a `<sz-search>` Web Component in the nav bar.
