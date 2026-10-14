#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音作品信息抓取（免登录、免签名）

原理：用本机 Chrome 的无头模式渲染视频页，再解析渲染后的 DOM。
     不依赖签名（x-bogus），也不需要登录态。

能拿到：文案（desc）、发布时间、点赞/评论/收藏/转发、作者、粉丝数
拿不到：口播全文（需语音转文字，见 SKILL.md 的能力边界）

用法：
    python3 fetch_douyin.py --url https://v.douyin.com/XXXX/ --url https://v.douyin.com/YYYY/
    python3 fetch_douyin.py --url ... --json out.json
    python3 fetch_douyin.py --id 7019227949152914719

注意：每条渲染约 30~90 秒；脚本并行处理，3 条同时跑约 1~2 分钟。
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def find_chrome() -> str:
    for p in CHROME_CANDIDATES:
        if Path(p).exists():
            return p
    for name in ("google-chrome", "chromium", "chrome"):
        p = shutil.which(name)
        if p:
            return p
    sys.exit("未找到 Chrome/Chromium，无法渲染页面")


def resolve_short_url(url: str) -> str:
    """短链 → 完整分享地址"""
    r = subprocess.run(
        ["curl", "-s", "-m", "20", "-o", "/dev/null",
         "-w", "%{redirect_url}",
         "-A", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
               "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
         url],
        capture_output=True, text=True)
    return r.stdout.strip()


def extract_id(url: str) -> str | None:
    m = re.search(r"/video/(\d+)", url)
    return m.group(1) if m else None


def render(chrome: str, video_id: str, budget: int = 9000, timeout: int = 240) -> str:
    """
    渲染视频页拿 DOM。

    ⚠️ 关键：stdout 必须重定向到**文件**，不能用管道。
    Chrome 会 fork 子进程，子进程继承 stdout 写端不关闭，
    用 capture_output/subprocess.PIPE 时会永远等不到 EOF，必然超时。

    成功的页面 DOM 约 1.4MB；低于 100KB 视为失败。
    """
    tmp = tempfile.mkdtemp(prefix="dychrome_")
    out = Path(tmp) / "dom.html"
    try:
        with open(out, "w") as fo, open(Path(tmp) / "err.log", "w") as fe:
            subprocess.run(
                [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--no-first-run", "--no-default-browser-check", "--disable-extensions",
                 "--disable-background-networking", "--mute-audio",
                 f"--user-data-dir={tmp}", f"--virtual-time-budget={budget}",
                 "--dump-dom", f"https://www.douyin.com/video/{video_id}"],
                stdout=fo, stderr=fe, stdin=subprocess.DEVNULL, timeout=timeout)
        if out.exists() and out.stat().st_size > 100_000:
            return out.read_text(encoding="utf-8", errors="ignore")
        return ""
    except subprocess.TimeoutExpired:
        return ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def parse(dom: str, video_id: str) -> dict:
    info = {"id": video_id, "url": f"https://www.douyin.com/video/{video_id}"}

    m = re.search(r"<title>(.*?)</title>", dom, re.S)
    if m:
        info["desc"] = re.sub(r"\s*-\s*抖音$", "", html.unescape(m.group(1)).strip())

    m = re.search(r"发布时间：([\d\-: ]+)", dom)
    info["publish"] = m.group(1).strip() if m else ""

    nums = re.findall(r">(\d+\.?\d*[万亿]?)<", dom)
    if len(nums) >= 5:
        info["like"], info["comment"], info["collect"], info["share"] = nums[1:5]
    if len(nums) >= 11:
        info["followers"], info["total_likes"] = nums[9], nums[10]

    # 标签
    if info.get("desc"):
        info["tags"] = re.findall(r"#([^\s#]+)", info["desc"])
    return info


def fetch_one(chrome: str, url_or_id: str, budget: int) -> dict:
    if url_or_id.isdigit():
        vid = url_or_id
    elif "v.douyin.com" in url_or_id:
        vid = extract_id(resolve_short_url(url_or_id))
    else:
        vid = extract_id(url_or_id)
    if not vid:
        return {"error": "无法解析视频 ID", "input": url_or_id}
    dom = render(chrome, vid, budget)
    if not dom:
        return {"error": "渲染失败或超时", "id": vid}
    return parse(dom, vid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", default=[], help="分享链接，可多次传入")
    ap.add_argument("--id", action="append", default=[], help="直接给视频 ID")
    ap.add_argument("--json", help="结果保存到 JSON 文件")
    ap.add_argument("--budget", type=int, default=9000, help="虚拟时间预算(ms)")
    ap.add_argument("--workers", type=int, default=3, help="并行数")
    a = ap.parse_args()

    targets = a.url + a.id
    if not targets:
        ap.error("需要 --url 或 --id")

    chrome = find_chrome()
    print(f"使用浏览器：{chrome}")
    print(f"共 {len(targets)} 条，并行 {a.workers} 条…\n")

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        results = list(ex.map(lambda t: fetch_one(chrome, t, a.budget), targets))

    for r in results:
        print("=" * 70)
        if r.get("error"):
            print(f"❌ {r.get('input') or r.get('id')}：{r['error']}")
            continue
        print(f"文案：{r.get('desc', '未抓到')}")
        print(f"发布：{r.get('publish') or '未抓到'}")
        print(f"数据：赞 {r.get('like','-')} / 评 {r.get('comment','-')} / "
              f"藏 {r.get('collect','-')} / 转 {r.get('share','-')}")
        if r.get("tags"):
            print(f"标签：{' '.join('#'+t for t in r['tags'])}")
        if r.get("followers"):
            print(f"账号：粉丝 {r['followers']} / 获赞 {r.get('total_likes','-')}")

    if a.json:
        Path(a.json).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n已保存：{a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
