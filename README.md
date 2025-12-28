# Minimal Second Brain

[![Tests](https://github.com/gokhanarkan/minimal-second-brain/actions/workflows/tests.yml/badge.svg?branch=dev)](https://github.com/gokhanarkan/minimal-second-brain/actions/workflows/tests.yml)

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

### Weekly Cleaning (GitHub Actions)

A GitHub Action runs every Monday and checks for:
- Out-of-sync manifests
- Inbox items older than 3 days
- Stale projects (30+ days)

If issues are found, it creates a GitHub Issue with detailed instructions. You can:
- **Assign to Copilot** - GitHub Copilot coding agent will create a PR
- **Assign to Claude** - Use Claude Code to work on the issue
- **Handle manually** - Follow the instructions yourself

No special tokens or configuration needed.

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

### Choosing Your AI Instructions

The template includes multiple formats. **You don't need all of them.**

| If you use... | Keep | Delete |
|---------------|------|--------|
| Claude Code only | `CLAUDE.md` | `AGENTS.md`, `copilot-instructions.md` |
| GitHub Copilot only | `copilot-instructions.md` | `CLAUDE.md`, `AGENTS.md` |
| Multiple AI tools | All files | - |
| Other AI agents | `AGENTS.md` | `CLAUDE.md`, `copilot-instructions.md` |

**CLAUDE.md** - Detailed, Claude Code-specific instructions with hooks integration.

**AGENTS.md** - Universal format following the [agents.md spec](https://agents.md). Works with Cursor, Codex, Windsurf, and 25+ other AI coding tools.

**copilot-instructions.md** - Quick reference for GitHub Copilot.

Pick one and delete the rest. Less clutter, same functionality.

## Philosophy

1. **Capture without friction** - No templates, no decisions
2. **Projects as workspaces** - Self-contained folders for active work
3. **Knowledge is discoverable** - Manifests let AI navigate your notes
4. **Automation disappears** - Maintenance happens in the background

## Licence

MIT
