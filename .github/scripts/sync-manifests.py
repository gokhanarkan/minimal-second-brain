#!/usr/bin/env python3
"""
Sync all Knowledge/MANIFEST.md files in the vault.

Scans for pillars (folders with Knowledge/ subdirectory) and regenerates
each manifest based on the files present.

Usage:
    python sync-manifests.py [--check]

Options:
    --check    Check if manifests are in sync (exit 1 if not)
"""

import sys
from pathlib import Path


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


def generate_manifest_content(knowledge_dir: Path) -> str:
    """Generate manifest content for a Knowledge/ directory."""
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
    return '\n'.join(lines)


def update_manifest(knowledge_dir: Path, check_only: bool = False) -> bool:
    """Update or check MANIFEST.md for a Knowledge/ directory.

    Returns True if manifest is in sync, False if it needed updating.
    """
    manifest_path = knowledge_dir / 'MANIFEST.md'
    new_content = generate_manifest_content(knowledge_dir)

    # Read current content if exists
    current_content = ''
    if manifest_path.exists():
        with open(manifest_path, 'r', encoding='utf-8') as f:
            current_content = f.read()

    # Check if update needed
    if current_content == new_content:
        return True  # Already in sync

    if check_only:
        return False  # Out of sync

    # Write updated manifest
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return False  # Was out of sync, now updated


def get_pillars(vault_root: Path) -> list[str]:
    """Auto-detect pillars by finding folders with Knowledge/ subdirectory."""
    pillars = []
    for item in vault_root.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            if (item / 'Knowledge').exists():
                pillars.append(item.name)
    return sorted(pillars)


def main():
    check_only = '--check' in sys.argv

    # Find vault root (script is in .github/scripts/)
    script_dir = Path(__file__).resolve().parent
    vault_root = script_dir.parent.parent

    pillars = get_pillars(vault_root)

    if not pillars:
        print('No pillars found (folders with Knowledge/ subdirectory)')
        sys.exit(0)

    all_in_sync = True

    for pillar in pillars:
        knowledge_dir = vault_root / pillar / 'Knowledge'
        if not knowledge_dir.exists():
            continue

        was_in_sync = update_manifest(knowledge_dir, check_only)

        if was_in_sync:
            print(f'✓ {pillar}/Knowledge/MANIFEST.md is in sync')
        else:
            if check_only:
                print(f'✗ {pillar}/Knowledge/MANIFEST.md is out of sync')
            else:
                print(f'✓ {pillar}/Knowledge/MANIFEST.md updated')
            all_in_sync = False

    if check_only and not all_in_sync:
        print('\nManifests are out of sync. Run without --check to update.')
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
