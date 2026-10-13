#!/usr/bin/env bash
set -euo pipefail

REMOTE="${CODEX_SYNC_REMOTE:-}"
VAULT="${CODEX_SYNC_VAULT:-$HOME/Documents/codex-sync-vault}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
NO_PUSH="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      REMOTE="$2"
      shift 2
      ;;
    --vault)
      VAULT="$2"
      shift 2
      ;;
    --codex-home)
      CODEX_HOME="$2"
      shift 2
      ;;
    --no-push)
      NO_PUSH="1"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

run_git() {
  git "$@"
}

ensure_repo() {
  if ! command -v git >/dev/null 2>&1; then
    echo "Git is required. Install Git first, then rerun this script." >&2
    exit 1
  fi

  if [[ ! -d "$VAULT" ]]; then
    if [[ -z "$REMOTE" ]]; then
      mkdir -p "$VAULT"
      git -C "$VAULT" init
    else
      git clone "$REMOTE" "$VAULT"
    fi
  fi

  if [[ ! -d "$VAULT/.git" ]]; then
    echo "$VAULT exists but is not a Git repository." >&2
    exit 1
  fi

  if [[ -n "$REMOTE" ]] && ! git -C "$VAULT" remote | grep -qx "origin"; then
    git -C "$VAULT" remote add origin "$REMOTE"
  fi
}

copy_to_vault() {
  local target="$VAULT/codex-home"
  mkdir -p "$target"

  if [[ -d "$CODEX_HOME/skills" ]]; then
    mkdir -p "$target/skills"
    rsync -a --delete \
      --exclude ".system/" \
      --exclude ".DS_Store" \
      --exclude "Thumbs.db" \
      "$CODEX_HOME/skills/" "$target/skills/"
  fi

  if [[ -d "$CODEX_HOME/plugins" ]]; then
    mkdir -p "$target/plugins"
    rsync -a --delete \
      --exclude "cache/" \
      --exclude ".plugin-appserver/" \
      --exclude ".remote-plugin-install-staging/" \
      --exclude ".DS_Store" \
      --exclude "Thumbs.db" \
      "$CODEX_HOME/plugins/" "$target/plugins/"
  fi

  if [[ -f "$CODEX_HOME/config.toml" ]]; then
    mkdir -p "$target/config"
    cp "$CODEX_HOME/config.toml" "$target/config/config.toml"
  fi
}

copy_from_vault() {
  local source="$VAULT/codex-home"
  [[ -d "$source" ]] || return 0
  mkdir -p "$CODEX_HOME"

  if [[ -d "$source/skills" ]]; then
    mkdir -p "$CODEX_HOME/skills"
    rsync -a \
      --exclude ".system/" \
      --exclude ".DS_Store" \
      --exclude "Thumbs.db" \
      "$source/skills/" "$CODEX_HOME/skills/"
  fi

  if [[ -d "$source/plugins" ]]; then
    mkdir -p "$CODEX_HOME/plugins"
    rsync -a \
      --exclude "cache/" \
      --exclude ".plugin-appserver/" \
      --exclude ".remote-plugin-install-staging/" \
      --exclude ".DS_Store" \
      --exclude "Thumbs.db" \
      "$source/plugins/" "$CODEX_HOME/plugins/"
  fi

  if [[ -f "$source/config/config.toml" ]]; then
    cp "$source/config/config.toml" "$CODEX_HOME/config.toml.synced"
    echo "Wrote config snapshot to $CODEX_HOME/config.toml.synced. Review before replacing config.toml."
  fi
}

commit_if_needed() {
  git -C "$VAULT" add codex-home
  if [[ -n "$(git -C "$VAULT" status --porcelain)" ]]; then
    git -C "$VAULT" commit -m "Sync Codex local assets from Mac"
  fi
}

ensure_repo
copy_to_vault
commit_if_needed

if git -C "$VAULT" remote | grep -qx "origin"; then
  git -C "$VAULT" pull --rebase --autostash origin HEAD
fi

copy_from_vault
copy_to_vault
commit_if_needed

if [[ "$NO_PUSH" != "1" ]]; then
  if git -C "$VAULT" remote | grep -qx "origin"; then
    git -C "$VAULT" push origin HEAD
  else
    echo "No remote configured. Local vault updated at $VAULT."
  fi
fi

echo "Codex sync complete. Restart Codex/ChatGPT desktop if plugin or skill changes do not appear immediately."
