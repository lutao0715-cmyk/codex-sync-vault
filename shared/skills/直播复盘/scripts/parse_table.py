#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用「飞书场次明细表」解析与聚合（活动复盘用）

用法：
  # 1) 先把表导出落盘（见 references/data-pipeline.md §1）
  lark-cli sheets +csv-get --as user --url "<表URL>" --sheet-id "<id>" \
      --range "A1:AT799" --output-path livedata_raw.json

  # 2) 按需调用
  python3 parse_table.py livedata_raw.json --map            # 打印列名 → 列号
  python3 parse_table.py livedata_raw.json --summary        # 大盘总量 + 有效率
  python3 parse_table.py livedata_raw.json --trend          # 导出 trend.json（逐日）
  python3 parse_table.py livedata_raw.json --anchors        # 导出 anchor_compare.json（主播维度）
  python3 parse_table.py livedata_raw.json --all            # 全跑一遍

  # 列名与源表不一致时，用 --cols 覆盖（JSON 或 key=value 逗号串）
  python3 parse_table.py livedata_raw.json --all \
      --cols '{"id":"创作者ID","name":"作者昵称","date":"日期","on":"直播开播时长(小时)","pl":"直播播放总时长(小时)","acu":"直播ACU","expo":"直播曝光次数","click":"直播点击次数","play":"直播播放次数","playuv":"直播播放用户数","inter":"直播互动次数","interuv":"直播互动用户数","fans":"直播间关注成功用户数"}'

  # 有效场次阈值（默认 2 小时）与活动周期也可覆盖
  python3 parse_table.py livedata_raw.json --anchors --min-hours 2 --start 2026-08-20 --end 2026-09-19
"""
import argparse, csv, io, json, re, sys
from collections import Counter, defaultdict

DEFAULT_COLS = {
    'id': '创作者ID', 'name': '作者昵称', 'date': '日期',
    'on': '直播开播时长(小时)', 'pl': '直播播放总时长(小时)', 'acu': '直播ACU',
    'expo': '直播曝光次数', 'click': '直播点击次数',
    'play': '直播播放次数', 'playuv': '直播播放用户数',
    'inter': '直播互动次数', 'interuv': '直播互动用户数',
    'fans': '直播间关注成功用户数',
}


def norm(s):
    return re.sub(r'[\s\u3000（）()：:]', '', str(s or '')).lower()


def load(path):
    """兼容 --output-path 与 stdout 重定向两种 JSON 结构。"""
    d = json.load(open(path))
    payload = d.get('data', d)
    return payload


def parse(payload):
    parts = [p for p in re.split(r'(?m)^\[row=\d+\] ', payload['annotated_csv']) if p.strip()]
    rows = [next(csv.reader([p])) for p in parts]
    return rows


def resolve_cols(header, cols):
    """按列名定位列号；找不到就报错并提示可用列名。"""
    idx = {}
    normed = [norm(h) for h in header]
    for key, want in cols.items():
        if want is None:
            idx[key] = None
            continue
        w = norm(want)
        hit = [i for i, h in enumerate(normed) if h == w]
        if not hit:
            hit = [i for i, h in enumerate(normed) if w and w in h]
        if not hit:
            sys.exit(f"[错误] 找不到列「{want}」({key})，可用列：{header}")
        idx[key] = hit[0]
    return idx


def fnum(v):
    try:
        return float(str(v).replace(',', '').strip())
    except Exception:
        return 0.0


def dkey(x):
    m = re.findall(r'\d+', str(x or ''))
    if not m:
        return None
    if len(m[0]) == 8:
        return (int(m[0][:4]), int(m[0][4:6]), int(m[0][6:8]))
    if len(m[0]) == 6:
        return (2026, int(m[0][:2]), int(m[0][2:4]))
    return tuple(int(v) for v in m[:3])


def relabel(rows, idx, min_hours, start, end):
    """表头定位 + 空行过滤 + 日期过滤；返回记录列表。"""
    out = []
    for r in rows:
        r = [str(c) for c in r]
        if len(r) <= max(i for i in idx.values() if i is not None):
            continue
        if not r[idx['id']].strip():          # ★ 空行必须过滤（否则分母错误）
            continue
        k = dkey(r[idx['date']])
        if start and (not k or k < dkey(start)):
            continue
        if end and (not k or k > dkey(end)):
            continue
        rec = {key: (r[i].strip() if i is not None else '') for key, i in idx.items()
               if key not in ('on', 'pl', 'acu', 'expo', 'click', 'play', 'playuv', 'inter', 'interuv', 'fans')}
        for key in ('on', 'pl', 'acu', 'expo', 'click', 'play', 'playuv', 'inter', 'interuv', 'fans'):
            i = idx.get(key)
            rec[key] = fnum(r[i]) if i is not None else 0.0
        rec['dk'] = k
        rec['valid'] = rec['on'] >= min_hours
        out.append(rec)
    return out


def cmd_map(rows):
    print('表格行数:', len(rows))
    for i, h in enumerate(rows[1] if len(rows) > 1 else rows[0]):
        print(f'  {i:>3}  {h}')


def cmd_summary(recs, idx, min_hours):
    S = lambda key: sum(r[key] for r in recs)
    n = len(recs)
    v = sum(1 for r in recs if r['valid'])
    print('=== 大盘（已过滤空行）===')
    print(f'场次: {n}')
    print(f'有效场次(开播≥{min_hours}h): {v}  有效率: {v}/{n} = {v/n*100:.1f}%')
    print(f'开播时长h: {S("on"):,.1f}')
    print(f'播放时长h: {S("pl"):,.1f}   场均播放h: {S("pl")/n:,.1f}')
    for key, label in [('expo', '曝光次数'), ('click', '点击次数'), ('play', '播放次数'),
                       ('playuv', '播放用户数'), ('inter', '互动次数'), ('interuv', '互动用户数'),
                       ('fans', '关注成功用户数')]:
        print(f'{label}: {S(key):,.0f}')
    if S('expo'):
        print(f'点击率(次数口径): {S("click")/S("expo")*100:.2f}%')
    if S('play'):
        print(f'互动率(次数口径): {S("inter")/S("play")*100:.2f}%')
    if S('playuv'):
        print(f'互动渗透(人数口径): {S("interuv")/S("playuv")*100:.2f}%')
    print(f'主播数(有开播记录): {len({(r["id"], r["name"]) for r in recs})}')
    # 重复场次提示
    dup = [k for k, c in Counter((r['id'], r['date'], r['on']) for r in recs).items() if c > 1]
    if dup:
        print(f'⚠ 疑似重复记录 {len(dup)} 组（同主播同日同开播时长），写文档时注明知悉')


def build_daily(recs):
    daily = defaultdict(lambda: dict(s=0, pl=0.0, acu=[], acu25=0))
    for r in recs:
        if not r['dk']:
            continue
        d = daily[r['dk']]
        d['s'] += 1
        d['pl'] += r['pl']
        d['acu'].append(r['acu'])
        if r['acu'] > 25:
            d['acu25'] += 1
    return [dict(date=f'{k[1]}.{k[2]}', s=v['s'], pl=round(v['pl'], 1),
                 acu=round(sum(v['acu'])/len(v['acu']), 1), acu25=v['acu25'])
            for k, v in sorted(daily.items())]


def build_anchors(recs, mid):
    def half(k):
        return 1 if (k and k <= mid) else 2
    A = defaultdict(lambda: defaultdict(lambda: dict(s=0, v=0, on=0.0, pl=0.0, acu=[], inter=0.0, fans=0.0)))
    for r in recs:
        a = A[(r['id'], r['name'])][half(r['dk'])]
        a['s'] += 1
        a['v'] += 1 if r['valid'] else 0
        a['on'] += r['on']; a['pl'] += r['pl']
        a['acu'].append(r['acu']); a['inter'] += r['inter']; a['fans'] += r['fans']
    E = dict(s=0, v=0, on=0.0, pl=0.0, acu=[], inter=0.0, fans=0.0)
    out = []
    for (aid, nm), hs in A.items():
        h1, h2 = hs.get(1, E), hs.get(2, E)
        tot_s = sum(h['s'] for h in hs.values())
        out.append(dict(
            aid=aid, nm=nm, s=tot_s, v=sum(h['v'] for h in hs.values()),
            on=round(sum(h['on'] for h in hs.values()), 1),
            pl=round(sum(h['pl'] for h in hs.values()), 1),
            acu=round((sum(h1['acu']) + sum(h2['acu'])) / max(1, tot_s), 1),
            inter=int(sum(h['inter'] for h in hs.values())),
            fans=int(sum(h['fans'] for h in hs.values())),
            s1=h1['s'], s2=h2['s'], pl1=round(h1['pl'], 1), pl2=round(h2['pl'], 1),
            acu1=round(sum(h1['acu'])/len(h1['acu']), 1) if h1['acu'] else 0,
            acu2=round(sum(h2['acu'])/len(h2['acu']), 1) if h2['acu'] else 0))
    out.sort(key=lambda x: -x['pl'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('json_file')
    ap.add_argument('--map', action='store_true')
    ap.add_argument('--summary', action='store_true')
    ap.add_argument('--trend', action='store_true')
    ap.add_argument('--anchors', action='store_true')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--cols', default='{}', help='JSON 覆盖列名映射')
    ap.add_argument('--min-hours', type=float, default=2.0, help='有效场次开播时长阈值（小时）')
    ap.add_argument('--start', default=None, help='活动开始日期 YYYY-MM-DD')
    ap.add_argument('--end', default=None, help='活动结束日期 YYYY-MM-DD')
    ap.add_argument('--mid', default=None, help='前后半程切点 YYYY-MM-DD（默认活动期中点）')
    ap.add_argument('--outdir', default='.')
    a = ap.parse_args()

    payload = load(a.json_file)
    rows = parse(payload)
    cols = dict(DEFAULT_COLS)
    cols.update(json.loads(a.cols) if a.cols.strip() not in ('', '{}') else {})

    if a.map and not (a.summary or a.trend or a.anchors or a.all):
        cmd_map(rows); return

    idx = resolve_cols(rows[1] if len(rows) > 1 else rows[0], cols)
    recs = relabel(rows[2:], idx, a.min_hours, a.start, a.end)
    if not recs:
        sys.exit('[错误] 过滤后没有记录，检查 --cols / --start / --end')

    mid = dkey(a.mid) if a.mid else (recs[len(recs)//2]['dk'])
    print(f'# 记录数 {len(recs)}｜有效阈值 {a.min_hours}h｜半程切点 {mid}', file=sys.stderr)

    if a.summary or a.all:
        cmd_summary(recs, idx, a.min_hours)
    if a.trend or a.all:
        t = build_daily(recs)
        json.dump(t, open(f'{a.outdir}/trend.json', 'w'), ensure_ascii=False)
        print(f'→ {a.outdir}/trend.json（{len(t)} 天）')
    if a.anchors or a.all:
        an = build_anchors(recs, mid)
        json.dump(an, open(f'{a.outdir}/anchor_compare.json', 'w'), ensure_ascii=False, indent=1)
        tot = sum(x['pl'] for x in an)
        t5 = sum(x['pl'] for x in an[:5]) / tot
        t10 = sum(x['pl'] for x in an[:10]) / tot
        print(f'→ {a.outdir}/anchor_compare.json（{len(an)} 位主播）')
        print(f'播放时长集中度: TOP5 {t5*100:.1f}%  TOP10 {t10*100:.1f}%')


if __name__ == '__main__':
    main()
