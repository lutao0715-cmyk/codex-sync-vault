# 长期记忆

## 响应模式规则（涛哥明确要求，适用所有会话）

- **默认轻量响应（ask 模式）**：日常提问、简单查询、闲聊、一句话能答的事，直接用文字回答，**不启动深度执行/多工具流程**，目的省积分。
- **深度进程才升级（craft 模式）**：仅当任务需要实际产出——写/改文件、跑脚本、处理 Excel、生成报告/视频/网页、多步骤工具链——才进入深度执行模式。
- 判断标准：看任务是否「要动东西」；只要答即可的 → 轻量；要产出物/要执行 → 深度。
- **积分告急时的兜底（2026-09-24）**：涛哥说「积分快用完了，可以切换到我的自定义模型 deepseek-flash」。
  - ⚠️ **模型切换只能涛哥自己在 WorkBuddy 设置里切**，我无法代切——遇到他提这个，告知路径即可，别假装能操作。
  - 省积分的正确做法（我这边能做的）：**少轮次、大工具调用批量做、避免截图/视觉类高开销操作**。
  - 重要认知：**跑本地脚本不消耗积分**（纯 CPU 计算）。所以「数据量大」的活（批量转录、表格处理、抓取）尽量集中在本地脚本里一次跑完，比多轮对话便宜得多。

## 环境事实

- **✅ 语音转写可用（2026-09-24 实测打通，推翻此前"本机跑不通"的结论）**
  - 方案：`faster-whisper`（CTranslate2 + **PyAV 自带 FFmpeg 库**）→ **不需要系统 ffmpeg，不需要 brew，不需要 sudo**
  - venv：`C:/Users/win/.workbuddy/binaries/python/envs/default`（已装 faster-whisper 1.2.1、av 18.1.0、zhconv）
  - 模型缓存：`~/.cache/huggingface`（base 140MB / small 480MB，共 625MB）
  - 必须先设两个环境变量，否则模型下载 401 失败：
    `HF_ENDPOINT=https://hf-mirror.com` 和 `HF_HUB_DISABLE_XET=1`
  - 实测速度：i7-8850H 上 `small` int8 ≈ **2.2x 实时**（59s 音频 → 26.8s）；`base` 更快但中文错字多
  - 封装为 `~/.workbuddy/skills/滑雪出片/scripts/transcribe_original.py`
  - ⚠️ zhconv 用 pip 装会报 EEXIST 构架错误 → 改为从 PyPI 下载 sdist、把 `zhconv/` 目录整个拷进 site-packages 才成功
  - ⚠️ PyAV 的 wheel **不含 AAC 编码器**（只能解码），所以不能靠 PyAV 造 mp4 测试文件

- 涛哥的主力 Mac 是 **Intel x86_64**（Core i7-8850H，macOS 15.5），**不是 Apple Silicon**。
  - 安装 macOS 软件时必须选 **Intel / x64** 版本；arm64-only 的应用无法运行。
  - 遇到「应用装了却打不开 / 找不到」，第一步先查架构：
    `file /Applications/Xxx.app/Contents/MacOS/Xxx`
  - 报错 `bad CPU type in executable` = 架构不匹配，不是文件损坏。
- 主力机型号：**MacBook Pro (15-inch, 2018)**，i7-8850H / 16GB / 512GB，2018 年 7 月国行首发价 ¥21,988。
  - 内存与 SSD 均焊死，**无法升级**，性能上限固定，只能优化软件层。
  - **电池已老化（2026-09 实测：Condition = Service Recommended，容量约 66%，循环 568 次）**，是「用着发卡」的首要原因，建议换电池（官方约 ¥1,500）。
  - 该机常年挂着 15+ 个第三方常驻服务（TeamViewer、ToDesk、深信服、Adobe CC、Google Keystone、搜狗输入法），是持续负载偏高的来源。
- **本机没有 LibreOffice，也没装 Python `formulas` 包。**
  - 影响：用 openpyxl 生成的 xlsx 里若写 Excel 公式，公式**无法重算**、不带缓存值，
    在多数预览器（微信/邮件附件预览、pandas、data_only=True）里会显示为**空白**。
  - 因此生成 xlsx 时**默认写静态值，不用公式**；确需公式时先向涛哥申请安装依赖的授权。
- **本机没有 `ffmpeg` / `ffprobe` / `edge-tts`**，Python 侧也没有 PIL / numpy / pydub / pyyaml。
  - 影响：所有靠 ffmpeg 合成视频、靠 edge-tts 做配音的 skill（`science-video-studio`、
    `ai-short-video-maker`、`script-to-voice`、`svf`）目前**装得上但跑不通**。
  - 修法：edge-tts 可装进隔离 venv（无需 sudo）；ffmpeg 要走 brew，需先向涛哥申请授权。
  - 本机**没有 `skills-security-check` skill**，安装第三方 skill 前无法做标准安全审计，需改为装后人工审查。

## 视频创作 skill 现状（2026-09-17 精简后）

- **纯文本类（装即用，保留）**：`seedance-video-script`（即梦分镜 prompt）、
  `lynxce-voiceover-script`（口播稿节奏）、`ai-digital-avatar-script`（数字人口播编导）
- **本地生产类（受 ffmpeg/edge-tts 缺失所限，暂时跑不通）**：`script-to-voice`（仅 16K，装 venv 可修）、
  `svf`（原子创私有二进制，⚠️ SKILL 要求 Agent 自动下载执行 install.sh，且需 ffmpeg）
- **需外部依赖**：`video-post`（美图 `designkit` CLI，本机未装）
- **已隔离**（`~/.workbuddy/_disabled_skills/`）：`science-video-studio`、`ai-short-video-maker`、
  `voiceover-narration-studio`、`talking-avatar-video`（后两个是 beatra.ai 付费 SaaS）、
  `jianying-dfq`（2026-09-28 隔离：剪映×达芬奇精剪闭环，链路组件全在 Windows 机上，Mac 跑不通）
  - 还原：`bash ~/.workbuddy/_disabled_skills/restore.sh <目录名>`

### 剪映 skill 去重结论（2026-09-28 梳理）

本机 5 个 jianying-* 技能里，**3 个功能重叠**——`jianying-editor`（JyWrapper，跨平台含 Mac Intel）、
`jianying-draft-free`（pyJianYingDraft 开源链，适合批量）、`jianying-ai-editor`（走 MCP，支持参考成片/草稿模仿），
核心都是「需求 → 剪映草稿工程」，**同一个活选一个即可**；`jianying-all` 是路由层不干活。
`jianying-dfq`、`jianying-all` 内含 Windows 路径（`E:\`、`C:\Users\win\`），Mac 上不可运行。
参考经验：**装 skill 前先读 SKILL.md 里的路径/依赖，别等触发才发现是别的机器上配的。**

### 判断视频 skill 能否跑通的前提

**先查依赖，再看功能。** 本机缺 `ffmpeg` / `ffprobe` / `edge-tts` / 美图 `designkit`，
所有"文案→成片"的本地生产类技能都是摆设；纯文本类（写提示词、写稿、写分镜）才是装即用。
详细精简方法与踩坑记录见技能 `workbuddy-skill-prune`。

## 写作与交付偏好

- **向上汇报的文档（复盘、周报、方案）在交付前要过一遍「去 AI 味」**：破折号、混用引号、表情符号、
  「全面/完全/显著/印证/核心判断」这类夸大词都是他要清掉的对象。触发话术：「帮我去 ai 味」。
  - 流程与坑表见技能 `直播复盘` 的 `references/deai-humanize.md`（也适用于任何飞书文档的逐块润色）。
  - 铁律：**数字和口径备注一个都不能改**；只改措辞与符号；改完必须回读文档验证。

## 关注领域

- **抖音账号**：主号「**滑雪研究院**」（滑雪垂类，专业/资讯/教学向）；另有一个泛户外垂类号（陆地/水上/雪上/跑步，生活方式向），两号需内容差异化。
  - 每天会问「今天有哪些适合我的话题/标签/活动」→ 用 skill `热点`（~/.workbuddy/skills/热点/）跑，不要现想方案。
  - 核心认知：标签是平台流量入口而非结果，但只有官方挑战/活动话题才真正有流量倾斜；硬蹭无关标签会打散人群精准度反而限流。

## 视频风格与配音偏好（2026-09-28 户外创作团队风格库相关）

- **模仿达人风格**：走方案二——**不克隆音色，只模仿语气/节奏/情绪起伏**。写旁白脚本时控制句子长短交错、关键处停顿留白、冷静语速，靠文案本身对齐风格，不换声音。
- **当前风格库**：好奇罗盘（悬念开篇+花字标注+节奏感）+ 神秘园（冷静叙事+上帝视角+金句收尾），覆盖短视频口播和深度叙事两种形态。
- **可补充方向**：如未来需要，可再加一个"快节奏硬核卡点"风格（15-60s 场景混剪/精彩合集），补完三个核心内容形态。

- 在探索 **AI 视频制作**：技术栈为 GPT（脚本/分镜/提示词）+ 豆包（中文口播稿、配音）+ 即梦 AI（文生图 → 图生视频 → 数字人对口型）+ 剪映（剪辑收口）。
  - 讲解这类问题时：先给「工具分工 + 五步流水线」的整体视角，再给可直接复制的提示词模板，最后点关键坑（图片提示词 vs 视频提示词写法不同、角色一致性靠首帧参考图锁定）。

## 剪映精修授权（Windows 机，2026-09-27 涛哥明确授权）

- **关剪映不用问**：写入草稿前直接 PowerShell `Stop-Process -Name JianyingPro,JianyingProTray -Force` 关掉剪映，无需征得同意；写完提醒重开即可。
- 字幕规矩沉淀在 skill `jianying-all` 三·C：逗号→拆两句；**句中空格→拆两句**；顿号/破折号/冒号→保留。
- 本机剪映 11.6 草稿真身在 `Timelines/<UUID>/draft_content.json`，写入必须三处双写（Timelines + .bak + 根目录）；解密工具 `E:\WorkBuddy\mcp-servers\tools\jy-draftc\jy-draftc-amd64-windows\jy-draftc.exe`（不支持 -o，默认输出 .dec.json/.enc.json）。
- **草稿 y 坐标系：负=画面下方、正=上方**（底部字幕 y≈-0.78，顶部花字 +0.72）。
- **花字审美（涛哥定稿）**：要与人物 1:1 对应且贯穿人物整个片段，要科技感（青色人名+辉光+描边），不要"念到名字闪一下"的简单样式；拆句新段样式范围必须全覆盖否则渲染巨字（坑已录 skill `jianying-all` 三·C）。
