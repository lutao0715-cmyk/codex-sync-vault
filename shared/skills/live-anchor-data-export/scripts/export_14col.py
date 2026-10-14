#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主播累计数据 14 列一键导出脚本（2026-09 最新版）

用法:
  python3 export_14col.py <大表明细.xlsx> <基准文件.csv|xlsx> [-o 输出.xlsx] [--sheet 表名]

输入:
  大表  : 二台跨天*.xlsx / 二台直播间明细*.xlsx 等直播明细（结构不固定，自动按表头定位列号）
  基准  : 导出直播活动内容列表*.csv / .xlsx（含"直播间ID"列的名单，决定统计哪些直播间）

内置逻辑（均已踩坑验证）:
  - 自动扫描大表表头按关键词定位列号，绝不硬编码列号
  - 同一直播间 ID 跨天多行 → 先累加再聚合
  - 基准若有多个 ID 列 → 实测命中率，选命中最高者（A列"直播id"常全 miss，B列"直播间ID"才对）
  - 数值可能是带千分位的文本 → num() 先去掉逗号
  - read_only 打开维度报 1x1 → 必须 ws.reset_dimensions()
  - 粉丝净增 = 活动期该主播所有「累计粉丝量」记录 max - min（2026-09-07 涛哥确认口径）
  - 输出 14 列：昵称/主播ID/场次/播放总时长h/曝光/播放用户/互动用户/关注成功/app拉新/
    粉丝净增/人均观看时长(分钟)/互动率%/CTR%/次均播放时长(分钟)
"""
import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, date

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# 大表关键列的关键词（按优先级排列；列名通常带"直播"前缀，如"直播曝光次数"）
COL_KEYWORDS = {
    "date":      ["日期"],
    "creator":   ["创作者"],
    "name":      ["昵称"],
    "live_id":   ["直播ID", "直播间ID"],      # 大表内的直播间主键
    "dur":       ["播放总时长"],               # 单位: 小时
    "exp":       ["曝光次数"],
    "click":     ["点击次数"],
    "play_cnt":  ["播放次数"],                 # 注意与"播放用户数"区分，关键词更长优先已由匹配顺序保证
    "play_u":    ["播放用户数"],
    "inter_u":   ["互动用户数"],
    "fans":      ["累计粉丝量", "粉丝量"],
    "avg_dur":   ["人均观看时长"],
    "follow":    ["关注成功用户数", "关注成功"],   # 2026-09-21 修正：先取"用户数"，否则会命中 108 列的"直播间关注成功次数"
    "dj":        ["拉新"],
    "start":     ["开始时间"],                # 真实开播时刻，用于开播天数（跨天直播的「日期」列会记到次日）
}

HEADERS_14 = ["主播昵称", "主播ID", "开播场次", "开播天数", "累计播放总时长(小时)", "累计直播曝光次数",
              "累计直播播放用户数", "累计直播互动用户数", "累计直播间关注成功用户数",
              "累计app手机拉新首播用户数", "累计粉丝量净增(活动期max-min)",
              "人均观看时长(分钟)", "互动率(%)", "CTR(%)", "次均播放时长(分钟)"]
COL_WIDTHS = [24, 14, 8, 10, 20, 16, 18, 18, 22, 24, 18, 18, 12, 12, 18]


def num(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def to_int_date(v):
    if isinstance(v, (datetime, date)):
        return v.year * 10000 + v.month * 100 + v.day
    if v is None:
        return None
    s = str(v).strip()
    for fmt in ("%Y%m%d", "%Y/%m/%d", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return int(datetime.strptime(s[:10], fmt).strftime("%Y%m%d"))
        except ValueError:
            pass
    if s.isdigit() and len(s) >= 8:          # 20260821141028 这类紧凑时间戳 → 取前8位
        return int(s[:8])
    try:
        return int(float(s))
    except ValueError:
        return None


def locate_headers(ws):
    """扫描表头，返回 {key: 0-based 列号}，找不到的 key 为 None"""
    hdr = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    hdr = [str(h).strip() if h is not None else "" for h in hdr]
    col = {}
    for key, kws in COL_KEYWORDS.items():
        found = None
        for ci, h in enumerate(hdr):
            if any(k in h for k in kws):
                # 排除误匹配：fans 关键词不要命中"粉丝直播播放用户数"这类列
                if key == "fans" and "粉丝直播" in h:
                    continue
                found = ci
                break
        col[key] = found
    return col, hdr


def iter_sheet_rows(path, sheet_name=None):
    wb = load_workbook(path, read_only=True, data_only=True)
    if sheet_name:
        if sheet_name not in wb.sheetnames:
            sys.exit(f"错误: 表 {sheet_name} 不存在，可用表: {wb.sheetnames}")
        ws = wb[sheet_name]
        ws.reset_dimensions()
        yield ws, wb
        return
    # 自动挑选数据行最多的 sheet
    best, best_n = None, -1
    for sn in wb.sheetnames:
        w = wb[sn]
        w.reset_dimensions()
        n = sum(1 for _ in w.iter_rows(min_row=2, values_only=True))
        if n > best_n:
            best, best_n = sn, n
    print(f"自动选择数据最多的表: {best}（{best_n} 行）")
    ws = wb[best]
    ws.reset_dimensions()
    yield ws, wb


def load_big_table(path, sheet_name=None, d_from=None, d_to=None):
    """读大表：直播ID -> [明细行 dict]，同时返回主播集合等

    d_from / d_to: YYYYMMDD 整数，闭区间过滤「归属日」。
    归属日 = 直播开始时间的日期（有效时），否则回退「日期」列 —— 跨天直播的「日期」列会记到次日。
    """
    gen = iter_sheet_rows(path, sheet_name)
    ws, wb = next(gen)
    col, hdr = locate_headers(ws)
    missing = [k for k, v in col.items() if v is None and k not in ("avg_dur", "dj", "click", "play_cnt", "start")]
    if missing:
        sys.exit(f"错误: 大表 {path} 缺少必要列 {missing}。表头如下，请核对列名:\n"
                 + "\n".join(f"  {i+1}: {h}" for i, h in enumerate(hdr) if h))

    lid_rows = defaultdict(list)
    n_rows = 0
    n_kept = 0
    warn_no_exp = 0
    warn_click_gt_exp = 0
    for row in ws.iter_rows(min_row=2, values_only=True):
        n_rows += 1
        if col["live_id"] >= len(row) or not row[col["live_id"]]:
            continue
        lid = str(row[col["live_id"]]).strip()
        rec = {
            "creator": str(row[col["creator"]] or "").strip() if col["creator"] is not None else "",
            "name": str(row[col["name"]] or "").strip() if col["name"] is not None else "",
            "date": to_int_date(row[col["date"]]) if col["date"] is not None else None,
            "sdate": to_int_date(row[col["start"]]) if col.get("start") is not None else None,
            "dur": num(row[col["dur"]]), "exp": num(row[col["exp"]]),
            "play_u": num(row[col["play_u"]]), "inter_u": num(row[col["inter_u"]]),
            "fans": num(row[col["fans"]]),
            "click": num(row[col["click"]]) if col["click"] is not None else 0.0,
            "play_cnt": num(row[col["play_cnt"]]) if col["play_cnt"] is not None else 0.0,
            "avg_dur": num(row[col["avg_dur"]]) if col["avg_dur"] is not None else 0.0,
            "follow": num(row[col["follow"]]) if col["follow"] is not None else 0.0,
            "dj": num(row[col["dj"]]) if col["dj"] is not None else 0.0,
        }
        # 日期区间过滤（归属日 = 开播日优先，无开播时间则用明细日期）
        if d_from is not None or d_to is not None:
            base_day = rec["sdate"] or rec["date"]
            if base_day is None:
                continue
            if d_from is not None and base_day < d_from:
                continue
            if d_to is not None and base_day > d_to:
                continue
        n_kept += 1
        if rec["exp"] == 0 and rec["play_u"] > 0:
            warn_no_exp += 1
        if 0 < rec["exp"] < rec["click"]:
            warn_click_gt_exp += 1
        lid_rows[lid].append(rec)
    wb.close()
    print(f"大表明细: {n_rows} 行, 保留 {n_kept} 行, 直播间 {len(lid_rows)} 个")
    if d_from or d_to:
        print(f"  日期过滤: {d_from or '-'} ~ {d_to or '-'}（按归属日：开播日优先，缺失回退明细日期）")
    if warn_no_exp:
        print(f"⚠️  注意: {warn_no_exp} 行曝光=0但播放用户>0（疑似千分位文本/字段缺失，已用 num() 规避）")
    if warn_click_gt_exp:
        print(f"⚠️  注意: {warn_click_gt_exp} 行点击>曝光（异常日，CTR 会失真，分析时留意）")
    return lid_rows


def read_base(path):
    """读基准文件（csv 或 xlsx），返回 (表头, 数据行 list)。不推断 ID 列。"""
    if path.lower().endswith(".csv"):
        rows = list(csv.reader(open(path, encoding="utf-8-sig")))
        return rows[0], rows[1:]
    gen = iter_sheet_rows(path)
    ws, wb = next(gen)
    hdr = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    data = [list(r) for r in ws.iter_rows(min_row=2, values_only=True)]
    wb.close()
    return hdr, data


def pick_base_id_col(hdr, sample_rows, big_lids):
    """基准若有多个 ID 候选列，实测命中率选最高者"""
    cands = []
    for ci, h in enumerate(hdr):
        s = str(h).strip() if h is not None else ""
        if s == "直播间ID" or ("直播" in s and ("id" in s.lower() or "ID" in s)):
            cands.append((ci, s))
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    best, best_n = None, -1
    for ci, s in cands:
        n = sum(1 for r in sample_rows if len(r) > ci and str(r[ci] or "").strip() in big_lids)
        print(f"  ID列测试 [{s}] 命中 {n}/{len(sample_rows)}")
        if n > best_n:
            best, best_n = (ci, s), n
    return best


def aggregate(base_path, lid_rows, sheet_name=None):
    hdr, rows = read_base(base_path)
    id_col = pick_base_id_col(hdr, rows, lid_rows)
    if id_col is None:
        sys.exit("错误: 基准表找不到 直播间ID/直播id 列")
    ci, cn = id_col
    # 基准里的昵称列（缺失场次要报到人）
    c_nm = next((i for i, h in enumerate(hdr)
                 if h and "昵称" in str(h)), None)
    base_ids, miss = [], []
    for r in rows:
        if len(r) <= ci or not str(r[ci] or "").strip():
            continue
        lid = str(r[ci]).strip()
        nm = str(r[c_nm]).strip() if c_nm is not None and len(r) > c_nm else ""
        if lid in lid_rows:
            base_ids.append(lid)
        else:
            miss.append((lid, nm or "?"))
    base_ids = list(dict.fromkeys(base_ids))
    print(f"基准用列: {cn}(col{ci+1}), 直播间去重 {len(base_ids)}, 未命中大表 {len(miss)}")
    for lid, nm in miss[:15]:
        print(f"    缺失: {nm}  ({lid[:16]}...)")

    # 按主播聚合
    agg = defaultdict(lambda: {"dur": 0.0, "exp": 0.0, "click": 0.0, "play_cnt": 0.0,
                               "play_u": 0.0, "inter_u": 0.0, "follow": 0.0, "dj": 0.0,
                               "fans_vals": [], "w_avg_dur": 0.0, "dates": set(), "start_dates": set()})
    sessions = defaultdict(int)
    for lid in base_ids:
        recs = lid_rows[lid]
        rec0 = recs[0]
        key = (rec0["creator"], rec0["name"])
        sessions[key] += 1
        for rec in recs:
            a = agg[key]
            a["dates"].add(rec["date"])
            a["start_dates"].add(rec.get("sdate"))
            a["dur"] += rec["dur"]
            a["exp"] += rec["exp"]
            a["click"] += rec["click"]
            a["play_cnt"] += rec["play_cnt"]
            a["play_u"] += rec["play_u"]
            a["inter_u"] += rec["inter_u"]
            a["follow"] += rec["follow"]
            a["dj"] += rec["dj"]
            # 粉丝净增=max-min，须收集该主播全部 fans 记录（含0）；若混入异常0会拉大净增，输出时人工复核
            a["fans_vals"].append(rec["fans"])
            a["w_avg_dur"] += rec["avg_dur"] * rec["play_u"]
    # 名单命中的直播间 → 其主播集合（供 full 口径判断"纳入哪些主播"）
    creators = {lid_rows[l][0]["creator"] for l in base_ids if lid_rows[l][0]["creator"]}
    return agg, sessions, creators


def aggregate_full(lid_rows, creators):
    """【大表全量口径】名单命中的主播，取其在大表中的**全部**明细行（不受名单直播间限制）。
    场次 = 该主播全部直播ID去重；天数 = 全部明细行日期去重。"""
    from collections import Counter
    nm_cnt = defaultdict(Counter)
    for lid, recs in lid_rows.items():
        c = recs[0]["creator"]
        if c not in creators:
            continue
        for rec in recs:
            nm_cnt[c][rec["name"] or recs[0]["name"]] += 1
    main_name = {c: (cnt.most_common(1)[0][0] if cnt else "") for c, cnt in nm_cnt.items()}

    agg = defaultdict(lambda: {"dur": 0.0, "exp": 0.0, "click": 0.0, "play_cnt": 0.0,
                               "play_u": 0.0, "inter_u": 0.0, "follow": 0.0, "dj": 0.0,
                               "fans_vals": [], "w_avg_dur": 0.0, "dates": set(), "start_dates": set()})
    lid_sets = defaultdict(set)
    for lid, recs in lid_rows.items():
        c = recs[0]["creator"]
        if c not in creators:
            continue
        key = (c, main_name.get(c, recs[0]["name"]))
        lid_sets[c].add(lid)
        for rec in recs:
            a = agg[key]
            a["dates"].add(rec["date"])
            a["start_dates"].add(rec.get("sdate"))
            a["dur"] += rec["dur"]; a["exp"] += rec["exp"]; a["click"] += rec["click"]
            a["play_cnt"] += rec["play_cnt"]; a["play_u"] += rec["play_u"]
            a["inter_u"] += rec["inter_u"]; a["follow"] += rec["follow"]; a["dj"] += rec["dj"]
            a["fans_vals"].append(rec["fans"])
            a["w_avg_dur"] += rec["avg_dur"] * rec["play_u"]
    sessions = {(c, main_name.get(c, "")): len(s) for c, s in lid_sets.items()}
    print(f"大表全量口径: 纳入主播 {len(lid_sets)} 位, 覆盖直播 {sum(len(s) for s in lid_sets.values())} 场")
    return agg, sessions


def build_result(agg, sessions):
    result = []
    for (creator, name), a in agg.items():
        fans_vals = [f for f in a["fans_vals"] if f is not None]
        net = int(max(fans_vals) - min(fans_vals)) if fans_vals else 0
        inter_rate = a["inter_u"] / a["play_u"] * 100 if a["play_u"] else 0.0
        ctr = a["click"] / a["exp"] * 100 if a["exp"] else 0.0
        per_play = a["dur"] * 60 / a["play_cnt"] if a["play_cnt"] else 0.0
        avg_dur = round(a["w_avg_dur"] / a["play_u"], 2) if a["play_u"] else round(a["dur"] * 60 / a["play_u"], 2) if a["play_u"] else 0.0
        sd = {d for d in a["start_dates"] if d}    # 开播天数：优先按「直播开始时间」的真实开播日去重
        days = len(sd) if sd else len({d for d in a["dates"] if d})   # 无开始时间列时回退明细日期（2026-09-20 修正跨天直播记日压缩问题）
        result.append([name, creator, sessions[(creator, name)], days, round(a["dur"], 2),
                       int(a["exp"]), int(a["play_u"]), int(a["inter_u"]), int(a["follow"]),
                       int(a["dj"]), net, round(avg_dur, 2), round(inter_rate, 2),
                       round(ctr, 2), round(per_play, 2)])
    result.sort(key=lambda x: -x[4])
    return result


def write_xlsx(result, out_path):
    wb = Workbook()
    sh = wb.active
    sh.title = "主播累计数据"
    sh.append(HEADERS_14)
    thin = Border(left=Side(style="thin"), right=Side(style="thin"),
                  top=Side(style="thin"), bottom=Side(style="thin"))
    for r in result:
        sh.append(r)
    for c in sh[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="4472C4")
        c.alignment = Alignment(horizontal="center", vertical="center")
    for i, w in enumerate(COL_WIDTHS, 1):
        sh.column_dimensions[get_column_letter(i)].width = w
    for row in sh.iter_rows(min_row=1, max_row=sh.max_row, max_col=len(HEADERS_14)):
        for c in row:
            c.border = thin
            if c.row > 1:
                c.alignment = Alignment(horizontal="center", vertical="center")
    wb.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="主播累计数据 15 列导出")
    ap.add_argument("detail", help="大表明细 xlsx")
    ap.add_argument("base", nargs="?", default=None,
                    help="基准名单 csv/xlsx（含直播间ID列）；不传=不限名单，大表全部直播间参与统计")
    ap.add_argument("-o", "--out", default=None, help="输出 xlsx 路径")
    ap.add_argument("--sheet", default=None, help="指定大表的 sheet 名（默认自动选行数最多者）")
    ap.add_argument("--scope", default="roster", choices=["roster", "full"],
                    help="roster(默认)=只统计名单内的直播间; full=名单命中的主播按其大表全部明细统计（场次/天数不再是名单口径）")
    ap.add_argument("--from", dest="d_from", type=int, default=None, help="起始日期 YYYYMMDD（闭区间，按归属日过滤）")
    ap.add_argument("--to", dest="d_to", type=int, default=None, help="结束日期 YYYYMMDD（闭区间，按归属日过滤）")
    args = ap.parse_args()

    lid_rows = load_big_table(args.detail, args.sheet, args.d_from, args.d_to)

    if args.base:
        agg, sessions, creators = aggregate(args.base, lid_rows)
        if args.scope == "full":
            agg, sessions = aggregate_full(lid_rows, creators)
    else:
        # 无名单：大表（已按日期过滤）全部创作者参与统计
        creators = {recs[0]["creator"] for recs in lid_rows.values() if recs[0]["creator"]}
        print(f"未提供基准名单 → 全量口径，纳入创作者 {len(creators)} 位")
        agg, sessions = aggregate_full(lid_rows, creators)

    result = build_result(agg, sessions)

    out = args.out or f"/Users/lutao/Downloads/主播累计数据_{datetime.now():%m%d}.xlsx"
    write_xlsx(result, out)

    print(f"\n主播数: {len(result)}")
    print(f"{'主播':<22}{'场':>4}{'天':>4}{'时长h':>11}{'曝光':>11}{'播放用户':>9}{'互动':>7}"
          f"{'关注':>6}{'拉新':>7}{'净增':>8}{'人均分':>7}{'互动率%':>8}{'CTR%':>7}{'次均分':>7}")
    for r in result:
        print(f"{r[0]:<22}{r[2]:>4}{r[3]:>4}{r[4]:>11,.1f}{r[5]:>11,}{r[6]:>9,}{r[7]:>7,}"
              f"{r[8]:>6,}{r[9]:>7,}{r[10]:>8,}{r[11]:>7.2f}{r[12]:>8.2f}{r[13]:>7.2f}{r[14]:>7.2f}")
    print(f"\n合计: {sum(r[2] for r in result)}场 | {sum(r[3] for r in result)}人天 | {sum(r[4] for r in result):,.0f}h | "
          f"曝光{sum(r[5] for r in result):,} | 播放用户{sum(r[6] for r in result):,} | "
          f"互动{sum(r[7] for r in result):,} | 关注{sum(r[8] for r in result):,} | "
          f"拉新{sum(r[9] for r in result):,}")
    print("已保存:", out)


if __name__ == "__main__":
    main()
