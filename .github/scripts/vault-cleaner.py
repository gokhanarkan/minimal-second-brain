#!/usr/bin/env python3
"""
Vault Cleaner - Detects cleaning tasks and generates a GitHub issue body for Copilot.

Checks:
1. Manifest sync - are MANIFEST.md files up to date?
2. Inbox items - are there files sitting in Inbox folders?
3. Stale projects - projects not modified in 30+ days?

Outputs:
- cleaning-tasks.md: Issue body for Copilot
- Sets GitHub Actions output: has_tasks=true/false
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime
from typing import TypedDict

# Configuration
INBOX_AGE_THRESHOLD_DAYS = 3
PROJECT_STALE_THRESHOLD_DAYS = 30


class FileItem(TypedDict):
    name: str
    age_days: int


def get_vault_root() -> Path:
    """Get the vault root directory."""
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent.parent


def get_pillars(vault_root: Path) -> list[str]:
    """Auto-detect pillars by finding folders with Inbox/Projects/Knowledge."""
    pillars = []
    for item in vault_root.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # A pillar has at least one of: Inbox, Projects, Knowledge
            has_inbox = (item / 'Inbox').exists()
            has_projects = (item / 'Projects').exists()
            has_knowledge = (item / 'Knowledge').exists()
            if has_inbox or has_projects or has_knowledge:
                pillars.append(item.name)
    return sorted(pillars)


def get_file_last_modified(file_path: Path, vault_root: Path) -> datetime:
    """Get the last modification date for a file.

    Uses git commit date if available, falls back to filesystem mtime.
    """
    # Try git first
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ct', '--', str(file_path)],
            capture_output=True,
            text=True,
            cwd=vault_root
        )
        if result.returncode == 0 and result.stdout.strip():
            timestamp = int(result.stdout.strip())
            return datetime.fromtimestamp(timestamp)
    except Exception:
        pass

    # Fall back to filesystem modification time
    try:
        mtime = file_path.stat().st_mtime
        return datetime.fromtimestamp(mtime)
    except Exception:
        pass

    # If all else fails, return now (0 days ago)
    return datetime.now()


def days_since(dt: datetime) -> int:
    """Calculate days since a datetime."""
    delta = datetime.now() - dt
    return delta.days


def parse_manifest(manifest_path: Path) -> set[str]:
    """Parse MANIFEST.md and return set of file names (without extension)."""
    entries: set[str] = set()
    if not manifest_path.exists():
        return entries

    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('|') and '[[' in line:
                    # Extract [[Name]] from table row
                    start = line.find('[[')
                    end = line.find(']]')
                    if start != -1 and end != -1:
                        entries.add(line[start + 2:end])
    except Exception:
        pass
    return entries


def get_actual_files(knowledge_dir: Path) -> set[str]:
    """Get set of markdown files in Knowledge/ (excluding MANIFEST.md)."""
    files: set[str] = set()
    if not knowledge_dir.exists():
        return files

    for f in knowledge_dir.glob('*.md'):
        if f.name != 'MANIFEST.md':
            files.add(f.stem)
    return files


def check_manifest_sync(vault_root: Path) -> dict:
    """Check if manifests are in sync with actual files."""
    issues = {}

    for pillar in get_pillars(vault_root):
        knowledge_dir = vault_root / pillar / 'Knowledge'
        manifest_path = knowledge_dir / 'MANIFEST.md'

        if not knowledge_dir.exists():
            continue

        manifest_entries = parse_manifest(manifest_path)
        actual_files = get_actual_files(knowledge_dir)

        missing_from_manifest = actual_files - manifest_entries
        extra_in_manifest = manifest_entries - actual_files

        if missing_from_manifest or extra_in_manifest:
            issues[pillar] = {
                'add': sorted(missing_from_manifest),
                'remove': sorted(extra_in_manifest)
            }

    return issues


def check_inbox_items(vault_root: Path) -> dict:
    """Check for items in Inbox folders."""
    items = {}

    for pillar in get_pillars(vault_root):
        inbox_dir = vault_root / pillar / 'Inbox'

        if not inbox_dir.exists():
            continue

        pillar_items: list[FileItem] = []
        for f in inbox_dir.glob('*.md'):
            last_modified = get_file_last_modified(f, vault_root)
            age_days = days_since(last_modified)

            if age_days >= INBOX_AGE_THRESHOLD_DAYS:
                pillar_items.append({
                    'name': f.name,
                    'age_days': age_days
                })

        if pillar_items:
            items[pillar] = sorted(pillar_items, key=lambda x: -x['age_days'])

    return items


def check_stale_projects(vault_root: Path) -> dict:
    """Check for stale projects (not modified in 30+ days)."""
    stale = {}

    for pillar in get_pillars(vault_root):
        projects_dir = vault_root / pillar / 'Projects'

        if not projects_dir.exists():
            continue

        pillar_stale: list[FileItem] = []
        for f in projects_dir.glob('*.md'):
            last_modified = get_file_last_modified(f, vault_root)
            age_days = days_since(last_modified)

            if age_days >= PROJECT_STALE_THRESHOLD_DAYS:
                pillar_stale.append({
                    'name': f.name,
                    'age_days': age_days
                })

        if pillar_stale:
            stale[pillar] = sorted(pillar_stale, key=lambda x: -x['age_days'])

    return stale


def generate_issue_body(manifest_issues: dict, inbox_items: dict, stale_projects: dict) -> str:
    """Generate the issue body for Copilot."""
    lines = [
        '# Vault Cleaning Tasks',
        '',
        'This issue was auto-generated by the weekly vault cleaning workflow.',
        'Please complete the following tasks.',
        ''
    ]

    task_num = 1

    # Manifest sync tasks
    if manifest_issues:
        lines.append(f'## {task_num}. Fix Manifest Files')
        lines.append('')
        lines.append('The following MANIFEST.md files are out of sync:')
        lines.append('')

        for pillar, issues in manifest_issues.items():
            lines.append(f'### {pillar}/Knowledge/MANIFEST.md')
            lines.append('')

            if issues['add']:
                for name in issues['add']:
                    lines.append(f'- Add: `[[{name}]]`')
            if issues['remove']:
                for name in issues['remove']:
                    lines.append(f'- Remove: `[[{name}]]`')
            lines.append('')

        lines.append('**Instructions:** Regenerate each manifest by scanning the Knowledge/ folder.')
        lines.append('Each entry should be: `| [[filename]] | first heading or description |`')
        lines.append('')
        task_num += 1

    # Inbox items tasks
    if inbox_items:
        lines.append(f'## {task_num}. Process Inbox Items')
        lines.append('')
        lines.append(f'The following items have been in Inbox for {INBOX_AGE_THRESHOLD_DAYS}+ days:')
        lines.append('')

        for pillar, items in inbox_items.items():
            lines.append(f'### {pillar}/Inbox/')
            lines.append('')
            for item in items:
                lines.append(f'- `{item["name"]}` ({item["age_days"]} days)')
            lines.append('')

        lines.append('**Instructions:** Review each file. Either:')
        lines.append('- Move to `Knowledge/` if it is reference material')
        lines.append('- Move to `Projects/` if it is active work')
        lines.append('- Delete if no longer needed')
        lines.append('')
        lines.append('After moving files to Knowledge/, update the corresponding MANIFEST.md.')
        lines.append('')
        task_num += 1

    # Stale projects tasks
    if stale_projects:
        lines.append(f'## {task_num}. Archive Stale Projects')
        lines.append('')
        lines.append(f'The following projects have not been modified in {PROJECT_STALE_THRESHOLD_DAYS}+ days:')
        lines.append('')

        for pillar, projects in stale_projects.items():
            lines.append(f'### {pillar}/Projects/')
            lines.append('')
            for proj in projects:
                lines.append(f'- `{proj["name"]}` ({proj["age_days"]} days)')
            lines.append('')

        lines.append('**Instructions:** For each stale project:')
        lines.append('1. Create an archived summary in `Knowledge/`')
        lines.append('2. Include the current git commit hash for reference')
        lines.append('3. Delete the original project file')
        lines.append('4. Update MANIFEST.md')
        lines.append('')
        task_num += 1

    # Footer
    lines.append('---')
    lines.append('')
    lines.append('When complete, the PR should include all changes and updated manifests.')
    lines.append('')

    return '\n'.join(lines)


def set_github_output(name: str, value: str):
    """Set a GitHub Actions output variable."""
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f'{name}={value}\n')
    else:
        # For local testing
        print(f'Output: {name}={value}')


def main():
    vault_root = get_vault_root()

    print('Checking vault for cleaning tasks...')
    print(f'Vault root: {vault_root}')
    print()

    # Run all checks
    manifest_issues = check_manifest_sync(vault_root)
    inbox_items = check_inbox_items(vault_root)
    stale_projects = check_stale_projects(vault_root)

    # Report findings
    has_tasks = bool(manifest_issues or inbox_items or stale_projects)

    if manifest_issues:
        print(f'Manifest issues: {len(manifest_issues)} pillar(s)')
        for pillar, issues in manifest_issues.items():
            print(f'  {pillar}: +{len(issues["add"])} -{len(issues["remove"])}')

    if inbox_items:
        total = sum(len(items) for items in inbox_items.values())
        print(f'Inbox items: {total} file(s)')
        for pillar, items in inbox_items.items():
            print(f'  {pillar}: {len(items)} file(s)')

    if stale_projects:
        total = sum(len(projs) for projs in stale_projects.values())
        print(f'Stale projects: {total} project(s)')
        for pillar, projs in stale_projects.items():
            print(f'  {pillar}: {len(projs)} project(s)')

    if not has_tasks:
        print('No cleaning tasks found. Vault is tidy!')

    # Generate issue body if there are tasks
    if has_tasks:
        issue_body = generate_issue_body(manifest_issues, inbox_items, stale_projects)

        # Write to file for gh CLI
        output_path = vault_root / 'cleaning-tasks.md'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(issue_body)
        print(f'\nIssue body written to: {output_path}')

    # Set GitHub Actions output
    set_github_output('has_tasks', str(has_tasks).lower())

    print()
    print(f'has_tasks: {has_tasks}')


if __name__ == '__main__':
    main()
