#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报名成功主播 多维度转化分析（基于二台跨天 2.xlsx 大表 + 飞书报名成功名单）
维度：曝光转化率 / 次均曝光带来时长 / 人均观看时长 / 互动率 / 次均播放时长 / 千次曝光涨粉&拉新 / 开播天数稳定度
"""
import csv
import re
import sys
from collections import defaultdict
from datetime import datetime, date

from openpyxl import load_workbook, Workbook
from openpyxl.chart import ScatterChart, Reference, Series
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

BIG = "C:/Users/win/Downloads/二台跨天 2.xlsx"
BASE = "/tmp/baoming_clean.csv"              # 飞书「报名成功主播明细」A=咪咕账号ID B=昵称
OUT = "C:/Users/win/Downloads/报名成功主播_多维分析_0914.xlsx"
MIN_DAYS = 7

KW = {
    "date": ["日期"], "creator": ["创作者"], "name": ["昵称"], "live_id": ["直播ID", "直播间ID"],
    "dur": ["播放总时长"], "live_dur": ["开播时长"], "exp": ["曝光次数"], "exp_u": ["曝光用户数"],
    "clk": ["点击次数"], "clk_u": ["点击用户数"], "play_cnt": ["播放次数"], "play_u": ["播放用户数"],
    "inter_u": ["互动用户数"], "fans": ["累计粉丝量"], "avg_dur": ["人均观看时长"],
    "follow": ["关注成功用户数"], "dj": ["app手机拉新首播用户数"],
}


def num(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def to_day(v):
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y%m%d")
    s = str(v or "").strip()
    if re.fullmatch(r"\d{8}(\.0)?", s):
        return s[:8]
    try:
        return str(int(float(s)))
    except ValueError:
        return None


wb = load_workbook(BIG, read_only=True, data_only=True)
ws = wb["表格0"]
ws.reset_dimensions()
hdr = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
hdr = [str(h).strip() if h else "" for h in hdr]
col = {}
for key, kws in KW.items():
    for ci, h in enumerate(hdr):
        if any(k in h for k in kws):
            if key == "fans" and "粉丝直播" in h:
                continue
            col[key] = ci
            break
print("列定位:", {k: (v + 1 if v is not None else None) for k, v in col.items()})

# 按创作者ID(主播ID)归集，另存直播间ID用于统计场次
creator_rows = defaultdict(list)
for r in ws.iter_rows(min_row=2, values_only=True):
    if col["creator"] >= len(r) or not r[col["creator"]]:
        continue
    creator_rows[str(r[col["creator"]]).strip()].append(r)
wb.close()
print(f"大表: {sum(len(v) for v in creator_rows.values()):,} 行, 创作者 {len(creator_rows):,} 个")

# 名单来源：报名成功主播_累计数据_0914v2.xlsx 的「名单ID」列（= 主播/创作者ID）
from openpyxl import load_workbook as _lw
_r = _lw("C:/Users/win/Downloads/报名成功主播_累计数据_0914v2.xlsx", data_only=True, read_only=True).active
want_ids = {}
for row in _r.iter_rows(min_row=2, values_only=True):
    if row and row[0]:
        want_ids[str(row[0]).strip()] = str(row[1]).strip()
print(f"名单(报名成功主播): {len(want_ids)} 位")


def g(row, key):
    ci = col.get(key)
    return num(row[ci]) if ci is not None and ci < len(row) else 0.0


agg = defaultdict(lambda: dict(name="", days=set(), sess=0, exp=0.0, exp_u=0.0, clk=0.0, clk_u=0.0,
                               play=0.0, play_u=0.0, inter=0.0, dur=0.0, live_dur=0.0,
                               follow=0.0, dj=0.0, fans=[], w_avg=0.0, hit=0, dirty=0, hi_exp=0.0))
miss = []
for aid, nm in want_ids.items():
    recs = creator_rows.get(aid)
    if not recs:
        miss.append((nm, aid))
        continue
    key = (aid, str(recs[0][col["name"]]))
    a = agg[key]
    a["name"] = key[1]
    a["sess"] = len({str(r[col["live_id"]]).strip() for r in recs})
    for r in recs:
        # 脏行过滤：点击次数 > 曝光次数 在物理上不成立（大表已知脏数据，如 10003% CTR）
        _e, _c = g(r, "exp"), g(r, "clk")
        if _e > 0 and _c > _e:
            a["dirty"] += 1
            continue
        a["hit"] += 1
        if _e >= 500 and _c / _e > 0.25:      # 直播 CTR 常识区间 ~5-10%，>25% 视为疑似异常
            a["hi_exp"] += _e
        a["days"].add(to_day(r[col["date"]]))
        a["exp"] += g(r, "exp")
        a["exp_u"] += g(r, "exp_u")
        a["clk"] += g(r, "clk")
        a["clk_u"] += g(r, "clk_u")
        a["play"] += g(r, "play_cnt")
        a["play_u"] += g(r, "play_u")
        a["inter"] += g(r, "inter_u")
        a["dur"] += g(r, "dur")
        a["live_dur"] += g(r, "live_dur")
        a["follow"] += g(r, "follow")
        a["dj"] += g(r, "dj")
        a["fans"].append(g(r, "fans"))
        a["w_avg"] += g(r, "avg_dur") * g(r, "play_u")

print(f"命中大表: {len(agg)} 位, 未命中: {len(miss)} 位 -> {[m[0] for m in miss]}")

recs = []
for (cid, nm), a in agg.items():
    fv = [x for x in a["fans"] if x is not None]
    net = int(max(fv) - min(fv)) if fv else 0
    e = a["exp"]
    r = dict(cid=cid, name=nm, sess=a["sess"], days=len(a["days"]), hit_rows=a["hit"],
             dirty=a["dirty"],
             exp=e, exp_u=a["exp_u"], clk=a["clk"], clk_u=a["clk_u"], play=a["play"],
             play_u=a["play_u"], inter=a["inter"], dur=a["dur"], live_dur=a["live_dur"],
             follow=a["follow"], dj=a["dj"], net=net)
    r["ctr"] = a["clk"] / e * 100 if e else 0                     # 曝光转化率(次数)
    r["ctr_u"] = a["clk_u"] / a["exp_u"] * 100 if a["exp_u"] else 0   # 曝光用户点击率
    r["sec_per_exp"] = a["dur"] * 3600 / e if e else 0            # 次均曝光带来时长(秒)
    r["avg_min"] = a["w_avg"] / a["play_u"] if a["play_u"] else (a["dur"] * 60 / a["play_u"] if a["play_u"] else 0)
    r["inter_rate"] = a["inter"] / a["play_u"] * 100 if a["play_u"] else 0
    r["per_play_min"] = a["dur"] * 60 / a["play"] if a["play"] else 0
    r["play_per_clk"] = a["play_u"] / a["clk_u"] * 100 if a["clk_u"] else 0
    r["net_per_1k"] = net / e * 1000 if e else 0
    r["dj_per_1k"] = a["dj"] / e * 1000 if e else 0
    r["follow_per_1k"] = a["follow"] / e * 1000 if e else 0
    r["hi_share"] = a["hi_exp"] / e * 100 if e else 0
    r["dur_per_day"] = a["dur"] / len(a["days"]) if a["days"] else 0
    r["exp_per_day"] = e / len(a["days"]) if a["days"] else 0
    recs.append(r)

for r in recs:
    r["reliable"] = r["exp"] >= 20000 and r["hit_rows"] >= 5
cat = [r for r in recs if r["days"] >= MIN_DAYS and r["reliable"]]
small = [r for r in recs if r["days"] < MIN_DAYS or not r["reliable"]]
for r in small:
    r["why"] = ("开播天数不足" if r["days"] < MIN_DAYS else "") + \
               ("曝光量过低(<2万)" if r["exp"] < 20000 else "") + \
               ("有效场次不足" if r["hit_rows"] < 5 else "")
    r["tier"] = "样本/数据不足"


def prank(rows, key):
    vs = sorted(rows, key=lambda x: x[key])
    n = len(vs)
    return {id(r): (i / (n - 1) if n > 1 else 0.5) for i, r in enumerate(vs)}


DIMS = {"ctr": ("曝光转化率", 0.20), "sec_per_exp": ("次均曝光带来时长", 0.25),
        "avg_min": ("人均观看时长", 0.20), "inter_rate": ("互动率", 0.15),
        "net_per_1k": ("千次曝光涨粉", 0.10), "days": ("开播稳定度", 0.10)}
ranks = {k: prank(cat, k) for k in DIMS}
for r in cat:
    r["score"] = round(sum(ranks[k][id(r)] * w for k, (_, w) in DIMS.items()) * 100, 1)
    for k in DIMS:
        r[f"p_{k}"] = round(ranks[k][id(r)] * 100)
cat.sort(key=lambda x: -x["score"])
n = len(cat)
for i, r in enumerate(cat):
    r["rank"] = i + 1
    r["tier"] = "A 潜力" if i < n / 3 else ("B 平平" if i < n * 2 / 3 else "C 待突破")
small.sort(key=lambda x: -x["days"])

print(f"\n可评估(≥{MIN_DAYS}天) {n} 位；样本不足 {len(small)} 位")
print(f"{'主播':<20}{'天':>3}{'曝光':>10}{'CTR%':>7}{'秒/曝光':>8}{'人均分':>7}{'互动率%':>8}{'次均分':>7}{'千次涨粉':>8}{'分':>6}{'层':>8}")
for r in cat:
    print(f"{r['name']:<20}{r['days']:>3}{int(r['exp']):>10,}{r['ctr']:>7.2f}{r['sec_per_exp']:>8.1f}"
          f"{r['avg_min']:>7.2f}{r['inter_rate']:>8.2f}{r['per_play_min']:>7.2f}{r['net_per_1k']:>8.1f}"
          f"{r['score']:>6}{r['tier']:>8}")

# ---------------- 输出 ----------------
HDR = ["分层", "综合分", "排名", "主播昵称", "主播ID", "开播场次", "开播天数", "累计曝光", "日均曝光",
       "曝光转化率%(次数)", "曝光用户点击率%", "次均曝光带来时长(秒)", "人均观看时长(分钟)",
       "次均播放时长(分钟)", "互动率%", "点击→播放用户%", "播放总时长(小时)", "粉丝净增",
       "千次曝光涨粉", "app拉新", "千次曝光拉新", "关注成功", "千次曝光关注",
       "疑似异常曝光占比%", "剔除脏行数"]
KEYS = ["tier", "score", "rank", "name", "cid", "sess", "days", "exp", "exp_per_day", "ctr", "ctr_u",
        "sec_per_exp", "avg_min", "per_play_min", "inter_rate", "play_per_clk", "dur", "net",
        "net_per_1k", "dj", "dj_per_1k", "follow", "follow_per_1k", "hi_share", "dirty"]

out = Workbook()
sh = out.active
sh.title = "多维综合排名"
sh.append(HDR)
for r in cat:
    sh.append([round(r[k], 2) if isinstance(r[k], float) else r[k] for k in KEYS])

sh2 = out.create_sheet("分维度得分(百分位)")
D2 = ["主播昵称", "综合分", "排名", "曝光转化率", "次均曝光时长", "人均观看时长", "互动率", "千次曝光涨粉", "开播稳定度"]
sh2.append(D2)
for r in cat:
    sh2.append([r["name"], r["score"], r["rank"], r["p_ctr"], r["p_sec_per_exp"], r["p_avg_min"],
                r["p_inter_rate"], r["p_net_per_1k"], r["p_days"]])

sh3 = out.create_sheet("样本不足(不评估)")
sh3.append(HDR)
for r in small:
    r.setdefault("tier", "样本少")
    r.setdefault("score", "")
    r.setdefault("rank", "")
    sh3.append([round(r[k], 2) if isinstance(r[k], float) else r[k] for k in KEYS])

TONE = {"A 潜力": "C6EFCE", "B 平平": "FFF2CC", "C 待突破": "F8CBAD"}
thin = Border(*[Side(style="thin")] * 4)
widths = [10, 8, 6, 22, 13, 9, 9, 12, 11, 16, 14, 18, 18, 18, 10, 15, 14, 10, 13, 10, 13, 10, 14, 16, 11]
for s, wlist in ((sh, widths), (sh3, widths), (sh2, [22, 8, 6, 12, 14, 14, 10, 14, 12])):
    for c in s[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="4472C4")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in s.iter_rows(min_row=2, max_row=s.max_row, max_col=len(s[1])):
        for c in row:
            c.border = thin
            c.alignment = Alignment(horizontal="center", vertical="center")
        if row[0].value in TONE:
            row[0].fill = PatternFill("solid", fgColor=TONE[row[0].value])
    for i, w in enumerate(wlist, 1):
        s.column_dimensions[get_column_letter(i)].width = w
    s.freeze_panes = "D2"

# 散点图：曝光转化率 vs 次均曝光带来时长
ch = ScatterChart()
ch.title = "曝光转化率 vs 次均曝光带来时长"
ch.x_axis.title = "曝光转化率(%)"
ch.y_axis.title = "次均曝光带来时长(秒)"
ch.height, ch.width = 9, 18
xref = Reference(sh, min_col=10, min_row=2, max_row=1 + len(cat))
for col_i, nm in ((12, "次均曝光带来时长"),):
    yref = Reference(sh, min_col=col_i, min_row=1, max_row=1 + len(cat))
    s = Series(yref, xref, title=nm)
    s.marker.symbol = "circle"
    s.graphicalProperties.line.noFill = True
    ch.series.append(s)
sh.add_chart(ch, "Y2")

out.save(OUT)
print("\n已保存:", OUT)
print("\n样本不足名单:", [f"{r['name']}({r['days']}天)" for r in small])
