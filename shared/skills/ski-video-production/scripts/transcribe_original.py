#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
原创作品分析器 —— 从涛哥自己的视频文件里提取「创作风格指纹」

能拿到什么（这是学风格的关键）：
  1. 口播全文（简体，带时间码）      → 学「脚本创作方式」
  2. 语速曲线（分段 + 快慢区间）      → 学「配音方式」的节奏
  3. 停顿图谱（句间静音位置与时长）    → 学「配音方式」的气口
  4. 剪辑节奏（场景切换点、平均镜长）   → 学「剪辑风格」

技术上：完全离线。用 faster-whisper（自带 PyAV，不需要系统 ffmpeg）。
模型缓存于 ~/.cache/huggingface（base 140MB + small 480MB）。

用法：
  python3 transcribe_original.py <文件或目录> [更多文件...]
      [--model small|base|medium]   # 默认 small
      [--outdir DIR]                # 产出目录，默认 ./style-out
      [--workers 3]                 # 并行度
      [--no-scene]                  # 跳过视频剪辑分析（快很多）
      [--scene-max-sec 300]         # 每条最多分析多少秒画面

产出：
  <outdir>/口播全文.md      人读的报告
  <outdir>/analysis.json    机读的完整数据（供后续写档案用）
"""
import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# ---- 模型下载必须先设环境变量，再 import faster_whisper ----
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

# 全角/半角标点，都不计入语速
PUNCT = set(" 　\t\n\r，。、；：？！「」『』（）《》〈〉【】…—～·\"'`´"
            ",.;:?!()[]{}<>/\\|~@#$%^&*_+=`-“”‘’·　")

CJK_PUNCT_RE = re.compile(r"[\u3000-\u303f\uff00-\uffef\u2000-\u206f]")


def count_chars(text: str) -> int:
    """只数「要念出来的字」，标点和空白不计入"""
    t = CJK_PUNCT_RE.sub("", text)
    return sum(1 for ch in t if not ch.isspace() and ch not in PUNCT)


def to_simplified(text: str) -> str:
    try:
        import zhconv
        return zhconv.convert(text, "zh-cn")
    except Exception:
        return text


def fmt_tc(sec: float) -> str:
    m, s = divmod(max(0.0, sec), 60)
    return f"{int(m):02d}:{s:05.2f}"


# ----------------------------------------------------------------------------
# 1) 元数据
# ----------------------------------------------------------------------------
def probe(path: str) -> dict:
    import av
    c = av.open(path)
    try:
        v = [s for s in c.streams if s.type == "video"]
        a = [s for s in c.streams if s.type == "audio"]
        dur = c.duration / av.time_base if c.duration else 0.0
        d = {"duration": round(dur, 2), "size_mb": round(os.path.getsize(path) / 1024 / 1024, 1)}
        if v:
            d.update(width=v[0].width, height=v[0].height,
                     fps=round(float(v[0].average_rate), 2),
                     aspect=("竖屏" if v[0].height > v[0].width else "横屏"))
        if a:
            d["audio"] = f"{a[0].codec_context.name} {a[0].codec_context.sample_rate}Hz"
        return d
    finally:
        c.close()


# ----------------------------------------------------------------------------
# 2) 语音转写
# ----------------------------------------------------------------------------
def transcribe(path: str, model_obj, initial_prompt: str) -> dict:
    t0 = time.time()
    segments, info = model_obj.transcribe(
        path,
        language="zh",
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 350},
        word_timestamps=True,
        initial_prompt=initial_prompt,
        condition_on_previous_text=False,   # 防幻觉复读
        no_speech_threshold=0.6,
    )
    segs = []
    for s in segments:
        txt = to_simplified(s.text.strip())
        if not txt:
            continue
        words = [{"w": to_simplified(w.word.strip()), "s": round(w.start, 2), "e": round(w.end, 2)}
                 for w in (s.words or []) if w.word.strip()]
        segs.append({"start": round(s.start, 2), "end": round(s.end, 2),
                     "text": txt, "words": words})
    return {"segments": segs, "duration": round(info.duration, 2),
            "elapsed": round(time.time() - t0, 1)}


# ----------------------------------------------------------------------------
# 3) 语速 + 停顿分析
# ----------------------------------------------------------------------------
def analyze_speech(segs: list, total_dur: float, window: float = 10.0) -> dict:
    if not segs:
        return {"chars": 0, "speech_sec": 0.0, "rate_speech": 0.0, "rate_total": 0.0,
                "speaking_ratio": 0.0, "windows": [], "rate_min": 0.0, "rate_max": 0.0,
                "tiers": {}, "pauses": [], "pause_count": 0, "pause_avg": 0.0,
                "longest_pause": 0.0, "inner_pauses": []}

    chars = sum(count_chars(s["text"]) for s in segs)
    speech = sum(s["end"] - s["start"] for s in segs)

    # --- 停顿：句子之间的静音 ---
    pauses = []
    for a, b in zip(segs, segs[1:]):
        gap = b["start"] - a["end"]
        if gap >= 0.35:
            pauses.append({
                "at": round(a["end"], 2), "gap": round(gap, 2),
                "before": a["text"][-14:], "after": b["text"][:14],
            })
    # 句内长停顿（说话人中途换气）
    inner = []
    for s in segs:
        ws = s["words"]
        for a, b in zip(ws, ws[1:]):
            g = b["s"] - a["e"]
            if g >= 0.40:
                inner.append({"at": round(a["e"], 2), "gap": round(g, 2),
                              "before": a["w"], "after": b["w"]})

    # --- 滑动窗口语速曲线 ---
    windows = []
    t = 0.0
    while t < total_dur:
        w0, w1 = t, t + window
        seg_slice = [s for s in segs if s["end"] > w0 and s["start"] < w1]
        if seg_slice:
            c = 0
            sp = 0.0
            for s in seg_slice:
                ov0, ov1 = max(s["start"], w0), min(s["end"], w1)
                if ov1 > ov0:
                    ratio = (ov1 - ov0) / max(0.01, s["end"] - s["start"])
                    c += count_chars(s["text"]) * ratio
                    sp += ov1 - ov0
            if sp > 1.0:
                windows.append({"t0": round(w0, 1), "t1": round(w1, 1),
                                "rate": round(c / sp, 2), "chars": int(round(c))})
        t += window

    tiers = {"很慢 <4.0": 0, "偏慢 4.0-4.6": 0, "标准 4.6-5.2": 0,
             "偏快 5.2-6.0": 0, "极快 >6.0": 0}
    for w in windows:
        r = w["rate"]
        if r < 4.0:
            tiers["很慢 <4.0"] += 1
        elif r < 4.6:
            tiers["偏慢 4.0-4.6"] += 1
        elif r <= 5.2:
            tiers["标准 4.6-5.2"] += 1
        elif r <= 6.0:
            tiers["偏快 5.2-6.0"] += 1
        else:
            tiers["极快 >6.0"] += 1

    return {
        "chars": chars,
        "speech_sec": round(speech, 2),
        "rate_speech": round(chars / speech, 2) if speech else 0.0,
        "rate_total": round(chars / total_dur, 2) if total_dur else 0.0,
        "speaking_ratio": round(speech / total_dur, 3) if total_dur else 0.0,
        "windows": windows,
        "rate_min": min((w["rate"] for w in windows), default=0),
        "rate_max": max((w["rate"] for w in windows), default=0),
        "tiers": tiers,
        "pauses": pauses,
        "pause_count": len(pauses),
        "pause_avg": round(sum(p["gap"] for p in pauses) / len(pauses), 2) if pauses else 0.0,
        "longest_pause": max((p["gap"] for p in pauses), default=0.0),
        "inner_pauses": inner[:60],
    }


# ----------------------------------------------------------------------------
# 4) 剪辑节奏（场景切换检测）
# ----------------------------------------------------------------------------
def analyze_cuts(path: str, max_sec: float = 300.0, sample_fps: float = 4.0,
                 thresh: float = 9.0) -> dict:
    import av
    import numpy as np
    c = av.open(path)
    try:
        vs = [s for s in c.streams if s.type == "video"]
        if not vs:
            return {"error": "无视频流"}
        vs[0].thread_type = "AUTO"
        cuts, prev, prev_t, bucket = [], None, None, -1
        step = 1.0 / sample_fps
        for frame in c.decode(video=0):
            ft = float(frame.time or 0)
            if ft > max_sec:
                break
            b = int(ft / step)
            if b == bucket:
                continue
            bucket = b
            g = frame.to_ndarray(format="gray")[::10, ::10].astype(np.float32)
            if prev is not None and prev.shape == g.shape:
                diff = float(np.mean(np.abs(g - prev)))
                if diff >= thresh:
                    cuts.append({"t": round(ft, 2), "diff": round(diff, 1)})
            prev, prev_t = g, ft
        # 合并 0.3s 内的连续切换（同一转场）
        merged = []
        for x in cuts:
            if merged and x["t"] - merged[-1]["t"] < 0.35:
                if x["diff"] > merged[-1]["diff"]:
                    merged[-1] = x
            else:
                merged.append(x)
        span = min(max_sec, prev_t or 1)
        shots = len(merged) + 1
        return {
            "cut_count": len(merged),
            "avg_shot_sec": round(span / shots, 2),
            "analyzed_sec": round(span, 1),
            "cuts": merged,
        }
    finally:
        c.close()


# ----------------------------------------------------------------------------
# 单文件全流程
# ----------------------------------------------------------------------------
def process_one(args_tuple):
    path, model_name, with_scene, scene_max = args_tuple
    name = os.path.basename(path)
    out = {"file": name, "path": path}
    try:
        out["meta"] = probe(path)
    except Exception as e:
        out["meta"] = {"error": f"{type(e).__name__}: {e}"}

    # 模型若已缓存，强制离线——否则 huggingface_hub 仍会联网校验，
    # 在有代理的机器上会抛 ProxyError: 502 导致整条转写失败。
    cache = Path.home() / ".cache/huggingface/hub" / f"models--Systran--faster-whisper-{model_name}"
    if cache.exists():
        os.environ["HF_HUB_OFFLINE"] = "1"

    try:
        from faster_whisper import WhisperModel
        m = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=4)
        tr = transcribe(path, m,
                        "以下是普通话的句子，请用简体中文输出，保留数字和专有名词。")
        out["transcript"] = tr
        out["speech"] = analyze_speech(tr["segments"], tr["duration"])
    except Exception as e:
        out["transcript"] = {"segments": [], "duration": 0, "elapsed": 0}
        out["speech"] = analyze_speech([], 0)
        out["error"] = f"转写失败 {type(e).__name__}: {e}"

    if with_scene:
        try:
            out["cuts"] = analyze_cuts(path, max_sec=scene_max)
        except Exception as e:
            out["cuts"] = {"error": f"{type(e).__name__}: {e}"}
    return out


# ----------------------------------------------------------------------------
# 渲染 Markdown
# ----------------------------------------------------------------------------
def render_md(results: list) -> str:
    L = ["# 原创作品分析 · 口播与节奏指纹", ""]
    tot_c = sum(r["speech"]["chars"] for r in results)
    tot_s = sum(r["speech"]["speech_sec"] for r in results)
    L.append(f"共 {len(results)} 条作品 | 有效说话 {tot_s/60:.1f} 分钟 | "
             f"口播总字数 {tot_c} | **全局语速 {tot_c/tot_s:.2f} 字/秒**" if tot_s else "")
    L.append("")

    # ---- 汇总表 ----
    L.append("## 汇总")
    L.append("")
    L.append("| 文件 | 时长 | 画面 | 字数 | 说话 | 语速(纯说) | 语速(含停顿) | 说话占比 | 停顿数 | 最长停顿 | 平均镜长 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in results:
        m, s = r.get("meta") or {}, r["speech"]
        cut = r.get("cuts") or {}
        if cut.get("error"):
            shot = "—"
        else:
            shot = f"{cut.get('avg_shot_sec','—')}s"
        L.append(f"| {r['file']} | {m.get('duration','—')}s | "
                 f"{str(m.get('width',''))+ 'x' + str(m.get('height','')) if m.get('width') else '—'} | "
                 f"{s['chars']} | {s['speech_sec']}s | **{s['rate_speech']}** | "
                 f"{s['rate_total']} | {s['speaking_ratio']*100:.0f}% | {s['pause_count']} | "
                 f"{s['longest_pause']}s | {shot} |")
    L.append("")

    for r in results:
        sp = r["speech"]
        m = r.get("meta") or {}
        L.append("---")
        L.append("")
        L.append(f"## {r['file']}")
        L.append("")
        L.append(f"- 时长 {m.get('duration','—')}s | "
                 f"{m.get('width','—')}x{m.get('height','—')} {m.get('aspect','')} "
                 f"{m.get('fps','')}fps | {m.get('size_mb','—')}MB")
        L.append(f"- 口播 **{sp['chars']} 字** | 有效说话 {sp['speech_sec']}s | "
                 f"**语速 {sp['rate_speech']} 字/秒**（纯说） / {sp['rate_total']} 字/秒（含停顿）")
        L.append(f"- 停顿 {sp['pause_count']} 次 | 平均 {sp['pause_avg']}s | 最长 {sp['longest_pause']}s")
        L.append("")

        # 语速曲线
        if sp["windows"]:
            L.append("**语速曲线**（每 10 秒）")
            L.append("")
            mx = max(sp["rate_max"], 6.0)
            for w in sp["windows"]:
                bar = "█" * max(1, int(w["rate"] / mx * 34))
                L.append(f"`{fmt_tc(w['t0'])}` {w['rate']:5.2f} {bar}")
            L.append("")
            ran = ", ".join(f"{k}×{v}" for k, v in sp["tiers"].items() if v)
            L.append(f"分布：{ran}")
            L.append("")

        # 停顿图谱
        if sp["pauses"]:
            L.append("**停顿图谱**（≥0.35s，句子之间）")
            L.append("")
            L.append("| 时间点 | 时长 | 停顿前 | 停顿后 |")
            L.append("|---|---|---|---|")
            for p in sp["pauses"][:40]:
                L.append(f"| {fmt_tc(p['at'])} | {p['gap']}s | …{p['before']} | {p['after']}… |")
            if len(sp["pauses"]) > 40:
                L.append(f"| … | 其余 {len(sp['pauses'])-40} 处 | | |")
            L.append("")

        # 剪辑
        cut = r.get("cuts") or {}
        if cut and not cut.get("error"):
            L.append(f"**剪辑节奏**：平均镜长 **{cut['avg_shot_sec']}s** "
                     f"（前 {cut['analyzed_sec']}s 内切换 {cut['cut_count']} 次）")
            if cut["cuts"]:
                ts = " ".join(fmt_tc(c["t"]) for c in cut["cuts"][:28])
                L.append("")
                L.append(f"切换点：{ts}")
            L.append("")

        # 口播全文
        L.append("### 口播全文")
        L.append("")
        for s in ev_segments(r):
            L.append(f"`{fmt_tc(s['start'])} → {fmt_tc(s['end'])}` {s['text']}")
        L.append("")

    return "\n".join(L)


def ev_segments(r):
    return (r.get("transcript") or {}).get("segments", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--model", default="small", choices=["base", "small", "medium"])
    ap.add_argument("--outdir", default="./style-out")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--no-scene", action="store_true")
    ap.add_argument("--scene-max-sec", type=float, default=300.0)
    a = ap.parse_args()

    files = []
    for p in a.inputs:
        p = os.path.abspath(os.path.expanduser(p))
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                if f.lower().endswith((".mp4", ".mov", ".m4v", ".mkv", ".mp3", ".m4a", ".wav")):
                    files.append(os.path.join(p, f))
        elif os.path.isfile(p):
            files.append(p)
        else:
            print(f"⚠️ 跳过（不存在）: {p}", file=sys.stderr)

    if not files:
        print("没有可处理的文件", file=sys.stderr)
        sys.exit(1)

    print(f"待处理 {len(files)} 个文件 | 模型 {a.model} | 并行 {a.workers} | "
          f"剪辑分析 {'关' if a.no_scene else '开'}", flush=True)

    tasks = [(f, a.model, not a.no_scene, a.scene_max_sec) for f in files]
    results, t0 = [], time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(process_one, t): t[0] for t in tasks}
        for fut in as_completed(futs):
            src = futs[fut]
            try:
                r = fut.result()
            except Exception as e:
                r = {"file": os.path.basename(src), "path": src,
                     "meta": {}, "speech": analyze_speech([], 0),
                     "transcript": {"segments": []}, "error": str(e)}
            results.append(r)
            sp = r["speech"]
            print(f"  ✅ {r['file']:18s} {sp['chars']:5d}字 "
                  f"语速 {sp['rate_speech']:5.2f} | 用时见下", flush=True)

    order = {os.path.basename(f): i for i, f in enumerate(files)}
    results.sort(key=lambda r: order.get(r["file"], 999))

    od = Path(a.outdir)
    od.mkdir(parents=True, exist_ok=True)
    (od / "analysis.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    (od / "口播全文.md").write_text(render_md(results), encoding="utf-8")

    tot_c = sum(r["speech"]["chars"] for r in results)
    tot_s = sum(r["speech"]["speech_sec"] for r in results)
    print(f"\n完成，总耗时 {time.time()-t0:.0f}s")
    print(f"  全局语速 {tot_c/tot_s:.2f} 字/秒（{tot_c} 字 / {tot_s:.0f}s）" if tot_s else "")
    print(f"  产出: {od/'口播全文.md'}")
    print(f"        {od/'analysis.json'}")


if __name__ == "__main__":
    main()
