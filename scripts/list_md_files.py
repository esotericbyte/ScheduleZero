#!/usr/bin/env python3
"""List all Markdown files in the project."""

from pathlib import Path


def main():
    """Find and list all .md files in the project."""
    project_root = Path(__file__).parent.parent
    
    # Find all .md files recursively
    md_files = sorted(project_root.rglob("*.md"))
    
    print(f"Found {len(md_files)} Markdown files:\n")
    
    for md_file in md_files:
        # Get relative path from project root
        rel_path = md_file.relative_to(project_root)
        print(rel_path)


if __name__ == "__main__":
    main()
