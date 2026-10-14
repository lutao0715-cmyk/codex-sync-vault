#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滑雪研究院 · 配音稿导出

输入：脚本数据 JSON（与 build_script.py 同一份）
输出：
  1. 分段配音稿 .txt —— 带时长、停顿提示、分段编号，便于剪映逐段「文本朗读」
  2. 纯文本 .txt     —— 整篇连续文案，便于一次性粘贴

用法：
    python3 export_voiceover.py --input script.json --outdir ./配音
"""
import argparse
import json
import re
import sys
from pathlib import Path

CPS = 4.3  # 口播语速 字/秒（参考安州牧 4.18 字/秒的娓娓道来风格设定）
PAUSE_BY_PUNCT = {"。": "0.6", "！": "0.6", "？": "0.6", "；": "0.4", "，": "0.25", "——": "0.7", "：": "0.35"}


def count_chars(t):
    return len(re.sub(r"\s", "", t or ""))


def annotate(text: str) -> str:
    """在句末标点后插入停顿提示"""
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        out.append(ch)
        # 优先匹配双字标点
        two = text[i:i + 2]
        if len(two) == 2 and two in PAUSE_BY_PUNCT:
            out.append(two[1])          # 补上双字标点的第二个字符
            out.append(f"（停 {PAUSE_BY_PUNCT[two]}s）")
            i += 2
            continue
        if ch in PAUSE_BY_PUNCT:
            out.append(f"（停 {PAUSE_BY_PUNCT[ch]}s）")
        i += 1
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()

    data = json.loads(Path(a.input).read_text(encoding="utf-8"))
    shots = data.get("shots", [])
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    total = sum(s.get("duration") or 0 for s in shots)
    chars = sum(count_chars(s.get("narration", "")) for s in shots)

    L = [
        f"# {data.get('title', '配音稿')} · 配音稿",
        f"# 目标总时长 {total} 秒 ｜ 口播 {chars} 字 ｜ 语速 {CPS} 字/秒",
        f"# 用法：剪映 → 文本朗读，每段单独生成一条音轨，再按时间码拼接",
        "",
    ]

    plain = []
    for s in shots:
        n = count_chars(s.get("narration", ""))
        if n == 0:
            continue
        dur = s.get("duration") or 0
        need = n / CPS
        flag = ""
        if dur and need > dur * 1.15:
            flag = f"  ⚠️超长，建议删 {int(n - dur * CPS)} 字"
        elif dur and need < dur * 0.85:
            flag = "  ⚠️偏短"

        L.append("─" * 60)
        L.append(f"【镜{s.get('no')} · {s.get('section','')} ｜ {s.get('time_code','')} ｜ {dur}秒 ｜ {n}字{flag}】")
        if s.get("subtitle"):
            L.append(f"花字参考：{s['subtitle']}")
        L.append(annotate(s.get("narration", "").strip()))
        L.append("")
        plain.append(s.get("narration", "").strip())

    base = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", data.get("title", "voiceover"))
    p1 = outdir / f"{base}_分段配音稿.txt"
    p2 = outdir / f"{base}_纯文本.txt"
    p1.write_text("\n".join(L), encoding="utf-8")
    p2.write_text("\n".join(plain), encoding="utf-8")

    print(f"已生成：{p1}")
    print(f"已生成：{p2}")
    print(f"总时长 {total}s ｜ 口播 {chars} 字 ｜ 按 {CPS} 字/秒需 {chars/CPS:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
