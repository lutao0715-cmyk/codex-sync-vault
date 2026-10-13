"""把 EditPlan 编译成 ffmpeg filtergraph 并渲染出片。

一次渲染 = 一个 filter_complex 脚本（写成临时文件，避免命令行超长）。
视频链：每个 Segment 做 trim + setpts + 归一化，再 concat。
音频链：按 meta.audio_source 决定用拼接音轨、BGM、还是两者混音。

音频处理分两段插入，位置很关键：
  片段拼接 →[人声处理链]→ 与 BGM 混音 →[母带链]→ 输出
人声处理（降噪 / EQ / 压缩）放在混音之前，这样它只作用于人声，
不会把 BGM 一起压扁；母带（响度 / 限幅 / 淡入淡出）放在混音之后，
因为它管的是整条节目。

注意：ffmpeg 里同名的输出标签不能定义两次，所以音频后处理一律以
「链」的形式追加，而不是重新定义 [outa]。
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Sequence

import audio as A
import ff
from audio import AudioSpec
from model import EditPlan, OutputSpec, ensure_dir

ProgressCb = Callable[[dict[str, Any]], None]

_SPEED_MIN = 0.5
_SPEED_MAX = 2.0

_FG_MODE: str | None = None

# 纯音频导出：后缀 -> 音频编码器。
# 不在这里指定容器格式名——ffmpeg 按输出扩展名自动推断最稳，
# 手写格式名反而容易踩坑（比如 "m4a" 是扩展名不是 muxer 名，
# 真正的 muxer 叫 ipod，写 -f m4a 会直接报 Requested output format is not known）。
_AUDIO_CODECS: dict[str, str] = {
    ".m4a": "aac",
    ".mp4": "aac",
    ".aac": "aac",
    ".mp3": "libmp3lame",
    ".wav": "pcm_s16le",
    ".flac": "flac",
    ".opus": "libopus",
    ".ogg": "libvorbis",
    ".mka": "flac",
    ".mkv": "aac",
}


def filtergraph_file_mode() -> str:
    """探测当前 ffmpeg 支持的「从文件读 filtergraph」写法。

    ffmpeg 9 移除了 -filter_complex_script，改用通用的 -/opt 前缀语法。
    这里跑一次极小的探针实测，不靠版本号猜——各发行版裁剪情况不一样。
    返回值：slash | script | inline
    """
    global _FG_MODE
    if _FG_MODE is not None:
        return _FG_MODE

    with tempfile.NamedTemporaryFile("w", suffix=".filter", delete=False, encoding="utf-8") as fh:
        fh.write("[0:v]null[v]")
        probe_path = fh.name

    for mode, extra in (("slash", ["-/filter_complex", probe_path]),
                        ("script", ["-filter_complex_script", probe_path])):
        cmd = [str(ff.ffmpeg()), "-hide_banner", "-v", "error", "-y",
               "-f", "lavfi", "-i", "color=c=black:s=32x32:d=0.04", *extra,
               "-map", "[v]", "-f", "null", "-"]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if proc.returncode == 0:
            _FG_MODE = mode
            break
    if _FG_MODE is None:
        _FG_MODE = "inline"

    try:
        os.unlink(probe_path)
    except OSError:
        pass
    return _FG_MODE


def filtergraph_args(text: str, script_path: str | None = None) -> list[str]:
    """生成传入 filtergraph 的命令行参数。"""
    mode = filtergraph_file_mode()
    if mode == "inline" or not script_path:
        return ["-filter_complex", text]
    if mode == "slash":
        return ["-/filter_complex", script_path]
    return ["-filter_complex_script", script_path]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def atempo_chain(speed: float) -> list[str]:
    """把任意倍速拆成 ffmpeg atempo 支持的 0.5~2.0 链。"""
    s = float(speed)
    if s <= 0:
        s = 1.0
    parts: list[str] = []
    while s > _SPEED_MAX + 1e-9:
        parts.append(f"atempo={_SPEED_MAX:g}")
        s /= _SPEED_MAX
    while s < _SPEED_MIN - 1e-9:
        parts.append(f"atempo={_SPEED_MIN:g}")
        s /= _SPEED_MIN
    parts.append(f"atempo={s:.6g}")
    return parts


def _pick_dims(plan: EditPlan, infos: Sequence[ff.MediaInfo]) -> tuple[int, int]:
    if plan.output.width and plan.output.height:
        return plan.output.width, plan.output.height
    vids = [i for i in infos if i.has_video]
    if not vids:
        return 0, 0
    dims = {(i.width, i.height) for i in vids if i.width}
    if not dims:
        return 0, 0
    if len(dims) == 1:
        w, h = next(iter(dims))
        return w - (w % 2), h - (h % 2)
    # 多素材尺寸不一致：统一到面积最大的那个
    w, h = max(dims, key=lambda d: d[0] * d[1])
    return w - (w % 2), h - (h % 2)


def _pick_fps(plan: EditPlan, infos: Sequence[ff.MediaInfo]) -> float:
    if plan.output.fps:
        return plan.output.fps
    vids = [i.fps for i in infos if i.has_video and i.fps]
    return round(max(vids), 6) if vids else 0.0


def _audio_codec_for(out_path: Path) -> str:
    """按后缀选音频编码器。未知后缀退回 aac（容器由 ffmpeg 按扩展名推断）。"""
    return _AUDIO_CODECS.get(out_path.suffix.lower(), "aac")


# ---------------------------------------------------------------------------
# filtergraph 构建
# ---------------------------------------------------------------------------


def _latency_compensation(chain: list[str]) -> list[str]:
    """给一条音频链补上它自己的固有延迟。

    afftdn 这类 FFT 滤波器要缓存前瞻样本，输出相对输入会整体后移。
    实测 afftdn 在 48kHz 下后移 24ms——肉眼能看出唇音不同步。
    修法是把开头的这段前瞻静音切掉，让时间轴重新对齐。

    延迟是实测出来的，不是写死的：不同滤波器、不同采样率的延迟都不一样，
    写死会在换档位时静默失效。measure_chain_latency() 用脉冲探针量。

    代价是音轨末尾会短掉同样的 24ms。相比「整条音轨错位 24ms」，
    「末尾少 24ms」可以忽略不计，而且 mux 时视频轨更长，不影响播放。
    """
    lat = A.measure_chain_latency(chain)
    if lat <= 0.0005:
        return []
    return [f"atrim=start={lat:.4f}", "asetpts=PTS-STARTPTS"]


def build_filtergraph(
    plan: EditPlan,
    infos: Sequence[ff.MediaInfo],
    *,
    out_w: int,
    out_h: int,
    fps: float,
    music_index: int | None,
    total_out: float,
    audio_only: bool = False,
    measured: dict | None = None,
    loudnorm_probe: bool = False,
) -> tuple[str, list[str]]:
    """返回 (filtergraph 文本, 输出映射标签列表)。

    measured: 两遍 loudnorm 第一遍量到的实测值，喂给第二遍做定标。
    loudnorm_probe: 探测模式。只跑到 loudnorm 为止、且不出画面，
    专门用来量「进入 loudnorm 的信号」。视频链此时完全不建，
    否则探测一遍要顺带把视频也解一遍，白白多花几倍时间。
    """
    lines: list[str] = []
    v_maps: list[str] = []
    a_maps: list[str] = []

    probe_only = loudnorm_probe
    all_have_audio = all(i.has_audio for i in infos)
    all_have_video = all(i.has_video for i in infos)
    do_video = all_have_video and not audio_only and not probe_only

    if not do_video and not audio_only and not probe_only and any(i.has_video for i in infos):
        raise ValueError("素材里既有带画面的文件又有纯音频文件，请先统一格式。")
    if not do_video and not all_have_audio:
        raise ValueError("素材里没有任何音轨，导不出音频。")

    # ── 先定音源，再建链 ──────────────────────────────────────
    # 顺序很要紧：如果先给每段都建了音轨链、最后却只用 BGM，
    # 那些没人消费的 [aN] 标签会让 ffmpeg 报 "output unconnected" 直接罢工。
    audio_source = str(
        plan.meta.get("audio_source") or ("music" if plan.mode == "beat" else "concat")
    )
    if audio_source == "music" and music_index is None:
        audio_source = "concat" if all_have_audio else "none"
    if audio_source == "concat" and not all_have_audio:
        audio_source = "music" if music_index is not None else "none"
    if audio_source == "mix" and not (all_have_audio and music_index is not None):
        audio_source = "concat" if all_have_audio else (
            "music" if music_index is not None else "none"
        )

    need_seg_audio = audio_source in ("concat", "mix") and all_have_audio

    for idx, seg in enumerate(plan.segments):
        si = seg.source
        if si >= len(infos):
            raise ValueError(f"第 {idx} 段指向不存在的素材 #{si}")
        a, b = f"{seg.start:.4f}", f"{seg.end:.4f}"
        sp = max(0.1, float(seg.speed))

        if do_video:
            chain = [
                f"trim=start={a}:end={b}",
                "setpts=(PTS-STARTPTS)" + (f"/{sp:.6g}" if abs(sp - 1) > 1e-9 else ""),
            ]
            if out_w and out_h:
                chain.append(f"scale={out_w}:{out_h}:flags=bicubic")
            chain.append("setsar=1")
            if fps:
                chain.append(f"fps={fps}")
            chain.append("format=yuv420p")
            lines.append(f"[{si}:v]{','.join(chain)}[v{idx}]")
            v_maps.append(f"[v{idx}]")

        if need_seg_audio:
            achain = [f"atrim=start={a}:end={b}", "asetpts=PTS-STARTPTS"]
            if abs(sp - 1) > 1e-9:
                achain.extend(atempo_chain(sp))
            achain.append(
                "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
            )
            lines.append(f"[{si}:a]{','.join(achain)}[a{idx}]")
            a_maps.append(f"[a{idx}]")

    n = len(plan.segments)
    if n == 0:
        raise ValueError("剪辑计划里没有任何片段。")

    out_labels: list[str] = []

    # ---------------------------------------------------------------- 视频
    if do_video:
        if n == 1:
            lines.append(f"{v_maps[0]}null[outv]")
        else:
            lines.append("".join(v_maps) + f"concat=n={n}:v=1:a=0[outv]")
        out_labels.append("[outv]")

    # ---------------------------------------------------------------- 音频
    cur: str | None = None
    prelude: list[str] = []
    pre_voice: list[str] = []   # 人声处理，插在混音之前

    spec = plan.audio
    # 纯 BGM 的场合不做人声处理：降噪和 EQ 会把音乐一起毁掉
    voice_on = spec.is_active() and audio_source in ("concat", "mix")
    vchain = A.build_voice_chain(spec) if voice_on else []

    mchain = A.build_master_chain(
        normalize=plan.output.normalize_loudness,
        target_lufs=plan.output.target_lufs,
        true_peak=spec.true_peak,
        limiter=spec.limiter,
        fade_in=plan.output.fade_in,
        fade_out=plan.output.fade_out,
        total_out=total_out,
        measured=measured,
        probe=loudnorm_probe,
    )

    if audio_source == "music" and music_index is not None:
        # 整条节目就是 BGM：只做截断、增益、补齐，不套人声链
        pre = [f"atrim=start=0:end={total_out:.4f}", "asetpts=PTS-STARTPTS"]
        vol = float(plan.meta.get("music_volume", 1.0))
        if abs(vol - 1.0) > 1e-6:
            pre.append(f"volume={vol:.4g}")
        pre.append(f"apad=whole_dur={max(0.01, total_out):.4f}")
        prelude.append(f"[{music_index}:a]{','.join(pre)}[amus]")
        cur = "[amus]"

    elif audio_source == "concat" and need_seg_audio:
        if n == 1:
            prelude.append(f"{a_maps[0]}anull[acat]")
        else:
            prelude.append("".join(a_maps) + f"concat=n={n}:v=0:a=1[acat]")
        if vchain:
            # 处理完立刻把滤波器自身的延迟切掉，后面的时间轴才是准的
            prelude.append(
                f"[acat]{','.join(vchain + _latency_compensation(vchain))}[avoice]"
            )
            cur = "[avoice]"
        else:
            cur = "[acat]"

    elif audio_source == "mix" and music_index is not None and need_seg_audio:
        if n == 1:
            prelude.append(f"{a_maps[0]}anull[acat]")
        else:
            prelude.append("".join(a_maps) + f"concat=n={n}:v=0:a=1[acat]")
        # 人声先在混音前处理干净，再和 BGM 相加
        if vchain:
            prelude.append(
                f"[acat]{','.join(vchain + _latency_compensation(vchain))}[avoice]"
            )
            voice_label = "[avoice]"
        else:
            voice_label = "[acat]"
        mvol = float(plan.meta.get("music_volume", 1.0))
        ovol = float(plan.meta.get("original_volume", 0.35))
        prelude.append(
            f"[{music_index}:a]atrim=start=0:end={total_out:.4f},asetpts=PTS-STARTPTS,"
            f"volume={mvol:.4g},aformat=sample_fmts=fltp:sample_rates=48000:"
            "channel_layouts=stereo[abgm]"
        )
        prelude.append(f"{voice_label}volume={ovol:.4g}[aovol]")
        prelude.append(
            "[aovol][abgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[amixed]"
        )
        cur = "[amixed]"

    if cur is not None:
        lines.extend(prelude)
        lines.extend(pre_voice)
        lines.append(f"{cur}{','.join(mchain)}[outa]")
        out_labels.append("[outa]")

    return ";".join(lines), out_labels


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------


def _probe_loudnorm(
    plan: EditPlan,
    infos: Sequence[ff.MediaInfo],
    music_path: Path | None,
    total_out: float,
) -> dict | None:
    """两遍 loudnorm 的第一遍：量出「进 loudnorm 之前」的实测响度。

    为什么非要两遍：单遍 loudnorm 是动态模式，增益随时间自适应爬升，
    对长片没问题，但几秒的短片还没收敛就结束了，落点会偏——实测目标
    -16 LUFS 跑出 -14.5 LUFS，偏了 1.5dB。第二遍带上 measured_* 走
    linear 定标模式，增益是算出来的定值，落点才准。

    这一步只解析音频、不建视频链（probe 模式），所以很便宜：几秒的素材
    在百毫秒级。代价相对于「整片响度偏 1.5dB」完全值得。

    探测失败不抛异常——宁可退回单遍动态模式（落点差一点），
    也不要因为量不出数就整片渲染不出来。
    """
    probe_text, probe_labels = build_filtergraph(
        plan, infos,
        out_w=0, out_h=0, fps=0.0,
        music_index=len(plan.sources) if music_path else None,
        total_out=total_out,
        loudnorm_probe=True,
    )
    if not probe_labels:
        return None

    with tempfile.NamedTemporaryFile(
        "w", suffix=".filter", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(probe_text)
        fgraph = fh.name

    cmd: list[str] = [str(ff.ffmpeg()), "-hide_banner", "-nostdin", "-y"]
    for s in plan.sources:
        cmd += ["-i", str(s)]
    if music_path is not None:
        cmd += ["-i", str(music_path)]
    cmd += filtergraph_args(probe_text, fgraph)
    for label in probe_labels:
        cmd += ["-map", label]
    cmd += ["-f", "null", "-"]

    try:
        proc = ff.run(cmd, check=False, timeout=600)
    finally:
        try:
            os.unlink(fgraph)
        except OSError:
            pass

    if proc.returncode != 0:
        return None
    return A.parse_loudnorm_json(proc.stderr or "")


def render(
    plan: EditPlan,
    out_path: str | Path,
    *,
    music: str | Path | None = None,
    progress: ProgressCb | None = None,
    overrides: dict[str, Any] | None = None,
    audio_only: bool = False,
    measured: dict | None = None,
) -> Path:
    """按 EditPlan 渲染出片，返回输出文件路径。

    audio_only=True 时只导音轨（走同一套剪辑与处理链），用来快速试听
    音频处理效果，或者把一段素材提成音频文件。

    measured 可以传入已量好的 loudnorm 实测值来跳过第一遍探测
    （面板上「改一下参数再试听」时能省掉一次探测）。
    """
    work = EditPlan.from_dict(plan.to_dict())  # 深拷贝，避免污染调用方
    if overrides:
        merged = work.output.to_dict()
        merged.update({k: v for k, v in overrides.items() if k in merged})
        work.output = OutputSpec.from_dict(merged)
        ov_audio = overrides.get("audio")
        if isinstance(ov_audio, AudioSpec):
            work.audio = AudioSpec.from_dict(ov_audio.to_dict())
        elif isinstance(ov_audio, dict):
            work.audio = AudioSpec.from_dict({**work.audio.to_dict(), **ov_audio})

    if not work.sources:
        raise ValueError("计划里没有源文件。")
    infos = [ff.probe(p) for p in work.sources]
    work.normalize()
    if not work.segments:
        raise ValueError("计划里没有有效片段。")

    music_path: Path | None = None
    if music:
        music_path = Path(music)
    elif work.mode == "beat" and work.meta.get("music"):
        music_path = Path(str(work.meta["music"]))
    if music_path is not None and not music_path.exists():
        music_path = None

    has_video_out = all(i.has_video for i in infos) and not audio_only
    out_w, out_h = _pick_dims(work, infos)
    fps = _pick_fps(work, infos)
    total_out = work.total_out_duration

    music_index = len(work.sources) if music_path else None

    # 响度归一化走两遍：先量一遍，再带实测值定标。见 _probe_loudnorm 的说明。
    if measured is None and work.output.normalize_loudness:
        measured = _probe_loudnorm(work, infos, music_path, total_out)
        if progress and measured and measured.get("ok"):
            progress({
                "event": "probe",
                "input_i": measured["input_i"],
                "target": work.output.target_lufs,
            })

    filter_text, out_labels = build_filtergraph(
        work, infos,
        out_w=out_w if has_video_out else 0,
        out_h=out_h if has_video_out else 0,
        fps=fps if has_video_out else 0.0,
        music_index=music_index,
        total_out=total_out,
        audio_only=audio_only,
        measured=measured,
    )

    out_path = Path(out_path)
    ensure_dir(out_path.parent)

    with tempfile.NamedTemporaryFile("w", suffix=".filter", delete=False, encoding="utf-8") as fh:
        fh.write(filter_text)
        fgraph = fh.name

    cmd: list[str] = [str(ff.ffmpeg()), "-hide_banner", "-nostdin", "-y"]
    for s in work.sources:
        cmd += ["-i", str(s)]
    if music_path is not None:
        cmd += ["-i", str(music_path)]

    cmd += filtergraph_args(filter_text, fgraph)
    for label in out_labels:
        cmd += ["-map", label]

    if has_video_out:
        cmd += [
            "-c:v", "libx264",
            "-preset", work.output.preset,
            "-crf", str(work.output.crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]

    if audio_only:
        a_codec = _audio_codec_for(out_path)
        cmd += ["-c:a", a_codec]
        # 无损编码不设码率，设了也会被忽略
        if a_codec not in ("pcm_s16le", "flac"):
            cmd += ["-b:a", work.output.audio_bitrate]
    else:
        cmd += ["-c:a", "aac", "-b:a", work.output.audio_bitrate]

    cmd += [
        "-ar", "48000",
        "-ac", "2",
        "-threads", "0",
        "-progress", "pipe:1",
        "-nostats",
        str(out_path),
    ]

    started = time.time()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        bufsize=1,
    )

    state: dict[str, str] = {}
    assert proc.stdout is not None
    for line in proc.stdout:
        k, _, v = line.strip().partition("=")
        if not k:
            continue
        state[k] = v
        if progress and k in ("out_time_us", "out_time_ms"):
            try:
                done = float(v) / 1_000_000.0
            except ValueError:
                continue
            pct = (done / total_out * 100.0) if total_out > 0 else 0.0
            progress({
                "event": "progress",
                "percent": round(min(99.9, pct), 2),
                "done": round(done, 3),
                "total": round(total_out, 3),
                "speed": state.get("speed", "?"),
                "elapsed": round(time.time() - started, 1),
            })

    proc.wait()
    stderr_text = proc.stderr.read() if proc.stderr else ""
    try:
        os.unlink(fgraph)
    except OSError:
        pass

    if proc.returncode != 0:
        tail = "\n".join((stderr_text or "").strip().splitlines()[-30:])
        raise ff.FFmpegError(cmd, proc.returncode, tail)

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise ff.FFmpegError(cmd, proc.returncode, "输出文件为空。\n" + stderr_text[-2000:])

    if progress:
        progress({
            "event": "done",
            "percent": 100.0,
            "output": str(out_path),
            "size": out_path.stat().st_size,
            "elapsed": round(time.time() - started, 1),
        })
    return out_path


def render_preview(
    plan: EditPlan,
    out_path: str | Path,
    *,
    music: str | Path | None = None,
    width: int = 640,
    progress: ProgressCb | None = None,
) -> Path:
    """低清预览：只求快，用来验证剪辑节奏对不对得上。"""
    height = 0
    if plan.sources:
        try:
            info = ff.probe(plan.sources[0])
            if info.width:
                height = int(round(width * info.height / info.width / 2) * 2)
        except Exception:  # noqa: BLE001
            height = 0
    return render(
        plan, out_path,
        music=music,
        progress=progress,
        overrides={
            "width": width,
            "height": max(2, height),
            "crf": 30,
            "preset": "ultrafast",
            "audio_bitrate": "96k",
            # 预览要能听出音频处理的效果，所以只降视频规格，
            # 响度归一化关掉（否则不好判断自己设的增益对没对）
            "normalize_loudness": False,
        },
    )


def render_audio(
    plan: EditPlan,
    out_path: str | Path,
    *,
    music: str | Path | None = None,
    audio_overrides: dict[str, Any] | None = None,
    progress: ProgressCb | None = None,
) -> Path:
    """只导音轨。用于试听音频处理效果，或把素材直接提成音频文件。

    走的是和出片完全相同的剪辑 + 处理链，所以试听听到的就是最终结果，
    不存在「预览一套、导出另一套」的问题。
    """
    return render(
        plan, out_path,
        music=music,
        progress=progress,
        audio_only=True,
        overrides={"audio": audio_overrides} if audio_overrides else None,
    )
