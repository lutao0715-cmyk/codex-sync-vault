#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滑雪研究院 · 脚本分镜表生成器

输入：脚本数据 JSON
输出：标准分镜表 xlsx（8 列，带视觉规范 + 语速校验）

用法：
    python3 build_script.py --input script.json --output out.xlsx
    python3 build_script.py --demo            # 生成 demo 脚本

JSON 结构见 assets/script_schema.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.properties import PageSetupProperties
except ImportError:
    sys.exit("缺少 openpyxl：pip install openpyxl")

# ── 风格硬指标 ──
CPS = 4.3                 # 口播语速 字/秒（参考安州牧 4.18 字/秒的娓娓道来风格设定）
CPS_TOLERANCE = 0.15      # 允许 ±15%
FONT = "微软雅黑"


def xl(css: str) -> str:
    v = css.removeprefix("#").upper()
    if len(v) != 6:
        raise ValueError(f"需要 #RRGGBB，收到 {css}")
    return "FF" + v


def count_chars(text: str) -> int:
    """口播字数：去掉空白，中文字符和标点都算（与脚本表口径一致）"""
    return len(re.sub(r"\s", "", text or ""))


def parse_timecode(tc: str):
    """'00:08-00:25' -> (8, 25)；容错 '0:08-0:25'"""
    m = re.match(r"(\d+):(\d+)\s*-\s*(\d+):(\d+)", tc or "")
    if not m:
        return None, None
    a, b, c, d = map(int, m.groups())
    return a * 60 + b, c * 60 + d


def audit(shots):
    """语速审计：返回 (报告行列表, 是否有问题)"""
    rows, bad = [], False
    for s in shots:
        n = count_chars(s.get("narration", ""))
        dur = s.get("duration")
        if not dur:
            start, end = parse_timecode(s.get("time_code", ""))
            dur = (end - start) if (start is not None and end is not None) else None
        if not dur:
            rows.append((s.get("no"), n, None, None, "⚠️ 缺时长"))
            continue
        need = n / CPS
        lo, hi = dur * (1 - CPS_TOLERANCE), dur * (1 + CPS_TOLERANCE)
        if n == 0:
            flag = "—  无口播"
        elif lo <= need <= hi:
            flag = "✅ 匹配"
        elif need > hi:
            flag = f"❌ 文案超长 {need:.0f}s > {dur}s，建议删 {int(n - dur * CPS)} 字或加时长"
            bad = True
        else:
            flag = f"⚠️ 文案偏短（{need:.0f}s < {dur}s），可补 {int(dur * CPS - n)} 字"
        rows.append((s.get("no"), n, dur, round(need, 1), flag))
    return rows, bad


def build(data: dict, out_path: str):
    BRAND = xl(data.get("brand_color", "#1E6BD6"))
    BRAND_LIGHT = xl(data.get("brand_color_light", "#D9E7F7"))
    ALT = xl("#F5F8FC")
    WHITE = xl("#FFFFFF")
    BORDER = xl("#BFBFBF")
    GREY = xl("#8C8C8C")

    thin = Side(style="thin", color=BORDER)
    box = Border(left=thin, right=thin, top=thin, bottom=thin)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "脚本分镜表"

    headers = data.get("headers") or ["序号", "段落", "时间码", "画面描述", "口播文案", "花字/字幕", "备注", "时长(秒)"]
    widths = data.get("col_widths") or [6, 12, 14, 34, 52, 26, 22, 10]
    keys = data.get("keys") or ["no", "section", "time_code", "visual", "narration", "subtitle", "notes", "duration"]
    ncol = len(headers)
    last_col = get_column_letter(ncol)

    # 第1行 标题
    ws.merge_cells(f"A1:{last_col}1")
    ws["A1"] = data.get("title", "短视频脚本")
    ws["A1"].font = Font(name=FONT, size=16, bold=True, color=BRAND)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # 第2行 副标题（生产约束）
    if data.get("subtitle"):
        ws.merge_cells(f"A2:{last_col}2")
        ws["A2"] = data["subtitle"]
        ws["A2"].font = Font(name=FONT, size=9, color=GREY)
        ws["A2"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[2].height = 24

    # 第3行 表头
    for i, (h, w) in enumerate(zip(headers, widths), 1):
        c = ws.cell(row=3, column=i, value=h)
        c.font = Font(name=FONT, size=11, bold=True, color=WHITE)
        c.fill = PatternFill("solid", start_color=BRAND, end_color=BRAND)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = box
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[3].height = 28

    # 数据行
    shots = data.get("shots", [])
    for idx, s in enumerate(shots):
        r = 4 + idx
        fill = PatternFill("solid", start_color=ALT, end_color=ALT) if idx % 2 else \
               PatternFill("solid", start_color=WHITE, end_color=WHITE)
        for ci, k in enumerate(keys, 1):
            v = s.get(k, "")
            if k == "narration" and isinstance(v, str):
                v = v.strip()
            c = ws.cell(row=r, column=ci, value=v)
            c.font = Font(name=FONT, size=10)
            c.fill = fill
            c.border = box
            c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            if k in ("no", "duration", "time_code"):
                c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        # 花字列用品牌色加粗（若存在该列）
        if "subtitle" in keys:
            ci = keys.index("subtitle") + 1
            ws.cell(row=r, column=ci).font = Font(name=FONT, size=10, bold=True, color=BRAND)

    total_row = 4 + len(shots)

    # 合计行
    ws.merge_cells(f"A{total_row}:{get_column_letter(ncol-1)}{total_row}")
    t = ws.cell(row=total_row, column=1, value="总时长（秒）")
    t.font = Font(name=FONT, size=10, bold=True)
    t.alignment = Alignment(horizontal="right", vertical="center")
    t.border = box
    total = sum(s.get("duration") or 0 for s in shots)
    tv = ws.cell(row=total_row, column=ncol, value=total)
    tv.font = Font(name=FONT, size=10, bold=True)
    tv.alignment = Alignment(horizontal="center", vertical="center")
    tv.border = box
    total_chars = sum(count_chars(s.get("narration", "")) for s in shots)

    cur = total_row + 1
    ws.merge_cells(f"A{cur}:{last_col}{cur}")
    t2 = ws.cell(row=cur, column=1,
                 value=f"口播总字数 {total_chars}（含标点） | 按 {CPS} 字/秒估算需 {total_chars/CPS:.0f} 秒 | 实际标注 {total} 秒")
    t2.font = Font(name=FONT, size=9, color=GREY)
    t2.alignment = Alignment(horizontal="left", vertical="center")

    # 语速审计区
    rows, bad = audit(shots)
    cur += 2
    ws.merge_cells(f"A{cur}:{last_col}{cur}")
    h = ws.cell(row=cur, column=1, value="【语速校验】" + ("  ⚠️ 有超长段落，需处理" if bad else "  全部通过"))
    h.font = Font(name=FONT, size=11, bold=True, color=(xl("#C0392B") if bad else BRAND))
    h.fill = PatternFill("solid", start_color=BRAND_LIGHT, end_color=BRAND_LIGHT)
    for i, (no, n, dur, need, flag) in enumerate(rows):
        rr = cur + 1 + i
        ws.merge_cells(f"A{rr}:{last_col}{rr}")
        c = ws.cell(row=rr, column=1, value=f"  镜{no}：{n} 字 / {dur if dur else '-'} 秒 → 需 {need if need else '-'} 秒　{flag}")
        c.font = Font(name=FONT, size=9)
        c.alignment = Alignment(horizontal="left", vertical="center")

    # 注意事项区
    if data.get("notes"):
        nr = cur + len(rows) + 2
        ws.merge_cells(f"A{nr}:{last_col}{nr}")
        nh = ws.cell(row=nr, column=1, value="【注意事项】")
        nh.font = Font(name=FONT, size=12, bold=True, color=BRAND)
        nh.fill = PatternFill("solid", start_color=BRAND_LIGHT, end_color=BRAND_LIGHT)
        for j, note in enumerate(data["notes"]):
            r = nr + 1 + j
            ws.merge_cells(f"A{r}:{last_col}{r}")
            c = ws.cell(row=r, column=1, value=note)
            c.font = Font(name=FONT, size=9)
            c.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    ws.freeze_panes = "A4"
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_setup.orientation = "landscape"
    wb.properties.title = data.get("title", "短视频脚本")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path, total, total_chars, bad


DEMO = {
    "title": "（示例）滑雪研究院 · 脚本分镜表",
    "subtitle": "时长约 45 秒 | 花字 #1E6BD6 | 字幕口播同步",
    "brand_color": "#1E6BD6",
    "brand_color_light": "#D9E7F7",
    "shots": [
        {"no": 1, "section": "钩子", "time_code": "00:00-00:06",
         "visual": "雪雾炸开的落地慢镜 + 硬切黑场白字「第三次摔倒」",
         "narration": "你知道新手第一次上雪，摔得最惨的是哪一步吗？",
         "subtitle": "新手摔最惨的是哪一步", "notes": "黑场白字制造悬念", "duration": 6},
        {"no": 2, "section": "论点", "time_code": "00:06-00:20",
         "visual": "脚部特写：固定器没扣紧 → 雪板脱开瞬间",
         "narration": "不是刹车，不是转弯。是穿板。80%的新手第一次摔倒，都发生在还没滑出去的时候——板没扣紧，一使劲人就飞了。",
         "subtitle": "80% 新手第一步就摔在穿板上", "notes": "先给结论再给数字", "duration": 14},
        {"no": 3, "section": "干货", "time_code": "00:20-00:38",
         "visual": "手部示范：脚跟先踩下 → 脚尖用力压 → 听到咔哒声 → 拉一下确认",
         "narration": "记住三步：脚跟先踩到底，脚尖往下压，听到咔的一声。然后用手拉一下板，拉不动才算锁死。就差这一下，你第一次上雪能省半天时间。",
         "subtitle": "脚跟压 → 脚尖踩 → 咔哒 → 拉一下确认", "notes": "口诀化，便于收藏", "duration": 18},
        {"no": 4, "section": "CTA", "time_code": "00:38-00:45",
         "visual": "滑行走远的背影定格 + 花字「先学会站住，再谈滑好」",
         "narration": "先学会站住，再谈滑好。这个细节，是很多人摔了一年才想明白的。",
         "subtitle": "先学会站住，再谈滑好", "notes": "金句收口，引导评论", "duration": 7},
    ],
    "notes": [
        "1. 口播语速按 6.1 字/秒控制（原创风格），本表已自动校验",
        "2. 花字只放数字和结论，不做装饰",
        "3. 品牌合作须标注「广而告之」/「品牌合作」",
        "4. 禁止绝对化用语（最好/首选/第一）",
    ],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="脚本 JSON 路径")
    ap.add_argument("--output", help="输出 xlsx 路径")
    ap.add_argument("--demo", action="store_true", help="用内置示例跑一遍")
    a = ap.parse_args()

    if a.demo:
        data = DEMO
        out = a.output or "/tmp/demo_脚本分镜表.xlsx"
    else:
        if not a.input:
            ap.error("需要 --input 或 --demo")
        data = json.loads(Path(a.input).read_text(encoding="utf-8"))
        out = a.output or str(Path(a.input).with_suffix(".xlsx"))

    p, total, chars, bad = build(data, out)
    print(f"已生成：{p}")
    print(f"总时长 {total} 秒 | 口播 {chars} 字 | 需 {chars/CPS:.0f} 秒")
    print("⚠️ 有超长段落，见表内【语速校验】区" if bad else "✅ 语速校验全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
