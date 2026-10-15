#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
活动复盘 6 张标准图（浅色主题，中文标注）

前置：
  1) 同目录放 trend.json（parse_table.py --trend 生成）
  2) 同目录放 anchor_compare.json（parse_table.py --anchors 生成）
  3) 顶部「常量区」按本次活动的真实数字改（漏斗 / 总量 / 分层 / 对比主播名单）

运行：
  C:/Users/win/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe make_charts.py
  产出 chart1_funnel.png ... chart6_layer.png
"""
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch
import numpy as np

# ---------------- 常量区：每次复盘改这里 ----------------
FUNNEL = [('报名提交', 84), ('审核通过', 42), ('实际开播', 39), ('坚持到结束', 31)]  # 人数口径
CONSUME = [('曝光次数', '1136.0 万', '点击率 6.97%'), ('点击次数', '79.2 万', '播放/点击 198%'),
           ('播放次数', '156.9 万', '互动率 55.0%'), ('互动次数', '86.3 万', '涨粉 1907 人')]
LAYERS = [(4, 'A 级 4 人（核心主推）'), (6, 'B+ 级 6 人（潜力培养）'),
          (13, 'B 级 13 人（观察池）'), (8, 'C 级 8 人（淘汰/换内容）')]
COMPARE_PICKS = ['晴晴-啦啦队长', '时不时', '石祈钓鱼', '用户哥（超爱文班亚马）',
                 '小年糕（尼克斯小迷妹）', '乒乓吕教练', '东北乒乓侠', '哇可爱的贤贤^_^']
ACTIVITY_TITLE = '（2026.8.20–9.19）'
# ------------------------------------------------------

for f in ['PingFang SC', 'Hiragino Sans GB', 'Arial Unicode MS', 'STHeiti']:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams['font.sans-serif'] = [f]; break
    except Exception:
        continue
plt.rcParams['axes.unicode_minus'] = False

C_MAIN, C_ORANGE, C_RED, C_GRAY = '#4E6EF2', '#FF7D3B', '#E64A3B', '#8A94A6'
C_DEEP, C_LIGHT, BG = '#2743B8', '#B9C6F7', '#FFFFFF'
TITLE = dict(fontsize=15, fontweight='bold', color='#111827', pad=12, loc='left')


def style(ax):
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    ax.spines['left'].set_color('#D9DEE7'); ax.spines['bottom'].set_color('#D9DEE7')
    ax.tick_params(colors='#4B5563')


def clean(ax):
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])


def chart1():
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150); fig.patch.set_facecolor(BG)
    cols = ['#8FA6F5', '#5B7DF5', '#3D63E8', C_DEEP]
    y = list(range(len(FUNNEL)))[::-1]
    for i, ((name, n), c) in enumerate(zip(FUNNEL, cols)):
        ax.barh(y[i], n, height=0.62, color=c, zorder=3)
        ax.text(n + 1.5, y[i], f'{n} 人', va='center', fontsize=13, fontweight='bold', color='#1F2937')
        if i:
            prev = FUNNEL[i-1][1]
            ax.text(n + 12, y[i], f'较上环节 {n/prev*100:.1f}%', va='center', fontsize=10, color=C_GRAY)
        ax.text(-3.5, y[i], name, va='center', ha='right', fontsize=12, color='#374151')
    ax.set_xlim(0, max(n for _, n in FUNNEL) * 1.45); ax.set_ylim(-0.6, len(FUNNEL) - 0.4)
    clean(ax); ax.set_title(f'报名 → 开播漏斗（人数）{ACTIVITY_TITLE}', **TITLE)
    plt.tight_layout(); plt.savefig('chart1_funnel.png', bbox_inches='tight', facecolor=BG); plt.close()


def chart2():
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150); fig.patch.set_facecolor(BG)
    cols = ['#8FA6F5', '#5B7DF5', '#3D63E8', C_DEEP]
    y = list(range(len(CONSUME)))[::-1]
    widths = [10, 6.97, 13.8, 7.6]   # 视觉宽度（数量级差异大，用配比宽度）
    for i, ((name, val, note), c, w) in enumerate(zip(CONSUME, cols, widths)):
        ax.barh(y[i], w, height=0.62, color=c, zorder=3)
        ax.text(w + 0.2, y[i], f'{name}  {val}', va='center', fontsize=12, fontweight='bold', color='#1F2937')
        ax.text(w + 4.4, y[i], note, va='center', fontsize=10, color=C_GRAY)
    ax.set_xlim(0, 30); ax.set_ylim(-0.6, len(CONSUME) - 0.35)
    clean(ax); ax.set_title('消费转化漏斗（次数口径）', **TITLE)
    plt.tight_layout(); plt.savefig('chart2_convert.png', bbox_inches='tight', facecolor=BG); plt.close()


def chart3():
    trend = json.load(open('trend.json'))
    dates = [t['date'] for t in trend]; ss = [t['s'] for t in trend]; acu = [t['acu'] for t in trend]
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=150); fig.patch.set_facecolor(BG)
    ax.bar(dates, ss, color=C_LIGHT, label='每日场次', zorder=2)
    ax2 = ax.twinx()
    ax2.plot(dates, acu, color=C_ORANGE, marker='o', markersize=4, linewidth=2, label='场均 ACU', zorder=3)
    half = len(dates) // 2
    ax2.axvline(x=half - 0.5, color=C_GRAY, linestyle='--', linewidth=1)
    ax2.text(half - 0.3, max(acu) * 0.86, '下半程放量期', fontsize=10, color='#374151')
    ax.set_xticks(range(len(dates))); ax.set_xticklabels(dates, rotation=60, fontsize=8)
    style(ax); ax2.spines['top'].set_visible(False); ax2.tick_params(colors='#4B5563')
    ax.set_ylabel('场次', fontsize=11); ax2.set_ylabel('场均 ACU', fontsize=11)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper left', frameon=False, fontsize=10)
    ax.set_title(f'逐日开播场次与场均 ACU 走势{ACTIVITY_TITLE}', **TITLE)
    plt.tight_layout(); plt.savefig('chart3_daily.png', bbox_inches='tight', facecolor=BG); plt.close()


def chart4():
    anchors = json.load(open('anchor_compare.json'))[:10]
    names = [a['nm'][:8] for a in anchors]; pls = [a['pl'] for a in anchors]; acus = [a['acu'] for a in anchors]
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=150); fig.patch.set_facecolor(BG)
    y = list(range(len(anchors)))[::-1]
    ax.barh(y, pls, height=0.62, color=[C_MAIN if a >= 25 else C_LIGHT for a in acus], zorder=3)
    for i, (p, a) in enumerate(zip(pls, acus)):
        ax.text(p + max(pls) * 0.01, y[i], f'{p:,.0f} h ｜ ACU {a}', va='center', fontsize=10, color='#1F2937')
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=11)
    ax.set_xlim(0, max(pls) * 1.35); clean(ax)
    ax.legend(handles=[Patch(color=C_MAIN, label='ACU≥25（有效供给）'), Patch(color=C_LIGHT, label='ACU<25')],
              loc='lower right', frameon=False, fontsize=10)
    ax.set_title('TOP10 主播累计播放时长（小时）', **TITLE)
    plt.tight_layout(); plt.savefig('chart4_top10.png', bbox_inches='tight', facecolor=BG); plt.close()


def chart5():
    anchors = {a['nm']: a for a in json.load(open('anchor_compare.json'))}
    picks = [p for p in COMPARE_PICKS if p in anchors]
    n1 = [anchors[p]['acu1'] for p in picks]; n2 = [anchors[p]['acu2'] for p in picks]
    labels = [p[:6] for p in picks]; x = np.arange(len(picks))
    fig, ax = plt.subplots(figsize=(10, 4.6), dpi=150); fig.patch.set_facecolor(BG)
    ax.bar(x - 0.19, n1, width=0.38, color=C_LIGHT, label='前段', zorder=3)
    ax.bar(x + 0.19, n2, width=0.38, color=C_ORANGE, label='后段', zorder=3)
    for i in range(len(picks)):
        ax.text(x[i] - 0.19, n1[i] + 1, f'{n1[i]:.0f}', ha='center', fontsize=9, color='#4B5563')
        ax.text(x[i] + 0.19, n2[i] + 1, f'{n2[i]:.0f}', ha='center', fontsize=9, fontweight='bold', color='#C2410C')
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=10, rotation=15)
    style(ax); ax.set_ylabel('场均 ACU', fontsize=11); ax.legend(frameon=False, fontsize=10)
    ax.set_title('代表主播前段 vs 后段场均 ACU 对比', **TITLE)
    plt.tight_layout(); plt.savefig('chart5_half.png', bbox_inches='tight', facecolor=BG); plt.close()


def chart6():
    sizes = [s for s, _ in LAYERS]; labels = [l for _, l in LAYERS]
    cols = [C_DEEP, '#5B7DF5', '#9FB3F5', '#D9DEE7']
    fig, ax = plt.subplots(figsize=(7, 4.4), dpi=150); fig.patch.set_facecolor(BG)
    w, _ = ax.pie(sizes, colors=cols, startangle=90, counterclock=False,
                  wedgeprops=dict(width=0.42, edgecolor='white'))
    ax.text(0, 0.06, str(sum(sizes)), ha='center', fontsize=26, fontweight='bold', color='#111827')
    ax.text(0, -0.22, '位在播主播', ha='center', fontsize=10, color=C_GRAY)
    ax.legend(w, labels, loc='center left', bbox_to_anchor=(1.02, 0.5), frameon=False, fontsize=11)
    ax.set_title('主播等级分层（运营评估口径）', **TITLE)
    plt.tight_layout(); plt.savefig('chart6_layer.png', bbox_inches='tight', facecolor=BG); plt.close()


if __name__ == '__main__':
    for fn in (chart1, chart2, chart3, chart4, chart5, chart6):
        fn(); print('✓', fn.__name__)
