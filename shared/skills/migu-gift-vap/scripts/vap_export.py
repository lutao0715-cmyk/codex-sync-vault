# -*- coding: utf-8 -*-
"""VAP 直播礼物导出 - 一键脚本
用法: python vap_export.py <源视频.mp4> <输出.vap> [分辨率]
前置: E:/WorkBuddy/tools/vaptool/vaptool_win (mp4edit), ffmpeg shim, venv(pillow numpy scipy)
"""
import os, sys, json, struct, subprocess
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

FFMPEG = r"C:\Users\win\.workbuddy\binaries\shims\ffmpeg.exe"
MP4EDIT = r"E:\WorkBuddy\tools\vaptool\vaptool_win\win\mp4edit.exe"
FPS = 24
GAP = 4
SCALE = 0.5
CRF = 18
TOL = 38.0
FEATHER = 1.2
WORK = r"E:\WorkBuddy\outputs\vap_work"


def extract_alpha(rgba):
    """边缘连通泛洪抠纯色底 + 羽化 + 右下角水印清除"""
    h, w = rgba.shape[:2]
    rgb = rgba[..., :3].astype(np.float32)
    border = np.concatenate([rgb[:3].reshape(-1, 3), rgb[-3:].reshape(-1, 3),
                             rgb[:, :3].reshape(-1, 3), rgb[:, -3:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    bglike = dist < TOL
    lbl, _ = ndimage.label(bglike)
    border_labels = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]])))
    border_labels.discard(0)
    bg_mask = np.isin(lbl, list(border_labels)) if border_labels else np.zeros_like(bglike)
    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
    alpha[int(h * 0.93):, int(w * 0.91):] = 0  # 豆包水印角
    return alpha


def build(rgba_dir, work_dir, out_file):
    os.makedirs(work_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(rgba_dir) if f.endswith(".png"))
    w, h = Image.open(os.path.join(rgba_dir, files[0])).size
    aw, ah = int(w * SCALE), int(h * SCALE)
    hW, vH = w + GAP + aw, h + GAP + ah
    if max(hW, h) > max(w, vH):  # 垂直布局
        ax, ay = 0, h + GAP
        outW, outH = w, vH
    else:  # 水平布局
        ax, ay = w + GAP, 0
        outW, outH = hW, h
    outW += 0 if outW % 16 == 0 else (outW // 16 + 1) * 16 - outW
    outH += 0 if outH % 16 == 0 else (outH // 16 + 1) * 16 - outH

    packed = os.path.join(work_dir, "packed")
    os.makedirs(packed, exist_ok=True)
    for i, f in enumerate(files):
        im = Image.open(os.path.join(rgba_dir, f)).convert("RGBA")
        arr = np.asarray(im).astype(np.float32)
        canvas = np.zeros((outH, outW, 3), dtype=np.float32)
        canvas[0:h, 0:w] = arr[..., :3] * (arr[..., 3:] / 255.0)
        a_small = np.asarray(im.split()[3].resize((aw, ah), Image.BILINEAR), dtype=np.float32)
        canvas[ay:ay + ah, ax:ax + aw] = a_small[..., None]
        Image.fromarray(canvas.astype(np.uint8)).save(os.path.join(packed, "%03d.png" % i))

    tmp = os.path.join(work_dir, "tmp_video.mp4")
    subprocess.run([FFMPEG, "-framerate", str(FPS), "-i", os.path.join(packed, "%03d.png"),
                    "-pix_fmt", "yuv420p", "-vcodec", "libx264", "-crf", str(CRF),
                    "-profile:v", "main", "-level", "4.0", "-bf", "0",
                    "-bufsize", "2000k", "-y", tmp], check=True, capture_output=True)

    cfg = {"info": {"v": 2, "f": len(files), "w": w, "h": h, "fps": FPS,
                    "videoW": outW, "videoH": outH, "aFrame": [ax, ay, aw, ah],
                    "rgbFrame": [0, 0, w, h], "isVapx": 0, "orien": 0}}
    raw = json.dumps(cfg, separators=(",", ":")).encode("utf-8")
    bin_path = os.path.join(work_dir, "vapc.bin")
    with open(bin_path, "wb") as fp:
        fp.write(struct.pack(">I", len(raw) + 8) + b"vapc" + raw)

    # mp4edit 按冒号分割参数，必须用相对路径（不能用 E: 盘符绝对路径）
    r = subprocess.run([MP4EDIT, "--insert", ":vapc.bin:3", "tmp_video.mp4",
                        os.path.abspath(out_file)], capture_output=True, text=True, cwd=work_dir)
    if r.returncode != 0 or not os.path.exists(out_file) or os.path.getsize(out_file) == 0 or r.stderr.strip():
        raise RuntimeError("mp4edit failed (rc=%s): %s" % (r.returncode, r.stderr))
    print("OK ->", out_file, os.path.getsize(out_file), "bytes, video %dx%d, %d frames" % (outW, outH, len(files)))


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    size = int(sys.argv[3]) if len(sys.argv) > 3 else 720
    os.makedirs(WORK, exist_ok=True)
    frames = os.path.join(WORK, "frames")
    rgba = os.path.join(WORK, "rgba")
    os.makedirs(frames, exist_ok=True)
    os.makedirs(rgba, exist_ok=True)
    vf = "scale=-1:%d,crop=%d:%d" % (size, size, size)  # 短边对齐后居中裁方
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", src, "-vf", vf,
                    os.path.join(frames, "f%04d.png")], check=True)
    for i, f in enumerate(sorted(os.listdir(frames))):
        img = Image.open(os.path.join(frames, f)).convert("RGB")
        a = Image.fromarray(extract_alpha(np.asarray(img)), "L").filter(ImageFilter.GaussianBlur(FEATHER))
        rgba_im = img.convert("RGBA")
        rgba_im.putalpha(a)
        rgba_im.save(os.path.join(rgba, "%03d.png" % i))
    build(rgba, os.path.join(WORK, "pack"), out)
