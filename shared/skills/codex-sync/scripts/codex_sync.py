#!/usr/bin/env python3
"""Synchronize portable Codex configuration through a Git vault."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path


DEFAULT_REMOTE = "git@github.com:lutao0715-cmyk/codex-sync-vault.git"
EXCLUDE_SKILL_DIRS = {".system"}

# Only skills that have been reviewed as portable across both macOS and Windows
# belong in the shared vault. Single-OS or unreviewed skills stay local by
# default until they are explicitly added here.
SHARED_SKILL_ALLOWLIST = {
    "codex-sync",
    "fangan-review__skillhub",
    "humanizer-zh__skillhub",
    "outdoor-creation-team",
    "product-manager",
    "热点",
    "直播复盘",
}

# Only plugin enablement that is useful on both Windows and macOS is shared.
# Browser/computer-control plugins and anything tied to a local executable stay
# in the per-host config profile.
SHARED_PLUGIN_ALLOWLIST = {
    "codex-app-tools@openai-bundled",
    "code-review@openai-bundled",
    "documents@openai-primary-runtime",
    "pdf@openai-primary-runtime",
    "presentations@openai-primary-runtime",
    "spreadsheets@openai-primary-runtime",
    "template-creator@openai-primary-runtime",
    "visualize@openai-bundled",
}

LOCAL_RUNTIME_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}
LOCAL_RUNTIME_FILE_NAMES = {".DS_Store", ".env", "Thumbs.db", "auth.json", "desktop.ini"}
LOCAL_RUNTIME_SUFFIXES = {
    ".db", ".dll", ".dylib", ".exe", ".log", ".pyc", ".pyd", ".pyo", ".so", ".sqlite", ".sqlite3"
}


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and proc.returncode:
        message = "\n".join(
            part for part in [
                f"Command failed: {' '.join(cmd)}",
                proc.stdout.strip(),
                proc.stderr.strip(),
            ] if part
        )
        raise RuntimeError(message)
    return proc


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def vault_dir() -> Path:
    return Path(os.environ.get("CODEX_SYNC_VAULT", codex_home() / "sync-vault")).expanduser()


def config_file() -> Path:
    return codex_home() / "sync-vault.toml"


def read_saved_remote() -> str | None:
    path = config_file()
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("remote"):
            _, _, value = line.partition("=")
            return value.strip().strip('"') or None
    return None


def save_remote(remote: str) -> None:
    path = config_file()
    path.write_text(f'remote = "{remote}"\n', encoding="utf-8")
    path.chmod(0o600)


def remote_url(args_remote: str | None = None) -> str | None:
    return args_remote or os.environ.get("CODEX_SYNC_REMOTE") or read_saved_remote() or DEFAULT_REMOTE


def ensure_vault(remote: str | None) -> Path:
    vault = vault_dir()
    if vault.exists() and (vault / ".git").exists():
        return vault

    vault.parent.mkdir(parents=True, exist_ok=True)
    if remote:
        proc = run(["git", "clone", remote, str(vault)], check=False)
        if proc.returncode == 0:
            return vault
        print("Remote clone failed; creating a local vault for now.")
        print((proc.stderr or proc.stdout).strip())

    vault.mkdir(parents=True, exist_ok=True)
    run(["git", "init"], cwd=vault)
    if remote:
        existing = run(["git", "remote"], cwd=vault, check=False).stdout.split()
        if "origin" not in existing:
            run(["git", "remote", "add", "origin", remote], cwd=vault, check=False)
    return vault


def should_skip_copy(path: Path) -> bool:
    return (
        any(part in LOCAL_RUNTIME_DIR_NAMES for part in path.parts)
        or path.name in LOCAL_RUNTIME_FILE_NAMES
        or path.suffix.lower() in LOCAL_RUNTIME_SUFFIXES
    )


def copy_tree(src: Path, dst: Path, delete: bool = False) -> None:
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    if delete:
        allowed = {
            item.relative_to(src)
            for item in src.rglob("*")
            if not should_skip_copy(item)
        }
        for item in sorted(dst.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if item.relative_to(dst) not in allowed:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
    for item in src.rglob("*"):
        if should_skip_copy(item):
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def backup(path: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.name}.codex-sync-backup-{stamp}")
    shutil.copy2(path, backup_path)
    return backup_path


def backup_dir(path: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = path.with_name(f"{path.name}.codex-sync-backup-{stamp}")
    shutil.copytree(path, backup_path)
    return backup_path


def machine_id() -> str:
    raw = f"{socket.gethostname()}-{platform.system()}-{platform.machine()}".lower()
    return "".join(ch if ch.isalnum() or ch in ".-" else "-" for ch in raw).strip("-")


def plugin_id_from_header(line: str) -> str | None:
    header = line.strip()
    if not (header.startswith("[plugins.") and header.endswith("]")):
        return None
    return header[len("[plugins."):-1].strip().strip('"')


def extract_plugin_blocks(config_text: str) -> str:
    lines = config_text.splitlines()
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        plugin_id = plugin_id_from_header(line)
        if plugin_id is not None:
            block = [line]
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("["):
                block.append(lines[i])
                i += 1
            if plugin_id in SHARED_PLUGIN_ALLOWLIST:
                blocks.extend(block)
                if blocks and blocks[-1] != "":
                    blocks.append("")
            continue
        i += 1
    return "\n".join(blocks).rstrip() + ("\n" if blocks else "")


def replace_plugin_blocks(config_text: str, plugin_text: str) -> str:
    lines = config_text.splitlines()
    kept: list[str] = []
    i = 0
    while i < len(lines):
        plugin_id = plugin_id_from_header(lines[i])
        if plugin_id in SHARED_PLUGIN_ALLOWLIST:
            i += 1
            while i < len(lines) and not lines[i].lstrip().startswith("["):
                i += 1
            continue
        kept.append(lines[i])
        i += 1
    base = "\n".join(kept).rstrip()
    plugin = plugin_text.strip()
    if not plugin:
        return base + "\n"
    return base + "\n\n" + plugin + "\n"


def write_plugin_manifest(vault: Path) -> None:
    plugins_dir = codex_home() / "plugins"
    manifest = vault / "profiles" / machine_id() / "plugin-manifest.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    entries: list[str] = []
    if plugins_dir.exists():
        for path in sorted(plugins_dir.rglob("*")):
            rel = path.relative_to(plugins_dir)
            if any(part in {"cache", ".plugin-appserver"} for part in rel.parts):
                continue
            if path.is_file():
                entries.append(str(rel))
    manifest.write_text("\n".join(entries) + ("\n" if entries else ""), encoding="utf-8")


def import_from_vault(vault: Path, mirror_skills: bool = False) -> None:
    shared = vault / "shared"
    home = codex_home()
    if mirror_skills and (home / "skills").exists():
        saved = backup_dir(home / "skills")
        print(f"Backed up local skills to {saved}")
    copy_tree(shared / "skills", home / "skills", delete=mirror_skills)

    remote_agents = shared / "AGENTS.md"
    local_agents = home / "AGENTS.md"
    if remote_agents.exists():
        if local_agents.exists() and local_agents.read_bytes() != remote_agents.read_bytes():
            saved = backup(local_agents)
            print(f"Backed up local AGENTS.md to {saved}")
        shutil.copy2(remote_agents, local_agents)

    plugin_config = shared / "plugin-config.toml"
    local_config = home / "config.toml"
    if plugin_config.exists() and local_config.exists():
        old = local_config.read_text(encoding="utf-8")
        new = replace_plugin_blocks(old, plugin_config.read_text(encoding="utf-8"))
        if new != old:
            saved = backup(local_config)
            local_config.write_text(new, encoding="utf-8")
            print(f"Updated plugin blocks in config.toml; backup: {saved}")


def export_to_vault(vault: Path) -> None:
    home = codex_home()
    shared = vault / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    legacy_shared_manifest = shared / "plugin-manifest.txt"
    if legacy_shared_manifest.exists():
        legacy_shared_manifest.unlink()

    skills_src = home / "skills"
    skills_dst = shared / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    allowed_skill_names: set[str] = set()
    if skills_src.exists():
        for child in skills_src.iterdir():
            if child.name in EXCLUDE_SKILL_DIRS or child.name not in SHARED_SKILL_ALLOWLIST or child.name.startswith("."):
                continue
            allowed_skill_names.add(child.name)
            target = skills_dst / child.name
            if child.is_dir():
                copy_tree(child, target, delete=True)
            elif child.is_file():
                shutil.copy2(child, target)
    for child in skills_dst.iterdir():
        if child.name not in allowed_skill_names:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    agents = home / "AGENTS.md"
    if agents.exists():
        shutil.copy2(agents, shared / "AGENTS.md")

    config = home / "config.toml"
    if config.exists():
        text = config.read_text(encoding="utf-8")
        (shared / "plugin-config.toml").write_text(extract_plugin_blocks(text), encoding="utf-8")
        profile = vault / "profiles" / machine_id()
        profile.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config, profile / "config.toml")

    write_plugin_manifest(vault)


def git_pull(vault: Path) -> None:
    if not (vault / ".git").exists():
        return
    if "origin" not in run(["git", "remote"], cwd=vault, check=False).stdout.split():
        return
    proc = run(["git", "pull", "--rebase", "origin", "main"], cwd=vault, check=False)
    if proc.returncode:
        proc = run(["git", "pull", "--rebase", "origin", "master"], cwd=vault, check=False)
    if proc.returncode:
        raise RuntimeError("Could not pull the sync vault. Resolve Git conflicts in " + str(vault))


def git_commit_push(vault: Path) -> bool:
    run(["git", "add", "."], cwd=vault)
    status = run(["git", "status", "--porcelain"], cwd=vault).stdout.strip()
    if status:
        run(["git", "commit", "-m", f"Sync Codex portable config from {machine_id()}"], cwd=vault)
    else:
        print("No vault changes to commit.")
    if "origin" in run(["git", "remote"], cwd=vault, check=False).stdout.split():
        branch = run(["git", "branch", "--show-current"], cwd=vault).stdout.strip() or "main"
        proc = run(["git", "push", "-u", "origin", branch], cwd=vault, check=False)
        if proc.returncode:
            print("Push failed. If the GitHub repo does not exist yet, create it as a private repo, then rerun sync.")
            print((proc.stderr or proc.stdout).strip())
            return False
        return True
    return False


def configure_git_identity(vault: Path) -> None:
    if not run(["git", "config", "user.name"], cwd=vault, check=False).stdout.strip():
        global_name = run(["git", "config", "--global", "user.name"], check=False).stdout.strip()
        run(["git", "config", "user.name", global_name or machine_id()], cwd=vault)
    if not run(["git", "config", "user.email"], cwd=vault, check=False).stdout.strip():
        global_email = run(["git", "config", "--global", "user.email"], check=False).stdout.strip()
        run(["git", "config", "user.email", global_email or f"{machine_id()}@local"], cwd=vault)


def cmd_init(args: argparse.Namespace) -> None:
    remote = remote_url(args.remote)
    if remote:
        save_remote(remote)
    vault = ensure_vault(remote)
    configure_git_identity(vault)
    print(f"Codex home: {codex_home()}")
    print(f"Sync vault: {vault}")
    print(f"Remote: {remote or '(none)'}")


def cmd_status(args: argparse.Namespace) -> None:
    remote = remote_url(args.remote)
    vault = ensure_vault(remote)
    print(f"Codex home: {codex_home()}")
    print(f"Sync vault: {vault}")
    print(f"Remote: {remote or '(none)'}")
    print(run(["git", "status", "--short"], cwd=vault, check=False).stdout.rstrip() or "Vault is clean.")


def cmd_pull(args: argparse.Namespace) -> None:
    remote = remote_url(args.remote)
    if remote:
        save_remote(remote)
    vault = ensure_vault(remote)
    configure_git_identity(vault)
    git_pull(vault)
    import_from_vault(vault)
    print("Pulled portable Codex content into this machine.")


def cmd_pull_mirror(args: argparse.Namespace) -> None:
    remote = remote_url(args.remote)
    if remote:
        save_remote(remote)
    vault = ensure_vault(remote)
    configure_git_identity(vault)
    git_pull(vault)
    import_from_vault(vault, mirror_skills=True)
    print("Pulled and mirrored portable Codex skills into this machine.")


def cmd_push(args: argparse.Namespace) -> None:
    remote = remote_url(args.remote)
    if remote:
        save_remote(remote)
    vault = ensure_vault(remote)
    configure_git_identity(vault)
    export_to_vault(vault)
    pushed = git_commit_push(vault)
    if pushed:
        print("Pushed this machine's portable Codex content to the remote vault.")
    else:
        print("Exported this machine's portable Codex content to the local vault.")


def cmd_sync(args: argparse.Namespace) -> None:
    remote = remote_url(args.remote)
    if remote:
        save_remote(remote)
    vault = ensure_vault(remote)
    configure_git_identity(vault)
    try:
        git_pull(vault)
        import_from_vault(vault)
    except RuntimeError as exc:
        print(exc)
        print("Continuing with local export; remote conflicts must be resolved manually.")
    export_to_vault(vault)
    pushed = git_commit_push(vault)
    if pushed:
        print("Codex portable sync finished and pushed to the remote vault.")
    else:
        print("Codex portable sync finished locally; remote push did not complete.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "sync", "push", "pull", "pull-mirror", "status"], nargs="?", default="sync")
    parser.add_argument("--remote", help="Git remote URL for the private sync vault.")
    args = parser.parse_args()
    try:
        {
            "init": cmd_init,
            "sync": cmd_sync,
            "push": cmd_push,
            "pull": cmd_pull,
            "pull-mirror": cmd_pull_mirror,
            "status": cmd_status,
        }[args.command](args)
        return 0
    except Exception as exc:
        print(f"codex-sync failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
