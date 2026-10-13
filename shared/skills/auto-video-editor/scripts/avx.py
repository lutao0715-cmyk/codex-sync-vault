#!/usr/bin/env python3
"""avx —— 自动剪辑命令行入口。

用法速查：
  avx.py doctor                              环境自检 / 一键修复
  avx.py info   IN.mp4                       看素材信息
  avx.py analyze IN.mp4 --thumbs ./th        全量分析（静音+镜头+节拍+波形）
  avx.py auto   IN.mp4 -o OUT.mp4 --mode silence
  avx.py auto   IN.mp4 -o OUT.mp4 --mode scene --threshold 0.35
  avx.py auto   IN.mp4 -o OUT.mp4 --mode beat --music bgm.mp3 --beats-per-cut 2
  avx.py auto   IN.mp4 -o OUT.mp4 --audio-preset voice      # 顺带处理音频
  avx.py auto   IN.mp4 -o OUT.m4a --audio-only --mode silence  # 只出音轨
  avx.py audio  IN.wav -o OUT.m4a --preset voice           # 纯音频处理
  avx.py audio  IN.wav --measure                            # 只量不处理
  avx.py render plan.json -o OUT.mp4
  avx.py panel                               启动本地剪辑面板
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze as A  # noqa: E402
import audio as AU  # noqa: E402
import ff, render as R  # noqa: E402
from audio import AudioSpec  # noqa: E402
from model import EditPlan, OutputSpec, Segment  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm", ".flv", ".wmv", ".mpg", ".mpeg", ".ts"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}

# 从 PRESETS 派生，不手写。手写会漂移——之前这份列表就漏了 hum
# （面板走的是 PRESETS，能用 hum；CLI 走这份手写列表，用不了）。
AUDIO_PRESET_CHOICES = list(AU.PRESETS)

# argparse 参数名 -> AudioSpec 字段名
_AUDIO_ARG_MAP: tuple[tuple[str, str], ...] = (
    ("denoise", "denoise"),
    ("highpass", "highpass"),
    ("lowpass", "lowpass"),
    ("gate", "gate"),
    ("gate_db", "gate_db"),
    ("warmth", "warmth"),
    ("presence", "presence"),
    ("deess", "deess"),
    ("compress", "compress"),
    ("comp_db", "comp_db"),
    ("comp_ratio", "comp_ratio"),
    ("declick", "declick"),
    ("stereo", "stereo"),
    ("gain_db", "gain_db"),
    ("true_peak", "true_peak"),
)


def _echo(msg: str) -> None:
    print(msg, file=sys.stderr)


def _progress(prefix: str = "") -> object:
    def cb(ev: dict) -> None:
        if ev.get("event") == "progress":
            bar = "#" * int(ev["percent"] / 4)
            sys.stderr.write(
                f"\r{prefix}[{bar:<25}] {ev['percent']:5.1f}%  "
                f"{ev['done']:.1f}/{ev['total']:.1f}s  x{ev.get('speed', '?')}   "
            )
            sys.stderr.flush()
        elif ev.get("event") == "done":
            sys.stderr.write(
                f"\r{prefix}[{'#' * 25}] 100.0%  "
                f"完成 {ev['size'] / 1e6:.1f}MB / {ev['elapsed']}s\n"
            )
            sys.stderr.flush()
    return cb


def collect_media(paths: list[str]) -> list[str]:
    """接受文件或目录，展开成排好序的素材列表。"""
    out: list[str] = []
    for p in paths:
        pp = Path(p).expanduser()
        if pp.is_dir():
            items = sorted(
                [q for q in pp.iterdir() if q.suffix.lower() in VIDEO_EXT | AUDIO_EXT]
            )
            out.extend(str(q) for q in items)
        else:
            out.append(str(pp))
    return out


# ---------------------------------------------------------------------------
# 音频参数
# ---------------------------------------------------------------------------


def add_audio_args(sp: argparse.ArgumentParser) -> None:
    """音频处理参数。全部默认 None，用来区分「没传」和「传了默认值」。"""
    g = sp.add_argument_group("音频处理")
    g.add_argument("--audio-preset", choices=AUDIO_PRESET_CHOICES, default=None,
                   help="一键预设：voice 口播 / interview 访谈 / outdoor 户外 / "
                        "rescue 抢救 / music 音乐为主 / off 不处理")
    g.add_argument("--denoise", choices=["none", "light", "standard", "strong"],
                   default=None,
                   help="降噪档位。注意 strong 不是「更狠的降噪」，而是"
                        "「标准降噪 + 一道 -38dB 噪声门」——实测加深降噪"
                        "只会连人声一起削")
    g.add_argument("--highpass", type=float, default=None, help="低切 Hz，人声常用 80~120")
    g.add_argument("--lowpass", type=float, default=None, help="高切 Hz")
    g.add_argument("--gate", action="store_true", default=None,
                   help="开噪声门。门限必须高于实际底噪，否则不会动作")
    g.add_argument("--gate-db", type=float, default=None,
                   help="噪声门门限 dB。要先量素材底噪，一般比底噪高 3~6dB")
    g.add_argument("--warmth", type=float, default=None, help="200Hz 增益 dB，胸腔共鸣")
    g.add_argument("--presence", type=float, default=None, help="3.2kHz 增益 dB，人声清晰度")
    g.add_argument("--deess", type=float, default=None, help="7kHz 增益 dB，衰减齿音要填负值")
    g.add_argument("--compress", action="store_true", default=None, help="开压缩器")
    g.add_argument("--comp-db", type=float, default=None, help="压缩门限 dB")
    g.add_argument("--comp-ratio", type=float, default=None, help="压缩比")
    g.add_argument("--declick", action="store_true", default=None, help="削波修复")
    g.add_argument("--stereo", choices=["keep", "center_boost", "center_remove", "mono"],
                   default=None,
                   help="center_boost 人声靠前 / center_remove 去人声做伴奏")
    g.add_argument("--gain-db", type=float, default=None, help="整体增益 dB")
    g.add_argument("--true-peak", type=float, default=None, help="限幅上限 dBTP，默认 -1.5")
    g.add_argument("--no-limiter", action="store_true", default=None, help="关掉限幅器")


def audio_from_args(args: argparse.Namespace) -> AudioSpec:
    """先套预设，再用显式传的单项参数覆盖。"""
    spec = AudioSpec()
    preset = getattr(args, "audio_preset", None)
    if preset:
        AU.apply_preset(spec, preset)
    for arg_name, field in _AUDIO_ARG_MAP:
        val = getattr(args, arg_name, None)
        if val is not None:
            setattr(spec, field, val)
    if getattr(args, "no_limiter", None):
        spec.limiter = False
    return spec


def _print_audio_summary(spec: AudioSpec, prefix: str = "") -> None:
    items = spec.active_list()
    print(f"{prefix}音频处理    {'、'.join(items) if items else '关闭（原样保留）'}")
    for w in spec.warnings():
        print(f"{prefix}⚠           {w}")


def has_audio_args(args: argparse.Namespace) -> bool:
    """命令行是否显式动过音频参数。"""
    if getattr(args, "audio_preset", None) or getattr(args, "no_limiter", None):
        return True
    return any(getattr(args, name, None) is not None for name, _ in _AUDIO_ARG_MAP)


def cmd_audio(args: argparse.Namespace) -> int:
    """纯音频处理：不涉及视频，直接把素材过一遍处理链。"""
    sources = collect_media(args.input)
    if not sources:
        raise SystemExit("没有找到任何素材。")

    spec = audio_from_args(args)

    # 多文件按顺序首尾相接
    segs: list[Segment] = []
    for i, p in enumerate(sources):
        info = ff.probe(p)
        if info.duration <= 0:
            raise SystemExit(f"{p} 读不出时长。")
        segs.append(Segment(0.0, info.duration, label="keep", source=i))
        if not info.has_audio:
            raise SystemExit(f"{p} 没有音轨。")

    plan = EditPlan(
        sources=sources, segments=segs, mode="manual",
        title="音频处理" if len(sources) == 1 else f"音频拼接（{len(sources)} 个文件）",
    )
    plan.audio = spec
    plan.output.normalize_loudness = not args.no_loudnorm
    plan.output.target_lufs = args.loudnorm_target
    plan.output.fade_in = args.fade_in or 0.0
    plan.output.fade_out = args.fade_out or 0.0
    plan.output.audio_bitrate = args.audio_bitrate

    st = plan.stats()
    print(f"素材        {len(sources)} 个，共 {st['output_duration']:.2f}s")
    _print_audio_summary(spec)
    print(f"响度归一化  {'开，目标 ' + str(args.loudnorm_target) + ' LUFS' if plan.output.normalize_loudness else '关'}")

    if args.measure:
        print("\n--- 处理前 ---")
        _print_measurements(sources[0])
        if not args.output:
            return 0

    if not args.output:
        print("\n（没给 -o，只做了参数检查，没有输出文件）")
        return 0

    _echo("开始处理……")
    out = R.render_audio(plan, args.output, progress=_progress())
    print(f"输出        {out}")

    if args.measure:
        print("\n--- 处理后 ---")
        _print_measurements(out)
    return 0


def _print_measurements(path: str | Path) -> None:
    loud = AU.measure_loudness(path)
    nf = AU.measure_noise_floor(path)
    if loud.get("ok"):
        print(f"  响度      {loud['input_i']:>7.2f} LUFS   "
              f"真峰值 {loud['input_tp']:>6.2f} dBTP   "
              f"动态范围 {loud['input_lra']:>5.2f} LU")
    else:
        print(f"  响度      读取失败：{loud.get('error')}")
    if nf.get("ok"):
        print(f"  底噪      {nf['noise_floor_db']:>7.1f} dB   "
              f"信号 {nf['signal_db']:>6.1f} dB   SNR {nf['snr_db']:>5.1f} dB")
    else:
        print(f"  底噪      读取失败：{nf.get('error')}")


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------


def cmd_doctor(args: argparse.Namespace) -> int:
    from doctor import doctor_report, auto_install, install_hint  # noqa: PLC0415

    report = doctor_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    print("环境自检")
    print("-" * 46)
    for name in ("ffmpeg", "ffprobe"):
        st = report.get(name, {})
        if st.get("path"):
            print(f"  {name:<8} OK      {st.get('version', '')[:60]}")
            print(f"  {'':<8}         {st['path']}")
        else:
            print(f"  {name:<8} 缺失")
    np_ver = report.get("numpy")
    print(f"  {'numpy':<8} {'OK      ' + np_ver if np_ver else '缺失（节拍检测不可用）'}")
    print(f"  python   {report.get('python')}")

    if report["ok"]:
        print("\n可以开工。")
        return 0

    print("\n缺少组件。", end="")
    if args.fix:
        print("开始自动安装……")
        ok = auto_install(echo=_echo)
        return 0 if ok else 1
    print("加 --fix 让我自动装。")
    print(install_hint())
    return 1


def cmd_info(args: argparse.Namespace) -> int:
    info = ff.probe(args.input)
    if args.json:
        print(json.dumps({
            "path": str(info.path), "duration": round(info.duration, 4),
            "size": info.size, "width": info.width, "height": info.height,
            "fps": round(info.fps, 4),
            "has_video": info.has_video, "has_audio": info.has_audio,
            "video_codec": info.video.codec if info.video else "",
            "audio_codec": info.audio.codec if info.audio else "",
            "summary": info.summary(),
        }, ensure_ascii=False, indent=2))
    else:
        print(info.summary())
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    result = A.analyze(
        args.input,
        do_silence=not args.no_silence,
        do_scenes=not args.no_scenes,
        do_beats=not args.no_beats,
        silence_kwargs={"noise_db": args.noise_db, "min_duration": args.min_silence},
        scene_kwargs={"threshold": args.threshold, "min_scene": args.min_scene},
        beat_kwargs={"sensitivity": args.sensitivity},
    )
    if args.thumbs:
        times: list[float] = []
        if result["scenes"]:
            times += [c["time"] for c in result["scenes"]["cuts"]]
        if result["beats"]:
            times += result["beats"]["times"][:40]
        times = sorted(set(times))[: args.thumb_limit]
        result["thumbs"] = A.extract_thumbs(args.input, times, args.thumbs, limit=args.thumb_limit)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        _echo(f"分析结果已写入 {args.out}")
    else:
        print(text)
    return 0


def _build_plan(args: argparse.Namespace) -> EditPlan:
    sources = collect_media(args.input)
    if not sources:
        raise SystemExit("没有找到任何素材。")

    if args.mode == "silence":
        plan = A.plan_from_silence(
            sources[0],
            noise_db=args.noise_db,
            min_silence=args.min_silence,
            padding=args.padding,
            min_keep=args.min_keep,
            silence_mode=args.silence_mode,
            silence_speed=args.silence_speed,
        )
    elif args.mode == "scene":
        plan = A.plan_from_scenes(
            sources[0],
            threshold=args.threshold,
            min_scene=args.min_scene,
            drop_shorter_than=args.min_keep,
        )
    elif args.mode == "beat":
        music = args.music
        if not music and len(sources) == 1:
            music = sources[0]
        if not music:
            raise SystemExit("卡点模式需要 --music 指定音乐。")
        plan = A.plan_from_beats(
            sources if len(sources) > 1 else sources[0],
            music=music,
            sensitivity=args.sensitivity,
            beats_per_cut=args.beats_per_cut,
            stride=args.stride,
            lead_in=args.lead_in,
        )
    else:
        raise SystemExit(f"未知模式：{args.mode}")

    plan.output = OutputSpec(
        crf=args.crf,
        preset=args.preset,
        normalize_loudness=args.loudnorm,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
        audio_bitrate=args.audio_bitrate,
    )
    plan.audio = audio_from_args(args)
    if args.vertical:
        plan.output.width, plan.output.height = (1080, 1920) if args.vertical == "9:16" else (1080, 1080)
    elif args.size:
        w, _, h = args.size.partition("x")
        plan.output.width, plan.output.height = int(w), int(h)
    return plan


def cmd_auto(args: argparse.Namespace) -> int:
    plan = _build_plan(args)
    st = plan.stats()

    if args.json:
        print(plan.to_json())
    else:
        print(f"模式        {plan.mode}")
        print(f"片段数      {st['segment_count']}")
        print(f"原始时长    {st['source_duration']:.2f}s")
        print(f"成片时长    {st['output_duration']:.2f}s")
        print(f"砍掉        {st['removed_duration']:.2f}s  ({st['removed_ratio'] * 100:.1f}%)")
        _print_audio_summary(plan.audio)
        for w in plan.warnings:
            print(f"提示        {w}")

    if args.plan_out:
        plan.save(args.plan_out)
        _echo(f"方案已写入 {args.plan_out}")

    if args.plan_only or not args.output:
        return 0

    music = None
    if plan.mode == "beat":
        music = args.music or str(plan.meta.get("music") or "") or None

    if args.dry_run:
        from render import build_filtergraph
        infos = [ff.probe(p) for p in plan.sources]
        w, h = plan.output.width, plan.output.height
        text, labels = build_filtergraph(
            plan, infos, out_w=w, out_h=h, fps=plan.output.fps,
            music_index=(len(plan.sources) if music else None),
            total_out=plan.total_out_duration,
            audio_only=args.audio_only,
        )
        print("\n--- 音频处理链 ---")
        vchain = AU.build_voice_chain(plan.audio)
        print("人声处理（混音前）:", ",".join(vchain) or "无")
        print("母带（混音后）:", ",".join(AU.build_master_chain(
            normalize=plan.output.normalize_loudness,
            target_lufs=plan.output.target_lufs,
            true_peak=plan.audio.true_peak,
            limiter=plan.audio.limiter,
            fade_in=plan.output.fade_in,
            fade_out=plan.output.fade_out,
            total_out=plan.total_out_duration,
        )))
        print("\n--- filtergraph ---")
        print(text.replace(";", ";\n"))
        print("--- maps ---", labels)
        return 0

    _echo("开始渲染……")
    if args.audio_only:
        out = R.render_audio(plan, args.output, music=music, progress=_progress())
    elif args.preview:
        out = R.render_preview(plan, args.output, music=music, progress=_progress())
    else:
        out = R.render(plan, args.output, music=music, progress=_progress())
    print(f"输出        {out}")
    if args.measure:
        _print_measurements(out)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    plan = EditPlan.load(args.plan) if str(args.plan).endswith(".json") else None
    if plan is None:
        raise SystemExit("请传入 EditPlan 的 JSON 文件。")

    # 命令行显式传了音频参数才覆盖方案里的设置，否则一律沿用方案
    applied: AudioSpec | None = None
    if has_audio_args(args):
        applied = audio_from_args(args)
        plan.audio = applied

    _print_audio_summary(plan.audio)
    if applied is not None:
        print("（以上来自命令行，已覆盖方案里的音频设置）")

    out = R.render(
        plan, args.output,
        music=args.music,
        progress=_progress(),
        overrides={"crf": args.crf} if args.crf else None,
        audio_only=args.audio_only,
    )
    print(f"输出        {out}")
    if args.measure:
        _print_measurements(out)
    return 0


def cmd_panel(args: argparse.Namespace) -> int:
    from panel import serve  # noqa: PLC0415

    return serve(
        port=args.port,
        open_browser=not args.no_open,
        workdir=args.workdir,
        attach=args.open or [],
    )


# ---------------------------------------------------------------------------
# 参数
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="avx",
        description="自动剪辑引擎：去静音 / 分镜 / 卡点 / 渲染",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="环境自检与修复")
    d.add_argument("--fix", action="store_true", help="自动下载缺失组件")
    d.add_argument("--json", action="store_true")
    d.set_defaults(func=cmd_doctor)

    i = sub.add_parser("info", help="查看素材信息")
    i.add_argument("input")
    i.add_argument("--json", action="store_true")
    i.set_defaults(func=cmd_info)

    a = sub.add_parser("analyze", help="全量分析素材")
    a.add_argument("input")
    a.add_argument("--out", help="结果写入 JSON 文件")
    a.add_argument("--thumbs", help="输出缩略图目录")
    a.add_argument("--thumb-limit", type=int, default=40)
    a.add_argument("--noise-db", type=float, default=-30.0)
    a.add_argument("--min-silence", type=float, default=0.35)
    a.add_argument("--threshold", type=float, default=0.30)
    a.add_argument("--min-scene", type=float, default=0.6)
    a.add_argument("--sensitivity", type=float, default=1.0)
    a.add_argument("--no-silence", action="store_true")
    a.add_argument("--no-scenes", action="store_true")
    a.add_argument("--no-beats", action="store_true")
    a.set_defaults(func=cmd_analyze)

    au = sub.add_parser("auto", help="一键自动剪辑")
    au.add_argument("input", nargs="+", help="素材文件，或装着素材的目录")
    au.add_argument("-o", "--output")
    au.add_argument("--mode", choices=["silence", "scene", "beat"], default="silence")
    au.add_argument("--plan-only", action="store_true", help="只出方案不渲染")
    au.add_argument("--plan-out", help="把方案存成 JSON")
    au.add_argument("--json", action="store_true", help="stdout 输出方案的 JSON")
    au.add_argument("--dry-run", action="store_true", help="只打印 filtergraph")
    au.add_argument("--preview", action="store_true", help="低清快速预览渲染")

    au.add_argument("--noise-db", type=float, default=-30.0, help="静音阈值 dB")
    au.add_argument("--min-silence", type=float, default=0.35, help="最短静音时长")
    au.add_argument("--padding", type=float, default=0.06, help="切除边界多留的余量")
    au.add_argument("--min-keep", type=float, default=0.25, help="最短保留片段")
    au.add_argument("--silence-mode", choices=["cut", "speed"], default="cut")
    au.add_argument("--silence-speed", type=float, default=4.0, help="静音段加速倍率")

    au.add_argument("--threshold", type=float, default=0.30, help="镜头切换阈值 0~1")
    au.add_argument("--min-scene", type=float, default=0.6, help="最短镜头时长")

    au.add_argument("--music", help="卡点用的音乐")
    au.add_argument("--sensitivity", type=float, default=1.0)
    au.add_argument("--beats-per-cut", type=int, default=1)
    au.add_argument("--stride", type=float, default=1.35, help="跳剪步进倍率")
    au.add_argument("--lead-in", type=float, default=0.0, help="忽略前 N 秒的节拍")

    au.add_argument("--crf", type=int, default=20)
    au.add_argument("--preset", default="veryfast")
    au.add_argument("--audio-bitrate", default="192k")
    au.add_argument("--loudnorm", action="store_true", help="响度归一化到 -16 LUFS")
    au.add_argument("--fade-in", type=float, default=0.0)
    au.add_argument("--fade-out", type=float, default=0.0)
    au.add_argument("--vertical", choices=["9:16", "1:1"], help="裁成竖屏/方形")
    au.add_argument("--size", help="自定义 WxH，如 1080x1920")
    au.add_argument("--audio-only", action="store_true",
                    help="只导出音轨（按 -o 的后缀选格式：m4a/mp3/wav/flac）")
    au.add_argument("--measure", action="store_true", help="渲染后量一遍响度与底噪")
    add_audio_args(au)
    au.set_defaults(func=cmd_auto)

    r = sub.add_parser("render", help="按方案 JSON 渲染")
    r.add_argument("plan")
    r.add_argument("-o", "--output", required=True)
    r.add_argument("--music")
    r.add_argument("--crf", type=int)
    r.add_argument("--audio-only", action="store_true", help="只导出音轨")
    r.add_argument("--measure", action="store_true", help="渲染后量一遍响度与底噪")
    add_audio_args(r)
    r.set_defaults(func=cmd_render)

    ao = sub.add_parser("audio", help="纯音频处理（不涉及视频）")
    ao.add_argument("input", nargs="+", help="音频或视频文件，多个文件按顺序首尾相接")
    ao.add_argument("-o", "--output", help="输出文件，后缀决定格式：m4a/mp3/wav/flac")
    ao.add_argument("--measure", action="store_true", help="量一遍响度与底噪")
    ao.add_argument("--no-loudnorm", action="store_true", help="关掉响度归一化")
    ao.add_argument("--loudnorm-target", type=float, default=-16.0,
                    help="响度目标 LUFS，默认 -16")
    ao.add_argument("--fade-in", type=float, default=0.0)
    ao.add_argument("--fade-out", type=float, default=0.0)
    ao.add_argument("--audio-bitrate", default="192k")
    add_audio_args(ao)
    ao.set_defaults(func=cmd_audio)

    pn = sub.add_parser("panel", help="启动本地剪辑面板")
    pn.add_argument("--port", type=int, default=8787)
    pn.add_argument("--no-open", action="store_true")
    pn.add_argument("--workdir", help="工作目录")
    # action="extend"：重复出现的 --open 才会计累，nargs="*" 会互相覆盖
    pn.add_argument("--open", nargs="*", action="extend", default=[],
                    help="启动时直接载入的素材，可重复传入")
    pn.set_defaults(func=cmd_panel)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except ff.FFmpegNotFound as exc:
        _echo(f"\n[环境缺失] {exc}")
        return 3
    except ff.FFmpegError as exc:
        _echo(f"\n[ffmpeg 失败] {exc}")
        return 4
    except KeyboardInterrupt:
        _echo("\n已中断。")
        return 130
    except Exception as exc:  # noqa: BLE001
        _echo(f"\n[出错] {type(exc).__name__}: {exc}")
        if __debug__ and "--traceback" in sys.argv:
            raise
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
