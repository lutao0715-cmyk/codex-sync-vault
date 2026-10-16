---
name: codex-sync
description: Synchronize portable Codex settings, custom skills, and plugin enablement between the user's computers through a private Git vault while excluding secrets and local runtime state.
---

# Codex Sync

Use this skill when the user wants to keep Codex configuration, custom skills, and plugin information in sync across multiple computers.

## What To Sync

Use `scripts/codex_sync.py` as the primary helper. It is intentionally conservative:

- Syncs custom skills under `$CODEX_HOME/skills`.
- Syncs only skills that have been explicitly reviewed as portable across both macOS and Windows. Single-OS or unreviewed skills must stay local until added to the allowlist in `scripts/codex_sync.py`.
- Syncs `$CODEX_HOME/AGENTS.md` when present.
- Extracts only explicitly allowlisted, cross-platform plugin enablement blocks from `$CODEX_HOME/config.toml`. Browser control, computer control, local executables, DaVinci MCP paths, and other OS-specific configuration remain per-host.
- Saves each machine's full `config.toml` as a per-host reference profile, but does not blindly apply it to other machines because paths and trusted projects are OS-specific.
- Windows-only DaVinci/Resolve skills, MCP servers, paths, presets, and timeline rules are host-local and must never be imported into the Mac shared layer. They may remain in the Windows profile; syncing must not delete, replace, or sanitize them on Windows.
- Saves the installed-plugin manifest inside the per-host profile rather than the shared layer.
- Excludes virtual environments, `node_modules`, compiled binaries and extensions (`.exe`, `.dll`, `.pyd`, `.so`, `.dylib`), `auth.json`, `.env`, sqlite databases, logs, caches, and other local runtime state.

## Normal Use

Run:

```bash
& "C:/Users/win/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" C:/Users/win/.codex/skills/codex-sync/scripts/codex_sync.py sync
```

The script will:

1. Prepare a local sync vault at `~/.codex/sync-vault`.
2. Pull the configured Git remote when available.
3. Import portable remote content into this Codex home with backups for changed single files.
4. Export this machine's portable content back into the vault.
5. Commit and push changes when a remote is configured and reachable.

If the user has not configured a remote, use:

```bash
& "C:/Users/win/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe" C:/Users/win/.codex/skills/codex-sync/scripts/codex_sync.py init --remote git@github.com:OWNER/codex-sync-vault.git
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
- `pull-mirror`: pull from the vault, back up the local skills directory, then mirror `shared/skills` into this machine with deletions. Use this only when this machine should adopt the curated cross-platform skill set exactly.
- `status`: show configured paths and Git status without changing files.

When a conflict occurs during Git pull or rebase, stop and explain the vault path and conflicted files. Do not delete local Codex data to resolve conflicts.

## DaVinci/Resolve protection

Treat all DaVinci/Resolve-related content as Windows-only unless explicitly reviewed otherwise. This includes Resolve MCP configuration, executable paths, timeline prompts, delivery presets, Resolve-specific subtitle parameters, and skills whose output is `clip_plan.json` for Resolve. Keep these in the Windows host profile only. The shared allowlists are the sole authority for cross-platform import/export, and no sync operation should remove or overwrite the Windows-local copies.
