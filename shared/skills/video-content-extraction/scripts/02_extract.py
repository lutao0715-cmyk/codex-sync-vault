# -*- coding: utf-8 -*-
"""抽帧 + OCR 提取内嵌字幕（一步到位）。

用法:
    python 02_extract.py <视频路径> [输出目录]

前置: 先用 01_probe.py 定位字幕行 y 范围，改下方 CROP_TOP / CROP_BOTTOM。
输出: subtitles_ocr.json + subtitles_ocr.txt（带时间轴，去重后）
"""
import sys, os, subprocess, json, glob, cv2, numpy as np
import imageio_ffmpeg
from rapidocr_onnxruntime import RapidOCR

# ===== 可调参数 =====
FPS = 2            # 抽帧帧率(每秒几帧)
CROP_TOP = 485     # 字幕行上边界 y（抖音竖屏录屏常在画面中下部）
CROP_BOTTOM = 560  # 字幕行下边界 y
SCALE = 2          # 裁剪后放大倍数(提升识别率)
MIN_SCORE = 0.4    # 置信度阈值
# =====================


def has_cjk(s):
    return any('\u4e00' <= ch <= '\u9fff' for ch in s)


def main():
    if len(sys.argv) < 2:
        print("用法: python 02_extract.py <视频路径> [输出目录]")
        return
    src = sys.argv[1]
    base = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(__file__))
    frames_dir = os.path.join(base, "_frames")
    os.makedirs(frames_dir, exist_ok=True)

    ff = imageio_ffmpeg.get_ffmpeg_exe()

    # 1) 抽帧
    out_pat = os.path.join(frames_dir, "f_%04d.jpg")
    print("抽帧中 ...", flush=True)
    subprocess.run([ff, "-y", "-i", src, "-vf", "fps=%d" % FPS, "-q:v", "3", out_pat],
                   capture_output=True)
    frames = sorted(glob.glob(os.path.join(frames_dir, "f_*.jpg")))
    print("total frames:", len(frames), flush=True)

    # 2) OCR
    print("init engine ...", flush=True)
    eng = RapidOCR()
    results = []
    prev_text = None
    for i, fp in enumerate(frames):
        img = cv2.imdecode(np.fromfile(fp, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        crop_bottom = min(CROP_BOTTOM, h)
        crop = img[CROP_TOP:crop_bottom, :]
        if SCALE != 1:
            crop = cv2.resize(crop, None, fx=SCALE, fy=SCALE, interpolation=cv2.INTER_CUBIC)
        res, _ = eng(crop)
        text = ""
        if res:
            parts = []
            for r in res:
                txt = r[1]
                sc = float(r[2]) if isinstance(r[2], str) else r[2]
                if sc < MIN_SCORE:
                    continue
                if has_cjk(txt):
                    parts.append(txt)
            text = " ".join(parts).strip()
        t = round(i / FPS, 2)
        if text and text != prev_text:
            results.append({"t": t, "text": text})
            prev_text = text
        if i % 300 == 0:
            print("processed %d/%d" % (i, len(frames)), flush=True)

    # 3) 输出
    out_json = os.path.join(base, "subtitles_ocr.json")
    out_txt = os.path.join(base, "subtitles_ocr.txt")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    lines = []
    for r in results:
        mm = int(r["t"] // 60)
        ss = r["t"] % 60
        lines.append("[%02d:%04.1f] %s" % (mm, ss, r["text"]))
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("DONE. 去重后字幕条数:", len(results), flush=True)
    print("输出:", out_txt, flush=True)


if __name__ == "__main__":
    main()
