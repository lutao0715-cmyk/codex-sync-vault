#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BGM 喜好分析器 —— 从涛哥自筛的曲库里量化「配乐品味」

曲库是他自己挑的，比任何推断都可信。要读出：
  节奏（BPM）    → 铺底型（慢）还是推进型（快）
  能量动态        → 有没有 build-up / 爆点（决定能不能配"高潮段落"）
  频谱重心        → 明亮（钢琴/弦乐高音）还是厚重（低音/鼓）
  低频占比        → 有没有打击乐/重低音（决定"燃"度）
  时长            → 是否够铺满一条视频

用法：
  python3 analyze_bgm.py <目录> [--out bgm-profile.json]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

SR = 22050
EXTS = (".mp3", ".m4a", ".mp4", ".flac", ".wav", ".ogg", ".aac")


def load(path, max_sec=180.0):
    import av
    c = av.open(path)
    try:
        if not [s for s in c.streams if s.type == "audio"]:
            return np.zeros(0), SR
        rs = av.AudioResampler(format="s16", layout="mono", rate=SR)
        out = []
        for frame in c.decode(audio=0):
            for f in rs.resample(frame):
                a = f.to_ndarray()
                out.append((a[0] if a.ndim == 2 else a).astype(np.float32))
            if sum(len(x) for x in out) > max_sec * SR:
                break
        for f in rs.resample(None):
            a = f.to_ndarray()
            out.append((a[0] if a.ndim == 2 else a).astype(np.float32))
        return (np.concatenate(out) / 32768.0)[: int(max_sec * SR)] if out else np.zeros(0), SR
    finally:
        c.close()


def profile(path: str, max_sec: float = 60.0) -> dict:
    y, sr = load(path, max_sec=max_sec)
    if len(y) < sr * 2:
        return {"error": "过短或读取失败"}
    hop, win = int(sr * 0.02), int(sr * 0.04)   # 20ms hop / 40ms win
    n = len(y) // hop
    fr = np.lib.stride_tricks.as_strided(
        y, shape=(n, win), strides=(y.strides[0] * hop, y.strides[0])).copy()
    rms = np.sqrt((fr ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms)

    # --- onset envelope + tempo ---
    onset = np.maximum(0, np.diff(db))
    onset = np.convolve(onset, np.ones(3) / 3, mode="same")
    ac = np.correlate(onset - onset.mean(), onset - onset.mean(), "full")[len(onset) - 1:]
    ac /= max(ac[0], 1e-9)
    lo, hi = int(60 / 180 / 0.02), int(60 / 60 / 0.02)      # 60–180 BPM
    bpm = 0.0
    if hi < len(ac):
        lag = np.argmax(ac[lo:hi]) + lo
        bpm = round(60 / (lag * 0.02), 1)

    # --- 频谱特征（整体）---
    seg = y[: sr * 30] if len(y) > sr * 30 else y
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1 / sr)
    tot = spec.sum() + 1e-9
    centroid = float((spec * freqs).sum() / tot)
    low_ratio = float(spec[freqs < 250].sum() / tot)         # 低频（鼓/贝斯）
    mid_ratio = float(spec[(freqs >= 250) & (freqs < 4000)].sum() / tot)
    high_ratio = float(spec[freqs >= 4000].sum() / tot)

    return {
        "duration_sec": round(len(y) / sr, 1),
        "tempo_bpm": bpm,
        "energy_db": {"median": round(float(np.median(db)), 1),
                      "p5": round(float(np.percentile(db, 5)), 1),
                      "p95": round(float(np.percentile(db, 95)), 1),
                      "dyn_range": round(float(np.percentile(db, 95) - np.percentile(db, 5)), 1)},
        "spectrum": {"centroid_hz": round(centroid),
                     "low_pct": round(low_ratio * 100, 1),
                     "mid_pct": round(mid_ratio * 100, 1),
                     "high_pct": round(high_ratio * 100, 1)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*", help="音频文件或目录")
    ap.add_argument("--out", default="bgm-profile.json")
    ap.add_argument("--one", default=None,
                    help="内部用：只处理单个文件并打印 JSON（每条独立进程，防 PyAV 段错误拖垮整批）")
    ap.add_argument("--max-sec", type=float, default=60.0)
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()

    # ---- 单文件模式（子进程入口）----
    if a.one:
        try:
            r = profile(a.one, max_sec=a.max_sec)
        except Exception as e:
            r = {"error": f"{type(e).__name__}: {e}"}
        r["file"] = os.path.basename(a.one)
        print("@@JSON@@" + json.dumps(r, ensure_ascii=False))
        return

    files = []
    for d in a.dirs:
        d = os.path.abspath(os.path.expanduser(d))
        if os.path.isdir(d):
            files += [os.path.join(d, f) for f in sorted(os.listdir(d))
                      if f.lower().endswith(EXTS)]
        elif os.path.isfile(d):
            files.append(d)

    print(f"共 {len(files)} 首 | 每首独立进程（防崩溃）| 最长分析 {a.max_sec:.0f}s", flush=True)

    # ---- 每条丢进独立子进程，段错误也只损失那一条 ----
    import subprocess
    from concurrent.futures import ThreadPoolExecutor

    def run_one(p):
        try:
            r = subprocess.run(
                [sys.executable, os.path.abspath(__file__),
                 "--one", p, "--max-sec", str(a.max_sec)],
                capture_output=True, text=True, timeout=300)
            for ln in (r.stdout or "").splitlines():
                if ln.startswith("@@JSON@@"):
                    return json.loads(ln[len("@@JSON@@"):])
            return {"file": os.path.basename(p),
                    "error": f"子进程退出码 {r.returncode}"
                             + ("（段错误）" if r.returncode == -11 else "")}
        except subprocess.TimeoutExpired:
            return {"file": os.path.basename(p), "error": "超时"}
        except Exception as e:
            return {"file": os.path.basename(p), "error": f"{type(e).__name__}: {e}"}

    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(run_one, files):
            rows.append(r)
            if r.get("error"):
                print(f"  ❌ {r['file'][:45]}: {r['error']}", flush=True)
            else:
                print(f"  {r['file'][:50]:52s} {r['tempo_bpm']:6.1f}BPM "
                      f"动态{r['energy_db']['dyn_range']:5.1f}dB "
                      f"低频{r['spectrum']['low_pct']:4.1f}% "
                      f"重心{r['spectrum']['centroid_hz']:5d}Hz", flush=True)

    ok = [r for r in rows if not r.get("error")]
    summ = {}
    if ok:
        summ = {
            "count": len(ok),
            "tempo_median": round(float(np.median([r["tempo_bpm"] for r in ok])), 1),
            "tempo_range": [min(r["tempo_bpm"] for r in ok), max(r["tempo_bpm"] for r in ok)],
            "dyn_median": round(float(np.median([r["energy_db"]["dyn_range"] for r in ok])), 1),
            "low_pct_median": round(float(np.median([r["spectrum"]["low_pct"] for r in ok])), 1),
            "centroid_median": int(np.median([r["spectrum"]["centroid_hz"] for r in ok])),
            "total_minutes": round(sum(r["duration_sec"] for r in ok) / 60, 1),
        }
        print(f"\n汇总: {summ}", flush=True)

    out = {"summary": summ, "tracks": rows}
    Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n✅ 产出 {a.out}", flush=True)


if __name__ == "__main__":
    main()
