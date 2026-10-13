"""素材分析：静音段、场景切换点、节拍点、波形包络。

所有分析都基于 ffmpeg 自身能力 + numpy，不依赖云端，音频不出本机。
"""

from __future__ import annotations

import math
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

import ff
from model import (
    LABEL_BEAT,
    LABEL_KEEP,
    LABEL_SCENE,
    LABEL_SILENCE,
    EditPlan,
    OutputSpec,
    SceneCut,
    Segment,
    SilenceRegion,
    complement,
    ensure_dir,
    merge_short,
)

try:
    import numpy as _np
except Exception:  # noqa: BLE001
    _np = None


def has_numpy() -> bool:
    return _np is not None


# ===========================================================================
# 1. 静音检测
# ===========================================================================

_SIL_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def detect_silence(
    path: str | Path,
    *,
    noise_db: float = -30.0,
    min_duration: float = 0.35,
    duration: float | None = None,
) -> list[SilenceRegion]:
    """用 ffmpeg silencedetect 找出静音区间。

    noise_db    低于该阈值的算静音（dB，负数；越小越严格）
    min_duration 持续多久才算一段静音
    """
    args = [str(ff.ffmpeg()), "-hide_banner", "-nostdin", "-v", "info", "-i", str(path)]
    if duration:
        args += ["-t", f"{duration:.4f}"]
    args += ["-vn", "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}", "-f", "null", "-"]

    proc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          text=True, errors="replace")
    text = proc.stderr or ""

    # 兜底：非 0 退出但拿到了部分输出也继续解析
    regions: list[SilenceRegion] = []
    open_start: float | None = None
    for line in text.splitlines():
        m = _SIL_START.search(line)
        if m:
            open_start = max(0.0, float(m.group(1)))
            continue
        m = _SIL_END.search(line)
        if m and open_start is not None:
            end = float(m.group(1))
            if end > open_start:
                regions.append(SilenceRegion(open_start, end))
            open_start = None

    # 音频尾部一直静音的情形
    if open_start is not None:
        total = duration or ff.probe(path).duration
        if total and total > open_start:
            regions.append(SilenceRegion(open_start, total))

    return regions


# ===========================================================================
# 2. 场景切换检测
# ===========================================================================

_PTS_TIME = re.compile(r"pts_time:\s*([\d.]+)")
_SCORE = re.compile(r"lavfi\.scene_score=\s*([\d.]+)")


def detect_scenes(
    path: str | Path,
    *,
    threshold: float = 0.30,
    min_scene: float = 0.6,
    duration: float | None = None,
) -> list[SceneCut]:
    """用 ffmpeg select=gt(scene,T) 找镜头切换点。

    threshold 0~1，越大越迟钝（只抓明显切换）
    min_scene 两个切换点之间的最短间隔，用于滤掉抖动
    """
    with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False, encoding="utf-8") as fh:
        meta_file = fh.name

    try:
        args = [str(ff.ffmpeg()), "-hide_banner", "-nostdin", "-v", "error", "-i", str(path)]
        if duration:
            args += ["-t", f"{duration:.4f}"]
        args += [
            "-an",
            "-filter:v", f"select='gt(scene,{threshold:.4f})',metadata=print:file={meta_file}",
            "-f", "null", "-",
        ]
        proc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                              text=True, errors="replace")

        raw: list[SceneCut] = []
        cur_time: float | None = None
        try:
            text = Path(meta_file).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        # 有些构建把 metadata 直接打到 stderr
        if not text:
            text = proc.stderr or ""

        for line in text.splitlines():
            mt = _PTS_TIME.search(line)
            if mt:
                cur_time = float(mt.group(1))
                continue
            ms = _SCORE.search(line)
            if ms and cur_time is not None:
                raw.append(SceneCut(cur_time, float(ms.group(1))))
                cur_time = None
    finally:
        try:
            Path(meta_file).unlink(missing_ok=True)
        except OSError:
            pass

    # 过滤 + 去抖
    out: list[SceneCut] = []
    for cut in sorted(raw, key=lambda c: c.time):
        if cut.time < 0.05:
            continue
        if out and cut.time - out[-1].time < min_scene:
            # 保留分数更高的那个
            if cut.score > out[-1].score:
                out[-1] = cut
            continue
        out.append(cut)
    return out


# ===========================================================================
# 3. 音频解码 / 节拍检测
# ===========================================================================


def decode_pcm_mono(
    path: str | Path,
    *,
    sample_rate: int = 22050,
    start: float | None = None,
    duration: float | None = None,
) -> "list[float] | Any":
    """把音轨解成单声道 PCM。有 numpy 时返回 ndarray(float32)，否则返回 list。"""
    args = [str(ff.ffmpeg()), "-hide_banner", "-nostdin", "-v", "error"]
    if start:
        args += ["-ss", f"{start:.4f}"]
    args += ["-i", str(path)]
    if duration:
        args += ["-t", f"{duration:.4f}"]
    args += ["-vn", "-ac", "1", "-ar", str(sample_rate),
             "-f", "f32le", "-acodec", "pcm_f32le", "-"]

    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    raw = proc.stdout or b""
    if _np is not None:
        return _np.frombuffer(raw, dtype="<f4")
    import struct  # noqa: PLC0415

    n = len(raw) // 4
    return list(struct.unpack(f"<{n}f", raw[: n * 4]))


def wavelet_peaks(
    path: str | Path,
    *,
    buckets: int = 900,
    sample_rate: int = 8000,
) -> dict[str, Any]:
    """给前端画波形用的峰值包络（每个 bucket 的 min/max/RMS）。"""
    data = decode_pcm_mono(path, sample_rate=sample_rate)
    n = len(data)
    if n == 0:
        return {"buckets": 0, "peaks": [], "duration": 0.0, "sample_rate": sample_rate}

    if _np is not None:
        y = _np.asarray(data, dtype=_np.float32)
        n = y.size
        buckets = max(1, min(buckets, n))
        edges = _np.linspace(0, n, buckets + 1).astype(int)
        peaks: list[list[float]] = []
        for i in range(buckets):
            a, b = edges[i], edges[i + 1]
            if b <= a:
                peaks.append([0.0, 0.0])
                continue
            chunk = y[a:b]
            amp = float(_np.abs(chunk).max())
            rms = float(_np.sqrt(_np.mean(chunk * chunk)))
            peaks.append([round(amp, 4), round(rms, 4)])
    else:
        step = max(1, n // buckets)
        peaks = []
        for i in range(0, n - step + 1, step):
            chunk = data[i:i + step]
            amp = max((abs(x) for x in chunk), default=0.0)
            rms = math.sqrt(sum(x * x for x in chunk) / len(chunk))
            peaks.append([round(amp, 4), round(rms, 4)])

    return {
        "buckets": len(peaks),
        "peaks": peaks,
        "duration": round(n / sample_rate, 4),
        "sample_rate": sample_rate,
    }


def detect_beats(
    path: str | Path,
    *,
    sensitivity: float = 1.0,
    min_gap: float = 0.14,
    sample_rate: int = 22050,
    hop: int = 512,
    win: int = 1024,
    max_seconds: float = 900.0,
) -> list[float]:
    """基于谱通量（spectral flux）的节拍/重音点检测。

    返回秒数列表。需要 numpy；缺失时抛 RuntimeError。
    """
    if _np is None:
        raise RuntimeError("节拍检测需要 numpy，请先运行 doctor.py 修复环境。")

    np = _np
    data = decode_pcm_mono(path, sample_rate=sample_rate, duration=max_seconds)
    y = np.asarray(data, dtype=np.float32)
    if y.size < win * 2:
        return []

    n_frames = 1 + (y.size - win) // hop
    window = np.hanning(win).astype(np.float32)

    flux = np.empty(max(0, n_frames - 1), dtype=np.float32)
    block = 512  # 分块做 FFT，避免长音频一次性吃满内存
    prev_mag: Any = None
    w = 0
    while w < n_frames:
        hi = min(w + block, n_frames)
        idx = np.arange(win, dtype=np.int64)[None, :] + hop * np.arange(w, hi, dtype=np.int64)[:, None]
        frames = y[idx] * window
        mag = np.abs(np.fft.rfft(frames, axis=1)).astype(np.float32)
        if prev_mag is not None:
            stack = np.vstack([prev_mag[None, :], mag])
        else:
            stack = mag
        diff = np.maximum(0.0, np.diff(stack, axis=0)).sum(axis=1)
        if prev_mag is None:
            flux[0:max(0, hi - w - 1)] = diff
        else:
            flux[w - 1:hi - 1] = diff
        prev_mag = mag[-1]
        w = hi

    # 归一化 + 轻度平滑
    if flux.size == 0:
        return []
    peak = float(flux.max())
    if peak <= 0:
        return []
    flux = flux / peak
    k = 3
    kernel = np.ones(k, dtype=np.float32) / k
    flux = np.convolve(flux, kernel, mode="same")

    # 自适应阈值：局部均值 * sensitivity
    radius = 16
    pad = np.pad(flux, radius, mode="edge")
    csum = np.cumsum(np.concatenate([[0.0], pad.astype(np.float64)]))
    local_mean = (csum[2 * radius + 1:] - csum[:-(2 * radius + 1)]) / (2 * radius + 1)
    thr = local_mean * (1.15 + 0.35 * sensitivity) + 0.012

    times: list[float] = []
    last_t = -1e9
    for i in range(1, flux.size - 1):
        v = float(flux[i])
        if v < thr[i]:
            continue
        if v < flux[i - 1] or v < flux[i + 1]:
            continue
        t = (i * hop + win / 2) / sample_rate
        if t - last_t < min_gap:
            continue
        times.append(round(t, 4))
        last_t = t
    return times


def estimate_tempo(beats: Sequence[float]) -> float:
    """从节拍间隔粗估 BPM。"""
    if len(beats) < 4:
        return 0.0
    gaps = [b - a for a, b in zip(beats, beats[1:]) if 0.05 < (b - a) < 2.0]
    if not gaps:
        return 0.0
    gaps.sort()
    med = gaps[len(gaps) // 2]
    if med <= 0:
        return 0.0
    bpm = 60.0 / med
    while bpm < 60:
        bpm *= 2
    while bpm > 200:
        bpm /= 2
    return round(bpm, 1)


# ===========================================================================
# 4. 缩略图
# ===========================================================================


def extract_thumb(
    path: str | Path,
    time: float,
    out: str | Path,
    *,
    width: int = 200,
) -> Path | None:
    """在指定时间点截一帧。失败返回 None（不抛异常拖垮整批）。"""
    out = Path(out)
    ensure_dir(out.parent)
    args = [
        str(ff.ffmpeg()), "-hide_banner", "-nostdin", "-v", "error",
        "-ss", f"{max(0.0, time):.4f}", "-i", str(path),
        "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "5", "-y", str(out),
    ]
    proc = subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return out if proc.returncode == 0 and out.exists() else None


def extract_thumbs(
    path: str | Path,
    times: Sequence[float],
    out_dir: str | Path,
    *,
    width: int = 200,
    limit: int = 60,
) -> list[dict[str, Any]]:
    """批量截帧，返回 [{time, file}, ...]。"""
    out_dir = Path(out_dir)
    ensure_dir(out_dir)
    results: list[dict[str, Any]] = []
    for i, t in enumerate(list(times)[:limit]):
        fp = out_dir / f"t_{i:04d}.jpg"
        got = extract_thumb(path, t, fp, width=width)
        if got:
            results.append({"time": round(float(t), 4), "file": got.name})
    return results


# ===========================================================================
# 5. 三种自动剪辑方案生成
# ===========================================================================


def plan_from_silence(
    path: str | Path,
    *,
    noise_db: float = -30.0,
    min_silence: float = 0.35,
    padding: float = 0.06,
    min_keep: float = 0.25,
    silence_mode: str = "cut",
    silence_speed: float = 4.0,
    duration: float | None = None,
) -> EditPlan:
    """去静音剪辑。

    silence_mode "cut"   直接删掉静音段
                 "speed" 静音段高速播放（保留时间连续性，适合口播）
    padding      每个切除边界多切一点点，避免爆音残留
    min_keep     短于此长度的保留段会被并进邻居，防止碎片化
    """
    info = ff.probe(path)
    total = duration or info.duration
    regions = detect_silence(path, noise_db=noise_db, min_duration=min_silence, duration=total)

    segs: list[Segment] = []
    if silence_mode == "speed":
        cursor = 0.0
        for r in regions:
            if r.start > cursor + 1e-6:
                segs.append(Segment(cursor, r.start, 1.0, LABEL_KEEP, 0, "正常段"))
            segs.append(Segment(r.start, r.end, silence_speed, LABEL_SILENCE, 0, "静音加速"))
            cursor = r.end
        if total > cursor + 1e-6:
            segs.append(Segment(cursor, total, 1.0, LABEL_KEEP, 0, "正常段"))
    else:
        keep = complement([(r.start, r.end) for r in regions], total, gap=padding)
        keep = merge_short(keep, min_keep, total=total)
        segs = [Segment(a, b, 1.0, LABEL_KEEP, 0, "保留") for a, b in keep]

    plan = EditPlan(
        sources=[str(Path(path))],
        segments=segs,
        output=OutputSpec(),
        mode="silence",
        title=f"{Path(path).stem} · 去静音",
        meta={
            "noise_db": noise_db,
            "min_silence": min_silence,
            "silence_mode": silence_mode,
            "silence_regions": [r.to_dict() for r in regions],
            "duration": round(total, 4),
        },
    )
    if not segs:
        plan.warnings.append("整段都被判定为静音，没有可保留的内容。")
    return plan.normalize()


def plan_from_scenes(
    path: str | Path,
    *,
    threshold: float = 0.30,
    min_scene: float = 0.6,
    drop_shorter_than: float = 0.0,
    duration: float | None = None,
) -> EditPlan:
    """按镜头切换自动切分。"""
    info = ff.probe(path)
    total = duration or info.duration
    cuts = detect_scenes(path, threshold=threshold, min_scene=min_scene, duration=total)

    bounds = [0.0] + [c.time for c in cuts] + [total]
    segs: list[Segment] = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        if b - a <= 1e-6:
            continue
        if drop_shorter_than > 0 and (b - a) < drop_shorter_than:
            continue
        segs.append(Segment(a, b, 1.0, LABEL_SCENE, 0, f"镜头 {i + 1}"))

    plan = EditPlan(
        sources=[str(Path(path))],
        segments=segs,
        output=OutputSpec(),
        mode="scene",
        title=f"{Path(path).stem} · 分镜",
        meta={
            "threshold": threshold,
            "min_scene": min_scene,
            "cuts": [c.to_dict() for c in cuts],
            "duration": round(total, 4),
        },
    )
    if len(segs) <= 1:
        plan.warnings.append("没有检测到明显的镜头切换，试试调低阈值。")
    return plan.normalize()


def plan_from_beats(
    path: str | Path | Sequence[str | Path],
    *,
    music: str | Path | None = None,
    sensitivity: float = 1.0,
    beats_per_cut: int = 1,
    stride: float = 1.35,
    lead_in: float = 0.0,
    max_segments: int = 400,
    duration: float | None = None,
) -> EditPlan:
    """卡点剪辑。

    单素材：在节拍点上跳剪（每段之间向前跳 stride 倍时长，制造跳跃感）。
    多素材：把素材按节拍依次排开（素材墙 / montage）。

    music  单独指定音乐；默认用第一个素材的音轨
    beats_per_cut  每几个节拍切一次（1=每拍，2=两拍一次）
    stride 跳剪步进倍率，1.0 表示源连续前进（无跳跃感）
    """
    srcs = [path] if isinstance(path, (str, Path)) else [Path(p) for p in path]
    srcs = [Path(p) for p in srcs]
    if not srcs:
        raise ValueError("至少需要一个素材")

    music_path = Path(music) if music else srcs[0]
    if not music_path.exists() and srcs[0].suffix.lower() in (".jpg", ".png", ".jpeg", ".webp"):
        raise ValueError("图片素材必须配合 music 参数使用")

    beats = detect_beats(music_path, sensitivity=sensitivity)
    # BPM 必须用完整节拍序列估，切片后再算会得到一半的数值
    bpm = estimate_tempo(beats)
    if beats_per_cut > 1:
        beats = beats[::beats_per_cut]
    if lead_in > 0:
        beats = [b for b in beats if b >= lead_in]
    if not beats:
        plan = EditPlan(sources=[str(p) for p in srcs], output=OutputSpec(),
                        mode="beat", title="卡点")
        plan.warnings.append("没有检测到节拍点，试试提高 sensitivity。")
        return plan

    music_info = ff.probe(music_path)
    music_end = music_info.duration or (beats[-1] + 0.5)

    # 切点：节拍点 + 收尾
    points = [b for b in beats if b < music_end - 0.05]
    points = points[: max_segments]
    bounds = points + [music_end]

    segs: list[Segment] = []
    if len(srcs) == 1:
        info = ff.probe(srcs[0])
        avail = duration or info.duration
        cursor = 0.0
        for i in range(len(bounds) - 1):
            out_len = bounds[i + 1] - bounds[i]
            if out_len <= 0.02:
                continue
            src_len = out_len * max(0.1, stride)
            if cursor + src_len > avail:
                cursor = 0.0  # 素材用尽则回头重来，保证卡点完整
                if src_len > avail:
                    src_len = avail
            if src_len <= 0.02:
                break
            segs.append(Segment(cursor, cursor + src_len, 1.0, LABEL_BEAT, 0, f"第 {i + 1} 拍"))
            cursor += src_len
    else:
        infos = [ff.probe(p) for p in srcs]
        for i in range(len(bounds) - 1):
            out_len = bounds[i + 1] - bounds[i]
            if out_len <= 0.02:
                continue
            si = i % len(srcs)
            avail = duration or infos[si].duration
            segs.append(Segment(0.0, min(out_len, avail), 1.0, LABEL_BEAT, si, f"第 {i + 1} 拍"))
            if out_len > avail:
                segs[-1].note += "（素材过短，已截断）"

    plan = EditPlan(
        sources=[str(p) for p in srcs],
        segments=segs,
        output=OutputSpec(),
        mode="beat",
        title="卡点成片",
        meta={
            "music": str(music_path),
            "music_duration": round(music_end, 4),
            "duration": round(duration or ff.probe(srcs[0]).duration, 4),
            "bpm": bpm,
            "beat_count": len(beats),
            "beats": [round(b, 4) for b in beats],
            "beats_per_cut": beats_per_cut,
            "stride": stride,
        },
    )
    plan.warnings.append(
        f"检测到 {len(beats)} 个节拍点，粗估 {bpm} BPM。"
        "卡点是主观活，成片后多半还要手调几个点。"
    )
    return plan.normalize()


# ===========================================================================
# 6. 统一入口
# ===========================================================================


def analyze(
    path: str | Path,
    *,
    do_silence: bool = True,
    do_scenes: bool = True,
    do_beats: bool = True,
    silence_kwargs: dict | None = None,
    scene_kwargs: dict | None = None,
    beat_kwargs: dict | None = None,
    wave_buckets: int = 900,
) -> dict[str, Any]:
    """一次性把素材分析结果全给前端。"""
    info = ff.probe(path)
    out: dict[str, Any] = {
        "ok": True,
        "media": {
            "path": str(info.path),
            "name": info.path.name,
            "duration": round(info.duration, 4),
            "size": info.size,
            "width": info.width,
            "height": info.height,
            "fps": round(info.fps, 4),
            "has_video": info.has_video,
            "has_audio": info.has_audio,
            "video_codec": info.video.codec if info.video else "",
            "audio_codec": info.audio.codec if info.audio else "",
            "summary": info.summary(),
        },
        "waveform": wavelet_peaks(path, buckets=wave_buckets) if info.has_audio else None,
        "silence": None,
        "scenes": None,
        "beats": None,
        "numpy": has_numpy(),
    }

    if do_silence and info.has_audio:
        kw = {"noise_db": -30.0, "min_duration": 0.35}
        kw.update(silence_kwargs or {})
        regions = detect_silence(path, duration=info.duration, **kw)
        out["silence"] = {
            "regions": [r.to_dict() for r in regions],
            "total": round(sum(r.duration for r in regions), 4),
            "count": len(regions),
        }

    if do_scenes and info.has_video:
        kw = {"threshold": 0.30, "min_scene": 0.6}
        kw.update(scene_kwargs or {})
        cuts = detect_scenes(path, duration=info.duration, **kw)
        out["scenes"] = {
            "cuts": [c.to_dict() for c in cuts],
            "count": len(cuts),
        }

    if do_beats and info.has_audio:
        kw = {"sensitivity": 1.0}
        kw.update(beat_kwargs or {})
        try:
            beats = detect_beats(path, **kw)
            out["beats"] = {
                "times": beats,
                "count": len(beats),
                "bpm": estimate_tempo(beats),
            }
        except RuntimeError as exc:
            out["beats"] = {"error": str(exc), "times": [], "count": 0, "bpm": 0.0}

    return out
