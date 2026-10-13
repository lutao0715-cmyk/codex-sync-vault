# -*- coding: utf-8 -*-
"""重点主播复盘 v3（终版）：曝光侧按日块解析 + 异常日剔除 + 有意义曝光日门槛 + 四维分层 + Excel 输出"""
import openpyxl, json, statistics
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

A = 'C:/Users/win/Downloads/重点主播的开播&转化数据(1).xlsx'
B = 'C:/Users/win/Downloads/报名成功主播_累计数据_0914v2.xlsx'
OUT = 'C:/Users/win/Downloads/重点主播复盘_分层评估_0914v3.xlsx'
SC = ['二台达人算法场景每日曝光', '二台达人首页feed场景每日曝光']
SCN = {'二台达人算法场景每日曝光': '算法场景', '二台达人首页feed场景每日曝光': '首页feed'}
MIN_DAY = 200          # 有意义曝光日门槛：单日曝光用户 <200 视为噪音日，不进日中位数/天数
GATE = dict(days=8, exp_u=50000, anom=40, conc=70, sess=5)


def num(v):
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).replace(',', '').replace('%', '').strip())
    except Exception:
        return 0.0


def dstr(v):
    return '' if v is None else str(v).strip().replace('/', '-')[:10]


KEYMAP = {'date': ('行为产生时间',), 'aid': ('作者ID',), 'name': ('作者昵称',),
          'exp_u': ('曝光用户数',), 'clk_u': ('点击用户数',), 'play_u': ('播放用户数',),
          'dur': ('点击视频总播放时长',), 'exp_c': ('曝光次数',), 'clk_c': ('点击次数',),
          'rec': ('推荐转化率',), 'min_pe': ('曝光人均播放时长',)}


def resolve(hdr):
    norm = [''.join(ch for ch in str(h or '') if ch not in '（()） ') for h in hdr]
    out = {}
    for k, pats in KEYMAP.items():
        for i, s in enumerate(norm):
            if any(s.startswith(p) for p in pats):
                out[k] = i
                break
    return out


# ---------- 解析曝光侧 ----------
wb = openpyxl.load_workbook(A, data_only=True, read_only=True)
day = defaultdict(lambda: {'exp_u': 0.0, 'clk_u': 0.0, 'play_u': 0.0, 'dur': 0.0, 'exp_c': 0.0,
                           'rec_w': 0.0, 'name': '', 'sc': defaultdict(lambda: {'exp_u': 0.0, 'clk_u': 0.0, 'dur': 0.0})})
nrow = 0
for sn in SC:
    ws = wb[sn]
    ws.reset_dimensions()
    I = None
    for r in ws.iter_rows(values_only=True):
        if not r or all(x is None for x in r):
            I = None
            continue
        if len(r) > 2 and str(r[1]).strip() == '作者ID':
            I = resolve(r)
            continue
        if I is None or r[1] is None:
            continue
        eu = num(r[I['exp_u']])
        dur = num(r[I['dur']]) if 'dur' in I else num(r[I['min_pe']]) * eu   # 个别块缺列时反推（口径等价）
        dd = day[(dstr(r[I['date']]), str(r[I['aid']]).strip())]
        dd['name'] = str(r[I['name']] or '').strip()
        dd['exp_u'] += eu
        dd['clk_u'] += num(r[I['clk_u']])
        dd['play_u'] += num(r[I['play_u']])
        dd['dur'] += dur
        dd['exp_c'] += num(r[I['exp_c']])
        dd['rec_w'] += num(r[I['rec']]) * eu
        s = dd['sc'][sn]
        s['exp_u'] += eu
        s['clk_u'] += num(r[I['clk_u']])
        s['dur'] += dur
        nrow += 1

ws = wb['异常曝光case（标红）']
ws.reset_dimensions()
rows = list(ws.iter_rows(values_only=True))
J = {str(h): i for i, h in enumerate(rows[0])}
anom, anom_cases = defaultdict(float), defaultdict(int)
for r in rows[1:]:
    if not r or r[1] is None:
        continue
    anom[(dstr(r[J['日期']]), str(r[J['作者ID']]).strip())] += num(r[J['曝光次数']])
    anom_cases[str(r[J['作者ID']]).strip()] += 1
wb.close()
print(f'曝光侧明细 {nrow} 行 | 日期×主播 {len(day)} 组 | 异常 case {len(rows)-1} 条/{len(anom_cases)} 人')

# ---------- 聚合 ----------
agg = defaultdict(lambda: {'dt_all': set(), 'dt': set(), 'dt_sig': set(), 'exp_u_all': 0.0, 'exp_c_all': 0.0,
                           'exp_u': 0.0, 'clk_u': 0.0, 'play_u': 0.0, 'dur': 0.0, 'rec_w': 0.0,
                           'day_ratio': [], 'day_exp': [], 'anom_days': 0, 'anom_exp': 0.0, 'name': '',
                           'sc': defaultdict(lambda: {'exp_u': 0.0, 'clk_u': 0.0, 'dur': 0.0})})
det = []
for (dt, aid), x in day.items():
    a = agg[aid]
    a['name'] = x['name']
    a['dt_all'].add(dt)
    a['exp_u_all'] += x['exp_u']
    a['exp_c_all'] += x['exp_c']
    is_anom = (dt, aid) in anom
    if is_anom:
        a['anom_days'] += 1
        a['anom_exp'] += anom[(dt, aid)]
    else:
        a['dt'].add(dt)
        a['exp_u'] += x['exp_u']
        a['clk_u'] += x['clk_u']
        a['play_u'] += x['play_u']
        a['dur'] += x['dur']
        a['rec_w'] += x['rec_w']
        if x['exp_u'] >= MIN_DAY:
            a['dt_sig'].add(dt)
            a['day_exp'].append(x['exp_u'])
            a['day_ratio'].append(x['clk_u'] / x['exp_u'])
        for k, v in x['sc'].items():
            a['sc'][k]['exp_u'] += v['exp_u']
            a['sc'][k]['clk_u'] += v['clk_u']
            a['sc'][k]['dur'] += v['dur']
    for k, v in x['sc'].items():
        if v['exp_u'] <= 0:
            continue
        det.append({'日期': dt, '主播': x['name'], '场景': SCN[k], '曝光用户': v['exp_u'],
                    '点击用户': v['clk_u'], '观看时长(分)': round(v['dur'], 1),
                    'CTR%': round(v['clk_u'] / v['exp_u'] * 100, 2),
                    '秒/曝光': round(v['dur'] * 60 / v['exp_u'], 2),
                    '是否异常日': '是' if is_anom else '',
                    '是否计入': '否(异常日)' if is_anom else ('否(噪音日)' if x['exp_u'] < MIN_DAY else '是')})

# ---------- 直播侧 ----------
wb = openpyxl.load_workbook(B, data_only=True, read_only=True)
ws = wb['关联结果明细']
ws.reset_dimensions()
rows = list(ws.iter_rows(values_only=True))
K = {str(h): i for i, h in enumerate(rows[0])}
live = {}
for r in rows[1:]:
    if not r or r[0] is None:
        continue
    g = lambda k: num(r[K[k]])
    live[str(r[0]).strip()] = dict(name=str(r[K['名单昵称']]), sess=g('开播场次'), days=g('开播天数'),
                                   dur_h=g('累计播放总时长(小时)'), exp=g('累计直播曝光次数'),
                                   play_u=g('累计直播播放用户数'), inter_u=g('累计直播互动用户数'),
                                   follow=g('累计直播间关注成功用户数'), dj=g('累计app手机拉新首播用户数'),
                                   fans=g('累计粉丝量净增(活动期max-min)'), avg_min=g('人均观看时长(分钟)'),
                                   inter_rate=g('互动率(%)'), ctr_live=g('CTR(%)'), per_play=g('次均播放时长(分钟)'))
wb.close()

recs, no_exp, no_live = [], [], []
ZERO = {'exp_u': 0.0, 'exp_u_all': 0.0, 'exp_c': 0.0, 'days': 0, 'days_clean': 0, 'days_all': 0,
        'ctr_u': 0.0, 'ctr_med': 0.0, 'spe': 0.0, 'w_min': 0.0, 'rec': 0.0, 'conc': 0.0,
        'anom_days': 0, 'anom_day_share': 0.0, 'sc_algo': 0.0, 'sc_feed': 0.0,
        'exp_algo': 0.0, 'exp_feed': 0.0}
for aid, L in live.items():
    a = agg.get(aid)
    if not a:
        # 曝光侧全程无记录：仍然保留在名单里，单独标记，绝不丢人
        no_exp.append(L['name'])
        r = dict(ZERO)
        r.update({'aid': aid, 'name': L['name'], 'no_exp': True, 'exp_per_day': 0.0})
        r['fans_per_1k'] = L['fans'] / L['exp'] * 1000 if L['exp'] else 0
        r.update({f'L_{k}': v for k, v in L.items() if k != 'name'})
        recs.append(r)
        continue
    e = a['exp_u']
    r = {'aid': aid, 'name': L['name'],
         'exp_u': e, 'exp_u_all': a['exp_u_all'], 'exp_c': a['exp_c_all'],
         'days': len(a['dt_sig']), 'days_clean': len(a['dt']), 'days_all': len(a['dt_all']),
         'ctr_u': a['clk_u'] / e * 100 if e else 0,
         'ctr_med': statistics.median(a['day_ratio']) * 100 if a['day_ratio'] else 0,
         'spe': a['dur'] * 60 / e if e else 0,
         'w_min': a['dur'] / a['play_u'] if a['play_u'] else 0,
         'rec': a['rec_w'] / e * 100 if e else 0,
         'conc': max(a['day_exp']) / e * 100 if e and a['day_exp'] else 0,
         'anom_days': a['anom_days'],
         'anom_day_share': a['anom_days'] / len(a['dt_all']) * 100 if a['dt_all'] else 0,
         'sc_algo': (a['sc'][SC[0]]['clk_u'] / a['sc'][SC[0]]['exp_u'] * 100) if a['sc'][SC[0]]['exp_u'] else 0,
         'sc_feed': (a['sc'][SC[1]]['clk_u'] / a['sc'][SC[1]]['exp_u'] * 100) if a['sc'][SC[1]]['exp_u'] else 0,
         'exp_algo': a['sc'][SC[0]]['exp_u'], 'exp_feed': a['sc'][SC[1]]['exp_u']}
    r['exp_per_day'] = r['exp_u'] / r['days'] if r['days'] else 0
    r['fans_per_1k'] = L['fans'] / L['exp'] * 1000 if L['exp'] else 0
    r.update({f'L_{k}': v for k, v in L.items() if k != 'name'})
    recs.append(r)
for aid, a in agg.items():
    if aid not in live:
        no_live.append((a['name'], a['exp_u']))
print(f'合并 {len(recs)} 人 | 曝光侧多出 {len(no_live)} 人 {no_live} | 名单缺曝光 {len(no_exp)} 人 {no_exp}')

# ---------- 闸门与打分 ----------
GATE2 = dict(days=5, exp_u=30000, sess=3)      # 样本可用底线
for r in recs:
    if r.get('no_exp'):
        r['hard'] = False
        r['bad'] = True
        r['thin_why'] = ['曝光侧无任何推荐曝光记录']
        r['分层'] = 'N 无推荐曝光'
        r['建议'] = '算法场景与首页feed 整个活动期均无曝光记录，平台未分配推荐流量；建议先排查是否未入选推荐池/被限流，再谈内容优化'
        continue
    r['hard'] = r['days'] >= GATE['days'] and r['exp_u'] >= GATE['exp_u'] and r['L_sess'] >= GATE['sess']
    r['thin_why'] = []
    if r['days'] < GATE['days']:
        r['thin_why'].append(f"有效曝光日{r['days']}天")
    if r['exp_u'] < GATE['exp_u']:
        r['thin_why'].append(f"净曝光用户{int(r['exp_u']):,}")
    if r['L_sess'] < GATE['sess']:
        r['thin_why'].append(f"直播场次{int(r['L_sess'])}")
    r['bad'] = r['days'] < GATE2['days'] or r['exp_u'] < GATE2['exp_u'] or r['L_sess'] < GATE2['sess']

suspect = [r for r in recs if not r.get('no_exp')
           and (r['anom_day_share'] > GATE['anom'] or r['conc'] > GATE['conc'])]
for r in suspect:
    r['flag'] = (f"异常日占比{r['anom_day_share']:.0f}%" if r['anom_day_share'] > GATE['anom']
                 else f"单日曝光集中度{r['conc']:.0f}%") + "（曝光被异常case污染）"
    r['分层'] = '⚠️ 数据存疑'
    r['建议'] = '曝光被异常 case 污染、率值与时长失真，净化后样本不足以定级；建议先核实流量来源再看内容'
pool = [r for r in recs if r not in suspect and not r['bad']]

for r in pool:
    r['exp_per_day'] = r['exp_u'] / r['days'] if r['days'] else 0

def pct(vals, v):
    n = len(vals)
    if n <= 1:
        return 50.0
    k = sum(1 for x in vals if x < v) + 0.5 * sum(1 for x in vals if x == v)
    return k / n * 100


DIMS = {'规模分': ({'a': 'exp_per_day', 'b': 'days'}, {'a': .6, 'b': .4}),
        '效率分': ({'a': 'ctr_u', 'b': 'rec'}, {'a': .5, 'b': .5}),
        '深度分': ({'a': 'spe', 'b': 'w_min'}, {'a': .5, 'b': .5}),
        '沉淀分': ({'a': 'L_inter_rate', 'b': 'fans_per_1k', 'c': 'L_avg_min'}, {'a': .4, 'b': .3, 'c': .3})}
W = {'规模分': .20, '效率分': .25, '深度分': .35, '沉淀分': .20}
for dn, (fl, w) in DIMS.items():
    for r in pool:
        r[dn] = round(sum(pct([x[fl[f]] for x in pool], r[fl[f]]) * w[f] for f in fl), 1)
for r in pool:
    r['综合分'] = round(sum(r[dn] * W[dn] for dn in W), 1)
    r['有量'] = r['exp_per_day'] >= 10000
    r['质优'] = r['效率分'] >= 55 and r['深度分'] >= 55
    if r['质优'] and not r['hard']:
        r['分层'] = 'T 质量达标·待给曝光'
        r['建议'] = '效率与观看深度已达标，但' + '、'.join(r['thin_why']) + '，建议定向加量测试后再定级'
    elif r['hard'] and r['有量'] and r['质优']:
        r['分层'] = 'A 加推主力'
        r['建议'] = '规模、效率、深度三项均达标，维持并加大推荐权重'
    elif r['hard'] and r['效率分'] < 45 and r['深度分'] < 45:
        r['分层'] = 'C 暂缓投入'
        r['建议'] = '点击与观看深度双低，先改内容承接，不宜加量'
    elif r['hard']:
        r['分层'] = 'B 观察优化'
        r['建议'] = '单项尚可、整体中游，按短板定位优化'
    elif r['效率分'] < 45 and r['深度分'] < 45:
        r['分层'] = 'C 暂缓投入'
        r['建议'] = '效率与观看深度双低（且' + '、'.join(r['thin_why']) + '），不建议继续投量'
    else:
        r['分层'] = 'P 样本偏薄'
        r['建议'] = '数据量不足以定级（' + '、'.join(r['thin_why']) + '），本轮不建议据此调整资源'
ok = [r for r in pool if r['分层'].startswith(('A', 'B', 'C'))]
ok.sort(key=lambda x: -x['综合分'])
for r in pool:
    if r['分层'].startswith(('A', 'B', 'C')):
        r['分层'] = r['分层']
ORD = {'A 加推主力': 0, 'T 质量达标·待给曝光': 1, 'B 观察优化': 2, 'P 样本偏薄': 3,
       'C 暂缓投入': 4, 'S 样本不足': 5, '⚠️ 数据存疑': 6, 'N 无推荐曝光': 7}
pool.sort(key=lambda x: (ORD[x['分层']], -x['综合分']))

# 全量名单（不丢人）：直接取 recs 全员，保证与名单一一对应
for r in recs:
    if '分层' not in r:
        r['分层'] = 'S 样本不足'
        r['建议'] = '样本量不足（' + '、'.join(r.get('thin_why', [])) + '），本轮不参与定级'
all33 = list(recs)
all33.sort(key=lambda x: (ORD.get(x['分层'], 99), -(x.get('综合分') or 0)))

json.dump({'ok': ok, 'pool': pool, 'suspect': suspect, 'no_exp': [r for r in recs if r.get('no_exp')],
           'all33': all33, 'det': det}, open('/tmp/final_scored.json', 'w'), ensure_ascii=False)

print(f"\n参评 {len(pool)} 人（其中A/B/C定级 {len(ok)} 人） | 数据存疑 {len(suspect)} 人\n")
h = f"{'#':>2} {'主播':<20}{'分层':<15}{'综合':>6}{'规模':>5}{'效率':>5}{'深度':>5}{'沉淀':>5}{'日均曝光':>9}{'有效日':>5}{'CTR%':>6}{'中位%':>6}{'秒/曝光':>8}{'分/人':>6}{'互动%':>6}{'千次涨粉':>8}{'场次':>5}"
print(h); print('-' * len(h))
for i, r in enumerate(pool, 1):
    print(f"{i:>2} {r['name']:<20}{r['分层']:<15}{r['综合分']:>6.1f}{r['规模分']:>5.0f}{r['效率分']:>5.0f}{r['深度分']:>5.0f}{r['沉淀分']:>5.0f}"
          f"{int(r['exp_per_day']):>9,}{r['days']:>5}{r['ctr_u']:>6.2f}{r['ctr_med']:>6.2f}{r['spe']:>8.1f}{r['w_min']:>6.2f}{r['L_inter_rate']:>6.2f}{r['fans_per_1k']:>8.2f}{int(r['L_sess']):>5}")
print('\n-- 数据存疑 --')
for r in sorted(suspect, key=lambda x: -(x['exp_u'] or 0)):
    print(f"   {r['name']:<20}{r['flag']}")
print('-- 样本不足（未进入参评池）--')
for r in sorted([x for x in recs if x not in pool and x not in suspect and not x.get('no_exp')], key=lambda x: -(x['exp_u'] or 0)):
    print(f"   {r['name']:<20}{'、'.join(r.get('thin_why', []))}")
print('-- 无推荐曝光（曝光侧零记录，保留不排名）--')
for r in [x for x in recs if x.get('no_exp')]:
    print(f"   {r['name']:<20}直播场次{int(r['L_sess'])} / 播放总时长{r['L_dur_h']:.1f}h / 累计直播曝光{int(r['L_exp']):,}")
print(f"\n全量合计 {len(all33)} 人（= 名单全量，无遗漏）")

# ---------- Excel ----------
wb = Workbook()
HF = Font(bold=True, color='FFFFFF', size=10)
HB = PatternFill('solid', fgColor='2F5597')
T = Side(style='thin', color='BFBFBF')
BD = Border(left=T, right=T, top=T, bottom=T)
TF = {'A 加推主力': 'C6EFCE', 'T 质量达标·待给曝光': 'DDEBF7', 'B 观察优化': 'FFF2CC',
      'P 样本偏薄': 'F2F2F2', 'C 暂缓投入': 'FCE4E4'}


def dump(ws, rows, cols):
    ws.append([c[0] for c in cols])
    for c in ws[1]:
        c.font = HF; c.fill = HB; c.border = BD
        c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    for r in rows:
        ws.append([r.get(k, '') for _, k, _ in cols])
    for i, (_, _, w) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.border = BD
            if isinstance(c.value, (int, float)):
                c.number_format = '#,##0.00' if isinstance(c.value, float) else '#,##0'
                c.alignment = Alignment(horizontal='right')
    ws.freeze_panes = 'B2'
    ws.auto_filter.ref = ws.dimensions


C1 = [('分层', '分层', 15), ('综合分', '综合分', 8), ('主播昵称', 'name', 22), ('主播ID', 'aid', 12),
      ('运营建议', '建议', 44), ('日均曝光用户', 'exp_per_day', 12), ('净曝光用户', 'exp_u', 12),
      ('有效曝光日', 'days', 10), ('曝光日合计', 'days_clean', 11), ('曝光集中度%', 'conc', 11),
      ('异常日占比%', 'anom_day_share', 11), ('曝光用户CTR%', 'ctr_u', 12), ('日中位CTR%', 'ctr_med', 11),
      ('推荐转化率%', 'rec', 11), ('秒/曝光', 'spe', 9), ('观看分钟/播放用户', 'w_min', 14),
      ('直播场次', 'L_sess', 9), ('开播天数', 'L_days', 9), ('累计播放总时长h', 'L_dur_h', 14),
      ('累计直播曝光', 'L_exp', 12), ('累计播放用户', 'L_play_u', 12), ('互动率%', 'L_inter_rate', 9),
      ('粉丝净增', 'L_fans', 9), ('千次曝光涨粉', 'fans_per_1k', 12), ('app拉新', 'L_dj', 9),
      ('关注成功', 'L_follow', 9), ('直播侧人均观看(分)', 'L_avg_min', 15),
      ('直播侧次均播放(分)', 'L_per_play', 15), ('规模分', '规模分', 8), ('效率分', '效率分', 8),
      ('深度分', '深度分', 8), ('沉淀分', '沉淀分', 8)]
ws = wb.active
ws.title = '分层结论'
dump(ws, all33, C1)
for row in ws.iter_rows(min_row=2):
    f = TF.get(row[0].value)
    if f:
        row[0].fill = PatternFill('solid', fgColor=f)

# 档位汇总页：一眼看清 33 人各在什么位置
GRP = ['A 加推主力', 'T 质量达标·待给曝光', 'B 观察优化', 'C 暂缓投入',
       'P 样本偏薄', 'S 样本不足', '⚠️ 数据存疑', 'N 无推荐曝光']
WDESC = {'A 加推主力': '规模/效率/深度三项达标 → 维持并加大推荐权重',
         'T 质量达标·待给曝光': '内容质量已达标，是曝光没给够 → 建议定向加量测试',
         'B 观察优化': '整体中游、单项尚可 → 按短板定向优化',
         'C 暂缓投入': '点击与观看深度双低 → 先改内容承接，不宜加量',
         'P 样本偏薄': '数据量不足以定级 → 本轮不据此调整资源',
         'S 样本不足': '数据量低于样本底线 → 本轮不据此调整资源，继续观察',
         '⚠️ 数据存疑': '曝光被异常 case 污染、率值失真 → 先核实流量来源',
         'N 无推荐曝光': '曝光侧整个活动期零记录 → 先排查是否未入选推荐池/限流'}
wsum = wb.create_sheet('档位汇总', 0)
wsum.append(['档位', '人数', '主播名单', '处置建议'])
for k in GRP:
    who = [x['name'] for x in all33 if x['分层'] == k]
    if not who:
        continue
    wsum.append([k, len(who), '、'.join(who), WDESC[k]])
tot = len(all33)
wsum.append(['合计（= 名单全量）', tot, f'覆盖名单全部 {tot} 人，无遗漏', ''])
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
wsum.column_dimensions['A'].width = 22
wsum.column_dimensions['B'].width = 6
wsum.column_dimensions['C'].width = 96
wsum.column_dimensions['D'].width = 46

thin = [x for x in recs if x not in pool and x not in suspect and not x.get('no_exp')]
noexp = [x for x in recs if x.get('no_exp')]
alls = []
for tag, lst in (('参评', pool), ('数据存疑', suspect), ('样本不足', thin), ('无推荐曝光', noexp)):
    for r in lst:
        r2 = dict(r)
        r2['name_pick'] = tag + ' / ' + (r.get('分层') or r.get('flag') or '')
        alls.append(r2)
alls.sort(key=lambda x: (ORD.get(str(x['name_pick']).split(' / ')[-1], 9), -(x['exp_u'] or 0)))
C2 = [('状态/分层', 'name_pick', 26)] + [(c[0], c[1], c[2]) for c in C1 if c[1] not in ('分层',)]
dump(wb.create_sheet('全量指标'), alls, C2)

dump(wb.create_sheet('数据存疑剔除'), sorted(suspect, key=lambda x: -x['exp_u']),
     [('主播昵称', 'name', 22), ('剔除原因', 'flag', 34), ('有效曝光日', 'days', 10), ('净曝光用户', 'exp_u', 12),
      ('净曝光用户(含异常日)', 'exp_u_all', 16), ('异常日占比%', 'anom_day_share', 11), ('曝光集中度%', 'conc', 11),
      ('曝光用户CTR%', 'ctr_u', 12), ('秒/曝光', 'spe', 9), ('直播场次', 'L_sess', 9), ('开播天数', 'L_days', 9),
      ('累计播放总时长h', 'L_dur_h', 14), ('粉丝净增', 'L_fans', 9), ('互动率%', 'L_inter_rate', 9)])
sm = []
for r in sorted(thin, key=lambda x: -x['exp_u']):
    r2 = dict(r); r2['未达标项'] = '、'.join(r.get('thin_why', [])); sm.append(r2)
w4 = wb.create_sheet('样本不足')
dump(w4, sm, [('主播昵称', 'name', 22), ('未达标项', '未达标项', 46), ('有效曝光日', 'days', 10),
              ('净曝光用户', 'exp_u', 12), ('曝光用户CTR%', 'ctr_u', 12), ('秒/曝光', 'spe', 9),
              ('观看分钟/播放用户', 'w_min', 14), ('推荐转化率%', 'rec', 11), ('直播场次', 'L_sess', 9),
              ('开播天数', 'L_days', 9), ('互动率%', 'L_inter_rate', 9), ('粉丝净增', 'L_fans', 9)])
for row in w4.iter_rows(min_row=2, min_col=2, max_col=2):
    for c in row:
        c.alignment = Alignment(horizontal='left', wrap_text=True)

# 无推荐曝光页：曝光侧零记录的人，单独列出，说明他们并未被丢弃
w7 = wb.create_sheet('无推荐曝光')
dump(w7, noexp, [('主播昵称', 'name', 22), ('主播ID', 'aid', 12), ('说明', '建议', 62),
                 ('直播场次', 'L_sess', 9), ('开播天数', 'L_days', 9), ('累计播放总时长h', 'L_dur_h', 14),
                 ('累计直播曝光', 'L_exp', 12), ('累计播放用户', 'L_play_u', 12), ('互动率%', 'L_inter_rate', 9),
                 ('粉丝净增', 'L_fans', 9), ('人均观看(分)', 'L_avg_min', 12)])
for row in w7.iter_rows(min_row=2, min_col=3, max_col=3):
    for c in row:
        c.alignment = Alignment(horizontal='left', wrap_text=True)

det.sort(key=lambda x: (x['日期'], -x['曝光用户']))
w5 = wb.create_sheet('曝光侧日明细')
dump(w5, det, [(k, k, w) for k, w in (('日期', 12), ('主播', 22), ('场景', 11), ('曝光用户', 11), ('点击用户', 11),
                                      ('观看时长(分)', 13), ('CTR%', 8), ('秒/曝光', 9), ('是否异常日', 11), ('是否计入', 13))])

cmp_rows = [
    ('上版结论', '主播', '本版结论', '变化原因'),
    ('强潜力', '北环大黑', '⚠️ 数据存疑', '80% 的曝光日命中异常曝光 case，剔除后只剩 1 个有效曝光日，CTR 24.9%、秒/曝光 327 明显失真'),
    ('强潜力', '雅文趣钓鱼', '⚠️ 数据存疑', '单日曝光集中度 86%，全靠一天爆量；有效曝光日仅 3 天'),
    ('强潜力', '东北乒乓侠', '⚠️ 数据存疑', '70% 曝光日命中异常 case（单场曝光 21.5 万），净化后只剩 3 天有效数据'),
    ('强潜力', '哇可爱的贤贤^_^', 'A 加推主力', '结论保留：CTR 0.96%、秒/曝光 9.8、互动率 2.35% 全场最高'),
    ('强潜力', '晴晴-啦啦队长', 'A 加推主力', '结论保留并升至第 1：秒/曝光 15.7、观看分钟/播放用户 1.82 双双第一'),
    ('强潜力', '快乐钓鱼柱子', 'C 暂缓投入', '降级：净化后 CTR 0.77%、秒/曝光 2.1、观看分/人 0.29，效率与深度双低；上版的高 CTR 来自异常行'),
    ('强潜力', '大伟路亚试钓师', 'C 暂缓投入', '降级：CTR 0.56%、秒/曝光 2.2，点击与观看深度双低'),
    ('强潜力', '辣堡不辣Rachel', 'T 质量达标·待给曝光', '质量没问题（效率82/深度79），但有效曝光日仅 5 天、日均 1.3 万，属曝光没给够'),
    ('强潜力', '奈奈然', 'T 质量达标·待给曝光', '质量达标（效率59/深度71），但直播只开 3 场，样本太薄'),
    ('—', '梅戈Meige', '样本不足', '曝光用户 27 万但只有 4 个有效曝光日，无法定级'),
    ('—', '时不时', 'A 加推主力', '新版升档：日均曝光 3.5 万（第 3）+ CTR 1.12% + 推荐转化 1.48%，规模与效率兼顾'),
]
wc = wb.create_sheet('与上版结论对比')
for r in cmp_rows:
    wc.append(list(r))
for c in wc[1]:
    c.font = HF; c.fill = HB; c.border = BD
for i, w in enumerate([12, 22, 20, 88], 1):
    wc.column_dimensions[get_column_letter(i)].width = w
for row in wc.iter_rows(min_row=2):
    row[0].font = Font(bold=True)
    for c in row:
        c.border = BD
    row[3].alignment = Alignment(wrap_text=True, vertical='top')
    if '数据存疑' in str(row[2].value):
        row[2].fill = PatternFill('solid', fgColor='FCE4E4')
    elif str(row[2].value).startswith('A'):
        row[2].fill = PatternFill('solid', fgColor='C6EFCE')

w6 = wb.create_sheet('口径与数据坑')
notes = [('项目', '说明'),
         ('数据源1', '重点主播的开播&转化数据(1).xlsx —— 曝光侧每日明细，含「二台达人算法场景」「二台达人首页feed场景」两张表'),
         ('数据源2', '报名成功主播_累计数据_0914v2.xlsx —— 直播侧累计数据（15列，含开播天数）'),
         ('坑1 多块堆叠', '两张曝光表各 24 个数据块（08-20~09-12 每天一块），块间空行分隔、表头有 4 种变体（列名带不带「(分)」、曝光节目次数与曝光次数位置互换），必须逐块解析，按首行表头会算错'),
         ('坑2 缺列', '个别块缺「点击视频总播放时长」列，用「曝光人均播放时长(分)」×曝光用户数反推，口径等价'),
         ('坑3 计数失真', '低流量行存在「点击次数 > 曝光次数」失真（实测有曝光27次/点击454次），计数列不可用；',
          ),
         ('应对', '全程改用去重用户级口径（曝光用户数/点击用户数/播放用户数），各块内部自洽（点击用户≤曝光用户）'),
         ('坑4 噪音日', '单日曝光用户<200 的极小流量日会算出「秒/曝光 2577」这类荒诞值，已剔除，不计入有效曝光日与日中位数'),
         ('坑5 异常曝光', '「异常曝光case（标红）」是直播间曝光口径，与本表推荐曝光不是同一分母，不能直接相除；本分析按「日期×主播」整日剔除'),
         ('指标口径', 'CTR(曝光用户)=Σ点击用户÷Σ曝光用户；秒/曝光=Σ观看时长(分)×60÷Σ曝光用户；观看分钟/播放用户=Σ观看时长÷Σ播放用户；推荐转化率按曝光用户加权；日均曝光用户=净曝光用户÷有效曝光日'),
         ('准入闸门', '定级门槛：有效曝光日≥8 且 净曝光用户≥5万 且 直播场次≥5；命中「异常日占比>40%」或「单日曝光集中度>70%」→ 数据存疑不参评；样本底线：有效曝光日≥5、净曝光用户≥3万、场次≥3，低于此归「样本不足」'),
         ('打分权重', '综合分=规模20%+效率25%+深度35%+沉淀20%，各维度取参评池内百分位'),
         ('分层规则', '① 效率≥55且深度≥55 但未过定级门槛 → T 质量达标·待给曝光；② 过门槛且日均曝光≥1万且质优 → A 加推主力；③ 过门槛但效率与深度双低(<45) → C 暂缓投入；④ 过门槛其余 → B 观察优化；⑤ 不过样本底线但过样本底线不满 → P 样本偏薄')]
for r in notes:
    w6.append(list(r))
for c in w6[1]:
    c.font = HF; c.fill = HB; c.border = BD
w6.column_dimensions['A'].width = 16
w6.column_dimensions['B'].width = 130
for row in w6.iter_rows(min_row=2):
    row[0].font = Font(bold=True)
    for c in row:
        c.border = BD
    row[1].alignment = Alignment(wrap_text=True, vertical='top')
wb.save(OUT)
print('\n已输出:', OUT)
