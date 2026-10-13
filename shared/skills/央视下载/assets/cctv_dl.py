# -*- coding: utf-8 -*-
"""央视网视频下载器
用法: python cctv_dl.py <tv.cctv.cn页面URL> [-o 输出文件.mp4]
流程: 页面取 guid -> 探测未加密 lxdns 链路 -> 顺序下载 TS 分片拼接 -> ffmpeg 校验
"""
import argparse, os, re, sys, time, urllib.parse, urllib.request

REFERER = "https://tv.cctv.cn/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": REFERER}
CDN = "http://hls.cntv.lxdns.com/asp/hls/"

def fetch(url, timeout=60, retries=3):
    for a in range(retries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except Exception as e:
            if a == retries - 1:
                raise
            print(f"  retry {a+1}: {e}", flush=True)
            time.sleep(2)

def get_guid(page_url):
    html = fetch(page_url, timeout=30).decode("utf-8", "ignore")
    m = re.search(r'guid\s*=\s*["\']([a-f0-9]{32})', html) or \
        re.search(r'videoCenterId["\'\s:=]+([a-f0-9]{32})', html)
    if not m:
        sys.exit("未在页面中找到视频 guid")
    return m.group(1)

def probe_playlist(guid):
    """探测未加密链路，返回内容最大码率的 variant m3u8 URL
    注意：main master 列表可能只登记 450 档，但 2000.m3u8 等高码率媒体列表
    实际可直接访问，所以先试数字码率（从高到低），main 作兜底。"""
    cands = ["2000", "1000", "720", "450", "main"]
    best = None
    for br in cands:
        u = f"{CDN}{br}/0303000a/3/default/{guid}/{br}.m3u8"
        try:
            pl = fetch(u, timeout=20, retries=1).decode("utf-8", "ignore")
        except Exception:
            continue
        if br == "main" and "#EXT-X-STREAM-INF" in pl:
            # master: 解析所有 variant，取 BANDWIDTH 最大者
            bw, path, cur = 0, None, 0
            for line in pl.splitlines():
                line = line.strip()
                if line.startswith("#EXT-X-STREAM-INF"):
                    m = re.search(r"BANDWIDTH=(\d+)", line)
                    cur = int(m.group(1)) if m else 0
                elif line and not line.startswith("#"):
                    if cur >= bw:
                        bw, path = cur, urllib.parse.urljoin(u, line)
            if path:
                return path, bw
        elif br != "main" and "#EXTINF" in pl:
            # 直接是媒体列表，记录码率最高的
            if best is None or br.isdigit() and int(br) > int(best[0]):
                best = (br, u)
    if best:
        return best[1], int(best[0])
    sys.exit("所有未加密链路均不可用")

def download(playlist_url, out):
    pl = fetch(playlist_url).decode("utf-8", "ignore")
    segs = [urllib.parse.urljoin(playlist_url, l.strip())
            for l in pl.splitlines() if l.strip() and not l.startswith("#")]
    print(f"共 {len(segs)} 个分片")
    with open(out, "wb") as f:
        for i, s in enumerate(segs):
            f.write(fetch(s))
            if i % 10 == 0 or i == len(segs) - 1:
                print(f"  {i+1}/{len(segs)}  {os.path.getsize(out)/1048576:.1f} MB", flush=True)

def verify(out):
    with open(out, "rb") as f:
        head = f.read(188 * 4)
    ok_ts = all(head[i * 188] == 0x47 for i in range(4))
    print("TS 同步字节:", "OK" if ok_ts else "FAIL")
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        print("(未装 imageio-ffmpeg，跳过 ffmpeg 校验；建议 pip install imageio-ffmpeg)")
        return
    import subprocess
    p = subprocess.run([ff, "-hide_banner", "-v", "error", "-i", out, "-f", "null", "-"],
                       capture_output=True, text=True)
    n_err = len([l for l in (p.stderr or "").splitlines() if "error" in l.lower()])
    print(f"ffmpeg 解码错误: {n_err}", "→ 文件正常" if n_err == 0 else "→ 文件异常！")
    if n_err:
        sys.exit(1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", help="tv.cctv.cn 节目页链接")
    ap.add_argument("-o", "--output", default=None, help="输出文件路径")
    args = ap.parse_args()
    out = args.output or "cctv_video.mp4"
    guid = get_guid(args.url)
    print("guid:", guid)
    pl_url, bw = probe_playlist(guid)
    print("m3u8:", pl_url, f"(≈{bw//1000}kbps)")
    download(pl_url, out)
    verify(out)
    print("DONE:", os.path.abspath(out), f"{os.path.getsize(out)/1048576:.1f} MB")

if __name__ == "__main__":
    main()
