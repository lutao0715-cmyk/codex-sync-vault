# -*- coding: utf-8 -*-
"""战术板排期表生成器

把赛事「总表」（含每场比赛多路信号）一键生成为《（AI战术板）正式排期》xlsx。

规则：
- 版式：严格套用模板 21 列（红底表头 / 列宽 / 日期 m月d日 / 时间 h:mm:ss）
- 取数行：总表「（赛场原声）」行，名称替换为「（AI战术板）」
- 收费策略：同 PID 组「主路」（名称不带括号备注那路；无则取含"主赛场/主路"的行）
- 频道：只有 269/270 可用；时间重叠不能同号；按比赛热度从高到低抢号，抢不到留空

用法：
    python3 build_schedule.py <总表.xlsx> [--tpl 模板.xlsx] [--out 输出.xlsx] [--channels 269,270]
不传总表时，自动在桌面找最新的赛事总表；模板同理。
"""
import argparse
import glob
import os
import re
import sys
from copy import copy

import openpyxl

DESKTOP = os.path.expanduser("~/Desktop")

# ==================== 可配置区 ====================

# 只有这两个频道可用；同一时段重叠的场次不能共用，抢不到就留空备注
CHANNELS = [269, 270]

# 比赛热度（数值越大越优先抢号）。
# 规则：中国比赛永远最高；其余取「两队中较高者」。
CHINA_HEAT = 100

# 男足（五大联赛等）——键名按「子串」匹配队名
MEN_HEAT = {
    # 英超
    "曼城": 93, "阿森纳": 94, "利物浦": 91, "曼联": 92, "切尔西": 90,
    "托特纳姆": 88, "热刺": 88, "纽卡斯尔": 80, "阿斯顿维拉": 78, "西汉姆联": 74,
    "埃弗顿": 72, "布莱顿": 70, "水晶宫": 66, "富勒姆": 62, "布伦特福德": 62,
    "狼队": 60, "诺丁汉森林": 60, "利兹联": 62, "伯恩茅斯": 58, "桑德兰": 55,
    "伯恩利": 54,
    # 西甲
    "皇家马德里": 96, "皇马": 96, "巴塞罗那": 95, "巴萨": 95, "马德里竞技": 85,
    "塞维利亚": 72, "皇家贝蒂斯": 70, "瓦伦西亚": 70, "毕尔巴鄂": 68, "皇家社会": 68,
    "比利亚雷亚尔": 66, "赫罗纳": 58, "西班牙人": 60, "埃尔切": 52, "赫塔菲": 52,
    "塞尔塔": 55, "莱万特": 50,
    # 意甲
    "尤文图斯": 88, "国际米兰": 88, "AC米兰": 87, "那不勒斯": 82, "罗马": 80,
    "拉齐奥": 76, "佛罗伦萨": 74, "亚特兰大": 74, "都灵": 62, "博洛尼亚": 62,
    "热那亚": 58, "乌迪内斯": 56, "卡利亚里": 54, "维罗纳": 54,
    # 德甲
    "拜仁": 93, "多特蒙德": 85, "勒沃库森": 78, "莱比锡": 76, "法兰克福": 72,
    "沙尔克04": 68, "斯图加特": 68, "门兴": 66, "云达不来梅": 66, "汉堡": 65,
    "沃尔夫斯堡": 62, "弗赖堡": 62, "柏林联合": 58, "埃尔沃斯贝格": 50,
    # 法甲
    "巴黎圣日耳曼": 92, "巴黎": 92, "马赛": 78, "里昂": 76, "摩纳哥": 74,
    "里尔": 72, "朗斯": 68, "尼斯": 66, "雷恩": 66, "斯特拉斯堡": 62,
    "欧塞尔": 56, "昂热": 58, "特鲁瓦": 55, "洛里昂": 55, "南特": 58,
}

# 女足——男女足热度不通用，单列
WOMEN_HEAT = {
    "切尔西女足": 90, "阿森纳女足": 90, "曼联女足": 89, "曼城女足": 88,
    "利物浦女足": 86, "托特纳姆热刺女足": 84, "埃弗顿女足": 70,
    "西汉姆联女足": 70, "阿斯顿维拉女足": 68, "布莱顿女足": 62,
    "水晶宫女足": 60, "伯明翰女足": 55, "查尔顿女足": 50,
    "伦敦城雌狮女足": 45,
}

DEFAULT_HEAT = 40          # 认不出的队/赛事按最低热度

# 赛事 → 赛季列取值；未列出的赛事赛季列留空
SEASON_MAP = {"英女超": 2027}

# 「演播室」列固定文案（2026-09-23 涛哥定的：不再取原声行的值，全部统一）
STUDIO_TEXT = "AI战术板不播出"

# 总表列名 → 内部字段（支持别名，按表头自动定位，换表不用改代码）
SRC_COLS = {
    "name":        ["排期名称", "节目名称"],
    "prog_date":   ["节目日期", "节目开始日期"],
    "prog_start":  ["节目开始时间"],
    "match_time":  ["比赛时间"],
    "prog_end":    ["节目结束时间", "节目结束日期"],
    "comp":        ["赛事"],
    "rnd":         ["轮次", "轮次/项目"],
    "studio":      ["演播室"],
    "venue":       ["场馆"],
    "commentator": ["解说/嘉宾", "解说"],
    "fee":         ["收费策略"],
    "channel":     ["所属频道"],
    "pid":         ["PID"],
}
REQUIRED = ["name", "prog_start", "prog_end", "comp", "fee", "pid"]

# 模板 21 列表头（用于自检对齐，勿改）
TPL_HEADERS = [
    "排期名称", "节目开始日期", "节目开始时间", "比赛日期", "比赛时间",
    "节目结束日期", "节目结束时间", "预计推流日期", "预计推流时间",
    "预计断流日期", "预计断流时间", "赛事", "轮次/项目", "演播室", "场馆",
    "解说/嘉宾", "收费策略", "备注", "通道标签", "赛季", "能力类型",
]

DEFAULT_TPL = os.path.join(DESKTOP, "（AI战术板）正式排期(2).xlsx")
OUT_PREFIX = "（AI战术板）正式排期_"

# ==================== 工具函数 ====================


def norm(v):
    """表头归一化：去空白，便于匹配"""
    return re.sub(r"\s+", "", str(v)) if v is not None else ""


def find_src_sheet(path):
    """在总表里找含 PID/排期名称 表头的 sheet；找不到取第一个"""
    wb = openpyxl.load_workbook(path, data_only=True)
    for ws in wb.worksheets:
        hdr = [norm(c.value) for c in ws[1]]
        if "PID" in hdr or "排期名称" in hdr:
            return ws
    return wb.worksheets[0]


def header_map(ws):
    """按表头定位列号"""
    hdr = [norm(c.value) for c in ws[1]]
    found, missing = {}, []
    for field, aliases in SRC_COLS.items():
        for a in aliases:
            if norm(a) in hdr:
                found[field] = hdr.index(norm(a)) + 1
                break
        else:
            missing.append(field)
    return found, hdr, missing


def match_heat(name):
    """比赛热度 = 两队中较高者；中国比赛永远最高"""
    if "中国" in name:
        return CHINA_HEAT
    table = WOMEN_HEAT if "女足" in name else MEN_HEAT
    hits = [v for k, v in table.items() if k in name]
    return max(hits) if hits else DEFAULT_HEAT


def pick_source():
    """未指定总表时，在桌面猜一个（排除自家输出与模板）"""
    cands = []
    for p in glob.glob(os.path.join(DESKTOP, "*.xlsx")):
        b = os.path.basename(p)
        if b.startswith("~$") or b.startswith(OUT_PREFIX) or "AI战术板" in b:
            continue
        cands.append((os.path.getmtime(p), p))
    return max(cands)[1] if cands else None


def build_out_path(src):
    base = os.path.splitext(os.path.basename(src))[0]
    base = re.sub(r"^(副本|最新|总表)", "", base)
    return os.path.join(DESKTOP, OUT_PREFIX + base + ".xlsx")


# ==================== 主流程 ====================


def main():
    ap = argparse.ArgumentParser(description="战术板排期表生成器")
    ap.add_argument("src", nargs="?", help="赛事总表 xlsx（不传则自动在桌面找）")
    ap.add_argument("--tpl", default=DEFAULT_TPL, help="模板 xlsx（含 21 列版式）")
    ap.add_argument("--out", default=None, help="输出路径")
    ap.add_argument("--channels", default=None, help="可用频道，逗号分隔，默认 269,270")
    args = ap.parse_args()

    channels = CHANNELS
    if args.channels:
        channels = [int(x) for x in re.split(r"[,\s]+", args.channels.strip()) if x]

    src_path = args.src or pick_source()
    if not src_path or not os.path.exists(src_path):
        sys.exit("找不到总表，请把总表路径作为参数传入。")
    if not os.path.exists(args.tpl):
        sys.exit("找不到模板：%s\n请用 --tpl 指定。" % args.tpl)
    out_path = args.out or build_out_path(src_path)

    print("总表 :", src_path)
    print("模板 :", args.tpl)
    print("输出 :", out_path)

    # ---- 读总表 ----
    ws_src = find_src_sheet(src_path)
    m, hdr, missing = header_map(ws_src)
    lack = [f for f in REQUIRED if f in missing]
    if lack:
        sys.exit("总表缺少必需列：%s\n实际表头：%s" % (lack, hdr))

    def cell(row, field):
        idx = m.get(field)
        return row[idx - 1] if idx and idx - 1 < len(row) else None

    rows_all, groups = [], {}
    for r in ws_src.iter_rows(min_row=2, values_only=True):
        if not any(v is not None and v != "" for v in r):
            continue
        pid = str(cell(r, "pid"))
        groups.setdefault(pid, []).append((cell(r, "name"), cell(r, "fee")))
        rows_all.append({f: cell(r, f) for f in SRC_COLS})

    def main_fee(pid):
        """同 PID 组主路收费策略"""
        g = groups.get(pid, [])
        plain = [f for n, f in g if "（" not in str(n)]
        if plain:
            return plain[0]
        host = [f for n, f in g if ("主赛场" in str(n) or "主路" in str(n))]
        return host[0] if host else (g[0][1] if g else None)

    # ---- 取赛场原声行 ----
    items = []
    for idx, r in enumerate(rows_all):
        name = str(r.get("name") or "")
        if "（赛场原声）" not in name:
            continue
        new_name = name.replace("（赛场原声）", "（AI战术板）")
        comp = r.get("comp")
        items.append({
            "name": new_name, "order": idx,
            "start": r.get("prog_start"), "end": r.get("prog_end"),
            "prog_date": r.get("prog_date"), "match_time": r.get("match_time"),
            "comp": comp, "rnd": r.get("rnd"), "studio": r.get("studio"),
            "venue": r.get("venue"), "commentator": r.get("commentator"),
            "fee": main_fee(str(r.get("pid"))),
            "season": SEASON_MAP.get(str(comp)),
            "heat": match_heat(new_name),
        })

    if not items:
        sys.exit("总表里没有找到「（赛场原声）」行，请确认总表格式。")

    # ---- 抢号：热度高的先占号；号被占则留空 ----
    placed = []
    for it in sorted(items, key=lambda x: (-x["heat"], x["start"], x["order"])):
        for ch in channels:
            if not any(ch == c and s < it["end"] and it["start"] < e for s, e, c in placed):
                it["channel"] = ch
                it["remark"] = '使用频道“咪咕赛事%d”' % ch
                placed.append((it["start"], it["end"], ch))
                break
        else:
            it["channel"], it["remark"] = None, None
    items.sort(key=lambda x: (x["start"], x["order"]))

    # ---- 套模板填数据 ----
    wb = openpyxl.load_workbook(args.tpl)
    ws = wb["体育类"] if "体育类" in wb.sheetnames else wb.worksheets[0]
    actual = [norm(c.value) for c in ws[1]][:21]
    if actual != [norm(h) for h in TPL_HEADERS]:
        print("⚠️ 模板表头与预期不一致，已按实际情况填写：", actual)
    proto = [ws.cell(row=2, column=c)._style for c in range(1, 22)]
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)

    for i, it in enumerate(items, start=2):
        row = [
            it["name"],
            it["prog_date"].date(), it["start"].time(),
            it["match_time"].date(), it["match_time"].time(),
            it["end"].date(), it["end"].time(),
            it["prog_date"].date(), it["start"].time(),
            it["end"].date(), it["end"].time(),
            it["comp"], it["rnd"], STUDIO_TEXT, it["venue"], it["commentator"],
            it["fee"], it["remark"], None, it["season"], None,
        ]
        for c, v in enumerate(row, 1):
            cell_obj = ws.cell(row=i, column=c, value=v)
            cell_obj._style = copy(proto[c - 1])

    wb.properties.title = "（AI战术板）正式排期"
    wb.save(out_path)

    # ---- 自检 + 结果 ----
    print("\nsaved:", out_path, "| 行数:", len(items))
    used = sorted({it["channel"] for it in items if it["channel"]})
    print("使用频道:", used, "| 频道占用:", {c: sum(1 for it in items if it["channel"] == c) for c in used},
          "| 留空:", sum(1 for it in items if not it["channel"]))
    bad = [(A["name"], B["name"], A["channel"])
           for i, A in enumerate(items) for B in items[i + 1:]
           if A["channel"] and A["channel"] == B["channel"]
           and A["start"] < B["end"] and B["start"] < A["end"]]
    print("重叠却同频道的情况（必须为 0）:", len(bad), bad)
    print("\n%-14s %-6s %-12s %-13s %-5s %s" % ("节目开始", "热度", "节目结束", "备注", "号", "排期名称"))
    for it in items:
        print("%-14s %-6d %-12s %-13s %-5s %s" % (
            it["start"].strftime("%m-%d %H:%M"), it["heat"],
            it["end"].strftime("%m-%d %H:%M"),
            (it["remark"] or "（留空）"), it["channel"] or "-", it["name"]))


if __name__ == "__main__":
    main()
