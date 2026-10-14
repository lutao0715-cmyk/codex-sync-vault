# AGENTS.md — 陆涛（涛哥）个人档案

> 本文件由 WorkBuddy（洛洛）于 2026-10-13 整理迁移，供 Codex 全局读取。目标是让任何会话中的 Codex 快速了解使用者是谁、他关心什么、怎么跟他协作。

## 一、我是谁

- **姓名**：陆涛（涛哥，Lu / lutao / Mr. Lu）。Mac 用户名 `lutao`，主工作目录 `/Users/lutao/`。
- **职业**：互联网公司直播团队 Leader，带约 10 人团队。负责「二台转化与基础功能优化二期」项目：APP 多预告、横竖分屏投屏、直播结束数据统一、固定最新直播链接等模块。
- **副业/深度兴趣**：资深户外行业从业者，多年持续关注全球户外行业动态；运营抖音账号（主号「滑雪研究院」滑雪垂类，专业/资讯/教学向；另有泛户外号，陆地/水上/雪上/跑步，生活方式向，需内容差异化）。
- **家人**：养了一只叫「洛洛」的猫（我名字的来源）；微信通讯录有「媳妇」（妻子）。

## 二、怎么跟我协作（最重要的沟通规则）

- **说中文，简洁直接，不废话。** 我说话风格极度口语化、短句（"好了""再发起一次""done"），聚焦任务，直接描述需求。不需要客套，不需要复述我的需求。
- **先给结论，再给细节。** 需要细节时再展开。
- **能直接执行就执行**（下载、跑脚本、处理文件），不要只给链接或操作说明。
- **结构化输出**：内容/资源类需求偏好表格（如分辨率/大小/链接列成表）；数据结果偏好 Markdown 表格按列展示。
- **脚本/任务卡顿时**：倾向「重新发起一次」而不是深度排查细节。
- **问问题要分步**：我遇到问题倾向于分步追问直到每个环节明确（例如行程规划：错过船→备选方案→中间时段→客服联系方式→准点率→路线）。
- **数据对账**：习惯用「具体单元格/列名」定位问题（例如"sheet2 的直播间 id 在 p 列"），用列名核对纠错。
- **下班前会主动收工**，不要拖堂。

## 三、我的硬性偏好与铁律

1. **面向领导的汇报文档（复盘、周报、方案）交付前必须「去 AI 味」**：清掉破折号、混用引号、表情符号、「全面/完全/显著/印证/核心判断」类夸大词。触发话术：「帮我去 ai 味」。
   - 铁律：**数字和口径备注一个都不能改**；只改措辞与符号；改完必须回读验证。
2. **生成 xlsx 默认写静态值，不用 Excel 公式**：本机无 LibreOffice / Python `formulas` 包，公式无法重算、会在预览器里显示空白。
3. **涉及安装系统级依赖（brew/ffmpeg 等）要先问**，不要擅自装。
4. **对外动作（发邮件、发消息、公开发布）先问再做**；对内动作（读文件、整理、学习）大胆做。

## 四、我的环境（macOS，Intel）

- **主力机**：MacBook Pro (15-inch, 2018)，**Intel x86_64**（Core i7-8850H / 16GB / 512GB，macOS 15.5）。⚠️ 不是 Apple Silicon！装软件必须选 Intel/x64 版；`bad CPU type in executable` = 架构不对。查架构用 `file /Applications/Xxx.app/Contents/MacOS/Xxx`。
- 内存/SSD 焊死不可升级；电池已老化（Service Recommended，容量约 66%），用着发卡优先怀疑电池。
- 常年挂 15+ 第三方常驻服务（TeamViewer、ToDesk、深信服、Adobe CC、Google Keystone、搜狗输入法），负载偏高。
- **本机没有**：系统 ffmpeg / ffprobe、edge-tts、LibreOffice、美图 designkit、Python 的 PIL/numpy/pydub。Python 主要在 `/Users/lutao/.codex/workbuddy-runtime/binaries/python/versions/3.13.12/bin/python3`，隔离 venv 在 `/Users/lutao/.codex/workbuddy-runtime/binaries/python/envs/default`。
- 语音转写可跑通：`faster-whisper`（venv 已装 + PyAV 自带 FFmpeg），需先设 `HF_ENDPOINT=https://hf-mirror.com` 和 `HF_HUB_DISABLE_XET=1`，否则模型下载 401。

## 五、高频任务（点开即用的方法论）

### 1. 直播主播数据导出（每 2-3 天一次，最高频）
- 源数据：`/Users/lutao/Downloads/二台直播间明细 N.xlsx`（名字带递增序号）等直播明细大表。
- 需求：按直播间 ID 跨天多行累加 → 按主播聚合指标：场次/开播天数/播放总时长/曝光/播放用户/互动用户/关注成功/app拉新/粉丝净增(max-min)/人均观看时长/互动率/CTR/次均播放时长。
- 可选：用飞书「报名成功」主播名单过滤，只保留名单内主播。
- 输出：格式化 xlsx + Markdown 表格。
- **方法已沉淀为技能 `live-anchor-data-export`**，先读它的 SKILL.md 再动手，别重建轮子。

### 2. 每日滑雪晨报 + 户外运动日报（自动化，持续运行）
- 滑雪晨报：`ski-morning-daily.html`，27 条（25 国际 + 恰好 2 国内），6 版块；只收录 7 天内新闻。
- 户外外刊：`outdoor-adventure-daily.html`，37 条，7 版块，国内≤3；受众加权配比 8 组 ±1。
- 生成工具：`gen_ski.py` / `gen_outdoor.py` + 补丁流（patch_MMDD.py / cards_MMDD_data.py + apply_MMDD.py），**禁止手写长 HTML**。跨期去重：近 5 期基线 + 6 字 shingle 检测 + 句式黑名单。
- 方法论详见技能 `outdoor-ski-daily-report` 与主工作区 `/Users/lutao/WorkBuddy/2026-08-10-16-06-16/.workbuddy/memory/MEMORY.md`。

### 3. 短视频内容生产（滑雪研究院）
- 工作流技能：`滑雪出片`（写脚本/口播/分镜/配音/剪辑单/配乐，区分抖音版与小红书版）。
- AI 视频技术栈：GPT（脚本/分镜/提示词）+ 豆包（中文口播稿、配音）+ 即梦 AI（文生图→图生视频→数字人对口型）+ 剪映（剪辑收口）。
- 每日热点：用技能 `热点` 生成「每日作战包」（抖音实时标签 + 小红书官方活动/趋势），不要现想。
- 核心认知：标签是流量入口，但只有官方挑战/活动话题才有流量倾斜；硬蹭无关标签会打散人群限流。

### 4. 咪咕运营（体育媒资）
- 通过咪咕运营系统（4A 账号 sjgl003lutao）+ 本地「移动办公2」软件，做体育媒资节目 ID 批量导入。
- 相关流程与方法论：技能 `咪咕礼物`（直播礼物动效 mp4→VAP 文件，720×720 24fps）、`央视下载`（央视网视频最高清 720p 下载）、`战术板`（赛事总表→AI战术板正式排期 xlsx，频道 269/270 抢号）。
- 每天 18:00 自动任务：提取体育媒资群赛场原声节目 id（`scripts/extract_sport_program_ids.py`）。

### 5. 直播检测/多开监控
- 工作区 `/Users/lutao/WorkBuddy/2026-08-10-12-21-39/live-monitor`，`daily-report.js` 生成前一日多开报告；`http://localhost:3456/api/check` 触发全量检测（每小时自动）。

## 六、关注领域与内容偏好

- **户外分类体系**：陆地 / 水上 / 雪上 / 跑步，关注各细分项目市场热度排名。
- **AI 视频讲解偏好**：先给「工具分工 + 五步流水线」整体视角，再给可直接复制的提示词模板，最后点关键坑（如图片 vs 视频提示词写法不同、角色一致性靠首帧参考图）。
- **学习中偏好**：结构化、图文并茂的中文详细讲解（时间线、剖面图、分点论述）。
- 曾做 100 位户外/极限运动纪录片主人公的 Word 文档数据收集整理。
- 生活兴趣：马尔代夫（已订 10/3 MU235 浦东→马累 + Escape Voyages 船票）；上海青浦淀山湖/元荡湖/淀浦河桨板皮划艇点位（人少、景美、有树林、宽阔水面）；研究 B 站 UP 主动画特效视频工具栈（AE/PS/AI 生成）。

## 七、可消费的资产（都在本机，Codex 版优先）

> 2026-10-13 已完成 WorkBuddy → Codex 全量迁移。后续优先读 Codex 路径；`.workbuddy` 只作为历史来源，不作为执行依赖。

| 资产 | 位置 |
|---|---|
| 迁移总报告 | `/Users/lutao/.codex/workbuddy-migration-report.md` |
| 技能总索引 | `/Users/lutao/.codex/workbuddy-import/indexes/skills.json` |
| 会话总索引 | `/Users/lutao/.codex/workbuddy-import/indexes/sessions.jsonl` |
| 记忆与身份档案 | `/Users/lutao/.codex/workbuddy-import/memory/` |
| 可直接触发的 Codex 技能 | `/Users/lutao/.codex/skills/`（126 个可触发入口：125 个迁移技能 + 1 个历史检索技能） |
| WorkBuddy 原始技能备份 | `/Users/lutao/.codex/workbuddy-import/skills-raw/` |
| 高频技能入口 | `live-anchor-data-export`、`outdoor-ski-daily-report`、`ski-video-production`、`hot-topic-report`、`migu-gift-vap`、`cctv-video-download`、`tactics-board-schedule`、`live-activity-review` |
| 我的自定义专家 | `outdoor-creation-team`，已迁移到 `/Users/lutao/.codex/skills/outdoor-creation-team/` |
| 全部历史会话 | `/Users/lutao/.codex/workbuddy-import/projects-raw/`（166 个 session 文件） |
| 项目记忆 | 各工作区 `/Users/lutao/WorkBuddy/*/.workbuddy/memory/` |
| 自动化任务备份 | `/Users/lutao/.codex/workbuddy-import/automations/` |

### 高频技能中文别名

用户以后可以直接说中文名或用途，按下表调起对应技能：

| 中文名 / 用途 | Codex 技能 |
|---|---|
| 直播主播数据导出 | `live-anchor-data-export` |
| 滑雪晨报 / 户外日报 | `outdoor-ski-daily-report` |
| 滑雪研究院出片脚本、口播、分镜 / 滑雪出片 | `ski-video-production` |
| 今日热点 / 抖音标签 / 小红书活动 / 热点 | `hot-topic-report` |
| 咪咕礼物 VAP / 咪咕礼物 | `migu-gift-vap` |
| 央视视频下载 / 央视下载 | `cctv-video-download` |
| AI 战术板排期 / 战术板 | `tactics-board-schedule` |
| 直播活动复盘 / 直播复盘 / 活动复盘 | `live-activity-review` |
| 户外创作专家团 / 户外创作 | `outdoor-creation-team` |
| 查历史聊天 / 查以前聊过的 / WorkBuddy 历史 | `workbuddy-history-search` |

## 八、技能使用注意（本机可用性，务必先查再跑）

- **装即用的纯文本/方法类**：`ski-video-production`、`live-activity-review`、`hot-topic-report`、`migu-gift-vap`(部分)、`cctv-video-download`、`tactics-board-schedule`、`live-anchor-data-export`、`outdoor-ski-daily-report`、`seedance-video-script`、`lynxce-voiceover-script`、`ai-digital-avatar-script`、`short-video-script`、`product-manager`、`qqmusic` 等。
- **受 ffmpeg/edge-tts 缺失限制，跑不了成片的**：script-to-voice、svf、science-video-studio、ai-short-video-maker 等「文案→成片」类。⚠️ 先查依赖（ffmpeg/ffprobe/edge-tts/designkit）再承诺结果。
- **含 Windows 路径不可在本机跑的**：jianying-dfq、jianying-all（E:\、C:\Users\win\）。
- **装新 skill 前先读 SKILL.md 的路径/依赖**，别等触发才发现是别的机器上配的。
