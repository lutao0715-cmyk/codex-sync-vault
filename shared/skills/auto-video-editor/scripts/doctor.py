#!/usr/bin/env python3
"""环境自检与一键修复。

只会往 skill 目录里写东西（bin/ 放二进制、.venv/ 放 python 依赖），
不碰系统目录，也不需要 Homebrew 或管理员权限。
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import ssl
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

SKILL_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = SKILL_ROOT / "bin"
VENV_DIR = SKILL_ROOT / ".venv"

# 按速度快慢排序，逐个尝试
MIRRORS = (
    "https://ffmpeg.martin-riedl.de/redirect/latest/macos/{arch}/release/{tool}.zip",
    "https://ffmpeg.martin-riedl.de/redirect/latest/linux/{arch}/release/{tool}.zip",
    "https://evermeet.cx/ffmpeg/getrelease/{path}",
)

TOOLS = ("ffmpeg", "ffprobe")


def _arch_tag() -> str:
    m = platform.machine().lower()
    if sys.platform == "darwin":
        return "arm64" if m in ("arm64", "aarch64") else "amd64"
    return "arm64" if m in ("arm64", "aarch64") else "amd64"


def _mirror_urls(tool: str) -> list[str]:
    arch = _arch_tag()
    urls = [
        MIRRORS[0].format(arch=arch, tool=tool),
        MIRRORS[1].format(arch=arch, tool=tool),
    ]
    if sys.platform == "darwin":
        urls.append(MIRRORS[2].format(path=tool if tool == "ffmpeg" else "ffprobe/zip"))
    else:
        urls.append(
            f"https://johnvansickle.com/ffmpeg/releases/{tool}-release-{arch}-static.tar.xz"
        )
    return urls


# ---------------------------------------------------------------------------


def doctor_report() -> dict:
    import ff  # noqa: PLC0415

    ff.reset_cache()
    report: dict = {"python": sys.version.split()[0], "platform": sys.platform,
                    "machine": platform.machine(), "skill_root": str(SKILL_ROOT)}
    ok = True
    for tool in TOOLS:
        entry: dict = {"path": None, "version": ""}
        try:
            path = ff.find_tool(tool)
            entry["path"] = str(path)
            proc = subprocess.run([str(path), "-version"], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, timeout=25)
            entry["version"] = (proc.stdout or "").splitlines()[0] if proc.stdout else ""
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc)
            ok = False
        report[tool] = entry

    try:
        import numpy  # noqa: PLC0415

        report["numpy"] = numpy.__version__
    except Exception:  # noqa: BLE001
        report["numpy"] = None

    report["ok"] = ok
    return report


def install_hint() -> str:
    return (
        "\n手动安装方式（任选其一）：\n"
        f"  1) 让我自动装：  python3 {SKILL_ROOT / 'scripts' / 'doctor.py'} --fix\n"
        "  2) 装了 Homebrew 的话：  brew install ffmpeg\n"
        f"  3) 自己下载静态包，把 ffmpeg / ffprobe 放进  {BIN_DIR}\n"
    )


def _download(url: str, dest: Path, echo: Callable[[str], None], label: str) -> bool:
    ctx = ssl.create_default_context()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "avx-doctor/1.0"})
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp, open(dest, "wb") as fh:
            total = int(resp.headers.get("Content-Length") or 0)
            got = 0
            last = -1
            while True:
                chunk = resp.read(262144)
                if not chunk:
                    break
                fh.write(chunk)
                got += len(chunk)
                if total:
                    pct = int(got * 100 / total)
                    if pct != last and pct % 5 == 0:
                        echo(f"  {label} {pct}%  ({got / 1e6:.0f}/{total / 1e6:.0f} MB)")
                        last = pct
        return dest.exists() and dest.stat().st_size > 1_000_000
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        echo(f"  {label} 下载失败：{exc}")
        return False


def _extract_binary(archive: Path, tool: str, dest: Path) -> bool:
    """从 zip / tar.xz 里把可执行文件挖出来。"""
    name = tool
    try:
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as zf:
                for member in zf.namelist():
                    if Path(member).name == name:
                        with zf.open(member) as src, open(dest, "wb") as out:
                            shutil.copyfileobj(src, out)
                        return True
            return False
        if archive.suffixes[-2:] == [".tar", ".xz"] or archive.suffix == ".xz":
            import tarfile  # noqa: PLC0415

            with tarfile.open(archive, "r:xz") as tf:
                for member in tf.getmembers():
                    if Path(member.name).name == name:
                        fh = tf.extractfile(member)
                        if fh is None:
                            continue
                        with open(dest, "wb") as out:
                            shutil.copyfileobj(fh, out)
                        return True
    except Exception:  # noqa: BLE001
        return False
    return False


def install_ffmpeg(echo: Callable[[str], None] = print) -> bool:
    """下载 ffmpeg / ffprobe 到 <skill>/bin/。"""
    from model import ensure_dir  # noqa: PLC0415

    ensure_dir(BIN_DIR)
    ok_all = True
    for tool in TOOLS:
        dest = BIN_DIR / tool
        if dest.exists() and os.access(dest, os.X_OK):
            echo(f"  {tool} 已存在，跳过。")
            continue

        echo(f"  安装 {tool} ……")
        done = False
        with tempfile.TemporaryDirectory() as td:
            archive = Path(td) / "pkg"
            for url in _mirror_urls(tool):
                host = url.split("/")[2]
                echo(f"    尝试 {host}")
                if not _download(url, archive, echo, tool):
                    continue
                if _extract_binary(archive, tool, dest):
                    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    echo(f"    完成 -> {dest}")
                    done = True
                    break
                echo(f"    {host} 的包里没找到 {tool}")
        if not done:
            ok_all = False
            echo(f"  {tool} 安装失败。")
    return ok_all


def _venv_python() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def install_numpy(echo: Callable[[str], None] = print) -> bool:
    """在 skill 自带 venv 里装 numpy。"""
    py = _venv_python()
    if not py.exists():
        echo("  创建虚拟环境……")
        base = sys.executable
        proc = subprocess.run([base, "-m", "venv", str(VENV_DIR)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if proc.returncode != 0:
            echo(f"  建 venv 失败：{proc.stdout[-400:]}")
            return False
        py = _venv_python()

    echo("  安装 numpy（节拍检测依赖）……")
    proc = subprocess.run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check",
                           "numpy"],
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        echo(f"  numpy 安装失败：{proc.stdout[-400:]}")
        return False
    echo("  numpy 就绪。")
    return True


def auto_install(echo: Callable[[str], None] = print) -> bool:
    echo("开始安装依赖……")
    ok_ff = install_ffmpeg(echo)
    ok_np = install_numpy(echo)
    report = doctor_report()
    echo("")
    if report["ok"]:
        echo("环境就绪。")
        echo(f"  ffmpeg  {report['ffmpeg']['version'][:60]}")
        echo(f"  numpy   {report.get('numpy')}")
        return True
    echo("仍有组件缺失，请检查上面的报错。")
    return ok_ff and ok_np


def main() -> int:
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(description="auto-video-editor 环境自检")
    ap.add_argument("--fix", action="store_true", help="自动下载缺失组件")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.json:
        print(json.dumps(doctor_report(), ensure_ascii=False, indent=2))
        return 0

    report = doctor_report()
    print("auto-video-editor 环境自检")
    print("=" * 52)
    for tool in TOOLS:
        e = report[tool]
        mark = "OK  " if e.get("path") else "缺失"
        print(f"  {tool:<8} {mark} {e.get('version', '')[:58]}")
        if e.get("path"):
            print(f"  {'':<8}      {e['path']}")
    print(f"  {'numpy':<8} {'OK  ' if report['numpy'] else '缺失'} {report['numpy'] or ''}")
    print(f"  {'python':<8} OK   {report['python']}")
    print("=" * 52)
    if report["ok"]:
        print("全部就绪。")
        return 0
    if args.fix:
        return 0 if auto_install() else 1
    print("有组件缺失。加 --fix 自动安装，或：")
    print(install_hint())
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
