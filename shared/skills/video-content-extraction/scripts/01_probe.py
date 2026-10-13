# -*- coding: utf-8 -*-
"""探帧工具：抽取若干时间点帧并全图 OCR，定位字幕所在水平行。

用法:
    python 01_probe.py <视频路径> [输出目录]

作用: 摸清视频结构——是否 App 录屏(画面里有固定 UI)、字幕在哪条水平线、
      正片时长/是否循环。是 02_extract.py 的前置步骤。
"""
import sys, os, subprocess, cv2, numpy as np
import imageio_ffmpeg
from rapidocr_onnxruntime import RapidOCR


def main():
    if len(sys.argv) < 2:
        print("用法: python 01_probe.py <视频路径> [输出目录]")
        return
    src = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probe")
    os.makedirs(outdir, exist_ok=True)

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    eng = RapidOCR()

    # 探测时间点(秒)，按视频长度自行增删
    times = [0, 8, 20, 40, 75, 120, 200, 300, 400, 500, 560]

    for t in times:
        fp = os.path.join(outdir, "t%03d.jpg" % t)
        subprocess.run([ff, "-y", "-ss", str(t), "-i", src, "-frames:v", "1", "-q:v", "2", fp],
                       capture_output=True)
        img = cv2.imdecode(np.fromfile(fp, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print("[t=%ds] 无帧(可能超时长)" % t, flush=True)
            continue
        res, _ = eng(img)
        texts = []
        if res:
            for r in res:
                box, txt = r[0], r[1]
                sc = float(r[2]) if isinstance(r[2], str) else r[2]
                if sc < 0.4:
                    continue
                texts.append((int(box[0][1]), txt))
            texts.sort()
        print("\n===== t=%ds =====" % t, flush=True)
        for y0, txt in texts:
            print("  [y=%3d] %s" % (y0, txt), flush=True)


if __name__ == "__main__":
    main()
