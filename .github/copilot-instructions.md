# Copilot Instructions

Quick reference for GitHub Copilot when working in this vault.

## Structure

```
[Pillar]/
├── Inbox/      # Quick captures
├── Projects/   # Active work
├── Knowledge/  # Reference (has MANIFEST.md)
```

## Routing

- Quick thought → `Inbox/`
- Active work → `Projects/`
- Reference → `Knowledge/`

## Key Rules

1. Read `MANIFEST.md` before searching Knowledge/
2. Update `MANIFEST.md` after modifying Knowledge/
3. Use `[[Note Name]]` for internal links
4. Scripts auto-detect pillars (folders with Inbox/Projects/Knowledge)

## Customisation

| Setting | File | Default |
|---------|------|---------|
| Inbox threshold | `.github/scripts/vault-cleaner.py` | 3 days |
| Stale threshold | `.github/scripts/vault-cleaner.py` | 30 days |
| Schedule | `.github/workflows/vault-cleaning.yml` | Monday 9 AM |
