#!/usr/bin/env python3
"""
Sync JavaScript Islands from schedulezero-islands to Python repo.

Copies built JavaScript components from the islands repo to the microsites
assets directories.
"""
import sys
import shutil
import subprocess
from pathlib import Path
import argparse


def print_step(msg):
    print(f"\033[36m➜ {msg}\033[0m")


def print_success(msg):
    print(f"\033[32m✓ {msg}\033[0m")


def print_error(msg):
    print(f"\033[31m✗ {msg}\033[0m", file=sys.stderr)


def print_warning(msg):
    print(f"\033[33m⚠ {msg}\033[0m")


def sync_islands(build=False, force=False):
    """Sync islands from islands repo to Python package."""
    
    # Paths
    root_dir = Path(__file__).parent.parent
    islands_repo = root_dir.parent / "schedulezero-islands"
    dist_dir = islands_repo / "dist"
    microsites_dir = root_dir / "src" / "schedule_zero" / "microsites"
    
    # Check if islands repo exists
    if not islands_repo.exists():
        print_error(f"Islands repo not found at: {islands_repo}")
        print(f"Expected path: {root_dir.parent / 'schedulezero-islands'}")
        return 1
    
    # Build if requested
    if build:
        print_step("Building islands project...")
        try:
            result = subprocess.run(
                ["pnpm", "run", "build"],
                cwd=islands_repo,
                check=True,
                capture_output=True,
                text=True
            )
            print_success("Build completed")
        except subprocess.CalledProcessError as e:
            print_error("Build failed")
            print(e.stderr)
            return 1
        except FileNotFoundError:
            print_error("pnpm not found. Install Node.js and pnpm first.")
            return 1
    
    # Check if dist directory exists
    if not dist_dir.exists():
        print_error(f"Distribution directory not found: {dist_dir}")
        print("Run with --build to build the islands project first")
        return 1
    
    # Map of source to destination
    sync_map = {
        # Container components (shared)
        dist_dir / "components" / "sz-nav.min.js": 
            microsites_dir / "_container" / "assets" / "js" / "components",
        
        # Dashboard components
        dist_dir / "components" / "vanilla" / "connection-status.min.js":
            microsites_dir / "sz_dash" / "assets" / "js" / "components" / "vanilla",
        dist_dir / "components" / "vanilla" / "copy-button.min.js":
            microsites_dir / "sz_dash" / "assets" / "js" / "components" / "vanilla",
        dist_dir / "components" / "vanilla" / "sz-flash.min.js":
            microsites_dir / "sz_dash" / "assets" / "js" / "components" / "vanilla",
        
        dist_dir / "components" / "vuetify" / "handler-grid.min.js":
            microsites_dir / "sz_dash" / "assets" / "js" / "components" / "vuetify",
        dist_dir / "components" / "vuetify" / "schedule-grid.min.js":
            microsites_dir / "sz_dash" / "assets" / "js" / "components" / "vuetify",
        dist_dir / "components" / "vuetify" / "schedule-form.min.js":
            microsites_dir / "sz_dash" / "assets" / "js" / "components" / "vuetify",
        dist_dir / "components" / "vuetify" / "execution-log-grid.min.js":
            microsites_dir / "sz_dash" / "assets" / "js" / "components" / "vuetify",
    }
    
    # Perform sync
    copied = 0
    skipped = 0
    errors = 0
    
    print_step("Syncing islands...")
    
    for src, dest_dir in sync_map.items():
        if not src.exists():
            print_warning(f"Source not found: {src.name}")
            skipped += 1
            continue
        
        # Create destination directory
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / src.name
        
        # Check if file has changed
        if dest_file.exists() and not force:
            src_mtime = src.stat().st_mtime
            dest_mtime = dest_file.stat().st_mtime
            
            if src_mtime <= dest_mtime:
                print(f"  → {src.name} (unchanged)")
                skipped += 1
                continue
        
        # Copy file
        try:
            shutil.copy2(src, dest_file)
            print(f"  ✓ {src.name} → {dest_dir.relative_to(root_dir)}")
            copied += 1
        except Exception as e:
            print_error(f"Failed to copy {src.name}: {e}")
            errors += 1
    
    # Summary
    print()
    print_success(f"Sync complete: {copied} copied, {skipped} skipped, {errors} errors")
    
    return 0 if errors == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Sync JavaScript islands")
    parser.add_argument("--build", "-b", action="store_true", 
                       help="Build islands project before syncing")
    parser.add_argument("--force", "-f", action="store_true",
                       help="Force copy even if files haven't changed")
    args = parser.parse_args()
    
    return sync_islands(build=args.build, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
