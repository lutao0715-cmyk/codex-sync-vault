#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_decisions.py — 从会议纪要文本中自动提取"会议决定/要求/明确"段，
生成督办任务表骨架（Markdown 表格）。

用法：
    python extract_decisions.py 纪要.md
    cat 纪要.md | python extract_decisions.py

输出：Markdown 督办表骨架，责任主体/时限/验收列为空，供人工或 Agent 补全。
说明：本脚本只做"提取"，不编造任何决议内容；未提取到时给出提示行。
"""

import sys
import os
import re

# 触发捕获的关键词（段标题）
TRIGGER = [r"会议决定", r"会议要求", r"会议明确"]
# 段内停止标志：遇到其他"会议X"标题且非触发词时停止
STOP = re.compile(r"^会议(认为|指出|决定|要求|明确|强调|希望|认为)[：:。]?")


def extract_items(text: str):
    lines = text.splitlines()
    items = []
    capturing = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # 触发段开始
        if any(re.search(p, line) for p in TRIGGER):
            capturing = True
            continue
        if capturing:
            # 遇到新的"会议X"标题
            if STOP.match(line):
                if any(re.search(p, line) for p in TRIGGER):
                    continue  # 又是决定/要求，继续捕获
                capturing = False
                continue
            # 跳过章节标题（如 "## 七、督办事项"）
            if line.startswith("#"):
                continue
            # 跳过纯分隔线
            if re.fullmatch(r"[-=*_]+", line):
                continue
            # 跳过表格分隔行
            if re.fullmatch(r"\|[-:\s|]+\|?", line):
                continue
            # 表格行：解析数据列，跳过表头与空占位行
            if "|" in line:
                cells = [c.strip() for c in line.strip("|").split("|")]
                header_kw = ["序号", "事项", "责任单位", "责任主体",
                             "完成时限", "验收标准", "当前状态", "状态"]
                if any(k in line for k in header_kw):
                    continue
                # 事项列通常为第 2 列；为空则该行为空占位，跳过
                if len(cells) >= 2 and cells[1]:
                    items.append(cells[1])
                continue
            # 普通行：去列表符号
            clean = re.sub(r"^[-–—·\d+.\s]+", "", line).strip()
            if clean:
                items.append(clean)
    return items


def render(items):
    out = ["# 督办任务表（由纪要自动提取，请核对并补全责任/时限/验收）\n"]
    out.append("| 序号 | 督办事项 | 责任主体 | 完成时限 | 验收标准 | 状态 |")
    out.append("|---|---|---|---|---|---|")
    if not items:
        out.append("| - | 未提取到“会议决定/要求/明确”段，请检查纪要是否含此类表述 | | | | |")
    else:
        for i, it in enumerate(items, 1):
            # 去掉行首的列表符号，保留原意
            clean = re.sub(r"^[-–—·\d+.\s]+", "", it).strip()
            out.append(f"| {i} | {clean} | | | | 未启动 |")
    out.append("")
    return "\n".join(out)


def main():
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()
    items = extract_items(text)
    print(render(items))


if __name__ == "__main__":
    main()
