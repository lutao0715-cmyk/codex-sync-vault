---
name: bilibili-documentary-miner
description: 系统性挖掘B站上符合条件的国外户外纪录片——搜索、验证链接有效性、检查中文字幕、剔除系列剧集、分类归档。适用于需要从B站批量采集特定条件的纪录片资源并生成结构化清单的场景。
agent_created: true
---

# Bilibili Documentary Miner

## Overview

从B站系统性地挖掘国外户外纪录片清单。核心能力：多关键词搜索 → 过滤（中文字幕/时长/单集成片/外国影片）→ 链接验证 → 相关推荐扩展 → 多P甄别 → CC字幕确认 → 9品类分类 → 最终文档生成。

## 触发条件

当用户需要以下任一场景时使用本skill：
- "整理B站XX纪录片清单"
- "在B站上找XX主题的纪录片"
- "搜索B站上有中文字幕的国外纪录片"
- "从B站批量采集户外运动纪录片"
- 任何涉及B站视频搜索、筛选、验证、分类的任务

## 工作流总览

```
多关键词搜索 → 标题过滤 → view API验证 → 链接有效性检查 → 多P甄别 → CC字幕确认 → 相关推荐扩展 → 品类分类 → 最终组装
```

## 核心API与工具

### 1. B站搜索API（推荐）
```
GET https://api.bilibili.com/x/web-interface/search/all/v2?keyword={kw}&page={N}
```
- 返回 `data.result` 数组，其中 `result_type='video'` 的元素下 `data` 为视频列表
- 每条视频字段：`bvid`(BV号), `title`(标题), `duration`(MM:SS字符串), `play`(播放量), `author`, `arcurl`(链接)
- **必须带Headers**：User-Agent(Mozilla/5.0 Mac), Referer(https://www.bilibili.com/), Cookie(含随机buvid3)
- **每条请求重新生成随机buvid3**，否则可能被风控

### 2. 相关推荐API（同类扩展最高效）
```
GET https://api.bilibili.com/x/web-interface/archive/related?bvid={bv}
```
- 返回同作者/同类型推荐视频列表
- **duration单位为秒**（不是MM:SS！）
- 可递归扩展（深度1-2层），收益趋零即止损

### 3. view API（验证链接有效性）
```
GET https://api.bilibili.com/x/web-interface/view?bvid={bv}
```
- `code == 0` 表示链接有效
- `data.duration`：总时长（秒）
- `data.pages`：多P信息（P数、每P标题、时长）
- `data.stat.view`：播放量
- `data.title`：真实标题

### 4. player API（CC字幕检测）
```
GET https://api.bilibili.com/x/web-interface/player/v2?bvid={bv}&cid={cid}
```
- `data.subtitle.subtitles[]` 中 `lan` 以 `'zh'` 开头表示有中文CC字幕
- 先用view API获取cid，再调此API
- **无标题中字标记的条目，可用此法兜底确认**

## 过滤规则

### 中文字幕判定（标题关键词）
```python
SUB_POS = ['中字', '中英', '双语', '国语', '国配', '中文', '熟肉', '简中', '繁中', '中文CC']
SUB_NEG = ['无字', '英字', '生肉', '无中字', '英文字幕', '日语', '韩语', '法语', '德语', '西班牙语', '俄语']
# 先检查SUB_NEG（排除），再检查SUB_POS（确认）
```

### 系列剧集检测
```python
SERIES_PAT = re.compile(
    r'第[一二三四五六七八九十\d]+[季集]|'   # 第X季/第X集
    r'S\d{1,2}E\d{1,2}|EP\d{1,3}|'          # S01E01 / EP01
    r'[Pp]\d{1,2}\s*(?:/|$)|'                # P1/P2
    r'全\d{1,3}[集话]|合集|'                  # 全集/合集
    r'[上中下]部|'                             # 上部/中部/下部
    r'\d{1,2}/\d{1,2}\s*(?:[集话]|$)'         # 1/4集 / 2/4
)
```

### 外国影片检测
```python
FOREIGN_PAT = re.compile(r'[A-Za-z]{3,}')  # 标题含3+连续拉丁字母
```

### 9品类分类
按优先级顺序匹配关键词，首次命中即分类：
1. 陆地/山地（徒步/登山/珠峰/喜马拉雅/Mountain/Trail/Expedition/国家公园等）
2. 骑行/轮式（骑行/Bike/Motorcycle/滑板/Skateboard/Unbound等）
3. 攀岩/崖壁/洞穴（攀岩/Climb/Free Solo/Boulder/洞穴救援等）
4. 冬季山地（滑雪/Ski/Snowboard/雪崩/Torn/冰川/南极等）
5. 水上（冲浪/Surf/Kayak/帆船/Kon-Tiki/漂流等）
6. 钓鱼（钓鱼/Fish/Fishing/Angler等）
7. 水下（潜水/Shark/Whale/鲨鱼/鲸/海洋/深海等）
8. 空中/高空（跳伞/Skydive/Wingsuit/翼装/滑翔伞/FlowState等）
9. 综合（以上均不匹配的落入此类）

## 多P甄别规则（重要！）

**多P ≠ 剧集**。B站上很多单片纪录片被分段上传，需甄别：

**保留为单片的情况**：
- 正片+预告（如"正片"/"Trailer"/"预告"分P）
- 连续分段上传（如Kon-Tiki分成Part1-4连续分段，仍是单片）
- 正片+花絮/访谈

**剔除为剧集的情况**：
- "S01E01" / "第1集" / "第1季"等明确剧集编号
- 各P标题独立成篇（如"大堡礁"P1、P2、P3各讲不同内容）
- 原片就是系列（如BBC蓝色星球系列）

## 推荐挖掘策略

### 第1轮：关键词搜索（最直接）
- 用中英文混合关键词：户外纪录片/Outdoor Documentary/户外运动+中字等
- 每页约20条，翻页到第2页收益已明显下降

### 第2轮：知名纪录片面名硬搜
- 准备100部左右的知名片单，逐条搜B站
- **注意：错误匹配率极高**（Endless Summer→演唱会、Happy People→游戏视频）
- 结果需人工复核

### 第3轮：相关推荐扩展（最高效）
- 用已验证的种子BV号，通过related API扩展
- 可递归1-2层
- 同UP主多纪录片可顺藤摸瓜

### 第4轮：UP主定向
- 找到高频纪录片UP主（如"夏末TnT-纪实影像录"、"亦深fjminxi"等）
- 浏览其投稿列表
- **收益通常趋零，前几轮无果即可止损**

### 停止条件
当连续N轮挖掘新增收益趋零（如每轮<5条可用），即可停止——说明平台资源池已基本挖尽。

## 技术坑与注意事项

1. **heredoc写长Python脚本必截断** → 一律用Write工具写独立.py文件再执行
2. **B站API风控** → 每条请求用随机buvid3；遇返回空结果重试2次
3. **同片多版本** → 按播放量择优保留（如Life Cycles有4个版本、逐冰之旅3个版本）
4. **verify_known式硬搜需人工复核** → 演唱会/游戏/综艺乱入不可避免
5. **野性澳洲等"野生区分P"** → 需逐条检查pages，确认是否为真剧集
6. **钓鱼/空中品类在B站极度稀缺** → 是平台生态客观现状，非策略问题
7. **约200部目标不现实** → B站符合"国外+单集+30min+确认中字+户外"全部条件的资源池约110部

## 参考脚本

本skill附带了 `scripts/search_bilibili.py`，支持以下命令：
- `search <keyword> [--page N]` — 搜索
- `verify <bvid> [bvid2 ...]` — 验证链接
- `related <bvid> [--depth N]` — 相关推荐扩展
- `cc-check <bvid> [bvid2 ...]` — 检查CC字幕
- `multip-check <bvid> [bvid2 ...]` — 检查多P
- `filter <json> [--min-dur 30] [--require-sub] [--standalone-only]` — 过滤JSON

使用方式：`python3 scripts/search_bilibili.py <command> <args>`

## 交付格式

最终输出 Word 文档 (.docx)，包含：
- 筛选标准说明
- 品类分布概览表
- 9大品类明细：序号/片名/外文名/国家/年份/时长/字幕/播放量/可点击B站链接
- 说明文档（品类缺口、放宽条件建议）