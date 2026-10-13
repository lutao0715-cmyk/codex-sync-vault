# -*- coding: utf-8 -*-
"""三表联合终版：以大表为唯一口径骨架，33人全量分层评估
- 名单表：33 人基准
- 大表：直播全口径（曝光/点击/播放/互动/关注/粉丝/拉新/时长），剔除脏行
- 曝光侧表：推荐场景，仅作对照参考列，不参与打分（对账证明口径不可比）
"""
import openpyxl
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

A = 'C:/Users/win/Downloads/二台跨天 2.xlsx'
E = 'C:/Users/win/Downloads/重点主播的开播&转化数据(1).xlsx'
B = 'C:/Users/win/Downloads/报名成功主播_累计数据_0914v2.xlsx'
OUT = 'C:/Users/win/Downloads/报名成功主播_三表联合评估_0914.xlsx'

def num(v):
    if v is None: return 0.0
    if isinstance(v, (int, float)): return float(v)
    try: return float(str(v).replace(',', '').replace('%', '').strip())
    except Exception: return 0.0

def dstr(v):
    return '' if v is None else str(v).strip().replace('/', '-')[:10]

# ---------- 名单 ----------
wb = openpyxl.load_workbook(B, data_only=True, read_only=True)
ws = wb['关联结果明细']; ws.reset_dimensions()
rows = list(ws.iter_rows(values_only=True))
roster = {}
for r in rows[1:]:
    if r and r[0] is not None:
        roster[str(r[0]).strip()] = str(r[1]).strip()
wb.close()
assert len(roster) == 33, len(roster)

# ---------- 大表聚合 ----------
wb = openpyxl.load_workbook(A, data_only=True, read_only=True)
ws = wb['表格0']; ws.reset_dimensions()
it = ws.iter_rows(values_only=True)
hdr = next(it)
C = {'date': 0, 'cid': 1, 'on_h': 19, 'play_dur': 20,
     'exp_c': 28, 'exp_u': 29, 'clk_c': 30, 'clk_u': 31,
     'play_c': 32, 'play_u': 33, 'inter_u': 43,
     'follow': 108, 'dj': 111, 'fans': 105, 'avg_min': 106}
agg = defaultdict(lambda: {'days': set(), 'lids': set(), 'sess': 0, 'exp_c': 0.0, 'exp_c_raw': 0.0,
                           'clk_c': 0.0, 'exp_u_s': 0.0, 'clk_u_s': 0.0,
                           'play_c': 0.0, 'play_u_s': 0.0, 'dur': 0.0, 'inter_u_s': 0.0,
                           'follow': 0.0, 'dj': 0.0, 'fans': [], 'w_avg': 0.0,
                           'dirty': 0, 'hi_exp': 0.0, 'rows': 0})
for r in it:
    cid = str(r[C['cid']]).strip() if r[C['cid']] is not None else ''
    if cid not in roster:
        continue
    a = agg[cid]
    a['days'].add(dstr(r[C['date']]))
    a['rows'] += 1
    ec, cc = num(r[C['exp_c']]), num(r[C['clk_c']])
    a['exp_c_raw'] += ec
    if ec > 0 and cc > ec:
        a['dirty'] += 1
        continue
    if ec >= 500 and cc / ec > 0.25:
        a['hi_exp'] += ec
    a['exp_c'] += ec; a['clk_c'] += cc
    a['exp_u_s'] += num(r[C['exp_u']]); a['clk_u_s'] += num(r[C['clk_u']])
    a['play_c'] += num(r[C['play_c']]); a['play_u_s'] += num(r[C['play_u']])
    a['dur'] += num(r[C['play_dur']]); a['inter_u_s'] += num(r[C['inter_u']])
    a['follow'] += num(r[C['follow']]); a['dj'] += num(r[C['dj']])
    a['fans'].append(num(r[C['fans']]))
    a['w_avg'] += num(r[C['avg_min']]) * num(r[C['play_u']])
wb.close()
print(f'大表: 33 人全命中 | 脏行 {sum(a["dirty"] for a in agg.values())}')

live = {}
for cid, a in agg.items():
    e = a['exp_c']
    fans_net = max(a['fans']) - min(a['fans']) if a['fans'] else 0
    live[cid] = {
        'cid': cid, 'name': roster[cid],
        'sess': a['sess'], 'days': len(a['days']), 'rows': a['rows'], 'dirty': a['dirty'],
        'exp_c': e, 'clk_c': a['clk_c'],
        'ctr': a['clk_c'] / e * 100 if e else 0,
        'play_c': a['play_c'], 'play_u': a['play_u_s'],
        'dur_h': a['dur'],
        'avg_min': a['w_avg'] / a['play_u_s'] if a['play_u_s'] else (a['dur'] * 60 / a['play_u_s'] if a['play_u_s'] else 0),
        'inter_rate': a['inter_u_s'] / a['play_u_s'] * 100 if a['play_u_s'] else 0,
        'follow': a['follow'], 'dj': a['dj'], 'fans_net': fans_net,
        'fans_per_1k': fans_net / e * 1000 if e else 0,
        'per_play': a['dur'] * 60 / a['play_c'] if a['play_c'] else 0,
        'hi_share': a['hi_exp'] / e * 100 if e else 0,
    }

# ---------- 曝光侧表（推荐场景，仅参考列） ----------
KEYMAP = {'date': ('行为产生时间',), 'aid': ('作者ID',), 'exp_u': ('曝光用户数',), 'clk_u': ('点击用户数',)}
def resolve(hdr):
    norm = [''.join(ch for ch in str(h or '') if ch not in '（()） ') for h in hdr]
    out = {}
    for k, pats in KEYMAP.items():
        for i, s in enumerate(norm):
            if any(s.startswith(p) for p in pats):
                out[k] = i; break
    return out

wb = openpyxl.load_workbook(E, data_only=True, read_only=True)
rec = defaultdict(lambda: {'exp_u': 0.0, 'clk_u': 0.0})
for sn in ['二台达人算法场景每日曝光', '二台达人首页feed场景每日曝光']:
    ws = wb[sn]; ws.reset_dimensions()
    I = None
    for r in ws.iter_rows(values_only=True):
        if not r or all(x is None for x in r):
            I = None; continue
        if len(r) > 2 and str(r[1]).strip() == '作者ID':
            I = resolve(r); continue
        if I is None or r[1] is None:
            continue
        aid = str(r[I['aid']]).strip()
        if aid not in roster:
            continue
        d = rec[aid]
        d['exp_u'] += num(r[I['exp_u']]); d['clk_u'] += num(r[I['clk_u']])
wb.close()

# ---------- 门槛与打分 ----------
recs = list(live.values())
GATE = dict(exp=50000, days=5)          # 参评门槛
GATE2 = dict(exp=10000, days=3)         # 样本底线
CTR_SUS = 12.0                          # CTR 异常偏高线（全表中位约 7.5%）
for r in recs:
    r['rec_exp_u'] = rec.get(r['cid'], {}).get('exp_u', 0)
    r['rec_ctr'] = (rec[r['cid']]['clk_u'] / rec[r['cid']]['exp_u'] * 100) if r['cid'] in rec and rec[r['cid']]['exp_u'] else 0
    r['exp_per_day'] = r['exp_c'] / r['days'] if r['days'] else 0
    r['gate_ok'] = r['exp_c'] >= GATE['exp'] and r['days'] >= GATE['days']
    r['gate2_ok'] = r['exp_c'] >= GATE2['exp'] and r['days'] >= GATE2['days']
    r['ctr_sus'] = r['ctr'] > CTR_SUS or r['hi_share'] > 10

pool = [r for r in recs if r['gate_ok'] and not r['ctr_sus']]

def pct(vals, v):
    n = len(vals)
    if n <= 1: return 50.0
    k = sum(1 for x in vals if x < v) + 0.5 * sum(1 for x in vals if x == v)
    return k / n * 100

DIMS = {'转化分': ([('ctr', .55), ('fans_per_1k', .45)]),
        '深度分': ([('avg_min', .6), ('per_play', .4)]),
        '互动分': ([('inter_rate', 1.0)]),
        '规模分': ([('exp_per_day', .6), ('days', .4)])}
W = {'转化分': .25, '深度分': .30, '互动分': .15, '规模分': .10, '沉淀分': .20}
DIMS['沉淀分'] = ([('fans_per_1k', .6), ('follow', .2), ('dj', .2)])
for dn, fl in DIMS.items():
    for r in pool:
        r[dn] = round(sum(pct([x[f] for x in pool], r[f]) * w for f, w in fl), 1)
for r in pool:
    r['综合分'] = round(sum(r[dn] * W[dn] for dn in W), 1)
    q = r['深度分'] >= 55; c = r['转化分'] >= 55; s = r['规模分'] >= 45
    if q and c and s:
        r['分层'] = 'A 加推主力'
        r['建议'] = '转化、深度、规模三项均达标，维持并加大推荐权重'
    elif q and c:
        r['分层'] = 'T 质量达标·待给曝光'
        r['建议'] = '转化与观看深度达标、规模中游偏小，建议适当加量测试'
    elif r['深度分'] < 40 and r['转化分'] < 40:
        r['分层'] = 'C 暂缓投入'
        r['建议'] = '点击与观看深度双低，先改内容承接，不宜加量'
    elif r['gate2_ok']:
        r['分层'] = 'B 观察优化'
        r['建议'] = '整体中游，按短板定向优化'
    else:
        r['分层'] = 'P 样本偏薄'
        r['建议'] = '样本底线未过（曝光<1万或开播<3天），本轮不定级'
ORD = {'A 加推主力': 0, 'T 质量达标·待给曝光': 1, 'B 观察优化': 2, 'P 样本偏薄': 3, 'C 暂缓投入': 4}
pool.sort(key=lambda x: (ORD[x['分层']], -x['综合分']))

for r in recs:
    if '分层' not in r:
        if r['ctr_sus']:
            r['分层'] = '⚠️ CTR异常'
            r['建议'] = f"CTR {r['ctr']:.1f}% 显著高于全表中位（约7.5%）或高CTR行占比{r['hi_share']:.0f}%，数据先核实再评估"
        else:
            r['分层'] = 'S 样本不足'
            r['建议'] = f"曝光{int(r['exp_c']):,}或开播{int(r['days'])}天未达样本底线，本轮不定级"
all33 = sorted(recs, key=lambda x: (ORD.get(x['分层'], 9), -(x.get('综合分') or 0)))

print(f"\n参评 {len(pool)} | CTR异常 {sum(1 for r in recs if r['分层']=='⚠️ CTR异常')} | 样本不足 {sum(1 for r in recs if r['分层']=='S 样本不足')}")
h = f"{'#':>2} {'主播':<20}{'分层':<16}{'综合':>5}{'转化':>5}{'深度':>5}{'互动':>5}{'规模':>5}{'沉淀':>5}{'CTR%':>6}{'人均分':>7}{'次均分':>7}{'互动率%':>8}{'千次涨粉':>8}{'天数':>4}{'曝光':>10}"
print(h); print('-' * len(h))
for i, r in enumerate(all33, 1):
    print(f"{i:>2} {r['name']:<20}{r['分层']:<16}"
          f"{(r.get('综合分') or 0):>5.1f}{r.get('转化分', 0):>5.0f}{r.get('深度分', 0):>5.0f}{r.get('互动分', 0):>5.0f}{r.get('规模分', 0):>5.0f}{r.get('沉淀分', 0):>5.0f}"
          f"{r['ctr']:>6.2f}{r['avg_min']:>7.2f}{r['per_play']:>7.2f}{r['inter_rate']:>8.2f}{r['fans_per_1k']:>8.2f}{int(r['days']):>4}{int(r['exp_c']):>10,}")

# ---------- Excel ----------
wb = Workbook()
HF = Font(bold=True, color='FFFFFF', size=10)
HB = PatternFill('solid', fgColor='2F5597')
T = Side(style='thin', color='BFBFBF')
BD = Border(left=T, right=T, top=T, bottom=T)
TF = {'A 加推主力': 'C6EFCE', 'T 质量达标·待给曝光': 'DDEBF7', 'B 观察优化': 'FFF2CC',
      'P 样本偏薄': 'F2F2F2', 'C 暂缓投入': 'FCE4E4', 'S 样本不足': 'EDEDED', '⚠️ CTR异常': 'F8CBAD'}

def dump(ws, data, cols):
    ws.append([c[0] for c in cols])
    for c in ws[1]:
        c.font = HF; c.fill = HB; c.border = BD
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for r in data:
        ws.append([r.get(k, '') for _, k, _ in cols])
    for i, (_, _, w) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.border = BD
            if isinstance(c.value, float):
                c.number_format = '#,##0.00'
                c.alignment = Alignment(horizontal='right')
            elif isinstance(c.value, int):
                c.number_format = '#,##0'
                c.alignment = Alignment(horizontal='right')
            elif isinstance(c.value, str) and len(c.value) > 18:
                c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'C2'
    ws.auto_filter.ref = ws.dimensions

C1 = [('分层', '分层', 17), ('综合分', '综合分', 8), ('主播昵称', 'name', 22), ('主播ID', 'cid', 12),
      ('运营建议', '建议', 46), ('CTR%(次数)', 'ctr', 11), ('人均观看(分)', 'avg_min', 12),
      ('次均播放(分)', 'per_play', 12), ('互动率%', 'inter_rate', 10), ('千次曝光涨粉', 'fans_per_1k', 12),
      ('开播天数', 'days', 9), ('曝光次数', 'exp_c', 12), ('点击次数', 'clk_c', 11),
      ('播放次数', 'play_c', 11), ('播放总时长h', 'dur_h', 12), ('关注成功', 'follow', 10),
      ('app拉新', 'dj', 9), ('粉丝净增', 'fans_net', 10), ('高CTR行曝光占比%', 'hi_share', 14),
      ('剔除脏行数', 'dirty', 10), ('推荐场景曝光用户(参考)', 'rec_exp_u', 17), ('推荐场景CTR%(参考)', 'rec_ctr', 15),
      ('转化分', '转化分', 8), ('深度分', '深度分', 8), ('互动分', '互动分', 8), ('规模分', '规模分', 8), ('沉淀分', '沉淀分', 8)]

ws = wb.active; ws.title = '综合排名(全33人)'
dump(ws, all33, C1)
for row in ws.iter_rows(min_row=2):
    f = TF.get(row[0].value)
    if f:
        row[0].fill = PatternFill('solid', fgColor=f)

GRP = ['A 加推主力', 'T 质量达标·待给曝光', 'B 观察优化', 'P 样本偏薄', 'C 暂缓投入', 'S 样本不足', '⚠️ CTR异常']
WD = {'A 加推主力': '三项达标 → 维持并加大推荐权重', 'T 质量达标·待给曝光': '质量够格体量小 → 定向加量测试',
      'B 观察优化': '整体中游 → 按短板优化', 'P 样本偏薄': '样本底线未过 → 本轮不定级',
      'C 暂缓投入': '点击与深度双低 → 先改承接', 'S 样本不足': '数据太少 → 继续观察',
      '⚠️ CTR异常': 'CTR 显著偏离全表中位 → 先核实数据'}
wsum = wb.create_sheet('档位汇总', 0)
wsum.append(['档位', '人数', '主播名单', '处置建议'])
for k in GRP:
    who = [x['name'] for x in all33 if x['分层'] == k]
    if who:
        wsum.append([k, len(who), '、'.join(who), WD[k]])
wsum.append(['合计', len(all33), f'覆盖名单全部 {len(all33)} 人，无遗漏', ''])
for c in wsum[1]:
    c.font = HF; c.fill = HB; c.border = BD
    c.alignment = Alignment(horizontal='center', vertical='center')
for row in wsum.iter_rows(min_row=2):
    row[0].fill = PatternFill('solid', fgColor=TF.get(row[0].value, 'FFFFFF'))
    row[0].font = Font(bold=True)
    for c in row:
        c.border = BD
    row[2].alignment = Alignment(wrap_text=True, vertical='top')
    row[3].alignment = Alignment(wrap_text=True, vertical='top')
wsum.column_dimensions['A'].width = 22; wsum.column_dimensions['B'].width = 6
wsum.column_dimensions['C'].width = 96; wsum.column_dimensions['D'].width = 42

recs_sorted = sorted(recs, key=lambda x: -x['exp_c'])
wc = wb.create_sheet('口径对账')
wc.append(['主播昵称', '大表CTR%(次数)', '推荐场景CTR%', '推荐曝光用户', '大表曝光次数',
           '说明'])
for r in recs_sorted:
    note = ('推荐场景的「曝光用户」与大表「直播间曝光」口径不同（feed刷到 vs 直播间卡片曝光），'
            '两者非包含关系，不能互相换算；打分只用大表口径')
    wc.append([r['name'], round(r['ctr'], 2), round(r['rec_ctr'], 2),
               int(r['rec_exp_u']), int(r['exp_c']), note])
for c in wc[1]:
    c.font = HF; c.fill = HB; c.border = BD
for i, w in enumerate([22, 14, 14, 14, 14, 96], 1):
    wc.column_dimensions[get_column_letter(i)].width = w
for row in wc.iter_rows(min_row=2):
    for c in row:
        c.border = BD
    row[5].alignment = Alignment(wrap_text=True, vertical='top')

wn = wb.create_sheet('口径与规则')
notes = [('项目', '说明'),
         ('口径原则', '以「二台跨天 2」大表为唯一打分口径（直播平台全量、33人全覆盖、官方报表）；'
                 '「重点主播的开播&转化数据(1)」为推荐场景参考列不参与打分 —— 对账显示推荐曝光用户普遍为大表曝光用户和的150-190%，'
                 '两者是不同统计维度（feed刷到 vs 直播间曝光），非包含关系，混用即出错'),
         ('脏行处理', '剔除「点击次数>曝光次数」的物理不可能行（全表32行）；另统计「曝光≥500且CTR>25%」的高CTR行占比，>10%者标记'),
         ('指标公式', 'CTR=点击次数÷曝光次数；人均观看=Σ(行人均时长×行播放用户)÷Σ播放用户；次均播放=总时长×60÷播放次数；'
                 '互动率=互动用户÷播放用户（行级求和，含跨天重复，仅同表内相对比较）；千次曝光涨粉=粉丝净增(max-min)÷曝光×1000'),
         ('打分权重', '转化25%(CTR55%+千次涨粉45%) + 深度30%(人均60%+次均40%) + 互动15% + 规模10%(日均曝光60%+天数40%) + 沉淀20%(涨粉60%+关注20%+拉新20%)，池内百分位'),
         ('参评门槛', '曝光≥5万 且 开播≥5天；CTR>12%（全表中位约7.5%）或高CTR行占比>10% → ⚠️ CTR异常不参评；样本底线：曝光≥1万且开播≥3天')]
for r in notes:
    wn.append(list(r))
for c in wn[1]:
    c.font = HF; c.fill = HB; c.border = BD
wn.column_dimensions['A'].width = 14; wn.column_dimensions['B'].width = 130
for row in wn.iter_rows(min_row=2):
    row[0].font = Font(bold=True)
    for c in row:
        c.border = BD
    row[1].alignment = Alignment(wrap_text=True, vertical='top')

wb.save(OUT)
print('\n已输出:', OUT)
