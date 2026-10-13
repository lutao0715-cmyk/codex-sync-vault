# Codex Sync Vault

Private Git vault for portable Codex settings.

## Daily Sync

Mac:

```bash
python3 ~/.codex/skills/codex-sync/scripts/codex_sync.py sync
```

Windows PowerShell:

```powershell
python "$env:USERPROFILE\.codex\skills\codex-sync\scripts\codex_sync.py" sync
```

## First Setup

Create this GitHub repository as a private repository, then run the daily sync command on the computer that already has the newest configuration.

The expected remote is:

```text
git@github.com:lutao0715-cmyk/codex-sync-vault.git
```

The sync script excludes auth tokens, environment files, sqlite sessions, logs, cache, and other local runtime state.
