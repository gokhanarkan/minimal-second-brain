# Minimal Second Brain

A simple knowledge management system designed to work with AI assistants.

## Structure

Each pillar (life area) has the same structure:

```
[Pillar]/
├── Inbox/      # Quick captures, process later
├── Projects/   # Active work with context
├── Knowledge/  # Reference, ideas, concepts (has MANIFEST.md)
├── CLAUDE.md
└── AGENTS.md
```

## Where to Put Notes

| Situation | Location |
|-----------|----------|
| Quick thought, process later | `Inbox/` |
| Active work with deadline | `Projects/` |
| Reference, ideas, concepts | `Knowledge/` |

## File Naming

| Type | Format | Example |
|------|--------|---------|
| General | `Title Case.md` | `API Design Principles.md` |
| Dated | `YYYY-MM-DD Title.md` | `2025-01-15 Team Standup.md` |
| People | `First Last.md` | `Jane Smith.md` |

## Tags

Context (required):
- `#context/personal`
- Add more for your pillars: `#context/work`, `#context/studies`, etc.

Type (optional):
- `#type/project`
- `#type/note`
- `#type/meeting`

## Knowledge Manifest

Each `Knowledge/` folder has a `MANIFEST.md` that indexes all files.

**Auto-update rule**: When you add, remove, or rename files in Knowledge/, update MANIFEST.md immediately.

## Do

- Use simple, descriptive titles
- Link related notes with `[[Note Name]]`
- Put files in the right pillar
- Update MANIFEST.md when modifying Knowledge/

## Don't

- Create files at vault root
- Over-complicate the structure

## Writing Style

- Use clear, concise language
- Prefer active voice

## Git Commits

- Write clean, descriptive commit messages
- Keep messages concise and focused on what changed

## Available Skills

- **archive-project** - Say "archive [project name]" to move completed projects to Knowledge/ with an AI-generated summary
- **github-summary** - Say "/github-summary" or "summarise my GitHub activity" to generate a narrative summary of your issues, PRs, and commits

## Pillars

- [[Personal/CLAUDE|Personal]]

Add more pillars by duplicating the Personal/ folder.
