"""ffmpeg / ffprobe 定位与调用封装。

定位优先级：
  1. 环境变量 AVX_FFMPEG / AVX_FFPROBE
  2. <skill>/bin/ffmpeg（随 skill 分发的静态二进制）
  3. PATH
  4. 常见安装位置
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

def _locate_skill_root() -> Path:
    """找 skill 根目录：从本文件往上，第一个放着 SKILL.md 的那一层。

    不写死层级。这套脚本在开发期放在 scripts/ 子包里、发布版是 scripts/ 平铺，
    写死 parents[N] 会在挪目录时静默指错地方——表现为「找不到 ffmpeg」，
    查半天才发现是根目录算错了。
    """
    here = Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / "SKILL.md").is_file():
            return cand
    return here.parent  # 兜底：scripts/ 的上一层


SKILL_ROOT = _locate_skill_root()
BIN_DIR = SKILL_ROOT / "bin"

_FFMPEG: Path | None = None
_FFPROBE: Path | None = None

COMMON_DIRS = (
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/opt/local/bin",
    "/usr/bin",
    "/snap/bin",
)


class FFmpegNotFound(RuntimeError):
    """找不到可用的 ffmpeg / ffprobe。"""


class FFmpegError(RuntimeError):
    """ffmpeg 执行失败。"""

    def __init__(self, cmd: Sequence[str], code: int, stderr: str):
        self.cmd = list(cmd)
        self.code = code
        self.stderr = stderr
        tail = "\n".join(stderr.strip().splitlines()[-25:])
        super().__init__(f"ffmpeg 退出码 {code}\n命令: {' '.join(self.cmd[:6])} ...\n{tail}")


def _candidates(name: str) -> Iterable[Path]:
    env = os.environ.get(f"AVX_{name.upper()}")
    if env:
        yield Path(env)
    yield BIN_DIR / name
    yield BIN_DIR / f"{name}.exe"
    which = shutil.which(name)
    if which:
        yield Path(which)
    for d in COMMON_DIRS:
        yield Path(d) / name
        yield Path(d) / f"{name}.exe"


def find_tool(name: str) -> Path:
    """返回可执行的 ffmpeg / ffprobe 路径。"""
    tried: list[str] = []
    for cand in _candidates(name):
        tried.append(str(cand))
        try:
            if cand.is_file() and os.access(cand, os.X_OK):
                return cand
        except OSError:
            continue
    raise FFmpegNotFound(
        f"未找到 {name}。已尝试：\n  " + "\n  ".join(tried) + "\n"
        f"请运行  python3 {SKILL_ROOT / 'scripts' / 'doctor.py'}  进行环境修复。"
    )


def ffmpeg() -> Path:
    global _FFMPEG
    if _FFMPEG is None:
        _FFMPEG = find_tool("ffmpeg")
    return _FFMPEG


def ffprobe() -> Path:
    global _FFPROBE
    if _FFPROBE is None:
        _FFPROBE = find_tool("ffprobe")
    return _FFPROBE


def reset_cache() -> None:
    """清掉二进制路径缓存（装完二进制后调用）。"""
    global _FFMPEG, _FFPROBE
    _FFMPEG = _FFPROBE = None


def run(
    args: Sequence[str],
    *,
    timeout: float | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """跑一条 ffmpeg/ffprobe 命令，返回 CompletedProcess（文本模式）。"""
    cmd = [str(a) for a in args]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise FFmpegError(cmd, proc.returncode, proc.stderr or "")
    return proc


def run_ffmpeg(
    args: Sequence[str],
    *,
    timeout: float | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    return run([ffmpeg(), "-hide_banner", "-nostdin", *args], timeout=timeout, check=check)


def run_bytes(
    args: Sequence[str],
    *,
    timeout: float | None = None,
    check: bool = True,
    input_bytes: bytes | None = None,
) -> subprocess.CompletedProcess:
    """跑一条命令并拿二进制 stdout。

    需要把 PCM 直接读进 numpy 时用它：run() 是 text 模式，
    stdout 会是 str，喂给 np.frombuffer 会报 TypeError。
    input_bytes 用于往 stdin 灌原始 PCM。
    """
    cmd = [str(a) for a in args]
    proc = subprocess.run(
        cmd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise FFmpegError(cmd, proc.returncode, (proc.stderr or b"").decode("utf-8", "replace"))
    return proc


# --------------------------------------------------------------------------
# 媒体信息
# --------------------------------------------------------------------------


def _parse_fps(rate: str | None) -> float:
    if not rate or rate in ("0/0", "N/A"):
        return 0.0
    if "/" in rate:
        num, _, den = rate.partition("/")
        try:
            n, d = float(num), float(den)
            return n / d if d else 0.0
        except ValueError:
            return 0.0
    try:
        return float(rate)
    except ValueError:
        return 0.0


@dataclass
class StreamInfo:
    index: int
    kind: str  # video / audio
    codec: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    pix_fmt: str = ""
    duration: float = 0.0
    bit_rate: int = 0
    rotation: int = 0
    raw: dict = field(default_factory=dict)


@dataclass
class MediaInfo:
    path: Path
    duration: float = 0.0
    size: int = 0
    format_name: str = ""
    video: StreamInfo | None = None
    audio: StreamInfo | None = None

    @property
    def has_video(self) -> bool:
        return self.video is not None

    @property
    def has_audio(self) -> bool:
        return self.audio is not None

    @property
    def width(self) -> int:
        return self.video.width if self.video else 0

    @property
    def height(self) -> int:
        return self.video.height if self.video else 0

    @property
    def fps(self) -> float:
        return self.video.fps if self.video else 0.0

    @property
    def is_portrait(self) -> bool:
        return self.height > self.width

    def summary(self) -> str:
        parts = [f"{self.path.name}  {self.duration:.2f}s  {self.size / 1e6:.1f}MB"]
        if self.video:
            parts.append(
                f"视频 {self.video.width}x{self.video.height}@{self.video.fps:.3g} "
                f"{self.video.codec}"
            )
        if self.audio:
            parts.append(
                f"音频 {self.audio.codec} {self.audio.sample_rate}Hz "
                f"{self.audio.channels}ch"
            )
        if not self.has_video and not self.has_audio:
            parts.append("(无可用流)")
        return " | ".join(parts)


_ROT_RE = re.compile(r"rotate\s*:\s*(-?\d+)")


def probe(path: os.PathLike | str) -> MediaInfo:
    """读取媒体元信息。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"文件不存在：{p}")

    proc = run(
        [
            ffprobe(),
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(p),
        ],
        check=False,
    )
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        raise FFmpegError([str(ffprobe()), str(p)], proc.returncode, proc.stderr or "")

    data = json.loads(proc.stdout)
    fmt = data.get("format") or {}

    info = MediaInfo(
        path=p,
        duration=float(fmt.get("duration") or 0.0),
        size=int(fmt.get("size") or p.stat().st_size),
        format_name=str(fmt.get("format_name") or ""),
    )

    for st in data.get("streams") or []:
        kind = st.get("codec_type")
        if kind not in ("video", "audio"):
            continue
        # 跳过封面图流
        if kind == "video" and st.get("disposition", {}).get("attached_pic"):
            continue

        rotation = 0
        for sd in st.get("side_data_list") or []:
            if "rotation" in sd:
                try:
                    rotation = int(float(sd["rotation"])) % 360
                except (TypeError, ValueError):
                    pass
        for tag, val in (st.get("tags") or {}).items():
            if tag.lower() == "rotate":
                m = _ROT_RE.match(str(val))
                if m:
                    rotation = int(m.group(1)) % 360

        si = StreamInfo(
            index=int(st.get("index", 0)),
            kind=kind,
            codec=str(st.get("codec_name") or ""),
            fps=_parse_fps(st.get("avg_frame_rate") or st.get("r_frame_rate")),
            sample_rate=int(st.get("sample_rate") or 0),
            channels=int(st.get("channels") or 0),
            pix_fmt=str(st.get("pix_fmt") or ""),
            duration=float(st.get("duration") or 0.0),
            bit_rate=int(st.get("bit_rate") or 0),
            rotation=rotation,
            raw=st,
        )
        if kind == "video":
            si.width = int(st.get("width") or 0)
            si.height = int(st.get("height") or 0)
            if rotation in (90, 270):
                si.width, si.height = si.height, si.width
            if info.video is None:
                info.video = si
        else:
            if info.audio is None:
                info.audio = si

    if not info.duration:
        cands = [s.duration for s in (info.video, info.audio) if s and s.duration]
        if cands:
            info.duration = max(cands)
    return info


# --------------------------------------------------------------------------
# 进度解析
# --------------------------------------------------------------------------


def parse_progress(line: str) -> dict:
    """解析 ffmpeg -progress 输出的 key=value 行。"""
    out: dict[str, str] = {}
    if "=" in line:
        k, _, v = line.strip().partition("=")
        out[k.strip()] = v.strip()
    return out


def hms(seconds: float, *, ms: bool = True) -> str:
    """秒 -> hh:mm:ss.mmm"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if ms:
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    return f"{h:02d}:{m:02d}:{int(s):02d}"


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024.0
    return f"{n:.1f}GB"


def describe_env() -> dict:
    """环境自检信息。"""
    out: dict = {"skill_root": str(SKILL_ROOT), "python": sys.version.split()[0]}
    for name in ("ffmpeg", "ffprobe"):
        try:
            p = find_tool(name)
            proc = run([p, "-version"], check=False, timeout=20)
            first = (proc.stdout or proc.stderr or "").splitlines()
            out[name] = {"path": str(p), "version": first[0] if first else "?"}
        except Exception as exc:  # noqa: BLE001
            out[name] = {"path": None, "error": str(exc)}
    try:
        import numpy  # noqa: PLC0415

        out["numpy"] = numpy.__version__
    except Exception:  # noqa: BLE001
        out["numpy"] = None
    return out
