# 图表化规范（charts）

> 用户的明确偏好：**数据向的内容用图表，不要堆表格**。保留在文档里的表只应有定性信息（目标达成、分层名单、机制措施、结论对照）。

## 1. 环境准备（本机一次性）

本机没有全局 matplotlib，装进隔离 venv（无需 sudo）：

```bash
/Users/lutao/.codex/workbuddy-runtime/binaries/python/envs/default/bin/pip install matplotlib -q
/Users/lutao/.codex/workbuddy-runtime/binaries/python/envs/default/bin/python -c "import matplotlib; print(matplotlib.__version__)"
```

中文字体（macOS）：

```python
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ['PingFang SC', 'Hiragino Sans GB', 'Arial Unicode MS', 'STHeiti']:
    try:
        font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams['font.sans-serif'] = [f]; break
    except Exception: pass
plt.rcParams['axes.unicode_minus'] = False
```

> 提示：PingFang SC 没有 bold 字重，会打印 `Failed to find font weight bold ... now using 600`，**属于正常警告，不影响出图**。

## 2. 视觉规范（浅色主题，与文档一致）

| 元素 | 取值 |
|-|-|
| 主色（正向/重点） | `#4E6EF2`，深阶 `#2743B8` |
| 次级/对照 | `#B9C6F7`（浅蓝） |
| 强调/增长 | `#FF7D3B`（橙） |
| 警示/下跌 | `#E64A3B` |
| 中性文字 | 标题 `#111827`、正文 `#374151`、弱 `#8A94A6` |
| 背景 | `#FFFFFF`，去掉 top/right 边框，左/下边框 `#D9DEE7` |
| 图幅 | 宽度 8–11 英寸，`dpi=150`，`bbox_inches='tight'` |
| 尺寸 | 单栏图 700px 宽插入文档（`--width 700`） |

**注意**：图表是图片插入文档，**所有中文、数字都要在图内写清楚**（标题、图例、数值标签），不要依赖正文解释。

## 3. 六张标准图（按需取用）

| # | 图 | 类型 | 表达什么 |
|-|-|-|-|
| 1 | 报名→开播漏斗 | 横向条 + 转化率标注 | 报名/审核/开播/完成四层流失 |
| 2 | 消费转化漏斗 | 横向条（次数口径） | 曝光→点击→播放→互动，标出最大漏水点 |
| 3 | 逐日走势 | 柱（场次）+ 折线（场均 ACU）双轴 | 冷启动期与放量分界 |
| 4 | TOP10 主播 | 横向条形 + ACU 标注 | 头部长尾结构，颜色区分 ACU 是否达标 |
| 5 | 代表主播前后段对比 | 分组柱 | 高成长 vs 回落，一眼看出调优效果 |
| 6 | 等级分层构成 | 环形图 | A/B+/B/C 人数结构 |

模板脚本见 `scripts/make_charts.py`（含全部 6 张图的实现，改数据源即可复用）。

## 4. 数据文件约定

绘图脚本读取同目录 JSON，避免重复解析：

| 文件 | 内容 | 生成方式 |
|-|-|-|
| `trend.json` | `[{date:"8.20", s:11, acu:3.7}, ...]` | 由解析脚本导出（见 `data-pipeline.md` §5.2） |
| `anchor_compare.json` | `[{nm, s, on, pl, acu, inter, fans, acu1, acu2, pl1, pl2, s1, s2}, ...]` | 由解析脚本导出（§5.3） |
| 其余常量 | 漏斗、总量、分层人数 | 直接写在脚本顶部常量区，**每次复核后再改** |

## 5. 出图后必做

1. **肉眼看图**：用 Read 打开 PNG 确认中文不乱码、数值标签没被裁掉、图例不压数据。
2. **数字复核**：图上的数字与源表复算一致（尤其比率类，写之前先看分子分母）。
3. **重跑友好**：脚本顶部集中放常量，源数据换了只改常量或换 JSON，不要改绘图逻辑。
