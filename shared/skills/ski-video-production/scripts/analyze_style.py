#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
嗓音调性分析器 —— 从音频本身量化「他说话是什么味道」

文案转写只能看出「讲了什么」，看不出「怎么讲的」。
判断激昂/沉稳/风趣/中二/忧伤，必须看声学特征：

  能量（RMS）     → 有没有爆发力、情绪推力
  基频（F0）      → 音高。起伏度大 = 有戏、有情绪；平稳 = 冷静克制
  F0 变异系数 CV  → 核心指标。CV 越高 = 音调越夸张（激昂/中二）；越低 = 越沉稳
  语速            → 快 = 急/兴奋；慢 = 沉/抒情
  停顿密度与时长   → 憋气发狠 vs 娓娓道来

用法：
  python3 analyze_style.py --analysis <analysis.json> [--outdir DIR]
      [--cuts]          # 顺带分析剪辑节奏（慢）
"""
import argparse
import json
import os
import re
from pathlib import Path

import numpy as np

SR = 16000
WIN = 0.05          # 40ms 窗（含 20ms 步进由 hop 控制）
HOP = 0.025


# ---------------------------------------------------------------------------
# 音频读取（PyAV，不需要系统 ffmpeg）
# ---------------------------------------------------------------------------
def load_audio(path: str, sr: int = SR, max_sec: float | None = None):
    import av
    c = av.open(path)
    try:
        streams = [s for s in c.streams if s.type == "audio"]
        if not streams:
            return np.zeros(0, dtype=np.float32), sr
        rs = av.AudioResampler(format="s16", layout="mono", rate=sr)
        out = []
        got = 0
        for frame in c.decode(audio=0):
            for f in rs.resample(frame):
                arr = f.to_ndarray()
                x = arr[0] if arr.ndim == 2 else arr
                out.append(x.astype(np.float32))
            got = sum(len(a) for a in out)
            if max_sec and got > max_sec * sr:
                break
        for f in rs.resample(None):
            arr = f.to_ndarray()
            out.append((arr[0] if arr.ndim == 2 else arr).astype(np.float32))
        if not out:
            return np.zeros(0, dtype=np.float32), sr
        y = np.concatenate(out) / 32768.0
        if max_sec:
            y = y[: int(max_sec * sr)]
        return y, sr
    finally:
        c.close()


# ---------------------------------------------------------------------------
# 声学特征
# ---------------------------------------------------------------------------
def frame_signal(y: np.ndarray, win: float, hop: float, sr: int = SR):
    n = int(win * sr)
    h = int(hop * sr)
    if len(y) < n:
        return np.zeros((0, n), dtype=np.float32), np.zeros(0)
    idx = np.arange(0, len(y) - n + 1, h)
    fr = np.lib.stride_tricks.as_strided(
        y, shape=(len(idx), n), strides=(y.strides[0] * h, y.strides[0])).copy()
    return fr, idx / sr


def est_f0(fr: np.ndarray, sr: int = SR, fmin=70.0, fmax=350.0):
    """自相关法估基频。返回 (f0, voiced_mask)"""
    lo, hi = int(sr / fmax), int(sr / fmin)
    win = np.hanning(fr.shape[1])
    x = fr * win
    x = x - x.mean(axis=1, keepdims=True)
    n = fr.shape[1]
    # 用 FFT 快速自相关
    nfft = 1 << int(np.ceil(np.log2(2 * n)))
    X = np.fft.rfft(x, nfft, axis=1)
    ac = np.fft.irfft(np.abs(X) ** 2, nfft, axis=1)[:, : n]
    ac = ac / np.maximum(ac[:, :1], 1e-9)
    seg = ac[:, lo:min(hi, n)]
    lag = np.argmax(seg, axis=1) + lo
    f0 = sr / np.maximum(lag, 1)
    peak = seg[np.arange(len(lag)), lag - lo]
    rms = np.sqrt((fr ** 2).mean(axis=1))
    voiced = (peak > 0.32) & (rms > 0.006)
    f0 = np.where(voiced, f0, np.nan)
    return f0, voiced, rms


def acoustic_profile(path: str, max_sec: float = 600.0) -> dict:
    y, sr = load_audio(path, max_sec=max_sec)
    if len(y) < sr * 0.5:
        return {"error": "音频过短"}
    fr, times = frame_signal(y, WIN, HOP, sr)
    if fr.shape[0] == 0:
        return {"error": "无法分帧"}
    f0, voiced, rms = est_f0(fr, sr)

    v = f0[~np.isnan(f0)]
    r = rms

    def db(x):
        return 20 * np.log10(np.maximum(x, 1e-6))

    dur = len(y) / sr
    # 说话/静音：RMS 阈值（相对中位数）
    thr = max(0.004, float(np.median(r)) * 0.22)
    speech_mask = r > thr
    speech_ratio = float(speech_mask.mean())

    # F0 统计（只在有声帧上算）
    f0_stats = {}
    if len(v) > 20:
        p5, p95 = np.percentile(v, [5, 95])
        f0_stats = {
            "f0_mean": round(float(np.mean(v)), 1),
            "f0_median": round(float(np.median(v)), 1),
            "f0_std": round(float(np.std(v)), 1),
            "f0_cv": round(float(np.std(v) / np.mean(v)), 3),   # ★ 核心：音调起伏度
            "f0_range_p5_p95": round(float(p95 - p5), 1),
            "voiced_ratio": round(float(voiced.mean()), 3),
        }

    # 能量动态
    rs = db(r[r > thr]) if (r > thr).any() else np.array([-60.0])
    dyn = float(np.percentile(rs, 95) - np.percentile(rs, 25)) if len(rs) > 20 else 0.0

    # 停顿 = 连续「无人声」段；语句段 = 连续「有人声」段
    # （注意：曾把判定写反过，量成了语句段长，已修正）
    pauses, runs, run = [], [], 0
    for m in speech_mask:
        if m:                       # 有声
            run += 1
        else:                       # 无声 → 记录上一段语句
            if run * HOP >= 0.35:
                runs.append(round(run * HOP, 2))
            run = 0
    if run * HOP >= 0.35:
        runs.append(round(run * HOP, 2))

    gap, run = [], 0
    for m in speech_mask:
        if not m:                   # 无声
            run += 1
        else:                       # 有声 → 记录上一段停顿
            if run * HOP >= 0.30:
                gap.append(round(run * HOP, 2))
            run = 0
    if run * HOP >= 0.30:
        gap.append(round(run * HOP, 2))

    return {
        "duration": round(dur, 1),
        "speech_ratio": round(speech_ratio, 3),
        "energy": {
            "median_db": round(float(np.median(rs)), 1),
            "dyn_range_db": round(dyn, 1),
            "peak_db": round(float(np.percentile(rs, 99)), 1),
            "std_db": round(float(np.std(rs)), 1),
        },
        "pitch": f0_stats,
        "pauses": {
            "count": len(gap),
            "mean": round(float(np.mean(gap)), 2) if gap else 0.0,
            "max": max(gap) if gap else 0.0,
            "per_min": round(len(gap) / (dur / 60), 1) if dur else 0,
            "longest3": sorted(gap, reverse=True)[:3],
        },
        "speech_runs": {
            "count": len(runs),
            "mean": round(float(np.mean(runs)), 2) if runs else 0.0,
            "max": max(runs) if runs else 0.0,
            "per_min": round(len(runs) / (dur / 60), 1) if dur else 0,
        },
    }


# ---------------------------------------------------------------------------
# 内容类型识别（文案特征）
# ---------------------------------------------------------------------------
CONTENT_RULES = [
    ("纪录片解说", ["纪录片", "这部电影", "影片", "电影", "镜头", "导演", "片名", "上映"]),
    ("人物传记", ["他叫", "出生", "从小", "父亲", "家族", "一生", "生涯", "成名", "传奇", "这个人", "经历"]),
    ("盘点/榜单", ["十大", "十个", "top", "排行", "盘点", "第1", "第一名", "史上最", "最牛逼", "之最"]),
    ("历史讲解", ["历史", "纪录", "世界纪录", "第一次", "首次", "年代", "上世纪", "由来", "起源", "冬奥会"]),
    ("滑雪科普", ["为什么", "原理", "其实", "物理", "技巧", "正确", "教你", "科普", "区别", "什么是"]),
    ("教学", ["新手", "入门", "怎么", "第一步", "教程", "注意", "教学", "学会", "建议"]),
    ("滑雪趣事", ["搞笑", "笑死", "离谱", "尴尬", "翻车", "没想到", "居然", "趣事", "太逗"]),
]


def classify_content(text: str) -> list[tuple[str, int]]:
    t = text.lower()
    hits = []
    for name, kws in CONTENT_RULES:
        c = sum(t.count(k.lower()) for k in kws)
        if c:
            hits.append((name, c))
    return sorted(hits, key=lambda x: -x[1])


# ---------------------------------------------------------------------------
# 调性判读（声学 + 文案双证据）
# ---------------------------------------------------------------------------
def judge_tone(ac: dict, sp: dict, text: str) -> dict:
    """返回 {判读, 置信, 依据[]}"""
    if ac.get("error"):
        return {"tone": "—", "conf": "低", "why": ["声学分析失败"]}
    cv = (ac.get("pitch") or {}).get("f0_cv", 0) or 0
    dyn = (ac.get("energy") or {}).get("dyn_range_db", 0) or 0
    rate = sp.get("rate_speech", 0) or 0
    pause_max = (ac.get("pauses") or {}).get("max", 0) or 0
    pause_per_min = (ac.get("pauses") or {}).get("per_min", 0) or 0
    run_mean = (ac.get("speech_runs") or {}).get("mean", 0) or 0
    sr_ = ac.get("speech_ratio", 0) or 0

    # 文案情绪信号
    excite_kw = ["最", "第一", "史上", "唯一", "绝对", "根本", "疯了", "不要命", "恐怖", "震撼", "巨"]
    soft_kw = ["感动", "命运", "温柔", "遗憾", "离开", "告别", "孤独", "安静", "曾经", "回不来"]
    fun_kw = ["哈哈", "居然", "离谱", "笑", "搞笑", "居然", "你说", "搞笑", "梗", "没想到", "翻车"]
    e = sum(text.count(k) for k in excite_kw)
    s = sum(text.count(k) for k in soft_kw)
    f = sum(text.count(k) for k in fun_kw)

    scores = {}
    why = {k: [] for k in ["激昂", "沉稳", "风趣", "中二", "忧伤", "诙谐"]}

    # --- 激昂：音调起伏大 + 能量动态大 + 语速偏快 ---
    sc = 0
    if cv > 0.20: sc += 2; why["激昂"].append(f"音调起伏 CV={cv} 很大")
    elif cv > 0.16: sc += 1; why["激昂"].append(f"音调起伏 CV={cv} 偏大")
    if dyn > 16: sc += 1; why["激昂"].append(f"能量动态 {dyn}dB 有爆发")
    if rate > 6.2: sc += 1; why["激昂"].append(f"语速 {rate} 偏快")
    if e >= 6: sc += 2; why["激昂"].append(f"最强级用词 {e} 处")
    scores["激昂"] = sc

    # --- 中二：起伏极大 + 短促爆发多 + 称号/绝对化 ---
    sc = 0
    if cv > 0.24: sc += 2; why["中二"].append(f"音调起伏 CV={cv} 极大")
    if pause_max > 1.4: sc += 1; why["中二"].append(f"最长停顿 {pause_max}s（憋气发狠）")
    if e >= 9: sc += 2; why["中二"].append(f"最强级用词密集 {e} 处")
    scores["中二"] = sc

    # --- 沉稳：起伏小 + 能量平稳 + 语速中 ---
    sc = 0
    if cv and cv < 0.14: sc += 2; why["沉稳"].append(f"音调起伏 CV={cv} 小（克制）")
    elif cv and cv < 0.17: sc += 1; why["沉稳"].append(f"音调起伏 CV={cv} 偏小")
    if dyn and dyn < 12: sc += 1; why["沉稳"].append(f"能量动态 {dyn}dB 平稳")
    if 4.6 <= rate <= 6.2: sc += 1; why["沉稳"].append(f"语速 {rate} 适中")
    scores["沉稳"] = sc

    # --- 风趣 / 诙谐：口语梗 + 短句连发（打点节奏）---
    sc = 0
    if f >= 4: sc += 2; why["风趣"].append(f"口语/梗类词 {f} 处")
    if 5.6 <= rate <= 7.2: sc += 1; why["风趣"].append(f"语速 {rate} 偏快（聊天感）")
    if 0 < run_mean < 2.3: sc += 1; why["风趣"].append(f"语句段均长 {run_mean}s（短句连发、抖包袱）")
    scores["风趣"] = sc
    scores["诙谐"] = max(0, sc - 1)   # 诙谐≈风趣的弱化版，靠文案定

    # --- 忧伤：慢 + 轻 + 长停顿 ---
    sc = 0
    if rate and rate < 5.6: sc += 2; why["忧伤"].append(f"语速 {rate} 偏慢")
    if (ac.get("energy") or {}).get("median_db", 0) < -26: sc += 1; why["忧伤"].append("整体能量偏低")
    if pause_max > 1.2: sc += 1; why["忧伤"].append(f"最长停顿 {pause_max}s（留白）")
    if s >= 3: sc += 2; why["忧伤"].append(f"抒情词 {s} 处")
    scores["忧伤"] = sc

    best = max(scores, key=scores.get)
    second = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
    conf = "高" if scores[best] - second >= 2 and scores[best] >= 4 else \
           ("中" if scores[best] >= 3 else "低")
    return {"tone": best if scores[best] >= 2 else "平和", "conf": conf,
            "scores": scores, "why": why[best]}


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", required=True, help="transcribe_original.py 产出的 analysis.json")
    ap.add_argument("--outdir", default="./style-audit")
    ap.add_argument("--out", default="风格判读.md")
    ap.add_argument("--max-sec", type=float, default=600.0)
    a = ap.parse_args()

    data = json.loads(Path(a.analysis).read_text(encoding="utf-8"))
    rows = []
    for r in data:
        print(f"  分析 {r['file']} ...", flush=True)
        ac = acoustic_profile(r["path"], max_sec=a.max_sec)
        text = "\n".join(s["text"] for s in (r.get("transcript") or {}).get("segments", []))
        tones = judge_tone(ac, r.get("speech") or {}, text)
        rows.append({"file": r["file"], "ac": ac, "tone": tones,
                     "content": classify_content(text), "speech": r.get("speech") or {},
                     "meta": r.get("meta") or {}, "text_len": len(text)})

    od = Path(a.outdir)
    od.mkdir(parents=True, exist_ok=True)
    (od / "acoustic.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                      encoding="utf-8")

    L = ["# 嗓音调性与内容类型判读", "",
         "> 依据 = **声学特征**（音高起伏/能量动态/停顿，客观测量）+ **文案特征**（用词）+ **语速**",
         "", "| 文件 | 内容类型 | 调性 | 置信 | 语速 | 音调起伏CV | 能量动态 | 语句段均长 | 最长停顿 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ac, t = r["ac"], r["tone"]
        ct = "、".join(n for n, _ in r["content"][:2]) or "—"
        p = ac.get("pitch") or {}
        L.append(f"| {r['file']} | {ct} | **{t['tone']}** | {t['conf']} | "
                 f"{r['speech'].get('rate_speech','—')} | {p.get('f0_cv','—')} | "
                 f"{(ac.get('energy') or {}).get('dyn_range_db','—')} | "
                 f"{(ac.get('speech_runs') or {}).get('mean','—')}s | "
                 f"{(ac.get('pauses') or {}).get('max','—')}s |")
    L.append("")
    L.append("## 逐条依据")
    L.append("")
    for r in rows:
        t = r["tone"]
        L.append(f"### {r['file']} → {t['tone']}（置信 {t['conf']}）")
        L.append("")
        ct = "、".join(f"{n}({c})" for n, c in r["content"][:3]) or "未命中规则"
        L.append(f"- 内容类型：{ct}")
        L.append(f"- 判读依据：{'；'.join(t.get('why', [])) or '—'}")
        if t.get("scores"):
            L.append(f"- 各调性得分：{t['scores']}")
        ac = r["ac"]
        if not ac.get("error"):
            p = ac.get("pitch") or {}
            L.append(f"- 声学：基频均值 {p.get('f0_median','—')}Hz（男声常见 85–155）｜ "
                     f"CV {p.get('f0_cv','—')} ｜ 起伏幅度 {p.get('f0_range_p5_p95','—')}Hz ｜ "
                     f"能量动态 {(ac.get('energy') or {}).get('dyn_range_db','—')}dB ｜ "
                     f"说话占比 {ac.get('speech_ratio','—')}")
        L.append("")

    (od / a.out).write_text("\n".join(L), encoding="utf-8")
    print(f"\n✅ 产出 {od/a.out}")
    print(f"   {od/'acoustic.json'}")


if __name__ == "__main__":
    main()
