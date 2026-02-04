# Task: Build ScheduleZero Portal Site with Vite + Validation

## Context
You are working in the `schedule-zero-islands` project. Build a complete portal site for ScheduleZero with Vite as the build system, including validation, TypeScript support, and component libraries (HTMX, Web Components).

## Reference Documentation
- `../schedule-zero/docs/SETUP_VITE_VALIDATION.md` - Complete Vite setup guide
- `../schedule-zero/docs/MULTI_PORTAL_ARCHITECTURE.md` - Portal structure examples
- `../schedule-zero/portal_config.yaml` - Configuration defining component libraries

## Current State
The ScheduleZero Python backend expects:
- Portal built to `dist/portal1/`
- Microsites: `sz_dash`, `sz_schedules`, `sz_handlers`, `mkdocs`
- Shared components in `_container/assets/js/components/`
- Component libraries: HTMX, Web Components (custom elements like `<sz-nav>`)

## Task Objectives

### 1. Initialize Vite Project
```bash
npm init -y
npm install -D vite typescript
npm install -D vite-plugin-html-validate html-validate
npm install -D vite-plugin-checker eslint
npm install -D @types/node
```

### 2. Create Project Structure
```
schedule-zero-islands/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   └── portal1/
│       ├── index.html
│       ├── static/
│       │   ├── main.ts
│       │   └── styles.css
│       └── microsites/
│           ├── _container/
│           │   └── assets/js/components/
│           │       └── sz-nav.ts
│           ├── sz_dash/
│           │   ├── templates/
│           │   │   ├── dashboard.html
│           │   │   └── component_test.html
│           │   └── assets/
│           │       ├── dashboard.ts
│           │       └── dashboard.css
│           ├── sz_schedules/
│           │   ├── templates/
│           │   │   └── schedules_list.html
│           │   └── assets/
│           │       ├── schedules.ts
│           │       └── schedules.css
│           ├── sz_handlers/
│           │   ├── templates/
│           │   │   └── handlers_list.html
│           │   └── assets/
│           │       ├── handlers.ts
│           │       └── handlers.css
│           └── mkdocs/
│               ├── templates/
│               │   └── docs_wrapper.html
│               └── assets/
│                   └── docs.css
├── config/
│   └── custom-elements.json
└── dist/
    └── portal1/
```

### 3. Configure TypeScript (tsconfig.json)
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "moduleResolution": "bundler",
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

### 4. Configure Vite (vite.config.ts)
```typescript
import { defineConfig } from 'vite';
import { HtmlValidate } from 'vite-plugin-html-validate';
import checker from 'vite-plugin-checker';
import { resolve } from 'path';
import { readFileSync } from 'fs';
import { load } from 'js-yaml';

// Load component library config from ScheduleZero
const configPath = resolve(__dirname, '../schedule-zero/portal_config.yaml');
let componentLibraries: string[] = [];

try {
  const config = load(readFileSync(configPath, 'utf8')) as any;
  componentLibraries = config.component_library || [];
} catch (e) {
  console.warn('Could not load portal_config.yaml, using defaults');
  componentLibraries = ['htmx', 'web-components'];
}

// Build ignore patterns for HTML validation
const ignorePatterns: string[] = [];
if (componentLibraries.includes('htmx')) {
  ignorePatterns.push('hx-*');
}
if (componentLibraries.includes('web-components')) {
  ignorePatterns.push('sz-*', '*-*');
}
if (componentLibraries.includes('vue')) {
  ignorePatterns.push('v-*', 'v:*');
}

export default defineConfig({
  root: './src',
  
  plugins: [
    HtmlValidate({
      config: {
        extends: ['html-validate:recommended'],
        elements: [
          'html-validate:standard',
          '../config/custom-elements.json'
        ],
        rules: {
          'no-unknown-elements': ignorePatterns.length > 0 
            ? ['error', { ignore: ignorePatterns }]
            : 'error',
          'no-implicit-close': 'off',
          'element-required-content': 'off',
          'require-sri': 'off'
        }
      }
    }),
    
    checker({
      typescript: true,
      eslint: {
        lintCommand: 'eslint src --ext .ts,.js'
      }
    })
  ],
  
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    
    rollupOptions: {
      input: {
        'portal1': resolve(__dirname, 'src/portal1/index.html'),
        'main': resolve(__dirname, 'src/portal1/static/main.ts'),
        'sz-nav': resolve(__dirname, 'src/portal1/microsites/_container/assets/js/components/sz-nav.ts'),
        'dashboard': resolve(__dirname, 'src/portal1/microsites/sz_dash/assets/dashboard.ts'),
        'schedules': resolve(__dirname, 'src/portal1/microsites/sz_schedules/assets/schedules.ts'),
        'handlers': resolve(__dirname, 'src/portal1/microsites/sz_handlers/assets/handlers.ts'),
        'docs': resolve(__dirname, 'src/portal1/microsites/mkdocs/assets/docs.ts'),
      },
      
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/chunks/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
        
        manualChunks(id) {
          if (id.includes('node_modules')) {
            return 'vendor';
          }
          if (id.includes('_container')) {
            return 'shared';
          }
        }
      }
    },
    
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
      }
    }
  },
  
  server: {
    port: 3000,
    open: false,
    cors: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8888',
        changeOrigin: true,
      }
    }
  }
});
```

### 5. Define Custom Elements (config/custom-elements.json)
```json
{
  "sz-nav": {
    "attributes": ["current-page", "class"],
    "void": false
  },
  "sz-handler-card": {
    "attributes": ["handler-id", "status", "class"],
    "void": false
  },
  "sz-schedule-list": {
    "attributes": ["filter", "sort", "class"],
    "void": false
  },
  "sz-execution-log": {
    "attributes": ["max-items", "class"],
    "void": false
  }
}
```

### 6. Create Package Scripts (package.json)
```json
{
  "name": "schedule-zero-islands",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build && npm run check-output",
    "preview": "vite preview",
    "check-output": "node scripts/validate-output.js",
    "sync": "node scripts/sync-to-python.js",
    "clean": "rimraf dist"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "typescript": "^5.3.0",
    "vite-plugin-html-validate": "^1.0.0",
    "html-validate": "^8.0.0",
    "vite-plugin-checker": "^0.6.0",
    "eslint": "^8.0.0",
    "@types/node": "^20.0.0",
    "js-yaml": "^4.1.0",
    "rimraf": "^5.0.0"
  }
}
```

### 7. Create Validation Script (scripts/validate-output.js)
```javascript
import { existsSync, readdirSync, statSync } from 'fs';
import { join } from 'path';

const DIST_DIR = '../dist/portal1';
const REQUIRED_DIRS = ['static', 'microsites'];
const REQUIRED_FILES = ['index.html'];

console.log('\n🔍 Validating build output...\n');

const errors = [];
const warnings = [];

// Check dist directory exists
if (!existsSync(DIST_DIR)) {
  errors.push(`❌ dist/portal1/ does not exist`);
  console.log(errors.join('\n'));
  process.exit(1);
}

// Check required directories
REQUIRED_DIRS.forEach(dir => {
  const path = join(DIST_DIR, dir);
  if (!existsSync(path)) {
    errors.push(`❌ Missing required directory: ${dir}`);
  } else {
    console.log(`✓ ${dir}/`);
  }
});

// Check required files
REQUIRED_FILES.forEach(file => {
  const path = join(DIST_DIR, file);
  if (!existsSync(path)) {
    errors.push(`❌ Missing required file: ${file}`);
  } else {
    console.log(`✓ ${file}`);
  }
});

// Check for asset hashing
const staticPath = join(DIST_DIR, 'static', 'assets');
if (existsSync(staticPath)) {
  const assets = readdirSync(staticPath);
  const hashedAssets = assets.filter(f => /-[a-f0-9]{8}\.(js|css)$/.test(f));
  
  if (hashedAssets.length === 0) {
    warnings.push(`⚠️  No hashed assets found (cache busting may not work)`);
  } else {
    console.log(`✓ ${hashedAssets.length} hashed assets`);
  }
}

// Check microsite structure
const micrositesPath = join(DIST_DIR, 'microsites');
if (existsSync(micrositesPath)) {
  const microsites = readdirSync(micrositesPath).filter(f => 
    statSync(join(micrositesPath, f)).isDirectory()
  );
  
  console.log(`✓ ${microsites.length} microsites: ${microsites.join(', ')}`);
  
  microsites.forEach(ms => {
    const templatesPath = join(micrositesPath, ms, 'templates');
    const assetsPath = join(micrositesPath, ms, 'assets');
    
    if (!existsSync(templatesPath)) {
      warnings.push(`⚠️  ${ms}: Missing templates/ directory`);
    }
    
    if (!existsSync(assetsPath)) {
      warnings.push(`⚠️  ${ms}: Missing assets/ directory`);
    }
  });
}

console.log('\n');

// Output results
if (errors.length > 0) {
  console.log('❌ Validation failed:\n');
  errors.forEach(e => console.log(e));
  process.exit(1);
}

if (warnings.length > 0) {
  console.log('⚠️  Warnings:\n');
  warnings.forEach(w => console.log(w));
  console.log('\n');
}

console.log('✅ Build output validation passed!\n');
```

### 8. Expected Output

After running `npm run build && npm run check-output`:

**If clean:**
```
🔍 Validating build output...

✓ static/
✓ microsites/
✓ index.html
✓ 15 hashed assets
✓ 4 microsites: sz_dash, sz_schedules, sz_handlers, mkdocs

✅ Build output validation passed!
```

**If issues found:**
```
🔍 Validating build output...

✓ static/
✓ microsites/
✓ index.html
⚠️  sz_handlers: Missing templates/ directory
⚠️  No hashed assets found (cache busting may not work)

⚠️  Warnings:

⚠️  sz_handlers: Missing templates/ directory
⚠️  No hashed assets found (cache busting may not work)

# TODO List:
- [ ] Create sz_handlers/templates/ directory
- [ ] Configure Vite asset hashing (check vite.config.ts output settings)
```

## Success Criteria

✅ `npm run build` completes without errors  
✅ HTML validation passes (no unknown elements for HTMX/Web Components)  
✅ TypeScript compilation succeeds  
✅ All microsites have templates/ and assets/  
✅ Assets are hashed for cache busting  
✅ Shared components in _container/ are tree-shaken properly  
✅ Output in `dist/portal1/` matches expected structure  
✅ Validation script reports "clean" or provides TODO list  

## Integration with Python Backend

After build:
```bash
npm run sync  # Copies dist/ → schedule-zero/src/schedule_zero/
```

Python server configuration (`portal_config.yaml`):
```yaml
portal_root: "../schedule-zero-islands/dist/portal1"
component_library:
  - htmx
  - web-components
```

## Development Workflow

```bash
# Terminal 1: Vite dev server (hot reload)
npm run dev

# Terminal 2: Python backend (API)
cd ../schedule-zero
poetry run python -m schedule_zero.server

# Visit http://localhost:3000 (Vite proxies /api to :8888)
```

## Notes

- **HTMX attributes** (`hx-get`, `hx-post`, etc.) must not trigger validation errors
- **Custom elements** (`<sz-nav>`, `<sz-*>`) must be defined in `custom-elements.json`
- **Tornado templates** (`{% block %}`, `{{ var }}`) are preserved in HTML
- **MkDocs content** is NOT built by Vite (separate `mkdocs build`)
- **Asset paths** in templates updated automatically by Vite
- **Validation output** should be actionable (clean or TODO list)

## Questions to Answer in Implementation

1. Are all microsites present with templates/ and assets/?
2. Are custom elements properly defined and validated?
3. Are assets hashed and optimized?
4. Does the dev server proxy API calls correctly?
5. Can the validation script output a TODO list of missing items?
6. Does `npm run sync` successfully copy to Python project?

Output either:
- **"CLEAN"** if everything validates
- **TODO list** of specific items that need to be created/fixed
