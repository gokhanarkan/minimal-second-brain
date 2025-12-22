#!/usr/bin/env python3
"""
Hook script to auto-update Knowledge/MANIFEST.md files.

Triggered by PostToolUse on Write/Edit/Bash operations.
Checks if affected file is in a Knowledge/ folder and regenerates the manifest.
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional


def get_first_heading(file_path: Path) -> str:
    """Extract the first markdown heading or first non-empty line as description."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Remove markdown heading prefix
                if line.startswith('#'):
                    return line.lstrip('#').strip()
                # Return first non-empty line if no heading
                return line[:80] + ('...' if len(line) > 80 else '')
    except Exception:
        pass
    return 'No description'


def update_manifest(knowledge_dir: Path) -> bool:
    """Regenerate MANIFEST.md for a Knowledge/ directory."""
    manifest_path = knowledge_dir / 'MANIFEST.md'

    # Find all .md files except MANIFEST.md
    md_files = sorted([
        f for f in knowledge_dir.glob('*.md')
        if f.name != 'MANIFEST.md'
    ])

    # Build manifest content
    lines = ['# Knowledge Manifest', '', '| File | Description |', '|------|-------------|']

    if not md_files:
        lines.append('| *(empty)* | Add notes to this folder |')
    else:
        for md_file in md_files:
            name = md_file.stem  # filename without .md
            description = get_first_heading(md_file)
            # Use Obsidian wiki-link format
            lines.append(f'| [[{name}]] | {description} |')

    lines.append('')  # trailing newline

    # Write manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    return True


def find_knowledge_dir(file_path: str) -> Optional[Path]:
    """Check if file_path is inside a Knowledge/ folder and return that folder."""
    path = Path(file_path).resolve()

    # Walk up the path looking for Knowledge/
    for parent in path.parents:
        if parent.name == 'Knowledge':
            return parent

    # Also check if the file itself is directly in Knowledge/
    if path.parent.name == 'Knowledge':
        return path.parent

    return None


def get_pillars(vault_root: Path) -> list[str]:
    """Auto-detect pillars by finding folders with Knowledge/ subdirectory."""
    pillars = []
    for item in vault_root.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            if (item / 'Knowledge').exists():
                pillars.append(item.name)
    return sorted(pillars)


def main():
    # Read JSON input from stdin
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No valid JSON input, exit silently
        sys.exit(0)

    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})

    # Determine affected file path based on tool
    file_path = None

    if tool_name in ('Write', 'Edit'):
        file_path = tool_input.get('file_path')
    elif tool_name == 'Bash':
        # For Bash, check if command involves Knowledge/ files
        command = tool_input.get('command', '')
        # Simple heuristic: look for Knowledge/ in command
        if 'Knowledge/' not in command:
            sys.exit(0)
        # Can't reliably determine exact file, so scan all Knowledge/ dirs
        project_dir = Path(os.environ.get('CLAUDE_PROJECT_DIR', '.'))
        for pillar in get_pillars(project_dir):
            knowledge_dir = project_dir / pillar / 'Knowledge'
            if knowledge_dir.exists():
                update_manifest(knowledge_dir)
        sys.exit(0)

    if not file_path:
        sys.exit(0)

    # Check if file is in a Knowledge/ folder
    knowledge_dir = find_knowledge_dir(file_path)
    if not knowledge_dir:
        sys.exit(0)

    # Update the manifest
    update_manifest(knowledge_dir)

    sys.exit(0)


if __name__ == '__main__':
    main()
