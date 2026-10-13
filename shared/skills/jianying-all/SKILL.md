---
name: jianying-all
slug: jianying-all
displayName: 剪映全家桶·总调度
version: 1.1.0
agent_created: true
summary: "剪映剪辑/精修总入口。把本机已装的剪映相关 skill（capcut、jianying-editor、jianying-draft-free、jianying-ai-editor、computer-use-windows、video-content-extraction、video-recap 系列 6 技能、capcut-cli CLI、capcut-mate API 服务）统一调度。触发词：剪映、精修、粗剪、剪辑视频、改草稿、加转场、加花字、批量剪辑、批量字幕、字幕修正、字幕标点、拆句、改字幕文本、ASR字幕、Excel对齐、二次校验、与Excel对比、视频解说、解说成片、剪映体检、草稿生成 API。"
description: "统一路由剪映全链路：健康体检 → 草稿蓝图解析 → 精修方案确认 → 新草稿生成（dry_run 先行，不覆盖原稿）→ 人工导出。覆盖加密草稿（11.6）读取、GUI 操控兜底、批量生成、成片分析四类场景。含字幕文本批量修正（拆句/标点/样式/ASR对齐）实战配方 + Excel 脚本二次校验对齐（三·D 高频流程）。"
tags:
  - 剪映
  - 精修
  - 总调度
  - MCP
  - pyJianYingDraft
  - 字幕修正
---

# 剪映全家桶·总调度（jianying-all）

本机已装配完毕的剪映自动化资产与其调度规则。**所有剪映剪辑/精修请求先走本技能做路由，再进入具体子技能。**

## 一、资产清单（2026-09-22 装配）

| 类型 | 名称 | 位置 / 启动方式 | 用途 |
|---|---|---|---|
| MCP | jianying-ai-mcp | `E:\WorkBuddy\mcp-servers\jianying-ai-mcp\.venv\Scripts\python.exe -m jianying_ai_mcp`（已注册进 `~/.workbuddy/mcp.json`） | 草稿蓝图解析、参考重建、批量换料、视频分析 |
| MCP | computer-use-windows | `C:\Users\win\.workbuddy\binaries\node\versions\22.22.2-3\node.exe C:\Users\win\.workbuddy\skills\computer-use-windows__skillhub\project\dist\cli.js`（已注册） | GUI 截图+鼠标键盘操控剪映界面 |
| Skill | capcut / jianying-editor / jianying-draft-free / jianying-ai-editor / computer-use-windows / video-content-extraction | `~/.workbuddy/skills/` | 各子能力详见各自 SKILL.md |
| 工具 | jy-draftc.exe | `E:\WorkBuddy\mcp-servers\tools\jy-draftc\jy-draftc-amd64-windows\`（.env 已配 `JY_INSTALL_DIR=C:\Users\win\AppData\Local\JianyingPro\Apps\11.6.0.14508`） | 加密草稿解密（-d）/回加密（-e） |
| 工具 | uv.exe | `E:\WorkBuddy\mcp-servers\tools\uv\uv.exe` | pip 失效时的备用 Python 包管理器 |
| CLI | capcut-cli v0.25.0 | `C:\Users\win\.workbuddy\binaries\node\versions\22.22.2-3\node.exe C:\Users\win\.workbuddy\binaries\node\workspace\node_modules\capcut-cli\dist\index.js <cmd>`（2026-09-22 安装，doctor 通过，已识别剪映草稿目录） | 明文草稿批量精修：import-srt/export-srt、trim/speed/volume、cut/detect-scenes/detect-silence（长切短）、templates、lint；写回自动 .bak。剪映 6.0+ 加密稿 doctor 报 encrypted 时先走 jy-draftc 解密 |
| Skill | video-recap / video-understanding / video-script / video-cut / video-voiceover / video-assemble | `~/.workbuddy/skills/`（源仓库 `E:\WorkBuddy\tools\video-recap-skills`） | 视频中文解说成片全流程：场景检测/ASR/VLM → 故事与视听规划 → 配音（小米 MiMo，需 MIMO_API_KEY）→ 混音字幕 → **一键导出可编辑剪映草稿** |
| Skill | auto-video-editor（自动剪辑台 v1.1.0） | `~/.workbuddy/skills/auto-video-editor`，入口 `run.sh doctor --fix` 自装 ffmpeg 静态包+numpy | 粗剪前处理（全程本地离线）：去静音跳剪、按镜头切分、音乐卡点、批量变速/竖屏裁切、降噪/响度归一化；产物再进剪映精修 |
| Skill | video-transcribe（视频转录 v1.1.0） | `~/.workbuddy/skills/video-transcribe`，本地 Whisper 优先，uv 自管 venv | 本地视频/音频 → SRT 字幕 + TXT；SRT 交给 capcut-cli `import-srt` 灌进剪映草稿（口播/访谈字幕全自动链路） |
| 文档库 | cutcli-cookbook | `E:\WorkBuddy\tools\cutcli-cookbook`（templates/captions、animations、filters、examples、prompts） | capcut-cli 的 JSON 模板库与提示词库，做批量精修前先查这里抄现成模板 |
| 服务 | capcut-mate API（FastAPI） | `E:\WorkBuddy\mcp-servers\capcut-mate\.venv\Scripts\python.exe main.py` → `http://localhost:30000/openapi/capcut-mate/v1`（2026-09-27 部署，39 路由，含 create_draft/add_videos/add_audios/add_captions/add_effects/add_keyframes/add_masks/easy_create_material/gen_video 等） | REST API 草稿生成：JSON 入参 → 剪映草稿工程；支持字幕/特效/关键帧/遮罩/云端渲染；与 capcut-mate-skill 配套使用 |
| Skill | capcut-mate-skill | `~/.workbuddy/skills/capcut-mate-skill`（OpenClaw 技能，仅 axios + localhost 调用） | capcut-mate API 的 Node.js 客户端适配层，自动拼 JSON 调 API；需配合 capcut-mate 服务使用 |

**本机关键事实**：剪映版本 **11.6.0.14508**；草稿目录 `C:\Users\win\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft`；venv 为 Python 3.13.12。`~/.workbuddy/mcp.json` 中 jianying-ai-mcp 的 env 已配 `JIANNYING_EXE` 与 `JIANYING_DRAFT_CRYPTO`（指向 jy-draftc.exe），**2026-09-22 实测体检 `encrypted_draft_reader.available=true`、reasons 为空**。**capcut-mate 服务（2026-09-27 部署）**：源码 `E:\WorkBuddy\mcp-servers\capcut-mate\`，Python 3.13.12 venv，端口 30000，ENABLE_APIKEY=false，DRAFT_SAVE_PATH 已指向本机剪映草稿目录，39 路由已实测 create_draft 通过；`uv sync` 装新依赖时需走 VPN 代理 `http://127.0.0.1:7890`。

## 二、路由规则（先体检，再路由）

**第 0 步永远是体检**：调用 jianying-ai-mcp 的 `get_jianying_capabilities`，看 `encrypted_draft_reader`：
- `available=true` → 加密草稿可直接走 `analyze_reference_draft` / `build_from_reference` / `batch_from_template`
- `available=false` → 按 reasons 处理：通常需配置 `JIANYING_DRAFT_CRYPTO` 或 `JIANYING_EXE`（所在目录须含 videoeditor.dll）；仍不行则用 jy-draftc 手动解密副本

| 用户需求 | 路由 |
|---|---|
| 整片精修（节奏/转场/花字方案化） | jianying-ai-mcp：`analyze_reference_draft` 出方案 → 确认 → `build_from_reference`（先 dry_run） |
| 局部小修、必须用剪映内置模板/花字库 | computer-use-windows GUI 操控（剪映须前台、勿最小化） |
| 从零生成草稿/批量混剪/SRT 字幕 | jianying-draft-free（pyJianYingDraft，venv 里已装 0.3.0） |
| 分析成片节奏/抽帧/OCR | video-content-extraction |
| 加密草稿手动解密/回加密 | jy-draftc（仅限用户自己的草稿） |
| 视频解说成片（选段→解说→配音→成片→剪映草稿） | video-recap 系列（video-recap 编排；MiMo key 未配时提示用户设置 `MIMO_API_KEY`） |
| 明文草稿批量小修（换 SRT 字幕、统一变速/音量、长视频切条、套模板） | capcut-cli（先 `doctor`/`info` 确认草稿 readable；JSON 输出 `--jianying` 用剪映命名；模板参考 cutcli-cookbook） |
| 粗剪素材预处理（口播/访谈去废话、素材分镜拆条、音乐卡点、降噪、响度统一、竖屏适配） | auto-video-editor（首次用先 `run.sh doctor --fix` 装好 ffmpeg；产物丢给剪映精修或 jianying-ai-mcp 建稿） |
| 语音转字幕（口播/访谈/素材出 SRT） | video-transcribe（本地 Whisper 优先，失败再试云端模式）→ capcut-cli `import-srt` → 剪映草稿 |
| 全部失败兜底 | 用户导出粗剪 MP4 → ffmpeg 后处理 |
| **API 化草稿生成（含云端渲染）** | capcut-mate-skill（先确认 `curl localhost:30000/openapi/capcut-mate/v1` 可达；服务未启动则 `cd E:\WorkBuddy\mcp-servers\capcut-mate && .venv\Scripts\python.exe main.py`）；create_draft → add_videos/add_captions/add_effects → gen_video；**优点**：支持特效/关键帧/遮罩/云端渲染，JSON 入参语义化；**与 jianying-draft-free 的选择**：需要遮罩/关键帧动画/云端渲染 → capcut-mate；纯素材拼接/批量混剪/SRT 字幕 → jianying-draft-free 更轻量 |
| **capcut-mate 服务管理** | 启动：`cd E:\WorkBuddy\mcp-servers\capcut-mate && .venv\Scripts\python.exe main.py`（端口 30000）；停止：`netstat -ano | findstr :30000` 查 PID → `taskkill /PID <pid>`；启动后首次请求较慢（加载 1673 花字效果）；**依赖代理**：`uv sync` 装依赖时需走 VPN 代理 `http://127.0.0.1:7890`，已装好后无需代理 |

## 三、标准精修工作流（粗剪 → 精修）

1. **收需求**：草稿名 + 精修要求清单（语速节奏点、花字范围及例外如"1:46-1:51 强制"、转场风格）
2. **体检**：`get_jianying_capabilities`
3. **只读分析**：解密副本 + 深度 JSON 分析（见下方"手术路线"）→ 输出**精修方案表**给用户确认，此阶段零改动
4. **重建**：用户确认后生成新草稿，先校验再交付；**新草稿用新名字，不覆盖原稿**
5. **人工收尾**：用户在剪映打开新草稿检查 → **手动导出**（剪映 7.0+ 官方隐藏自动化控件，自动导出不可靠，勿浪费时间调试）

## 三·A、外科手术式精修路线（2026-09-22 实战验证，整片精修首选）

**适用**：转场系统重建、花字/字幕样式改造、变速调整——`build_from_reference` 只支持换源/换字，做不了这些。**全部验证通过**，已在「9月18日→9月18日-大师精修版」实跑成功（56 转场 + 83 字幕精修）。

### ⚠️ 第一大坑：11.6 的真身是 Timelines，不是根目录（实测翻车教训）

剪映 11.6 **打开/保存草稿的真实数据源是 `Timelines/<UUID>/draft_content.json`**（加密），根目录的 draft_content.json 只是它的同步副本。只写根目录 = 白写：剪映打开草稿时会用 Timelines 版本把根目录覆盖回去，**修改全部丢失且无任何报错**（2026-09-22 22:09 实测翻车）。正确做法：

1. **写入必须双写**：精修加密稿同时覆盖 `Timelines/<UUID>/draft_content.json`、`Timelines/<UUID>/draft_content.json.bak`、根目录 `draft_content.json`（UUID 可从草稿目录 `Timelines/` 下唯一子目录名获取）
2. **写入前必须确认剪映完全退出**——⚠️ 不要用 Git Bash 的 `taskkill /F`（`/F` 会被转成路径 `F:/` 静默失败，剪映存活 → 写入被内存旧稿覆盖，2026-09-27 实测翻车）。用 PowerShell `Stop-Process -Name JianyingPro,JianyingProTray -Force`，回查 `tasklist | grep -ci jianying` = 0 才动手
3. 写入前把 Timelines 原版备份到 E 盘；`Timelines/<UUID>/template.json` 是**明文**缓存/模板，剪映打开保存均不回写它，无需修改
4. 验证写入用"解密回读"：重新 cp 出来 → `jy-draftc -d` → 核对转场数/字体分布（注意：检查字体时搜 `优设`/`font.ttf` 这类实际路径尾部字符串，别只搜拼音小写）

流程（绝不改原稿文件夹）：
1. `jy-draftc -d` 解密原稿 draft_content.json 副本（明文只放 E:\WorkBuddy\mcp-servers\jy-test）
2. Python 直接改 JSON：
   - **转场**：`pyJianYingDraft.video_segment.Transition(TransitionType.叠化/闪黑, 时长us).export_json()` 生成官方结构素材 → append 进 `materials.transitions` → 把素材 id 加到**后一个** segment 的 `extra_material_refs`；转场时长 ≤ 前后段较短者的 40%
   - **字幕样式**：智能字幕素材顶层有全套字段（text_color/border_width/shadow_alpha/shadow_distance/font_path/fonts[]/font_resource_id），content.styles[].font 与 strokes[].width 要同步改；换字体时 fonts[] 整条替换为同款字体素材的 fonts[0]
   - **保护区**：按字幕轨 segment 时间轴判定 material_id，命中的整条跳过
3. `jy-draftc -e` 回加密（**roundtrip 已验证逐字节一致**）→ 覆盖新文件夹的 draft_content.json 和 .bak
4. 新文件夹 = 整包复制原稿（实际只有约 100MB，媒体都是绝对路径引用）；draft_meta_info.json 解密后改 draft_name/draft_id(新UUID)/draft_fold_path/draft_cover 再加密写回
5. root_meta_info.json（明文）注册：克隆原稿条目 → 改 id/名/路径/tm_draft_create → append
6. **坑**：剪映运行中会自动扫描注册新文件夹（生成第二条不同 id 的重复条目）→ 必须去重，保留与 meta_info 一致的 draft_id
7. **坑**：jianying-ai-mcp 内部调 jy-draftc 的参数格式不兼容（code=64 usage error），`analyze_reference_draft` 对加密稿会失败 → 直接走本路线，不要反复重试 MCP

## 三·B、全维度包装配方（2026-09-22 v2 实战验证：滤镜/特效/音频工程/关键词高亮）

以下 JSON 均已实测落盘并被剪映正常解析（在手术路线上叠加使用）：

- **滤镜**：`pyJianYingDraft.video_segment.Filter(FilterType.自然.value, 0.55).export_json()`（intensity 0~1）→ append 进 `materials.filters` + segment `extra_material_refs`；全片统一低强度滤镜是"包装层"最低成本的高级感
- **场景特效**：`VideoEffect(VideoSceneEffectType.暗角, [0.6]).export_json()`（params 0~100 语义）→ `materials.video_effects` + ref；暗角只打片头片尾，克制
- **音频淡入淡出**：`{"id":hex,"fade_in_duration":us,"fade_out_duration":us,"fade_type":0,"type":"audio_fade"}` → `materials.audio_fades` + ref；BGM 换乐边界必加，否则切换生硬
- **音量 ducking 关键帧**：segment `common_keyframes` = `[{"id":hex,"keyframe_list":[{"curveType":"Line","graphID":"","left_control":{"x":0,"y":0},"right_control":{"x":0,"y":0},"id":hex,"time_offset":us,"values":[vol]}],"material_id":"","property_type":"KFTypeVolume"}]`；**配音窗口来源 = 字幕轨(flag=1)段的 target_timerange**（解说连续时合并阈值别超过 1s，语句间隙让 BGM 呼吸）
- **字幕关键词高亮**：字幕素材 `content`（JSON 字符串）的 `styles[]` 追加深拷贝 style，改 `range` 为数字子串区间 + `fill.content.solid.color`（金色 [1.0,0.82,0.36]）；样式大小同步改 content.styles[].size 和顶层 font_size
- **坑**：部分 segment 的 `target_timerange` 缺 `start`（空段），排序/遍历前必须过滤，否则 KeyError
- **坑**：本机剪映素材库 `materials.stickers` 恒为空、pyJianYingDraft 无贴纸元数据——**真贴纸做不了**，用关键词高亮+特效补位，别硬造 resource_id（会显示"素材丢失"）
- 分段音量参考：主 BGM 0.6（ducking 时 0.35）、包装垫乐 0.38、人声/口播音效段不动

## 三·C、字幕文本批量修正实战配方（2026-09-27 实战验证：「9月27日-副本」126→137 段全流程）

**适用**：改字幕文本、标点规范化（如"逗号拆成两句、保留顿号/破折号/冒号"）、**字幕与 Excel 脚本二次校验对齐**（高频必做）、ASR 字幕修正。

### 数据结构事实（实测确认）

- 字幕文本存放在 **`materials.texts[]`**，每条的 `content` 字段是 **JSON 字符串**：`{"text": "...", "styles": [{"range":[0,n], "size":5, "fill":..., "strokes":...}]}`
- segment（text 轨）通过 `material_id` ↔ `texts[].id` 关联；**segment 自身的 `content` 字段是空字符串**，别在 segment 上找文本
- `texts[].words` / `current_words` 是空 dict，改文本不用动它们
- **text segment 必须引用 materials.texts 素材，否则整轨丢弃**（字幕全部消失）
- 样式字段事实：
  - **字号体系非像素**：剪映内部值默认 8，常规字幕用 5（写 28 会巨大无比）
  - **颜色是浮点数组** `[1.0,1.0,1.0]`，不是 `#FFFFFF` 字符串
  - 字体需引用真实资源：思源黑体 Regular `font_resource_id = 7072226413880921374`，font path 形如 `C:/Users/win/AppData/Local/JianyingPro/User Data/Cache/effect/<id>/<md5>/font.ttf`
  - **黄金模板法**：样式搞不定时，让用户在剪映里手动调好一轨 → 解密后把该素材整条 deepcopy 克隆，最可靠

### 拆句/改文本操作要点

1. **改文本**：解析 `content` JSON → 改 `text` → 同步把 `styles[].range[1]` 压到新文本长度 → 重新序列化（`ensure_ascii=False`）
2. **一句拆两句**（按逗号拆分等）：
   - 前半句：改原素材 content，原 segment 的 `target_timerange.duration` 缩短
   - 后半句：**deepcopy 原素材 + 原 segment**，id 和 material_id 都换新 UUID（`str(uuid.uuid4()).upper()`），`start = 原 start + 前半时长`，`render_timerange` 同步更新
   - 时间码**按字数比例**分配：`ratio = len(part1)/(len(part1)+len(part2))`，单段最短 0.5s（500000us）
   - 全部拆完后按 `target_timerange.start` 排序；排序/遍历前过滤缺 `start` 的空段（KeyError 坑）
3. **标点与空格处理规则（涛哥定稿，2026-09-27 追加空格规则）**："逗号→拆两句；**句中空格→拆两句**（如「接着说 他们明明…」必须拆成前后两条字幕，不要在一条里留空格）；顿号/破折号/冒号→保留"——**不要想当然删掉所有标点**（v1 误删顿号被要求恢复）。注意区分"句间空格"（要拆）与英文/数字内部空格（如 "LEWIS HAMILTON"、"120 多年" 不拆），拆前逐条人工过一遍。
4. 新增段在遍历 `list(segments)` 快照上做，最后统一 `segments.extend(new_segs)` 再排序
5. **⚠️ 样式范围退化 = 巨字事故（2026-09-27 v1 翻车实录）**：拆句时若**先改了原素材 content 再 deepcopy 它给后半句**，后半句的 styles.range 会被前半句的裁剪污染成 `[[0,0]]` 空覆盖 → 剪映找不到任何样式覆盖文本 → **渲染回退默认巨字号**（一条 17 字字幕能占满整屏）。铁律：**每一段拆分部分都必须从"纯净原始 content"独立 deepcopy**，样式用区间求交重算；**重算后若某部分样式为空，克隆覆盖该区间的最近样式强行补全**。验证：对全部字幕段做"样式覆盖体检"（每个字符必须被某个 styles[].range 覆盖），缺一即炸。
6. **存量稿也有雷**：ASR 导入的原生字幕可能自带样式缺口（实测「9月27日-副本」136 段里有 5 段尾部字符未被样式覆盖，如 2:00 处一条缺 12 字）。重建/精修时顺手对**所有**字幕素材跑一遍覆盖补全（克隆最近样式补缺口），否则随时炸巨字。

### 花字/人名标注规范（2026-09-27 涛哥定稿，「9月27日」实战）

- **1:1 对应**：花字必须和画面人物一一对应，且**贯穿该人物的整个片段**（人名念出时才闪一下 = 涛哥不要）；双人同框、无人脸的 b-roll、<0.7s 的微窗口不标
- **人物↔素材要先抽帧确认**：不能凭文件名猜（实测「TVC素材.m4v」里的护目镜年轻人其实是苏翊鸣——竖版画面自带「苏翊鸣顺滑无阻」烧录字幕才实锤）
- **y 坐标系（11.6 实测，易翻车）**：**负值=画面下方，正值=上方**。底部字幕 y≈-0.78，顶部花字用 **+0.72**，上部次层用 +0.35；别想当然以为正=下
- **科技感花字配方（涛哥认可方向）**：人名青色 `[0.0,0.898,1.0]`(#00E5FF) size 7 + 领域白色 size 5.5（styles 数组两个 range）+ 青色辉光（material 级 `shadow_color=#00E5FF, shadow_distance=9`）+ 深藏青描边 `[0.0,0.055,0.13]` width 0.09 + 思源黑体 bold。样式结构必须走 content.styles 正规 schema（fill.content.render.solid），克隆已验证字幕素材再改，别从零发明字段
- 剪映 11.6 本地无花字预设可克隆（其他草稿全查过，用户草稿 text 素材都是纯样式）；云端花字库拿不到，就按上面配方手搓

### ⚠️ 进程管理第一大坑（2026-09-27 21:53 实测翻车）

**Git Bash 下 `taskkill /F /IM JianyingPro.exe` 会静默失败**：Git Bash 把 `/F` 转换成路径 `F:/`，报"无效参数"但被 `2>/dev/null` 吞掉 → 剪映还活着 → 写入完成后剪映用**内存里的旧稿把文件覆盖回去**（文件大小变回旧值、修改全部丢失，用户看到的还是旧字幕）。

**正确杀法（必须用 PowerShell）**：
```powershell
Stop-Process -Name JianyingPro -Force -ErrorAction SilentlyContinue
Stop-Process -Name JianyingProTray -Force -ErrorAction SilentlyContinue
```
杀完必须回查：`tasklist 2>/dev/null | grep -ci jianying` 输出 `0` 才能写；写入后提醒用户**重新打开剪映**才能看到新内容。

### jy-draftc 参数格式（2026-09-27 实测）

- **不支持 `-o` 参数**（报 `too many arguments for single-file mode`）
- 正确用法：`jy-draftc -d <file>` 默认输出 `<file>.dec.json`；`jy-draftc -e <file> [output]` 默认输出 `<file>.enc.json`，第二个位置参数可直接指定输出路径
- 多文件模式：`jy-draftc -d "file1","file2"`（只用默认输出路径）

### 路径与工具链注意

- Git Bash 里 `cp`/`ls` 中文路径用 `/e/...` 形式加引号可以；但 **Python 的 `open()` 必须用 Windows 原生路径** `r'E:\...'`（`/e/...` 会 FileNotFoundError）
- 解密明文统一放 `E:\WorkBuddy\mcp-servers\jy-test\`，不落进草稿目录
- **验证闭环**：写入 → 重新 cp 出来 → `jy-draftc -d` 解密回读 → 统计段数/标点数（顿号/破折号/冒号计数）/抽查关键文本 → 全绿才交付

## 三·D、字幕与 Excel 脚本二次校验对齐（高频必做流程）

**用户核心要求**：字幕配完后，**必须**用提供的 Excel 脚本逐句做二次校验。改词区保留实际发音，未改词区用 Excel 原文。这是一条规矩，不是建议。

### 流程全景

1. ASR 转写 → 按 audio 时间码写入草稿 → **用户来一句"和我的 Excel 对比一下"** → 进入二次校验模式
2. 读 Excel（openpyxl）：源列 = 参考文本列，从中提取全部非空行
3. 从草稿解密后的 `materials.texts[]` 提取全部字幕文本（按 segment target_timerange.start 排序）
4. **滚动窗口模糊匹配 v4 算法**：逐条字幕找最佳 Excel 匹配行
5. 按匹配结果替换文本（改后必须同步更新 content JSON 里的 text 和 styles[0].range[1]）
6. 输出 Markdown 对比表给用户确认
7. 用户反馈后回加密写入

### 滚动窗口模糊匹配 v4（变长窗口 + 距离 tie-break）

**为什么不能简单按行号配对**：ASR 识别可能有断句差异、合并/拆分，Excel 行数和 ASR 段数不一致；且用户可能在 Excel 某句前面加了"哎你知道吗"这类预期外内容。

**算法**：
```
对每条字幕 text T[i]:
  1. 用 difflib.SequenceMatcher 算 T[i] 与 Excel 每行 E[j] 的 ratio
  2. 从 j_start 开始向前搜索一个变长窗口：
     - 初始窗口 = [j_start, j_start+3]
     - 如果窗口内 max_ratio < 0.4，扩窗口直到 j_start+10 或 max_ratio >= 0.4
     - 如果窗口内 max_ratio < 0.3，说明可能是 Excel 没有的新段 → 跳过保留 ASR
  3. 取 best_j = argmax ratio（踩坑：ratio 相同（如 "哎" / "啊" 同分）→ 取离 j_start 近的 → tie-break）
  4. j_start = best_j + 1（向前扫不回头）
```

### 文本替换规则（写死，不能想当然）

- **匹配 ratio >= 0.5**（粗略匹配）：用 Excel 行替换字幕文本（Excel 是定稿，优先）
- **ratio < 0.3**：说明 Excel 没有该段 → 保留 ASR 原文本不动
- **ratio 在 [0.3, 0.5)**：交给用户确认，或看语境手动判断
- **改词区判断**：如果 Excel 某行明显是"诶你知道吗"这类填充语/语气词 vs ASR 的原词 → 保留实际发音
- 逐段对比后生成 **修正记录表**（每行：序号 | 字幕原文本 | Excel 参考文本 | 匹配度 | 修正结果）

### 时间码偏移重算（音频轨调整后必须做）

剪辑师可能在音频轨上手动调整了帧间隙（如静音收缩、呼吸扩宽），导致 ASR 音频 → 字幕时码的线性映射失效。​​

**三段映射法**（实战实测对「9月27日-副本」有效）：

```
偏移段 1：0s ~ 245.17s    → 偏移 0s（前 4 分钟严格对齐）
偏移段 2：245.17 ~ 271.67s → 偏移 +0.5s（中间段有 0.5s 漂移）
偏移段 3：271.67s 以后     → 偏移 +0.7s（越往后漂移越大）
```

偏移后字幕素材的 `content.text` 不变，只调 segment 的 `target_timerange` + 新增段按中点映射音频轨时间。

### 最终交付物

- 修正后的加密草稿（三处写入：root、Timelines、.bak）
- 一段给用户的 Markdown 汇总：总段数、修正数、保留发音数、截图标点问题等

## 四、红线与坑

- 只操作用户自己创建/有权处理的草稿；jy-draftc 不得用于他人草稿或分发的模板
- 生成物必须人工过一遍再导出
- **杀剪映进程只能用 PowerShell `Stop-Process`**——Git Bash 的 `taskkill /F` 参数会被转成路径静默失败（详见三·C 进程管理坑），写入前回查 `grep -ci jianying` 必须为 0
- **pip 安装必须用阿里云源** `-i https://mirrors.aliyun.com/pypi/simple/`（清华源对本机 pip 返回空列表）；且需 `unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy` 摘掉本地代理 `127.0.0.1:3611`
- 本机 bash 缺 coreutils，每条命令前置：`export PATH="/c/Users/win/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:$PATH"`
- 沙箱 stderr 出现 `[safe-delete]` 噪音属正常，可忽略
- jy-draftc 官方验证范围 10.3.0~10.6.5；**2026-09-22 本机实测 11.6.0.14508 双向通过**：解密(-d)真实加密稿成功（结构完整可解析）；回加密(-e) roundtrip 逐字节一致，且回写的加密稿剪映可正常打开（见"Timelines 真身"坑）。注意 jianying-ai-mcp 的加密读取器只走"复制→解密副本→解析→删明文"安全流程，不回写
- 体检报告兼容性提示：jianying-ai-mcp 的 tested 版本是 10.0.5，与本机 11.6 不一致（`matches_tested_version=false`）——动画/在线素材/滤镜可能显示差异，**每次生成后必须人工抽查**
- 会话内 ToolSearch 若找不到 jianying-ai-mcp 工具（宿主未枚举），可用本地 stdio 探针直连验证：向 `python -m jianying_ai_mcp` 管道灌入 initialize / notifications/initialized / tools/call 三行 JSON，**必须保持 stdin 打开（`{ printf ...; sleep 12; } |` 形式）**，否则结果被提前截断；宿主侧修复 = 重启 WorkBuddy 会话让 MCP 重新枚举并信任
