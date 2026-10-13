#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风格画像抽取脚本（范例学习模式支撑工具）

输入：用户提供的 3-N 份同环节历史成品（Markdown）
输出：style_profile.md —— 一份"格式约束画像"，供生成时精确套用其结构骨架与文风

设计原则（诚信）：
- 只做"真实可统计的结构特征抽取"，不宣称"AI 自动学会文风"；
- 文风模仿由大模型基于本画像完成，本脚本只提供精确、可追溯的格式约束；
- 不读取、不引入任何用户未主动提供的外部模板或涉密文件。

用法：
    python profile_style.py a.md b.md c.md [--out style_profile.md]
    python profile_style.py --dir ./history_minutes/ [--out style_profile.md]
"""

import sys
import os
import re
import glob
from collections import Counter

# 公文特征动词（仅做频率统计，反映作者/单位的表述偏好）
FEATURE_VERBS = [
    "会议认为", "会议指出", "会议决定", "会议要求", "会议强调",
    "指出", "强调", "部署", "明确", "压实", "统筹", "狠抓",
    "聚焦", "坚持", "要求", "决定", "审议", "传达", "研究",
    "安排", "落实", "扎实推进", "持续深化", "从严", "强化",
]

# 常用称谓（反映单位/场景的称呼习惯）
SALUTATIONS = [
    "同志", "同志们", "各部门", "各单位", "各直属单位", "各子公司",
    "公司领导", "领导班子", "全体员工", "相关方", "承包商",
]


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def collect_paths(args):
    """解析输入：支持多文件路径 + --dir 目录"""
    paths = []
    use_dir = None
    out_path = "style_profile.md"
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--dir":
            use_dir = args[i + 1]
            i += 2
        elif a == "--out":
            out_path = args[i + 1]
            i += 2
        else:
            paths.append(a)
            i += 1
    if use_dir:
        paths += sorted(glob.glob(os.path.join(use_dir, "*.md")))
    # 去重并过滤掉输出文件自身
    seen = set()
    result = []
    for p in paths:
        ap = os.path.abspath(p)
        if ap in seen:
            continue
        seen.add(ap)
        if os.path.abspath(out_path) == ap:
            continue
        if os.path.isfile(p):
            result.append(p)
    return result, out_path


def analyze(paths):
    headings = []          # (level, content)
    table_cols = []        # 每张表的列数
    ordered = 0
    unordered = 0
    verbs = Counter()
    salutations = Counter()
    total_chars = 0
    total_lines = 0
    seq_patterns = set()

    for p in paths:
        text = read_text(p)
        lines = text.splitlines()
        total_lines += len(lines)
        total_chars += len(text)
        for line in lines:
            s = line.strip()
            # 标题层级
            m = re.match(r"^(#{1,4})\s+(.*)$", s)
            if m:
                level = len(m.group(1))
                content = m.group(2).strip()
                headings.append((level, content))
                # 中文序号风格检测
                if re.match(r"^[一二三四五六七八九十百]+、", content):
                    seq_patterns.add("中文数字+顿号（一、二、）")
                elif re.match(r"^（[一二三四五六七八九十百]+）", content):
                    seq_patterns.add("全角括号（（一））")
                elif re.match(r"^\d+[\.、]", content):
                    seq_patterns.add("阿拉伯数字（1. / 1、）")
                elif re.match(r"^[A-Za-z][\.、]", content):
                    seq_patterns.add("英文字母（A. / A、）")
            # 表格行
            if re.match(r"^\|.*\|$", s) and "---" not in s:
                cols = s.count("|") - 1
                if cols > 0:
                    table_cols.append(cols)
            # 列表
            if re.match(r"^[-*]\s+\S", s):
                unordered += 1
            if re.match(r"^\d+[\.、]\s+\S", s):
                ordered += 1
        # 公文动词频率
        for v in FEATURE_VERBS:
            c = text.count(v)
            if c:
                verbs[v] += c
        # 称谓
        for sal in SALUTATIONS:
            c = text.count(sal)
            if c:
                salutations[sal] += c

    return {
        "n": len(paths),
        "total_chars": total_chars,
        "total_lines": total_lines,
        "headings": headings,
        "table_cols": table_cols,
        "ordered": ordered,
        "unordered": unordered,
        "verbs": verbs,
        "salutations": salutations,
        "seq_patterns": seq_patterns,
    }


def build_profile(d, paths):
    n = max(d["n"], 1)
    avg_chars = d["total_chars"] // n
    # 标题层级指纹
    level_counter = Counter(lv for lv, _ in d["headings"])
    heading_samples = d["headings"][:12]
    # 表格列数分布
    col_counter = Counter(d["table_cols"])
    # 列表风格
    list_total = d["ordered"] + d["unordered"]
    list_style = "无明显列表"
    if list_total > 0:
        if d["ordered"] >= d["unordered"]:
            list_style = "偏有序列表（1. / 1、）"
        else:
            list_style = "偏无序列表（- / *）"
    # 公文动词 Top
    top_verbs = [v for v, _ in d["verbs"].most_common(10)]
    # 称谓 Top
    top_sal = [s for s, _ in d["salutations"].most_common(6)]
    # 序号风格
    seq = sorted(d["seq_patterns"]) if d["seq_patterns"] else ["（未检测到明显中文序号，可能用段落直述）"]

    L = []
    L.append("# 风格画像（范例学习 · 格式约束）")
    L.append("")
    L.append(f"> 本画像由 `scripts/profile_style.py` 基于您提供的 **{d['n']}** 份历史成品抽取生成，")
    L.append("> 供本次及后续生成时作为**精确格式约束**使用。文风模仿由大模型基于本画像完成，")
    L.append("> 脚本仅做真实可统计的结构特征抽取。")
    L.append("")
    L.append("## 一、样本概况")
    L.append(f"- 范例份数：{d['n']} 份")
    L.append(f"- 平均篇幅：约 {avg_chars} 字 / 份（区间参考，非硬约束）")
    L.append("")
    L.append("## 二、标题层级指纹")
    if level_counter:
        lv_desc = "、".join(f"{'#'*lv}({c}次)" for lv, c in sorted(level_counter.items()))
        L.append(f"- 使用层级：{lv_desc}")
    if heading_samples:
        L.append("- 典型标题示例：")
        for lv, c in heading_samples[:8]:
            L.append(f"  - {'#'*lv} {c}")
    L.append("")
    L.append("## 三、序号风格")
    for s in seq:
        L.append(f"- {s}")
    L.append("")
    L.append("## 四、表格样式")
    if col_counter:
        col_desc = "、".join(f"{k}列×{v}处" for k, v in sorted(col_counter.items()))
        L.append(f"- 表格列数分布：{col_desc}")
        L.append("- 套用要求：沿用范例的表格列结构（表头字段、列顺序），不擅自增减列。")
    else:
        L.append("- 范例中未使用表格（以段落/列表为主），本次默认不强制表格。")
    L.append("")
    L.append("## 五、列表风格")
    L.append(f"- {list_style}")
    L.append("")
    L.append("## 六、公文动词偏好（Top）")
    if top_verbs:
        L.append("- 高频表述：" + "、".join(top_verbs))
        L.append("- 套用要求：沿用上述表述习惯（如惯用\"会议指出/决定/要求\"三段式则保持）。")
    else:
        L.append("- 未检测到明显公文动词偏好。")
    L.append("")
    L.append("## 七、常用称谓")
    if top_sal:
        L.append("- 高频称谓：" + "、".join(top_sal))
        L.append("- 套用要求：沿用范例中的称呼体系（如\"各部门/各单位\"\"同志\"）。")
    else:
        L.append("- 未检测到明显称谓偏好。")
    L.append("")
    L.append("## 八、套用提示（生成时务必遵守）")
    L.append("1. **结构骨架**：严格沿用第二节标题层级与第三节序号风格，不随意改层级。")
    L.append("2. **表格/列表**：按第四、五节样式输出；无则不强求。")
    L.append("3. **文风**：模仿第六节动词与第七节称谓，保持与范例一致的正式度与语气。")
    L.append("4. **内容独立**：本次成品内容必须基于本次真实素材，不把范例中的旧决议/旧数据抄入。")
    L.append("5. **落款/固定栏目**：范例中出现的固定落款、固定栏目（如\"会议认为/指出/决定/要求\"）一律沿用。")
    L.append("")
    L.append("---")
    L.append("生成成品时，请将本画像作为首要格式约束，置于本次素材之前。")
    return "\n".join(L)


def main():
    if len(sys.argv) < 2:
        print("用法：python profile_style.py a.md b.md c.md [--out style_profile.md]")
        print("      python profile_style.py --dir ./history/ [--out style_profile.md]")
        sys.exit(1)
    paths, out_path = collect_paths(sys.argv[1:])
    if not paths:
        print("[错误] 未找到有效的 .md 范例文件。请检查路径或 --dir。")
        sys.exit(1)
    d = analyze(paths)
    profile = build_profile(d, paths)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(profile)
    print(f"[完成] 已基于 {d['n']} 份范例生成风格画像：{out_path}")
    print(f"        平均篇幅约 {d['total_chars'] // max(d['n'],1)} 字/份；"
          f"标题层级 {len(set(lv for lv,_ in d['headings']))} 种；"
          f"表格 {len(d['table_cols'])} 处；公文动词命中 {sum(d['verbs'].values())} 次。")


if __name__ == "__main__":
    main()
