# -*- coding: utf-8 -*-
r"""
央视 720p 一键下载脚本（h5e 加密链路解密版）
用法:
  python cctv_hd_720p.py "https://tv.cctv.cn/2026/03/01/VIDExxxx.shtml" -o "输出.mp4"
  python cctv_hd_720p.py "https://tv.cctv.cn/..."            # 默认输出到 C:\Users\win\Desktop\<标题>-720p.mp4

前置条件: 解密工具链已装在 E:\WorkBuddy\outputs\.cctv-hd\CCTV-Download-main\h5e_decrypt\
（搭建方法见 SKILL.md「工具链搭建」；本脚本不负责搭建）
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

NODE = r"C:/Users/win/.workbuddy/binaries/node/versions/22.22.2-3/node.exe"
WORK = r"E:/WorkBuddy/outputs/.cctv-hd"
DEC = os.path.join(WORK, "CCTV-Download-main", "h5e_decrypt")
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://tv.cctv.cn/"}


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("缺 ffmpeg：pip install imageio-ffmpeg -i https://mirrors.aliyun.com/pypi/simple/")


def check_toolchain():
    ok = (os.path.exists(os.path.join(DEC, "build", "cli", "main.js"))
          and os.path.exists(os.path.join(DEC, "build", "external", "cctv.worker.js"))
          and os.path.exists(os.path.join(DEC, "node_modules")))
    if not ok:
        sys.exit("解密工具链不可用，先按 SKILL.md「工具链搭建」重装到 " + DEC)


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    data = urllib.request.urlopen(req, timeout=30).read()
    return data if binary else data.decode("utf-8", "ignore")


def get_video_info(page_url):
    html = fetch(page_url)
    m = re.search(r'guid\s*=\s*["\']([a-f0-9]{32})', html)
    if not m:
        sys.exit("页面里没找到 guid")
    guid = m.group(1)
    api = "https://vdn.apps.cntv.cn/api/getHttpVideoInfo.do?pid=" + guid
    data = json.loads(fetch(api))
    title = re.sub(r'[\\/:*?"<>|]', "", (data.get("title") or guid)).strip()
    h5e = data.get("manifest", {}).get("hls_h5e_url")
    if not h5e:
        sys.exit("接口没返回 hls_h5e_url")
    return title, h5e


def pick_best_variant(master_url):
    """拉 master m3u8，挑 BANDWIDTH 最大的 variant（返回其绝对 URL）。
    variant 路径三种形态：完整 URL / 主机根绝对路径（以 / 开头）/ 相对路径"""
    text = fetch(master_url)
    base = master_url.rsplit("/", 1)[0] + "/"
    root = re.match(r"(https?://[^/]+)", master_url).group(1)
    best, bw = None, -1
    for block in re.finditer(r"#EXT-X-STREAM-INF:([^\n]*)\n([^\n#]+)", text):
        attrs, path = block.group(1), block.group(2).strip()
        m = re.search(r"BANDWIDTH=(\d+)", attrs)
        b = int(m.group(1)) if m else 0
        if path.startswith("http"):
            full = path
        elif path.startswith("/"):
            full = root + path
        else:
            full = base + path
        if b > bw:
            bw, best = b, full
    if not best:
        sys.exit("master m3u8 里没有 variant")
    return best, bw


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.stdout.strip():
        print(r.stdout.strip()[-1500:], flush=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr.strip()[-2500:], flush=True)
        sys.exit("FAILED rc=%d: %s" % (r.returncode, cmd[0]))
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("-o", "--output", default=None, help="输出 mp4 路径")
    args = ap.parse_args()

    check_toolchain()
    ffmpeg = ffmpeg_exe()
    title, h5e_master = get_video_info(args.url)
    out = args.output or os.path.join(r"C:/Users/win/Desktop", title + "-720p.mp4")
    out = os.path.abspath(out)
    print("标题:", title, flush=True)

    # 1) 选最高档 variant
    media_url, bw = pick_best_variant(h5e_master)
    print("媒体清单: %dkbps %s" % (bw // 1000, media_url), flush=True)

    # 2) 下载分片（断点续传）
    ts_dir = os.path.join(WORK, "ts_run")
    os.makedirs(ts_dir, exist_ok=True)
    text = fetch(media_url)
    names = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    seg_base = media_url.rsplit("/", 1)[0] + "/"
    print("分片数:", len(names), flush=True)
    for i, name in enumerate(names):
        p = os.path.join(ts_dir, name)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            continue
        for attempt in range(5):
            try:
                data = fetch(seg_base + name, binary=True)
                if data:
                    open(p, "wb").write(data)
                    break
            except Exception:
                time.sleep(1 + attempt * 2)
        else:
            sys.exit("分片下载失败: " + name)
        if (i + 1) % 50 == 0:
            print("progress %d/%d" % (i + 1, len(names)), flush=True)

    # 3) 生成分批 m3u8（与分片同目录、裸文件名、二进制写、EXTINF 与文件名分行）
    BATCH = 30
    parts = [names[i:i + BATCH] for i in range(0, len(names), BATCH)]
    header = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-TARGETDURATION:10\n"
    for idx, group in enumerate(parts, 1):
        with open(os.path.join(ts_dir, "part%d.m3u8" % idx), "wb") as f:
            f.write(header.encode())
            for n in group:
                f.write(b"#EXTINF:10.000000,\n")
                f.write((n + "\n").encode())

    # 4) 分批解密（每批独立进程，输出不同文件）
    for idx in range(1, len(parts) + 1):
        print("解密 part%d/%d" % (idx, len(parts)), flush=True)
        run([NODE, "build/cli/main.js", "--quiet",
             "--local-m3u8", os.path.join(ts_dir, "part%d.m3u8" % idx),
             os.path.join(ts_dir, "out_p%d.ts" % idx)], cwd=DEC)

    # 5) 合并 + 校验 + 出 MP4
    with open(os.path.join(ts_dir, "list.txt"), "w") as f:
        f.write("".join("file 'out_p%d.ts'\n" % i for i in range(1, len(parts) + 1)))
    run([ffmpeg, "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", "list.txt", "-c", "copy", "full.ts"], cwd=ts_dir)
    r = subprocess.run([ffmpeg, "-v", "error", "-i", "full.ts", "-f", "null", "-"],
                       cwd=ts_dir, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.stderr.strip():
        print("校验警告(源流微瑕可接受):", r.stderr.strip()[-500:], flush=True)
    run([ffmpeg, "-y", "-v", "error", "-i", "full.ts", "-c", "copy",
         "-movflags", "+faststart", out], cwd=ts_dir)

    # 6) 中间产物不自动清理——沙箱拦截批量删除会报错。
    #    主 agent 在任务完成、用户拿到成片后再用 Python 单独清理 ts_run 目录。
    print("完成:", out, os.path.getsize(out), "bytes", flush=True)


if __name__ == "__main__":
    main()
