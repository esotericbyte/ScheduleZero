# Documentation Organization Guide

## Using Frontmatter Tags

All documentation uses YAML frontmatter for metadata and organization.

### Basic Format

```markdown
---
title: Document Title
tags:
  - tag1
  - tag2
status: active
---

# Document Content

Your markdown here...
```

### Standard Tag Taxonomies

**Content Type Tags:**
- `specification` - Technical specs and API docs
- `user-guide` - How-to guides and tutorials
- `user-docs` - Reference documentation
- `exploration` - Research and analysis documents
- `planning` - Roadmaps and decision documents

**Topic Tags:**
- `api` - REST API documentation
- `deployment` - Deployment and operations
- `architecture` - System architecture and design
- `orchestration` - Handler orchestration
- `testing` - Test documentation

**Status Tags:**
- `active` - Current, maintained documentation
- `complete` - Finished and stable
- `draft` - Work in progress
- `exploration` - Exploratory analysis
- `archived` - Historical, no longer maintained

### Example Documents

**API Documentation:**
```markdown
---
title: Job Execution Logging API
tags:
  - api
  - specification
  - user-docs
status: complete
---
```

**Exploration Document:**
```markdown
---
title: ConductorZero Architecture
tags:
  - exploration
  - architecture
  - orchestration
status: exploration
date: 2025-11-10
---
```

**User Guide:**
```markdown
---
title: Deployment Guide
tags:
  - deployment
  - user-guide
  - production
status: complete
---
```

### Finding Documents by Tag

**In MkDocs site:**
- Visit `/tags` page for auto-generated tag index
- Click any tag to see all documents with that tag
- Tags appear at top of each document

**In Repository:**
```bash
# Find all documents with "api" tag
grep -r "tags:" docs/*.md | grep "api"

# Find exploration documents
grep -r "status: exploration" docs/*.md
```

### Adding Tags to New Documents

1. Create markdown file in `docs/`
2. Add frontmatter at the very top:
```markdown
---
title: My New Document
tags:
  - relevant-tag
  - another-tag
status: active
---

# Document starts here
```
3. Build docs: `python build_docs.py`
4. Tags will auto-appear in tag index

### Best Practices

- **Use multiple tags** - Documents can have many tags from different taxonomies
- **Keep tag names lowercase** - Consistent naming convention
- **Add dates to exploration docs** - `date: 2025-11-10`
- **Update status** - Change `draft` → `active` → `complete` as appropriate
- **Don't duplicate info** - Let tags describe the document, not the title

### Tag Combinations

Good examples:
- `[api, specification, user-docs]` - API reference doc
- `[deployment, user-guide, production]` - Production deployment guide
- `[exploration, architecture, planning]` - Design exploration
- `[testing, specification, active]` - Test suite documentation

Avoid:
- Too few tags (< 2) - harder to discover
- Too many tags (> 6) - dilutes meaning
- Redundant tags - Don't use both `api` and `api-docs`
