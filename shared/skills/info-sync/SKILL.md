---
name: info-sync
description: Synchronize portable Codex local assets between the user's Windows and Mac computers when they ask for 信息同步, Codex sync, skills/plugins sync, or two-computer setup sync.
metadata:
  display_name: "信息同步"
  short-description: "Sync portable Codex skills and local plugin assets between Windows and Mac"
---

# 信息同步

Use this skill when the user wants to sync their Codex setup between their Windows home computer and Mac work computer, especially when they say “信息同步”, “同步技能”, “同步插件”, “同步 Windows 和 Mac 的 Codex”, or ask to run the existing sync flow.

The skill provides local scripts for a Git-backed sync vault:

- `scripts/windows-codex-sync.ps1` for Windows PowerShell.
- `scripts/mac-codex-sync.sh` for macOS bash/zsh.

## What To Sync

Sync only portable Codex local assets:

- Personal skills under `~/.codex/skills`, excluding bundled `.system` skills.
- Local plugin assets under `~/.codex/plugins`, excluding plugin caches and temporary appserver/staging folders.
- A `config.toml` snapshot, restored as `config.toml.synced` for manual review before replacement.

Never sync secrets or machine-specific runtime state:

- Do not sync `auth.json`, provider tokens, browser sessions, credentials, or app logins.
- Do not sync SQLite state such as chat history, queues, memories, logs, sessions, or thread history.
- Do not sync sandbox folders, caches, temp directories, or generated runtime files.

## Default Workflow

When invoked, do the minimum useful action based on the current machine and the user's wording:

1. Locate this skill's `scripts/` directory.
2. If the user has not configured a sync remote, ask for the private Git repository URL before performing a first real sync. A local dry run without a remote is acceptable only when the user requests testing.
3. On Windows, run `windows-codex-sync.ps1`.
4. On macOS, run `mac-codex-sync.sh`.
5. If the user wants a command they can reuse, help them create a shell alias/function that points to the script.

Use `CODEX_SYNC_REMOTE` as the preferred environment variable for the private sync repository. Use `CODEX_SYNC_VAULT` only if the user wants a custom vault folder.

## Execution Rules

Before a first real sync, confirm that the remote is private or controlled by the user/company. A public repository is unsafe for this use.

If running from Codex and the script needs network access to clone, pull, or push the Git repository, request escalation in the normal tool flow. Do not work around network restrictions.

If Git reports a merge conflict, stop and explain which files conflicted. Do not overwrite one computer's version with the other unless the user explicitly chooses that outcome.

After a successful sync, tell the user to restart Codex/ChatGPT desktop if newly synced skills or plugins do not appear immediately.

## Common Commands

Windows:

```powershell
$env:CODEX_SYNC_REMOTE = "git@github.com:YOUR-NAME/codex-sync-vault.git"
powershell -ExecutionPolicy Bypass -File "$HOME\.codex\skills\info-sync\scripts\windows-codex-sync.ps1"
```

Mac:

```bash
export CODEX_SYNC_REMOTE="git@github.com:YOUR-NAME/codex-sync-vault.git"
bash "$HOME/.codex/skills/info-sync/scripts/mac-codex-sync.sh"
```

Use these as examples and replace the remote with the user's actual private repository URL.
