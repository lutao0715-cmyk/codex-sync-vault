---
name: outdoor-ski-daily-report
description: 生成并校验「滑雪晨报」与「户外运动每日外刊」两份 HTML 日报。当用户说「日报」「今天日报」「出日报」「滑雪日报」「户外日报」「晨报」「再出一期」时触发。核心是数据驱动生成（gen_ski.py / gen_outdoor.py）+ 硬性配额校验（滑雪 27 条 / 6 版块 / 国内恰好 2 条；户外 37 条 / 7 版块 / 国内≤3 条 / 受众加权 8 组达标）+ 跨期去重（补丁式写入 + 6 字 shingle 检测 + 句式模板黑名单）。agent_created: true
---

# 滑雪晨报 / 户外日报 生成与查重

工作目录：`/Users/lutao/WorkBuddy/2026-08-10-16-06-16/`

## 0. 先确认状态（别急着写内容）

```bash
cd /Users/lutao/WorkBuddy/2026-08-10-16-06-16
grep -o '2026年9月[0-9]*日[^<]*' ski-morning-daily.html | head -2
grep -o '2026年9月[0-9]*日[^<]*' outdoor-adventure-daily.html | head -2
```

- 若日期已是今天 → 问用户是否要重做，不要盲目覆盖。
- **自动化任务可能处于 PAUSED**，见 `.workbuddy/automations/` 下两个目录（滑雪 `automation-1786349719094`、户外 `automation-1786350650737`、户外9:30 `automation-1786690476254`）。用户手动说「日报」时两份都要做。

## 1. 硬性规格（不可妥协）

| | 滑雪晨报 | 户外日报 |
|---|---|---|
| 文件 | `ski-morning-daily.html` | `outdoor-adventure-daily.html` |
| 生成器 | `gen_ski.py` | `gen_outdoor.py` |
| 条数 | **27** | **37** |
| 版块 | **6**（热点5/竞技4-5/运动员4/雪场5-6/行业4/装备4） | **7**（5/5/5/7/5/5/5） |
| 国内 | **恰好 2 条**（命中任一即算：境内事件 / 中国运动员 / 中国品牌组织 / 中国资本） | **≤3 条** |
| 地区标签 | `tag-international`=25 / `tag-china`=2 | — |
| 主题 | 深色主题、自包含、顶部 stats-bar | 深色主题、顶部导航、3 列卡片 |

户外另有**受众加权配比**（内置于 `gen_outdoor.py` 顶部）：

```
SPORT_GROUPS / GROUP_TARGET = {"hike":8,"run":6,"ride":6,"ski":5,"water":4,"air":2,"fish":1,"multi":5}
```
运行 `gen_outdoor.py` 会打印「受众加权配比报告」，**偏离超 1 条的组数必须为 0**，否则换题重生成。

> **国内选题常年超额，必须先列候选再排序取舍**（2026-09-24 实测：单期候选 8 条，配额只有 3 条）。取舍口径：优先有国际参与度或明确公共价值的（国际公开赛、国字号赛事、执法/政策通报），纯地方性活动一律让位。
>
> ⚠️ **「在中国境内举办的国际赛事」也计入国内配额**（2026-10-02 踩坑：上海场地世锦赛、成都赛艇公开赛都被计入，加上亚运攀岩双金共 4 条超标）。判定后再数一遍，超了就换掉价值最低的那条，换成同 tag 的国际选题以保住配比不变。

## 2. 生成流程（严禁手写整份 HTML，历史上多次被截断）

### 滑雪晨报

```bash
cp gen_ski.py gen_ski.py.bakMMDD          # 1) 备份（备份即"上一期"的去重基线）
# 2) 写 patch_MMDD.py（见下）
python3 patch_MMDD.py && python3 gen_ski.py
```

`patch_MMDD.py` 骨架（一次完成日期常量 + SECTIONS 整块 + 页脚来源）：

```python
import re, ast
NEW_SECTIONS = '''[
{"name": "🔥 今日热点", "items": [
 {"t": "标题", "p": "正文", "tag": "intl", "src": "来源"},
 ...
]}
]'''

src = open("gen_ski.py", encoding="utf-8").read()
# 1) 三个日期常量
for pat, val in [(r'DATE = "[^"]*"', 'DATE = "2026年9月23日"'),
                 (r'WEEKDAY = "[^"]*"', 'WEEKDAY = "星期三"'),
                 (r'TITLE_DATE = "[^"]*"', 'TITLE_DATE = "2026年9月23日 · 星期三"')]:
    src = re.sub(pat, val, src, count=1)
# 2) SECTIONS 整块（括号配平，跳过字符串内部）
def block_span(s):
    i = s.index("SECTIONS"); j = s.index("[", i); d = 0; in_str = None; p = j
    while p < len(s):
        c = s[p]
        if in_str:
            if c == "\\": p += 2; continue
            if c == in_str: in_str = None
        else:
            if c in "\"'": in_str = c
            elif c == "[": d += 1
            elif c == "]":
                d -= 1
                if d == 0: return j, p + 1
        p += 1
a, b = block_span(src)
src = src[:a] + NEW_SECTIONS.strip() + src[b:]
# 3) 页脚来源
src = re.sub(r'数据来源：[^<]*', '数据来源：xxx 等30+国际媒体', src, count=1)
ast.literal_eval(NEW_SECTIONS)     # 自检
compile(src, "gen_ski.py", "exec") # 自检
open("gen_ski.py", "w", encoding="utf-8").write(src)
```

**引号铁律**：`"t"` / `"p"` 值里**只能用中文「」**，出现 ASCII 双引号会与定界符冲突 → SyntaxError。

### 户外日报

卡片数据外置到项目根目录 `cards_MMDD_data.py`（字典 `CARDS = {"hot":[("#1", 标题, 来源, 标签class, 标签文案, 正文, 链接), ...]}`），再用**补丁脚本** `apply_MMDD.py` 注入生成器：

```bash
cp gen_outdoor.py gen_outdoor.py.bakMMDD     # 备份
# 写 cards_MMDD_data.py（37 条 7 元组）
# 写 apply_MMDD.py —— 基于上一期 apply 脚本模板，需含：
#   ① 4 类日期替换：X月N日→X月N+1日 / X月N→X月N+1 / YYYY年X月N日→YYYY年X月N+1日 / YYYY-MM-DD→次日
#   ② sources 行：re.sub(r'数据来源：[^<]*', '数据来源：...', src)
#   ③ from cards_MMDD_data import CARDS as NEW_CARDS
#   ④ 以括号配平定位旧 CARDS 块（含其上方注释行）后整块替换
#   ⑤ 写回 + compile(src, "gen_outdoor.py", "exec") 自检
python3 apply_MMDD.py                         # 必须看到 "Compile OK"
python3 gen_outdoor.py                        # 必须看到 "偏离超1条的组数 = 0"
```

> ⚠️ **不要**再用老的 `sed | cat` 拼接法（`/tmp/cards_sepN.py` + `tail_sepN.py`）——日期替换靠 `sed 's/9月X日/9月Y日/g'` 在跨月时会失效，且无法做 compile 自检。补丁脚本法可自检、可回退。

> **配比解法（先解约束、再写内容）**：① 固定版块配额；② 先安排"天然归属"明确的条目（行业 5 条必属 multi，安全类事件自带 water/fish 属性）；③ 用余量表倒推还缺哪些运动组，把缺口当选题指令去搜；④ 按缺口定向搜索补齐。这样一次成型，不返工。
>
> **tag_text 必须命中 SPORT_GROUPS 的键（2026-09-24 实测踩坑）**：卡片第 5 个字段（标签文案）会被拿去查 `SPORT_GROUPS` 归组算配比。**水上运动只有「自由潜/潜水/冲浪/帆船/皮划艇/游泳/桨板」七个键，没有通用的「水上」**；综合类必须写「户外装备/行业/目的地」；骑行类含「骑行/公路车/山地车/砾石/自行车/场地车」。**标了不存在的键会静默不计入任何组**——配比报告看着正常，实际少算一条，排查成本极高。写 tag_text 前先回读 `gen_outdoor.py` 顶部的 `SPORT_GROUPS`。已实测替代：救生/铁人一类写「游泳」；场地车/追逐赛写「自行车」（2026-10-02 曾因「场地车」未登记导致 multi 虚高 2 条，已把该键补进 SPORT_GROUPS）。
>
> 页面日期与来源在模板尾部（`<title>`、`<p class="sub">`、`<footer>` 的「数据来源：」行），拼接尾部时用 `sed` 一并替换；若原模板首个 `<p>` 未闭合，顺手补 `</p>`。

## 3. 去重（三条防线，缺一不可）

```bash
python3 scripts/verify_dedup.py ski --n 5        # 滑雪：基线上溯 5 期
python3 scripts/verify_dedup.py outdoor --n 5    # 户外：基线上溯 5 期
```

脚本自动完成：结构校验（条数/版块/标签/编号连续性/日期）+ 跨期 6 字 shingle 查重（过白名单）+ 同期内部查重。

### 三个必须知道的坑

1. **基线来源**：`ski_latest_titles.json` 被生成器**每次覆盖**，绝不能当"上一期"用。
   正确基线 = `patch_MMDD.py` / `gen_ski.py.bakMMDD` / `gen_outdoor.py.bakMMDD`。
   脚本已内置「**剔除当天补丁**」逻辑——历史上两次出现"拿今天当昨天"导致误报 27 条全重复。
2. **解析陷阱**：`patch_MMDD.py` 里 `NEW_SECTIONS` 有**两种历史写法**（`'''[` 和 `'''SECTIONS = [`）；且 `s.index("SECTIONS")` 会命中补丁里 `re.sub(r'^SECTIONS = \[...')` 的**正则字符串内部**，直接喂 `ast.literal_eval` 会报 `unterminated string literal`。
   稳法已写进脚本：先切三引号块 → 对块内第一个 `[` 做括号配平（跳过字符串内部与转义）→ 再 `literal_eval`。
3. **白名单不能省**：6 字检测命中片段若为**纯品牌/年份/通用赛事名** → 假阳性放行（`XGames`、`202627`、`Atomic`、`Salomon`、`世界杯`…）；若为**句式模板或具体事实** → 必须改题。

### 句式模板黑名单（跨期复用必须换模板，不能只换地区/对象/品牌）

- 「开板日历 / 开门时间表」类
- 「X月X日或成北美超级开板日」类
- 「索尔登揭幕战」类
- 「启动史上最大XXX」类
- 「媒体名 + 年份 + 品类 + 测试」类 → 改法：去媒体前缀 + 结论前置
- 「雪季进入最后 N 周/天」类 → 改法：换主语视角
- 「X 换帅：人名＋日期＋接任」类 → 改法：去掉「换帅」，把人物关系/履历前置
- 「X 定档 X月X日开幕/首映：…」类 → **「定档」二字应默认禁用**（9/16 连用三次，9/24 复发：麦罗单板电影「定档 10 月 10 日」撞 9/20「Diavolezza 定档 10 月 17 日」）。改法：删掉「定档」+ 把内容/画面/背景前置到题首
- 「X 第 N 季赛历 / 阵容敲定」类 → 同类赛事上期报过就不能只换角度重发，必须换事件
- 「人名 + 冒号 + 结论」起手（户外）
- **低成本通则**：通用短语里**插一个「的」字**即可打断 6 字连续片段。

### 正文事实级重复（shingle 抓不到）

6 字检测**只管标题**。若上一期内容特别密集（如 9/16、9/23 这类「高危密集期」），必须把该期 27/37 条标题全量打印出来人工过一遍，再决定正文里哪些具体数字、雪场名、日期不能重复写。

### 易撞主题清单（跨期需换角度）

X Games 联赛、雪盟 Snow League/Cardrona、Aspen、惠斯勒、路易斯湖、日本开季日历/二世谷、Vail 董事会 Oasis 提名、BOA 雪靴、戈吉亚、曾坪；
**酒店/雪场品牌扩张类**：Bear Den、Canopy by Hilton —— 同一品牌 10 天内极易二次撞题。
黑名单数据源：`miraitalk.com`（未来日期、不可靠）。

## 4. 验收清单（全部通过才算完）

```bash
grep -o '<h3[^>]*>' ski-morning-daily.html | wc -l                 # 27
grep -o 'class="section-title"' ski-morning-daily.html | wc -l      # 6
grep -o 'class="tag tag-international"' ski-morning-daily.html | wc -l  # 25
grep -o 'class="tag tag-china"' ski-morning-daily.html | wc -l          # 2
grep -o '<h3[^>]*>' outdoor-adventure-daily.html | wc -l           # 37
grep -o 'class="section-title"' outdoor-adventure-daily.html | wc -l    # 7
```

> 版块标题实际是 `<div class="section-title">`（**不是 h2**）；`grep '<h3>'` 会漏计，因为渲染器可能给 h3 注入属性。
> 卡片编号必须 01–N 连续。

## 5. 收尾（必做）

1. 追加当日记录到 `.workbuddy/memory/YYYY-MM-DD.md` 与
   `.workbuddy/automations/automation-1786349719094/memory.md`（滑雪）——写清：条数/版块分布、国内 2 条是哪两条、去重结果、本期新发现的撞题与教训、备份与产物路径。
2. `present_files` 把两份 HTML 交给用户。
3. 长期性教训（新句式模板、新易撞主题）同步写进 `.workbuddy/memory/MEMORY.md`。

## 6. 环境

Python：`/Users/lutao/.codex/workbuddy-runtime/binaries/python/versions/3.13.12/bin/python3`（不用系统 python3）
