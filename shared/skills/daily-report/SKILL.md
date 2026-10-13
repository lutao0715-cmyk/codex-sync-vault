---
name: daily-report
description: >
  生成「滑雪晨报」与「户外运动每日外刊」两份 HTML 日报。当用户说「日报」「今天日报」「出日报」「滑雪日报」「户外日报」「晨报」「再出一期」时触发。
  核心是数据驱动流水线（数据块 + 渲染脚本 + 校验脚本），绝不手写 HTML，最后跑 verify_dedup.py 全绿才算完。
---

# 滑雪晨报 / 户外日报 生成

工作目录（固定）：`C:/Users/win/WorkBuddy/daily-report/`
Python：`C:/Users/win/.workbuddy/binaries/python/versions/3.13.12/python.exe`（不用系统 python）

本技能的所有细节（搜索矩阵 / 数据块格式 / 三条书写铁律 / 句式模板黑名单 / 已知坑速查）见同目录：
- `README.md`（完整手册）
- `PROMPT.md`（可直接整段当提示词的工作流 + 单次执行指令）

## 0. 先确认状态（别急着搜新闻）

```bash
cd C:/Users/win/WorkBuddy/daily-report
ls *.html *.py.bak* patch_*.py 2>/dev/null
grep -o '2026年[0-9]*月[0-9]*日[^<]*' ski-morning-daily.html | head -2
grep -o '2026年[0-9]*月[0-9]*日[^<]*' outdoor-adventure-daily.html | head -2
```

- 若产物日期已是今天 → 先问用户是否重做，不要盲目覆盖。
- 记下「上一期日期」——决定时效窗口（7 天）与去重基线。
- 基线 = `patch_MMDD.py` / `gen_*.py.bakMMDD`。**绝不能拿 `*_latest_titles.json` 当基线**（被生成器每次覆盖）。
- 若无任何备份 → 本期无跨期基线，F 阶段只能人工复核，写入日志。

## 1. 硬性规格（验收红线）

| | 滑雪晨报 | 户外日报 |
|---|---|---|
| 文件 | `ski-morning-daily.html` | `outdoor-adventure-daily.html` |
| 条数 | **27** | **37** |
| 版块 | **6**：🔥今日热点5 / ⚔️竞技赛场5 / 🏆人物4 / 🏔️雪场动态5 / 🏭行业观察4 / 🎿装备风向4 | **7**（版块内可弹性，总数必须 37） |
| 地区标签 | tag-international 恰好 **25** / tag-china 恰好 **2** | 国内条目 **≤3** |
| 时效 | 只收 7 天内新闻 | 只收 7 天内新闻 |
| 编号 | 01–27 连续 | 01–37 连续 |

户外另有**受众加权配比**（写死在 `gen_outdoor.py` 顶部，不可改）：

```
SPORT_GROUPS = {"hike":8,"run":6,"ride":6,"ski":5,"water":4,"air":2,"fish":1,"multi":5}  # 合计 37
```

运行 `gen_outdoor.py` 打印「受众加权配比报告」，**偏离超 1 条的组数必须为 0**，否则换题重生成。

> 国内选题常年超额：先列全部候选再排序取舍。优先有国际参与度或公共价值的（国际公开赛、国字号赛事、执法/政策通报），纯地方性活动让位。

## 2. 流程（严格按序）

### A 选题搜索（只收 7 天内，每条四要素：标题≤30字 + 正文2-3句含硬信息 + 来源 + 标签）

搜索矩阵与来源白名单见 `README.md` 第 5 节。黑名单数据源：`miraitalk.com`（禁止）。

### B 配额分配（先解约束再写内容）

先固定条数/版块/国内外配额 → 先排「天然归属」明确的条目（行业归 multi、安全类带 water/fish、开板归 ski）→ 用余量表倒推缺哪些组 → 把缺口当选题指令去搜。

### C 写数据块（最容易炸的一步）

滑雪：`SECTIONS = '''[ {name, items:[{t,p,tag,src}]} ]'''`（patch_product 换入）
户外：`CARDS = { "版块名": [ [tag, 标题, 正文, 来源], ... ] }`，**必须内联进 gen_outdoor.py**（不能 import），且写在 SPORT_GROUPS 之前。

三条铁律：
1. **引号**：t/p 值里只能用中文「」，ASCII 双引号 → SyntaxError。
2. **逗号**：每个列表项行末必须有逗号。
3. **户外 tag 必须严格命中 SPORT_GROUPS 的键**（hike/run/ride/ski/water/air/fish/multi）。水上运动没有「水上」这个键，写错键会静默不计入任何组，排查成本极高。救生/铁人一类写「游泳」→ water。

### D 生成 HTML（严禁手写整份 HTML，历史上多次被截断）

```bash
cd C:/Users/win/WorkBuddy/daily-report
# 滑雪：备份即下期去重基线，必须做
cp gen_ski.py gen_ski.py.bakMMDD
python C:/Users/win/.workbuddy/binaries/python/versions/3.13.12/python.exe patch_template.py --date 2026年X月X日 --weekday 星期X --sections-file 数据块.py --footer "数据来源：…"
python C:/Users/win/.workbuddy/binaries/python/versions/3.13.12/python.exe gen_ski.py

# 户外：备份 + CARDS 内联 + 拼接尾部
cp gen_outdoor.py gen_outdoor.py.bakMMDD
# CARDS 写进文件头部，尾部从旧文件切（sed -n '/^# ============ 受众加权配置/,$p'）
# 必须看到「偏离超1条的组数 = 0」
python C:/Users/win/.workbuddy/binaries/python/versions/3.13.12/python.exe gen_outdoor.py
```

> ⚠️ `patch_template.py` 一定要放在工作目录根（它按自身所在目录找 gen_*.py），不要留在 skill 的 scripts/ 子目录里运行。
> `scripts/`（skill 内）是模板源，已复制一份到工作目录根。

### E 去重与校验（三条防线，缺一不可）

```bash
python C:/Users/win/.workbuddy/binaries/python/versions/3.13.12/python.exe verify_dedup.py ski --n 5
python C:/Users/win/.workbuddy/binaries/python/versions/3.13.12/python.exe verify_dedup.py outdoor --n 3
```

- 6 字命中片段是纯品牌/年份/通用赛事名 → 假阳性放行（XGames、202627、Atomic、Salomon、世界杯、FIS、BOA、UCI…）；是句式模板或具体事实 → 必须改题。
- 句式模板黑名单（复用必须换模板，不能只换地区/对象/品牌）：「开板日历/开门时间表」「X月X日或成北美超级开板日」「索尔登揭幕战」「启动史上最大XXX」「媒体名+年份+品类+测试」「X换帅：人名＋日期＋接任」「X定档X月X日」（**「定档」默认禁用**）「X第N季赛历/阵容敲定」「人名+冒号+结论」起手。
- 低成本通则：通用短语插一个「的」字打断 6 字连续片段。
- 6 字只查标题；正文里重复的具体数字/雪场名/日期需人工复核（把上期标题打印出来过一遍）。
- 易撞主题：X Games 联赛、Snow League/Cardrona、Aspen、惠斯勒、路易斯湖、日本开季日历/二世谷、Vail 董事会、BOA 雪靴、Bear Den、Canopy by Hilton。

### F 验收（全绿才算完）

```bash
grep -o '<h3[^>]*>' ski-morning-daily.html | wc -l                      # 27
grep -o 'class="section-title"' ski-morning-daily.html | wc -l           # 6
grep -o 'class="tag tag-international"' ski-morning-daily.html | wc -l   # 25
grep -o 'class="tag tag-china"' ski-morning-daily.html | wc -l           # 2
grep -o '<h3[^>]*>' outdoor-adventure-daily.html | wc -l                 # 37
grep -o 'class="section-title"' outdoor-adventure-daily.html | wc -l     # 7
```

> 版块标题是 `<div class="section-title">` 不是 h2；卡片编号必须连续。

### G 归档（不做下期就瞎了）

1. 写当日记录：条数/版块分布、国内条目、去重结果、新撞题与教训、备份与产物路径。
2. 保留 `patch_MMDD.py` + `gen_*.py.bakMMDD` 作为下期基线。
3. 交付两份 HTML 给用户。