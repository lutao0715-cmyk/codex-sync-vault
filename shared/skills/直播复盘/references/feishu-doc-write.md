# 飞书文档写入（feishu-doc-write）

## 1. 创建（走 lark-doc 创建工作流，不要自己拼 markdown）

```bash
# 1) 初始化草稿工作区
lark-cli docs +script --command init-draft --presentation-decision '{
  "audience":"<谁看>","reader_task":"<看完要做什么决策>",
  "genre_contract":"report.data_report","adapter":null,"presentation_mode":"rich",
  "visual_plan":{"reason":"<为什么需要图>","blocks":[{"type":"img","min_count":10,"purpose":"主播直播截图"}]}
}' --format json
# → 产出 <cwd>/<work_dir>/draft.xml，把截图 cp -r 到 <work_dir>/shots/

# 2) 校验结构
lark-cli docs +script --command parse --content "@./<work_dir>/draft.xml" --format json   # 看 assessment.status

# 3) 创建文档
lark-cli docs +create --as user --doc-format xml --content "@./<work_dir>/draft.xml" --format json
```

## 2. 文档结构模板（经验证好用）

1. 一句话结论 `callout`（最亮眼的数字 + 最刺眼的判断）
2. 整体情况：漏斗表 / 目标达成对照表 / 总量表 / 走势表 / 消费漏斗表 + 口径与数据质量 `callout`
3. 主播个体数据变化：TOP 表 + 三类轨迹（含前后半程对比）+ 效率异常
4. 内容分层复盘：4 层，每层「数据 + 运营评价原文 + 截图 grid」
5. 做得好 / 做得不好（各 4–5 条，每条带证据）+ 主播层面的优点与问题
6. 其他值得复盘的点（规则口径、流量激励效果、人力成本、冷启动期）
7. 下一期怎么做：分层名单 + 机制措施 + 验证门（量化阈值）

## 3. 增量编辑（用户会反复要求改，不要整篇重建）

> 原则：`overwrite` 会丢图片和评论，**非必要不用**。

```bash
# 定位：先看大纲，再按节取带 id 的内容
lark-cli docs +fetch --as user --doc "<id>" --scope outline --max-depth 2 --detail with-ids
lark-cli docs +fetch --as user --doc "<id>" --scope section --start-block-id "<标题id>" --detail with-ids
lark-cli docs +fetch --as user --doc "<id>" --scope keyword --keyword "66.2|7.3" --context-before 1 --context-after 1

# 改文字（含表格单元格内的文字）
lark-cli docs +update --as user --doc "<id>" --command str_replace --pattern "旧文本" --content "新文本"

# 插块（标题后插段落 / callout / 表格）
lark-cli docs +update --as user --doc "<id>" --command block_insert_after --block-id "<锚点id>" --content '<p>新段落</p>'

# 替换 / 删除
lark-cli docs +update --as user --doc "<id>" --command block_replace --block-id "<id>" --content '<p>新内容</p>'
lark-cli docs +update --as user --doc "<id>" --command block_delete --block-id "<id>"
```

- 每次写操作后 **block id 都可能变**，下一轮操作前重新 fetch，不要复用旧 id。
- 一次 `str_replace` 只改一处文本；多处相同文本会被要求唯一，改用更大上下文。
- 行内换行用 `<br/>`；文本里的 `<` `>` `&` 要转义。

## 4. 图片插入与定位（图要在指定小节，不能只在文末）

> **优先用 `block_insert_after` 直接引用本地图片**，比 `media-insert` + `move` 少两步，且能精确落位：
>
> ```bash
> lark-cli docs +update --as user --doc "<id>" --command block_insert_after \
>   --block-id "<锚点id>" --content '<img path="@/abs/path/chart.png"/>'
> ```
>
> `<img path="@绝对或相对路径"/>` 会由服务端自动上传。`media-insert` 只在「图已经在剪切板」时更省事。

`+media-insert` 只能插到**文末**，需要批量插图的场景用下面三步：

```bash
# 1) 上传到文末，拿到 block_id
IMG=$(lark-cli docs +media-insert --as user --doc "<id>" --file chart1.png \
      --width 700 --align center --caption "图1 报名→开播漏斗" 2>/dev/null)
BID=$(echo "$IMG" | python3 -c "import sys,json;print(json.load(sys.stdin)['data']['block_id'])")

# 2) 移动到目标位置（锚点通常是小节标题 block）
lark-cli docs +update --as user --doc "<id>" --command block_move_after --block-id "<标题id>" --src-block-ids "$BID"

# 3) 删掉被图取代的旧数据表
lark-cli docs +update --as user --doc "<id>" --command block_delete --block-id "<表id>"
```

**已存在的图要挪位就用 `block_move_after`（保 file_token，不必重新上传）**，按目标顺序逐张移动：把第 1 张移到表格后，第 2 张移到第 1 张后……连成一条链。若某张已在目标位，「no document changes」是正常提示，不是失败。

**`block_replace` 区间的坑**：`--start-block-id` 必须在 `--end-block-id` **之前**，否则报 `Invalid block range`。取 id 时要按**块的开标签**定位（`<h2 id="...">标题文字`），不要在「标题文字」之后找最近的 `<h2`——会拿到下一个标题，顺序反过来。

## 4b. 分层名单版式（主播等级分层页的固定结构）

名单页必须「一层一小节」，图和表都挂在层下面，不能裸堆在总表后：

```
h2（二）四层名单：谁值得继续投
  p    分层依据说明（数据指标 + 运营评价双向交叉；每层附截图）
  h3   第一层 · 重点续约（N 人）   → 数据与运营评价双优的头部，建议优先续约
  p    本层特征 / 续约动作（1 句，可带关键数字）
  table 主播 | 有效场次 | 播放时长(h) | 场均ACU | 关注 | 运营评价摘录
  img   该层代表性截图 1–4 张（caption 写「场次 / ACU / 前后段变化」）
  h3   第二层 · 加流量试探（N 人） …
```

- **截图必须 grid 横排并排，不能竖排堆叠**（用户明确反馈「竖版太乱，要和昨天一样横版」）：`<grid><column width-ratio="0.333333"><img path="@..." caption="..."/></column>×3</grid>`。3 张一行用 3 列（0.333333），2 张一行用 2 列（0.5）；4 张拆成两个 2 列 grid；末层单图可不放 grid。
- 每张截图只能归属于它所在的层，数量按层的重要性分配（头部队列 3–4 张，末层 1 张）。
- 「运营评价摘录」用运营原话（加引号），不要改写成自己的话。
- 末层要写清处置动作（不再邀请 / 名额释放给哪一层）。

## 4c. 正式汇报语气（给老板看 vs 给同事解释）

交付物是**向上汇报文档**，不是工作过程说明。以下内容一律不写进文档：

| 不该出现 | 例子 | 该怎么做 |
|-|-|-|
| 版本演进史 | 「本版与此前两版的口径差异，请先读」 | 删；只呈现当前结论 |
| 口径自证 | 「此前合格率 54.5% 严重失真，不算数」 | 删；直接写现在的口径与数值 |
| 辩解口吻 | 「本批主播不该背这个锅」 | 改成中性陈述或正向结论 |
| 复盘方法论 | 「复盘口径要三审」 | 删或写进内部总结，不进汇报 |
| 解释某问题是我怎么查的 | 「必须单独说明的 X 问题：…」 长段推导 | 压缩成一句事实 + 影响，或只留结论 |

保留：中性的「数据口径备注」（定义主口径 / 对照口径 / 数据来源），放在文末。
交付前 grep 检查：`本版` `首版` `此前` `修正` `剔除后` `险些` `不该背` `请先读` 应全部为 0。


## 5. 样式语法（XML）

| 需求 | 写法 |
|-|-|
| 高亮块 / 重点段 | `<callout emoji="🎯" background-color="light-blue" border-color="blue"><p>…</p><p>…</p></callout>` |
| 高亮块限制 | 子块只支持 `p`/`ol`/`ul`/`checkbox`/行内标签；**不能放 table/img/pre** |
| 背景色（高亮块） | `gray` / `light-{red,orange,yellow,green,blue,purple}` / `medium-{色相}`（强提醒才用 medium） |
| 表头底色 | `<th background-color="light-gray">` |
| 两栏 | `<grid><column width-ratio="0.5"><p>左</p></column><column width-ratio="0.5"><p>右</p></column></grid>` |
| 图片 | `<img path="@./<work_dir>/shots/xxx.jpg"/>` 或 `href="https://..."` |
| 无原生加粗标签 | 强调靠 `callout`、`light-*` 底色、`【】`「」等符号；彩色文字只强调短语 |

## 6. 交付校验

```bash
lark-cli docs +fetch --as user --doc "<id>" --doc-format markdown   # 数图片、数剩余表格、查口径残留
lark-cli docs +fetch --as user --doc "<id>" --doc-format xml        # 数 <img> 条目（服务端可能静默丢图）
```

- 图片数 = 预期张数（截图 + 图表），少一张就去查 caption/文件名是否有特殊字符。
- 搜索被修正过的错误口径关键词（如旧的错误百分比），确认残留为 0。
