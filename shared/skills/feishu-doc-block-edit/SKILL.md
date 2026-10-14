---
name: feishu-doc-block-edit
description: 用 lark-cli 对飞书云文档做「块级」结构化编辑：抓取带块 ID 的结构、按范围删块、把表格/图片移动到指定位置、插入新章节、替换整表、改标题编号、去时间/去敏感词等定点改写。适合「文档结构乱、章节顺序不对、图要贴到对应段落、大纲编号跳号、表要加一行、某段措辞要统一改」这类重排重建任务。触发词：飞书文档 结构调整、块 移动/删除、大纲 编号、章节 顺序、把图放到对应 阶段、表格加一行、替换整表。agent_created: true
version: 1.0
updated: 2026-09-29
---

# 飞书文档块级编辑（lark-cli docs +update / +fetch）

> 适用场景：**文档结构重建**——删章节、移块、插图、改编号、加表行。
> 不适用：纯写作（那用 lark-doc 的写作流），也不适用飞书项目/Meegle（另一个 CLI）。

## 0. 铁律

1. **先抓结构，再动手。** 每次改之前先 `+fetch --detail with-ids`，改完再抓一次核对。
2. **命令是 `+fetch`，不是 `+read`**（`+read` 会报 `unknown subcommand`）。
3. **块 ID 只在 `--detail with-ids` 输出里才有**；默认输出没有 id 属性。
4. **改完结构后所有块 ID 不变**（只有被删/被移动的块变化），但**顺序变了就别复用上次的"第 N 块"**，一律用 id。
5. **不要用管道直接喂 python**（曾触发 `Could not identify command root to obtain permission from user.`）。先重定向到文件，再解析。

## 1. 抓结构（带 ID）

```bash
lark-cli docs +fetch --doc <docToken> --detail with-ids > /tmp/doc.xml
```

解析（XML 有多个根节点，必须包一层 `<root>`；文本要 `itertext()`，否则 `<b>` 里的字抓不到）：

```python
import json, xml.etree.ElementTree as ET
data = json.load(open('/tmp/doc.xml'))
content = data['data']['document']['content']
rev = data['data']['document']['revision_id']
root = ET.fromstring(f'<root>{content}</root>')
for i, c in enumerate(root, 1):
    t = ''.join(c.itertext()).strip()          # 关键：itertext 而非 c.text
    print(f'{i:3d} {c.tag:8s} id={c.get("id","")} {t[:70]}')
```

## 2. 常用命令矩阵

| 目的 | 命令 | 关键参数 |
|------|------|----------|
| 删单个块 | `block_delete` | `--block-id X` |
| **按范围删连续块** | `block_delete` | `--start-block-id X --end-block-id Y`（含首含尾，比逐块删快得多） |
| 移动块（表格/图片）到某块之后 | `block_move_after` | `--block-id <锚点> --src-block-ids a,b`（多个源按顺序落到锚点后） |
| 在某块后插入内容 | `block_insert_after` | `--block-id <锚点> --content '<p>..</p>'` 或 `--content @/tmp/x.xml` |
| 替换整块（图 alt、整张表） | `block_replace` | `--block-id X --content @/tmp/x.xml` |
| 纯文本定点替换 | `str_replace` | `--pattern "旧" --content "新"` |

全部走 `lark-cli docs +update --doc <token> --command <cmd> ...`。

## 3. 各操作要点与坑

### 3.1 按范围删（省事首选）

一段章节（标题+正文+表）连续时，直接首尾 ID 一次删掉：

```bash
lark-cli docs +update --doc $DOC --command block_delete \
  --start-block-id <首个块> --end-block-id <末个块>
```

### 3.2 移动表格/图片（原型图贴到对应段落）

```bash
# 多个源会按给定顺序依次落在锚点块之后
lark-cli docs +update --doc $DOC --command block_move_after \
  --block-id <目标内容表id> --src-block-ids <图1id>,<图2id>
```

坑：**锚点必须已经存在于正文**，不能拿另一个"待移动块"当锚点。

### 3.3 插入新章节（标题+段落+表格一次成型）

多块内容写进文件，用 `@file`：

```bash
cat > /tmp/sec.xml << 'EOF'
<h3>2.2 章节名</h3><p>正文…</p><table><colgroup><col width="150"/><col width="150"/></colgroup><thead><tr><th background-color="rgba(245,246,247,0.9)" vertical-align="top"><p>列1</p></th><th background-color="rgba(245,246,247,0.9)" vertical-align="top"><p>列2</p></th></tr></thead><tbody><tr><td vertical-align="top"><p>a</p></td><td vertical-align="top"><p>b</p></td></tr></tbody></table><p>结尾…</p>
EOF
lark-cli docs +update --doc $DOC --command block_insert_after --block-id <锚点> --content @/tmp/sec.xml
```

表头单元格建议带 `background-color="rgba(245,246,247,0.9)"` + `vertical-align="top"`，与文档既有表风格一致。
表格列宽用 `<colgroup><col width="N"/>`。

### 3.4 给表格加一行（没有行级插入命令）

做法：**把整张表 XML 抓出来 → 手工加 `<tr>` → `block_replace` 整表回写**。

```python
import re
m = re.search(r'<table id="'+tid+r'".*?</table>', content, re.DOTALL)
table = m.group(0)   # 复制出来，加行后写到文件
```

注意：加行时**列数必须与表头一致**（有的表被改成了 3 列、有的 4 列，不要照老版本抄）。

### 3.5 改标题编号 / 段落措辞 / checkbox 文案

用 `str_replace`，但要注意 **替换顺序**：

- **重排编号必须从大到小改**（2.5→2.6 先做，再 2.4→2.5…），否则会连环撞车或误替换。
- pattern 里带上标题原文（如 `"5.1 第一阶段：xxx"`），避免误伤表格单元格里的同名词。
- 若同名文本在别处也出现且不该改，把 pattern 写长、或直接改块（`block_replace`）。
- checkbox 的文案就是元素文本，`str_replace` 直接可用（去掉「——截止：xxx」这类缀词很方便）。

### 3.6 `str_replace` 改不了的东西

- **图片 alt / 任何 XML 属性**：`str_replace` 会返回 `result: failed`（"produced no document changes"）。
  → 改用 `block_replace` 重写整个 `<img>`：需要带上原 `src`（token）、`mime`、`scale`，否则图会丢。

### 3.7 让"我奥篮球"这类第三方名字出现在 PRD 里

涛哥的偏好：**对外方案不要点竞品名字**，改成"参考站外专业数据统计和直播体系"这类中性表述。
写正文时默认走中性口径。

## 4. 验收清单

1. `+fetch --detail with-ids` 打印出 h2/h3 大纲，确认编号连续、不跳号。
2. 确认图片表都贴在对应章节内容之后（不是全堆在文末）。
3. 全文搜一遍残留项：`截止`、`第.*周`、`Sprint`、已删章节名（如"发布计划"）的交叉引用。
4. 表格替换后抽查行数/列数是否与预期一致。

## 5. 常见报错

| 报错 | 原因 | 处理 |
|------|------|------|
| `unknown subcommand "+read"` | 命令名错 | 用 `+fetch` |
| `Could not identify command root...` | 把 lark-cli 输出接管道给 python | 先 `> /tmp/x` 再解析 |
| `degrade_code=1011, produced no document changes` | str_replace pattern 未命中（或改的是属性） | 核对原文；属性改用 block_replace |
| `junk after document element` / `NameError: true` | XML 多根 / 直接把 JSON 当 Python 解析 | 包 `<root>`；用 `json.load()` |
| 顶部 proxy WARN | 环境有代理 | 无害，可忽略或设 `LARK_CLI_NO_PROXY=1` |
