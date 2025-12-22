# Minimal Second Brain

A simple, AI-native knowledge management system for Obsidian.

Three folders. Zero templates. Works seamlessly with Claude Code, GitHub Copilot, and other AI assistants.

## Quick Start

1. Click **"Use this template"** to create your own repository
2. Clone it and open in Obsidian
3. Start capturing notes

That's it. The automation handles the rest.

## Structure

```
Personal/
├── Inbox/      # Quick captures, process later
├── Projects/   # Active work with deadlines
└── Knowledge/  # Reference, ideas, concepts
    └── MANIFEST.md
```

### Where to Put Notes

| Situation | Location |
|-----------|----------|
| Quick thought | `Inbox/` |
| Active work with deadline | `Projects/` |
| Reference, ideas, concepts | `Knowledge/` |

## Adding Pillars

The template includes one pillar (`Personal/`). To add more:

1. Duplicate the `Personal/` folder
2. Rename it (e.g., `Work/`, `Studies/`)
3. Update the `CLAUDE.md` and `AGENTS.md` inside
4. Update root `CLAUDE.md` to list your pillars

The automation scripts auto-detect pillars. Any folder with `Inbox/`, `Projects/`, or `Knowledge/` is treated as a pillar.

## Automation

### Manifest Updates (Claude Code)

The `.claude/hooks/update-manifest.py` hook automatically updates `MANIFEST.md` whenever you create or edit files in `Knowledge/`.

Requires [Claude Code](https://claude.ai/claude-code) with hooks enabled.

### Project Archiving (Claude Code)

Say "archive the project" and Claude will:
1. Create an AI-generated summary in `Knowledge/`
2. Store the git commit hash for restoration
3. Delete the original project file

### Weekly Cleaning (GitHub Actions + Copilot)

A GitHub Action runs every Monday and checks for:
- Out-of-sync manifests
- Inbox items older than 3 days
- Stale projects (30+ days)

If issues are found, it creates a GitHub Issue and assigns it to Copilot. Copilot autonomously creates a PR with the fixes.

Requires [GitHub Copilot coding agent](https://docs.github.com/en/copilot/using-github-copilot/using-copilot-coding-agent).

## Customisation

| Setting | File | Default |
|---------|------|---------|
| Inbox threshold | `.github/scripts/vault-cleaner.py` | 3 days |
| Stale project threshold | `.github/scripts/vault-cleaner.py` | 30 days |
| Cleaning schedule | `.github/workflows/vault-cleaning.yml` | Monday 9 AM UTC |

## AI Instructions

The vault includes instruction files for AI assistants:

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code instructions |
| `AGENTS.md` | Universal agent instructions (works with any AI) |
| `.github/copilot-instructions.md` | GitHub Copilot quick reference |

## Philosophy

1. **Capture without friction** - No templates, no decisions
2. **Projects as workspaces** - Self-contained folders for active work
3. **Knowledge is discoverable** - Manifests let AI navigate your notes
4. **Automation disappears** - Maintenance happens in the background



## Licence

MIT
