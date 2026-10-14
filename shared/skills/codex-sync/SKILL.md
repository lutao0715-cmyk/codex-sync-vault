---
name: codex-sync
description: Synchronize portable Codex settings, custom skills, and plugin enablement between the user's computers through a private Git vault while excluding secrets and local runtime state.
---

# Codex Sync

Use this skill when the user wants to keep Codex configuration, custom skills, and plugin information in sync across multiple computers.

## What To Sync

Use `scripts/codex_sync.py` as the primary helper. It is intentionally conservative:

- Syncs custom skills under `$CODEX_HOME/skills`.
- Syncs `$CODEX_HOME/AGENTS.md` when present.
- Extracts plugin enablement blocks from `$CODEX_HOME/config.toml` and applies only those blocks cross-machine.
- Saves each machine's full `config.toml` as a per-host reference profile, but does not blindly apply it to other machines because paths and trusted projects are OS-specific.
- Excludes `auth.json`, `.env`, sqlite databases, sessions, logs, cache, IPC files, shell snapshots, and other local runtime state.

## Normal Use

Run:

```bash
python3 ~/.codex/skills/codex-sync/scripts/codex_sync.py sync
```

The script will:

1. Prepare a local sync vault at `~/.codex/sync-vault`.
2. Pull the configured Git remote when available.
3. Import portable remote content into this Codex home with backups for changed single files.
4. Export this machine's portable content back into the vault.
5. Commit and push changes when a remote is configured and reachable.

If the user has not configured a remote, use:

```bash
python3 ~/.codex/skills/codex-sync/scripts/codex_sync.py init --remote git@github.com:OWNER/codex-sync-vault.git
```

For this user's Mac, the expected default remote is:

```bash
git@github.com:lutao0715-cmyk/codex-sync-vault.git
```

The GitHub repository should be private.

## Directional Operations

- `sync`: normal daily operation; imports remote portable content, exports local portable content, commits, and pushes.
- `push`: export this machine's portable content and push it to the vault.
- `pull`: pull from the vault and import portable content into this machine.
- `pull-mirror`: pull from the vault, back up the local skills directory, then mirror `shared/skills` into this machine with deletions. Use this only when this machine should adopt the curated shared skill set exactly.
- `status`: show configured paths and Git status without changing files.

When a conflict occurs during Git pull or rebase, stop and explain the vault path and conflicted files. Do not delete local Codex data to resolve conflicts.
