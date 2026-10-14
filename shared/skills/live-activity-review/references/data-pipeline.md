# 数据拉取与解析（data-pipeline）

## 1. 拉取全部落盘，不要在上下文里堆全表

```bash
# 工作簿结构：先看有哪些子表（sheet_id / title / row_count）
lark-cli sheets +workbook-info --as user --url "<表URL>"

# 小表（<300 行）直接读
lark-cli sheets +csv-get --as user --url "<表URL>" --sheet-id "<id>" --range "A1:V200" > raw.json

# 大表（场次明细，常见 700+ 行）直接落盘
lark-cli sheets +csv-get --as user --url "<表URL>" --sheet-id "<id>" --range "A1:AT799" --output-path livedata_raw.json
```

**两种返回结构的差异（必记）**：

| 调用方式 | JSON 顶层 |
|-|-|
| `--output-path x.json` | 直接是 `{actual_range, annotated_csv, ...}` |
| stdout 重定向 `> x.json` | `{ok, identity, data:{actual_range, annotated_csv, ...}}` |

统一用这种写法兜住两种：

```python
d = json.load(open('livedata_raw.json'))
payload = d.get('data', d)
csv_text = payload['annotated_csv']
```

## 2. 解析 annotated_csv（三个必踩的坑）

```python
import json, csv, re

d = json.load(open('livedata_raw.json'))
payload = d.get('data', d)
parts = [p for p in re.split(r'(?m)^\[row=\d+\] ', payload['annotated_csv']) if p.strip()]
rows = [next(csv.reader([p])) for p in parts]   # rows[0] = 表格第 1 行
header = rows[1]                                 # 表头通常在第 2 行（第 1 行常是分组标题）
data = rows[2:]
```

- **坑 1：引号字段内含换行** → 不能按物理行 `split('\n')`；必须按 `[row=N]` 前缀切逻辑行（上面的写法）。
- **坑 2：日期列常是 8 位数字**（`20260820`）→ 必须按 8 位切年月日，否则前后半程对比全错：

```python
def dkey(x):
    m = re.findall(r'\d+', str(x))
    if not m: return None
    if len(m[0]) == 8: return (int(m[0][:4]), int(m[0][4:6]), int(m[0][6:8]))
    return tuple(int(v) for v in m[:3])
```

- **坑 3：列位必须逐列对齐表头**，不要按「表头占 1 行所以数据从第 2 行」心算。用表头名字取列号，或先打印 `list(enumerate(header))` 确认。

## 3. 过滤空行（v1.1 血泪教训）

源表尾部常有大量空行（如 797 行里只有 668 行有 ID）。**所有统计的分母都必须先过滤掉空行**：

```python
data = [r for r in rows[2:] if len(r) > 20 and r[4].strip()]   # r[4] = 创作者ID
```

> 前车之鉴：某次复盘分母直接用了全部行数，算出「有效率 66.2%」，正确值是 `528/668 = 79.0%`。**任何比率在写进文档前，先输出 `分子/分母` 两个原始值复核。**

## 4. 数值解析与去重

```python
def f(v):
    try: return float(str(v).replace(',', '').strip())
    except: return 0.0
```

- 检查重复场次：`Counter((r[ID列], r[开始时间列]))`，重复的单独列出并在文档注明（通常源表本身就有，不必强行去重，但要知道有）。
- 昵称/ID 组合作为主播主键（同一 ID 可能改名）。

## 5. 指标算法（场次明细 → 各层聚合）

### 5.1 大盘总量（一次性）

```python
S = lambda i: sum(f(r[i]) for r in data)
场次 = len(data)
有效场次 = sum(1 for r in data if f(r[开播时长列]) >= 2)   # 阈值以方案为准，常见 120 分钟
有效率 = 有效场次 / 场次
```

### 5.2 逐日走势（用于冷启动论证）

```python
from collections import defaultdict
daily = defaultdict(lambda: dict(s=0, pl=0.0, acu=[]))
for r in data:
    k = dkey(r[日期列])
    if not k: continue
    daily[k]['s'] += 1
    daily[k]['pl'] += f(r[播放时长列])
    daily[k]['acu'].append(f(r[ACU列]))
trend = [dict(date=f'{k[1]}.{k[2]}', s=v['s'],
              acu=round(sum(v['acu'])/len(v['acu']), 1)) for k, v in sorted(daily.items())]
```

### 5.3 主播个体 + 前段/后段对比

```python
mid = (2026, 9, 4)   # 活动中点，按实际周期定
def half(date):
    k = dkey(date)
    return 1 if k and k <= mid else 2
```

对每位主播聚合：场次、有效场次、开播 h、播放 h、场均 ACU、互动次数、互动用户、关注数，再算 `acu1/acu2`、`pl1/pl2`、`s1/s2`，按播放时长降序。

### 5.4 集中度（头部依赖）

```python
tot = sum(x['pl'] for x in anchor_list)
top5  = sum(x['pl'] for x in anchor_list[:5])  / tot
top10 = sum(x['pl'] for x in anchor_list[:10]) / tot
```

### 5.5 效率与异常

| 指标 | 算法 | 说明用途 |
|-|-|-|
| 内容效率 | 播放 h ÷ 开播 h | 同样时长谁更留人 |
| 人均观看 | 播放时长 ÷ 播放用户数 | 流量质量，配合曝光涨幅一起看 |
| 互动渗透 | 互动用户 ÷ 播放用户 | 人数口径，能识破「少数人高频互动」 |
| 互动强度 | 互动次数 ÷ 播放次数 | 次数口径，与平台口径对齐 |
| 多开嫌疑 | 场次多但有效场次少、互动占比极低 | 结合运营评价人工确认 |

## 6. 截图（单元格嵌入图片）提取

`+csv-get` **读不到**嵌入图片（返回空），必须用 `+cells-get` 取 `rich_text[].image_token`：

```bash
lark-cli sheets +cells-get --as user --url "<表URL>" --sheet-id "<id>" --range "C3:C799" \
  --include value --output-path imgs.json
```

```python
rng = json.load(open('imgs.json'))['data']['ranges'][0]
row_anchor = {}                       # 行号 → 主播名（从同一份 csv-get 解析结果里取）
for ri, cells in zip(rng['row_indices'], rng['cells']):
    for seg in (cells[0].get('rich_text') or []):
        if seg.get('type') == 'embed-image':
            token = seg['image_token']
```

下载（文件名不带扩展名也可以）：

```bash
lark-cli docs +media-download --as user --token "<image_token>" --output shots/<主播名>
```

图片放入草稿工作区 `shots/`，供文档内引用。
