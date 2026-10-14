#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频号（微信视频号）作品信息抓取

原理
----
视频号分享短链 https://weixin.qq.com/sph/XXXX
  --301--> https://channels.weixin.qq.com/finder-preview/pages/sph?id=XXXX
该预览页是 Vue SPA，未登录也能渲染出：文案、作者、发布时间、地点、四项互动数据。
渲染手段：本机 Chrome 无头模式 --dump-dom。

⚠️ 已知边界（实测）
- 页面**不暴露音视频文件**。页面里唯一的 stodownload 地址返回的是封面图（JPEG 540x720），
  不是 mp4。所以**拿不到口播音频，无法转录口播全文**。
- 文案字段（feed-desc-wrap）通常是短标题，不等于口播全文。

用法
----
  python3 fetch_channels.py --url https://weixin.qq.com/sph/AZXSyBN27 [--url ...]
  python3 fetch_channels.py --url ... --json out.json
"""

import argparse
import html as htmllib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
]

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# 互动项图标 → 中文含义（顺序即页面顺序）
ICON_MEANING = {
    "thumb-regular": "点赞",
    "share-regular": "转发",
    "heart-regular": "推荐",
    "bubble-regular": "评论",
}

MIN_DOM_LEN = 8_000          # 正常预览页约 27KB，低于这个视为渲染失败
RENDER_BUDGET_MS = 12_000    # 虚拟时间预算


def find_chrome() -> str:
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    found = shutil.which("google-chrome") or shutil.which("chromium")
    if found:
        return found
    sys.exit("❌ 未找到可用的 Chrome / Chromium，无法渲染视频号页面")


def resolve_short_link(url: str, timeout: int = 20) -> str:
    """短链 → 落地页 URL。失败则原样返回。"""
    try:
        r = subprocess.run(
            ["curl", "-s", "-m", str(timeout), "-o", "/dev/null",
             "-w", "%{http_code}\t%{redirect_url}", "-A", UA, url],
            capture_output=True, text=True, timeout=timeout + 5)
        parts = (r.stdout or "").split("\t")
        if len(parts) == 2 and parts[1].startswith("http"):
            return parts[1].strip()
    except Exception:
        pass
    return url


def render(chrome: str, url: str, budget: int = RENDER_BUDGET_MS,
           timeout: int = 180, retries: int = 3) -> str:
    """
    渲染页面拿 DOM。

    重要：Chrome 会 fork 子进程并持有 stdout 管道，直接 capture_output=True
    会让 Python 永远等不到 EOF（表现为超时）。所以这里把 stdout 重定向到文件。
    """
    last = ""
    for attempt in range(1, retries + 1):
        tmp = tempfile.mkdtemp(prefix="sphchrome_")
        out_path = os.path.join(tmp, "dom.html")
        try:
            with open(out_path, "w", encoding="utf-8", errors="ignore") as fo, \
                 open(os.path.join(tmp, "err.log"), "w") as fe:
                proc = subprocess.Popen(
                    [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                     "--no-first-run", "--no-default-browser-check",
                     "--disable-extensions", "--disable-background-networking",
                     "--mute-audio", "--window-size=1280,900",
                     f"--user-data-dir={tmp}", f"--virtual-time-budget={budget}",
                     "--dump-dom", url],
                    stdout=fo, stderr=fe, stdin=subprocess.DEVNULL)
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
            with open(out_path, encoding="utf-8", errors="ignore") as f:
                last = f.read()
            if len(last) >= MIN_DOM_LEN:
                return last
        except Exception:
            last = ""
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return last


def _text_of(dom: str, class_name: str) -> str:
    """取 class 内含的可见文本（剥标签）"""
    m = re.search(r'class="[^"]*\b' + re.escape(class_name) + r'\b[^"]*"[^>]*>(.*?)</div>',
                  dom, re.S)
    if not m:
        return ""
    txt = re.sub(r"<[^>]+>", "", m.group(1))
    return htmllib.unescape(txt).strip()


def parse(dom: str) -> dict:
    """从渲染后的 DOM 提取结构化字段"""
    data = {}

    # 文案 / 标题
    data["desc"] = _text_of(dom, "feed-desc-wrap")

    # 作者
    m = re.search(r'class="author-name">([^<]*)<', dom)
    data["author"] = htmllib.unescape(m.group(1)).strip() if m else ""

    # 发布时间
    m = re.search(r'class="feed-create-time-wrap"[^>]*>([^<]*)<', dom)
    data["publish"] = htmllib.unescape(m.group(1)).strip() if m else ""

    # 地点
    m = re.search(r'class="feed-location-text">([^<]*)<', dom)
    data["location"] = htmllib.unescape(m.group(1)).strip() if m else ""

    # 互动数据：按图标 class 顺序配对文本
    stats = {}
    for mm in re.finditer(
            r'class="(i-weui:[a-z-]+)"[^>]*>\s*</i>\s*<div[^>]*class="operate-item-text">([^<]*)<',
            dom):
        icon = mm.group(1).split(":")[-1]
        if icon in ICON_MEANING:
            stats[ICON_MEANING[icon]] = htmllib.unescape(mm.group(2)).strip()
    if not stats:
        nums = re.findall(r'class="operate-item-text">([^<]*)<', dom)
        for i, name in enumerate(["点赞", "转发", "推荐", "评论"]):
            if i < len(nums):
                stats[name] = htmllib.unescape(nums[i]).strip()
    data["stats"] = stats

    # 解析出的视频 id
    m = re.search(r"[?&]id=([A-Za-z0-9]+)", dom) or re.search(r"id=([A-Za-z0-9]+)", dom)
    data["sph_id"] = m.group(1) if m else ""

    data["_dom_size"] = len(dom)
    return data


def fetch_one(chrome: str, url: str) -> dict:
    landing = resolve_short_link(url)
    dom = render(chrome, landing)
    if not dom:
        return {"input": url, "landing": landing, "ok": False,
                "error": "渲染失败（页面未在超时内返回可用 DOM）"}
    d = parse(dom)
    d.update({"input": url, "landing": landing, "ok": True})
    return d


def main():
    ap = argparse.ArgumentParser(description="抓取视频号作品信息")
    ap.add_argument("--url", action="append", required=True,
                    help="视频号分享链接，可重复传入")
    ap.add_argument("--json", help="把结果写入指定 JSON 文件")
    ap.add_argument("--workers", type=int, default=3, help="并发数（默认 3）")
    args = ap.parse_args()

    chrome = find_chrome()
    print(f"Chrome: {chrome}")
    print(f"待抓取: {len(args.url)} 条，并发 {args.workers}\n")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(lambda u: fetch_one(chrome, u), args.url))

    for i, r in enumerate(results, 1):
        print("=" * 68)
        print(f"【{i}】{r['input']}")
        if not r.get("ok"):
            print(f"   ❌ {r.get('error')}")
            continue
        print(f"   文案   : {r['desc'] or '（空）'}")
        print(f"   作者   : {r['author'] or '—'}")
        print(f"   发布   : {r['publish'] or '—'}   地点: {r['location'] or '—'}")
        s = r.get("stats", {})
        print(f"   数据   : 点赞 {s.get('点赞','—')} · 转发 {s.get('转发','—')} "
              f"· 推荐 {s.get('推荐','—')} · 评论 {s.get('评论','—')}")
        print(f"   DOM    : {r.get('_dom_size', 0)} bytes")

    ok = [r for r in results if r.get("ok")]
    print(f"\n成功 {len(ok)}/{len(results)}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=1)
        print(f"已写入 {args.json}")


if __name__ == "__main__":
    main()
