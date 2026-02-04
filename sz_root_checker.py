#!/usr/bin/env python3
"""
ScheduleZero Site Root Checker

⚠️  NOTE: This Python validator is currently ON HOLD.
Frontend validation is now primarily handled by Vite in schedule-zero-islands:
- html-validate for HTML/custom elements
- TypeScript for type checking  
- ESLint for JavaScript
- See docs/VITE_BUILD_TASK.md for primary validation approach

This tool may be useful as:
- A sanity check layer between schedule-zero-islands and schedule-zero
- Quick validation without running full Vite build
- CI/CD pre-flight checks

DO NOT CO-DEVELOP unless it proves clearly useful vs redundant.

Validates a ScheduleZero site root directory containing portal and microsites.
Checks HTML, CSS, JavaScript syntax and microsite API conformance.

Usage:
    poetry run python sz_root_checker.py <site_root_path>
    poetry run python sz_root_checker.py --default  # Check built-in site root
"""

import argparse
import sys
from pathlib import Path
import json
import importlib.util
import re
import yaml

# Try to import validation libraries (optional dependencies)
try:
    import html5lib
    HAS_HTML5LIB = True
except ImportError:
    HAS_HTML5LIB = False
    print("⚠️  html5lib not installed - HTML validation will be limited")
    print("   Install with: pip install html5lib")

try:
    import cssutils
    cssutils.log.setLevel(logging.CRITICAL)  # Suppress warnings
    HAS_CSSUTILS = True
except ImportError:
    HAS_CSSUTILS = False
    print("⚠️  cssutils not installed - CSS validation will be limited")
    print("   Install with: pip install cssutils")

# JavaScript validation is complex - we'll do basic syntax checking
import logging


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class ValidationError:
    """Represents a validation error."""
    def __init__(self, severity, category, file, message, line=None):
        self.severity = severity  # 'error', 'warning', 'info'
        self.category = category  # 'html', 'css', 'js', 'structure', 'api'
        self.file = file
        self.message = message
        self.line = line

    def __str__(self):
        color = Colors.RED if self.severity == 'error' else Colors.YELLOW if self.severity == 'warning' else Colors.BLUE
        location = f":{self.line}" if self.line else ""
        return f"{color}[{self.severity.upper()}]{Colors.RESET} {self.category} | {self.file}{location}\n  {self.message}"


class SiteRootChecker:
    """Validates a ScheduleZero site root directory."""
    
    def __init__(self, site_root: Path, component_library=None):
        self.site_root = Path(site_root)
        self.errors = []
        self.warnings = []
        self.info = []
        self.component_library = component_library or []
        self.known_custom_elements = self._build_known_elements()
        
    def add_error(self, category, file, message, line=None):
        """Add an error."""
        self.errors.append(ValidationError('error', category, file, message, line))
        
    def add_warning(self, category, file, message, line=None):
        """Add a warning."""
        self.warnings.append(ValidationError('warning', category, file, message, line))
        
    def add_info(self, category, file, message, line=None):
        """Add an info message."""
        self.info.append(ValidationError('info', category, file, message, line))
    
    def _build_known_elements(self):
        """Build list of known custom elements based on component_library config."""
        known = set()
        
        if 'htmx' in self.component_library:
            # HTMX custom elements and attributes
            known.update(['hx-get', 'hx-post', 'hx-put', 'hx-delete', 'hx-patch',
                         'hx-swap', 'hx-target', 'hx-trigger', 'hx-boost', 'hx-select',
                         'hx-indicator', 'hx-push-url', 'hx-confirm'])
        
        if 'web-components' in self.component_library:
            # Web components use hyphens: <sz-nav>, <my-component>
            # We'll check for hyphenated tags in HTML validation
            known.add('web-components')
        
        if 'vue' in self.component_library:
            # Vue directives and components
            known.update(['v-if', 'v-for', 'v-show', 'v-model', 'v-bind', 'v-on',
                         'v-html', 'v-text', 'v-pre', 'v-cloak', 'v-once'])
        
        return known
    
    def _is_known_custom_element(self, tag):
        """Check if tag is a known custom element."""
        # Web components always have hyphens
        if 'web-components' in self.component_library and '-' in tag:
            return True
        
        # HTMX elements
        if 'htmx' in self.component_library and tag.startswith('hx-'):
            return True
        
        # Vue components
        if 'vue' in self.component_library and (tag.startswith('v-') or '-' in tag):
            return True
        
        return False
    
    def validate(self):
        """Run all validations."""
        print(f"\n{Colors.BOLD}🔍 ScheduleZero Site Root Checker{Colors.RESET}")
        print(f"{'='*60}\n")
        print(f"Checking: {Colors.BLUE}{self.site_root}{Colors.RESET}\n")
        
        # Check site root exists
        if not self.site_root.exists():
            self.add_error('structure', str(self.site_root), "Site root directory does not exist")
            return self.report()
        
        # Validate structure
        self.validate_structure()
        
        # Validate portal
        portal_path = self.site_root / 'portal'
        if portal_path.exists():
            print(f"\n{Colors.BOLD}📄 Validating Portal{Colors.RESET}")
            self.validate_portal(portal_path)
        
        # Validate microsites
        microsites_path = self.site_root / 'microsites'
        if microsites_path.exists():
            print(f"\n{Colors.BOLD}🏠 Validating Microsites{Colors.RESET}")
            self.validate_microsites(microsites_path)
        
        # Report results
        return self.report()
    
    def validate_structure(self):
        """Validate basic directory structure."""
        print(f"{Colors.BOLD}📁 Validating Structure{Colors.RESET}")
        
        required_dirs = ['portal', 'microsites']
        for dir_name in required_dirs:
            dir_path = self.site_root / dir_name
            if not dir_path.exists():
                self.add_error('structure', dir_name, f"Required directory '{dir_name}' not found")
            else:
                print(f"  ✓ {dir_name}/")
    
    def validate_portal(self, portal_path: Path):
        """Validate portal directory."""
        # Check for index.html
        index_html = portal_path / 'index.html'
        if not index_html.exists():
            self.add_error('structure', 'portal/index.html', "Required index.html not found")
        else:
            print(f"  ✓ index.html")
            self.validate_html(index_html)
        
        # Check for static assets
        static_path = portal_path / 'static'
        if static_path.exists():
            print(f"  ✓ static/")
            self.validate_static_assets(static_path, 'portal/static')
        else:
            self.add_warning('structure', 'portal/static', "static/ directory not found")
    
    def validate_microsites(self, microsites_path: Path):
        """Validate all microsites."""
        # Check for _container
        container_path = microsites_path / '_container'
        if not container_path.exists():
            self.add_error('structure', 'microsites/_container', "Required _container microsite not found")
        else:
            print(f"  ✓ _container/ (shared components)")
            self.validate_container(container_path)
        
        # Find all microsites (directories starting with sz_ or special ones)
        for microsite_dir in microsites_path.iterdir():
            if microsite_dir.is_dir() and (microsite_dir.name.startswith('sz_') or microsite_dir.name in ['mkdocs', '_container']):
                if microsite_dir.name != '_container':
                    print(f"\n  📦 {microsite_dir.name}")
                    self.validate_microsite(microsite_dir)
    
    def validate_container(self, container_path: Path):
        """Validate _container shared components."""
        # Check for assets
        assets_path = container_path / 'assets'
        if not assets_path.exists():
            self.add_warning('structure', '_container/assets', "assets/ directory not found")
        else:
            # Check for key shared assets
            expected_files = [
                'assets/js/htmx.min.js',
                'assets/js/components/sz-nav.js',
            ]
            for rel_path in expected_files:
                file_path = container_path / rel_path
                if not file_path.exists():
                    self.add_warning('structure', f'_container/{rel_path}', f"Expected shared file not found")
                else:
                    print(f"    ✓ {rel_path}")
    
    def validate_microsite(self, microsite_path: Path):
        """Validate individual microsite structure and API."""
        microsite_name = microsite_path.name
        
        # Check for routes.py
        routes_file = microsite_path / 'routes.py'
        if not routes_file.exists():
            self.add_error('api', f'{microsite_name}/routes.py', "Required routes.py not found")
        else:
            print(f"    ✓ routes.py")
            self.validate_routes_file(routes_file, microsite_name)
        
        # Check for templates/
        templates_path = microsite_path / 'templates'
        if templates_path.exists():
            print(f"    ✓ templates/")
            self.validate_templates(templates_path, microsite_name)
        else:
            self.add_warning('structure', f'{microsite_name}/templates', "templates/ directory not found")
        
        # Check for assets/
        assets_path = microsite_path / 'assets'
        if assets_path.exists():
            print(f"    ✓ assets/")
            self.validate_static_assets(assets_path, f'{microsite_name}/assets')
        else:
            self.add_info('structure', f'{microsite_name}/assets', "assets/ directory not found (optional)")
    
    def validate_routes_file(self, routes_file: Path, microsite_name: str):
        """Validate routes.py microsite API conformance."""
        try:
            content = routes_file.read_text(encoding='utf-8')
            
            # Check for required exports
            if 'routes = [' not in content:
                self.add_error('api', f'{microsite_name}/routes.py', "Missing 'routes' list definition")
            else:
                print(f"      ✓ exports 'routes' list")
            
            # Check for tornado imports
            if 'import tornado.web' not in content and 'from tornado' not in content:
                self.add_warning('api', f'{microsite_name}/routes.py', "No tornado imports found")
            
            # Check for handler classes (should have RequestHandler base)
            handler_pattern = r'class\s+(\w+)\(.*RequestHandler.*\):'
            handlers = re.findall(handler_pattern, content)
            if handlers:
                print(f"      ✓ defines {len(handlers)} handler(s): {', '.join(handlers)}")
            else:
                self.add_warning('api', f'{microsite_name}/routes.py', "No RequestHandler classes found")
            
        except Exception as e:
            self.add_error('api', f'{microsite_name}/routes.py', f"Failed to read/parse: {e}")
    
    def validate_templates(self, templates_path: Path, microsite_name: str):
        """Validate HTML templates."""
        html_files = list(templates_path.glob('*.html'))
        
        if not html_files:
            self.add_warning('structure', f'{microsite_name}/templates', "No HTML templates found")
            return
        
        for html_file in html_files:
            rel_path = html_file.relative_to(templates_path)
            self.validate_html(html_file, f'{microsite_name}/templates/{rel_path}')
    
    def validate_html(self, html_file: Path, display_path: str = None):
        """Validate HTML file syntax."""
        display_path = display_path or str(html_file.relative_to(self.site_root))
        
        try:
            content = html_file.read_text(encoding='utf-8')
            
            # Basic checks
            if not content.strip():
                self.add_error('html', display_path, "File is empty")
                return
            
            # Check for basic HTML structure
            if '<!DOCTYPE html>' not in content and '<!doctype html>' not in content:
                self.add_warning('html', display_path, "Missing DOCTYPE declaration")
            
            if '<html' not in content:
                self.add_warning('html', display_path, "Missing <html> tag")
            
            # Use html5lib if available
            if HAS_HTML5LIB:
                try:
                    html5lib.parse(content, treebuilder='etree')
                    print(f"      ✓ {display_path} (valid HTML5)")
                except Exception as e:
                    self.add_error('html', display_path, f"HTML5 validation failed: {e}")
            else:
                # Basic tag matching (include hyphens for custom elements)
                open_tags = re.findall(r'<([\w-]+)[^>]*>', content)
                close_tags = re.findall(r'</([\w-]+)>', content)
                
                # Check for obviously mismatched tags
                self_closing = ['meta', 'link', 'img', 'br', 'hr', 'input']
                open_count = {tag: open_tags.count(tag) for tag in set(open_tags) if tag not in self_closing}
                close_count = {tag: close_tags.count(tag) for tag in set(close_tags)}
                
                for tag, count in open_count.items():
                    if close_count.get(tag, 0) != count:
                        # Skip warning if it's a known custom element
                        if not self._is_known_custom_element(tag):
                            self.add_warning('html', display_path, f"Possibly mismatched <{tag}> tags")
                
        except UnicodeDecodeError:
            self.add_error('html', display_path, "File encoding error (not UTF-8)")
        except Exception as e:
            self.add_error('html', display_path, f"Failed to read: {e}")
    
    def validate_static_assets(self, assets_path: Path, display_prefix: str):
        """Validate static assets (CSS, JS)."""
        # Find CSS files
        css_files = list(assets_path.rglob('*.css'))
        for css_file in css_files:
            rel_path = css_file.relative_to(assets_path)
            self.validate_css(css_file, f'{display_prefix}/{rel_path}')
        
        # Find JS files
        js_files = list(assets_path.rglob('*.js'))
        for js_file in js_files:
            if js_file.name.endswith('.min.js'):
                continue  # Skip minified files
            rel_path = js_file.relative_to(assets_path)
            self.validate_js(js_file, f'{display_prefix}/{rel_path}')
    
    def validate_css(self, css_file: Path, display_path: str):
        """Validate CSS file syntax."""
        try:
            content = css_file.read_text(encoding='utf-8')
            
            if not content.strip():
                self.add_warning('css', display_path, "File is empty")
                return
            
            if HAS_CSSUTILS:
                try:
                    cssutils.parseString(content)
                    print(f"      ✓ {display_path} (valid CSS)")
                except Exception as e:
                    self.add_error('css', display_path, f"CSS validation failed: {e}")
            else:
                # Basic brace matching
                open_braces = content.count('{')
                close_braces = content.count('}')
                if open_braces != close_braces:
                    self.add_error('css', display_path, f"Mismatched braces: {open_braces} open, {close_braces} close")
                
        except UnicodeDecodeError:
            self.add_error('css', display_path, "File encoding error (not UTF-8)")
        except Exception as e:
            self.add_error('css', display_path, f"Failed to read: {e}")
    
    def validate_js(self, js_file: Path, display_path: str):
        """Validate JavaScript file syntax."""
        try:
            content = js_file.read_text(encoding='utf-8')
            
            if not content.strip():
                self.add_warning('js', display_path, "File is empty")
                return
            
            # Basic syntax checks
            open_braces = content.count('{')
            close_braces = content.count('}')
            if open_braces != close_braces:
                self.add_error('js', display_path, f"Mismatched braces: {open_braces} open, {close_braces} close")
            
            open_parens = content.count('(')
            close_parens = content.count(')')
            if open_parens != close_parens:
                self.add_error('js', display_path, f"Mismatched parentheses: {open_parens} open, {close_parens} close")
            
            # Check for common syntax errors
            if re.search(r'\bfunction\s+\w+\s*\([^)]*\)\s*{', content):
                print(f"      ✓ {display_path} (basic JS syntax)")
            
        except UnicodeDecodeError:
            self.add_error('js', display_path, "File encoding error (not UTF-8)")
        except Exception as e:
            self.add_error('js', display_path, f"Failed to read: {e}")
    
    def report(self):
        """Print validation report and return exit code."""
        print(f"\n{'='*60}")
        print(f"{Colors.BOLD}📊 Validation Report{Colors.RESET}")
        print(f"{'='*60}\n")
        
        # Print all issues
        for error in self.errors:
            print(error)
        
        for warning in self.warnings:
            print(warning)
        
        if self.info:
            print(f"\n{Colors.BLUE}ℹ️  Information:{Colors.RESET}")
            for info in self.info:
                print(f"  {info.file}: {info.message}")
        
        # Summary
        print(f"\n{'='*60}")
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        
        if error_count == 0 and warning_count == 0:
            print(f"{Colors.GREEN}✅ All checks passed!{Colors.RESET}")
            print(f"\nSite root is valid and ready for use.")
            return 0
        elif error_count == 0:
            print(f"{Colors.YELLOW}⚠️  Validation completed with {warning_count} warning(s){Colors.RESET}")
            print(f"\nSite root is usable but has warnings.")
            return 0
        else:
            print(f"{Colors.RED}❌ Validation failed with {error_count} error(s) and {warning_count} warning(s){Colors.RESET}")
            print(f"\nFix errors before using this site root.")
            return 1


def get_default_site_root():
    """Get the built-in site root path."""
    # Assuming this script is in the project root
    project_root = Path(__file__).parent
    return project_root / 'src' / 'schedule_zero'


def load_portal_config():
    """Load portal_config.yaml to get component_library settings."""
    config_path = Path('portal_config.yaml')
    if not config_path.exists():
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config.get('component_library', [])
    except Exception as e:
        print(f"⚠️  Could not load portal_config.yaml: {e}")
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Validate ScheduleZero site root directory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Check built-in site root
  poetry run python sz_root_checker.py --default

  # Check custom site root
  poetry run python sz_root_checker.py /path/to/custom/site

  # Check with detailed output
  poetry run python sz_root_checker.py /path/to/site --verbose
'''
    )
    parser.add_argument('site_root', nargs='?', help='Path to site root directory')
    parser.add_argument('--default', action='store_true', help='Check built-in site root')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Determine site root
    if args.default:
        site_root = get_default_site_root()
        print(f"Using built-in site root: {site_root}")
    elif args.site_root:
        site_root = Path(args.site_root)
    else:
        parser.print_help()
        return 1
    
    # Load component library config
    component_library = load_portal_config()
    if component_library:
        print(f"📋 Component libraries: {', '.join(component_library)}")
        print(f"   (Custom elements from these libraries will not trigger warnings)\n")
    
    # Run validation
    checker = SiteRootChecker(site_root, component_library=component_library)
    return checker.validate()


if __name__ == '__main__':
    sys.exit(main())
