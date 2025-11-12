#!/usr/bin/env python3
"""
Build MkDocs documentation for ScheduleZero.

Usage:
    python build_docs.py              # Build docs
    python build_docs.py --serve      # Build and serve locally
    python build_docs.py --clean      # Clean build directory
"""
import subprocess
import shutil
import argparse
from pathlib import Path


def build_docs():
    """Build the documentation using mkdocs."""
    print("📚 Building documentation...")
    result = subprocess.run(["poetry", "run", "mkdocs", "build"], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Documentation built successfully!")
        print(f"📁 Output: docs_site_build/")
        print(f"🌐 View in server: http://localhost:8888/docs/")
        return True
    else:
        print("❌ Build failed:")
        print(result.stderr)
        return False


def serve_docs():
    """Serve documentation locally for development."""
    print("🌐 Serving documentation locally...")
    print("📍 http://127.0.0.1:8000")
    print("Press Ctrl+C to stop")
    subprocess.run(["poetry", "run", "mkdocs", "serve"])


def clean_docs():
    """Clean the build directory."""
    build_dir = Path("docs_site_build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print(f"🗑️  Cleaned {build_dir}")
    else:
        print("ℹ️  Build directory doesn't exist")


def main():
    parser = argparse.ArgumentParser(description="Build ScheduleZero documentation")
    parser.add_argument("--serve", action="store_true", help="Serve docs locally")
    parser.add_argument("--clean", action="store_true", help="Clean build directory")
    args = parser.parse_args()
    
    if args.clean:
        clean_docs()
    elif args.serve:
        serve_docs()
    else:
        build_docs()


if __name__ == "__main__":
    main()
