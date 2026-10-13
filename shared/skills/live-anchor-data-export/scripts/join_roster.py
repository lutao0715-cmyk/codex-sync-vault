#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按主播ID，用「报名/活动名单」过滤「主播累计数据」表，只保留名单内的主播。

用法:
    python3 join_roster.py <主播累计数据.xlsx> <名单文件> -o <输出.xlsx> [--order roster|data]

名单文件支持两种格式：
  1) lark-cli 的 JSON 信封（`lark-cli sheets +csv-get ... --format json > x.json` 的输出），
     自动解析 data.annotated_csv，去掉 [row=N] 前缀；默认第 1 行是表头，第 1 列是ID、第 2 列是昵称。
  2) 纯 CSV / TSV 文本：第 1 行表头，第 1 列 ID，第 2 列（可选）昵称。

可选参数：
  --id-col N     名单 ID 所在列序号（1-based，默认 1）
  --name-col N   名单昵称所在列序号（1-based，默认 2）
  --skip-rows N  名单里跳过开头几行（默认 1 = 跳表头）
  --data-id-col  累计数据表里主播ID 的列序号（1-based，默认 2）
  --order        输出顺序：roster（跟随名单顺序，默认）| data（跟随累计数据表顺序）
"""
import argparse
import csv
import io
import json
import os
import re
import sys

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def load_roster(path, id_col, name_col, skip_rows):
    """返回 [(id, name), ...]，保持名单原始顺序。"""
    raw = open(path, encoding='utf-8').read()
    text = raw
    stripped = raw.lstrip()
    if stripped.startswith('{'):
        env = json.loads(raw)
        if not env.get('ok', True):
            raise SystemExit(f'名单 JSON 不是成功响应：{env.get("error")}')
        text = env.get('data', {}).get('annotated_csv')
        if text is None:
            raise SystemExit('名单 JSON 里没有 data.annotated_csv')
        # json.loads 已把 \n 转义还原为真实换行；只需去掉 [row=N] 前缀
        text = re.sub(r'^\[row=\d+\]\s?', '', text, flags=re.M)
    # 统一走 csv 解析，自动处理引号/逗号
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader]
    out = []
    for i, r in enumerate(rows):
        if i < skip_rows:
            continue
        if not r or not str(r[0]).strip():
            continue
        aid = str(r[id_col - 1]).strip() if len(r) >= id_col else ''
        name = str(r[name_col - 1]).strip() if len(r) >= name_col else ''
        name = name or '（名单无昵称）'
        if not aid:
            continue
        # 数字型 ID 统一成纯数字串（去掉 Excel/CSV 带出的 .0）
        if re.fullmatch(r'\d+\.0', aid):
            aid = aid[:-2]
        out.append((aid, name))
    return out


def load_anchor_data(path, id_col):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    ws.reset_dimensions()          # read_only 下维度常报 1x1
    rows = list(ws.iter_rows(values_only=True))
    header = list(rows[0])
    data = {}
    order = []
    for r in rows[1:]:
        if r is None or len(r) < id_col or r[id_col - 1] is None:
            continue
        aid = str(r[id_col - 1]).strip()
        if re.fullmatch(r'\d+\.0', aid):
            aid = aid[:-2]
        if aid not in data:
            data[aid] = r
            order.append(aid)
    return header, data, order, ws.title


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('data_xlsx', help='主播累计数据 xlsx')
    ap.add_argument('roster', help='报名/活动名单（lark-cli JSON 信封 或 纯 CSV/TSV）')
    ap.add_argument('-o', '--output', required=True, help='输出 xlsx 路径')
    ap.add_argument('--id-col', type=int, default=1, help='名单 ID 列序号(1-based)，默认 1')
    ap.add_argument('--name-col', type=int, default=2, help='名单昵称列序号(1-based)，默认 2')
    ap.add_argument('--skip-rows', type=int, default=1, help='名单跳过开头几行，默认 1（表头）')
    ap.add_argument('--data-id-col', type=int, default=2, help='累计数据表主播ID列序号(1-based)，默认 2')
    ap.add_argument('--order', choices=['roster', 'data'], default='roster')
    args = ap.parse_args()

    roster = load_roster(args.roster, args.id_col, args.name_col, args.skip_rows)
    roster_ids = {a for a, _ in roster}
    header, data, order, dsheet = load_anchor_data(args.data_xlsx, args.data_id_col)
    print(f'名单：{len(roster)} 条（去重后 {len(roster_ids)}）')
    print(f'累计数据表 [{dsheet}]：{len(data)} 位主播')

    if args.order == 'roster':
        seq = roster
    else:
        seq = [(aid, next((n for a, n in roster if a == aid), '')) for aid in order if aid in roster_ids]

    matched, miss_in_data = [], []
    for aid, name in seq:
        if aid in data:
            matched.append((aid, name, data[aid]))
        elif aid in roster_ids:
            miss_in_data.append((aid, name))

    not_in_roster = [(aid, data[aid][0]) for aid in order if aid not in roster_ids]
    print(f'关联成功：{len(matched)} 位')
    if miss_in_data:
        print(f'⚠️ 在名单里但累计数据表查不到：{len(miss_in_data)} 位 -> {miss_in_data}')
    print(f'（累计数据表中有 {len(not_in_roster)} 位不在名单内，已按要求剔除）')

    # ---------- 写出 ----------
    out = openpyxl.Workbook()
    s1 = out.active
    s1.title = '关联结果明细'
    hdr = ['名单ID', '名单昵称'] + [str(h) for h in header[args.data_id_col:]]
    s1.append(hdr)
    for aid, name, r in matched:
        s1.append([aid, name] + list(r[args.data_id_col:]))

    head_font = Font(bold=True, color='FFFFFF')
    head_fill = PatternFill('solid', fgColor='4472C4')
    thin = Side(style='thin', color='D0D0D0')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for c in s1[1]:
        c.font = head_font
        c.fill = head_fill
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    s1.freeze_panes = 'C2'
    for i in range(1, len(hdr) + 1):
        s1.column_dimensions[get_column_letter(i)].width = 14 if i == 1 else (26 if i == 2 else 17)
    for row in s1.iter_rows(min_row=1, max_row=s1.max_row, max_col=len(hdr)):
        for c in row:
            c.border = border
    s1.auto_filter.ref = f'A1:{get_column_letter(len(hdr))}{s1.max_row}'

    if miss_in_data or not_in_roster:
        s2 = out.create_sheet('未关联备查')
        s2.append(['ID', '昵称', '说明'])
        for aid, name in miss_in_data:
            s2.append([aid, name, '在名单里，但累计数据表中无此主播（可能未开播/大表未收录）'])
        for aid, name in not_in_roster:
            s2.append([aid, name, '累计数据表有，但不在名单内（已剔除）'])
        for c in s2[1]:
            c.font = head_font
            c.fill = head_fill
        for col, w in zip('ABC', (14, 30, 46)):
            s2.column_dimensions[col].width = w

    out.save(args.output)
    print(f'已写出：{args.output}')
    print()
    print('| ID | 名单昵称 | 数据表昵称 | ' + ' | '.join(str(h) for h in header[args.data_id_col:args.data_id_col + 3]) + ' |')
    print('|---|---|---|' + '---|' * 3)
    for aid, name, r in matched:
        cells = ' | '.join('' if v is None else str(v) for v in r[args.data_id_col:args.data_id_col + 3])
        print(f'| {aid} | {name} | {r[0]} | {cells} |')


if __name__ == '__main__':
    main()
