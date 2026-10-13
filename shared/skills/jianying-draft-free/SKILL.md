---
name: jianying-draft-free
slug: jianying-draft-free
displayName: 剪映草稿自动化·批量剪辑·Python生成·免费版
version: 1.0.1
summary: "剪映草稿自动化 / JianYing draft automation —— 当需要 generate、batch build、automate 剪映（CapCut 国内版）草稿，把分镜脚本批量变成可编辑工程时使用：自动生成多轨草稿、批量替换素材、SRT 字幕导入、批量混剪、电商带货矩阵出片。触发词 Trigger phrases：剪映草稿、剪映自动化、批量剪辑、批量出片、混剪、自动生成草稿、剪映批量导出、字幕导入、JianYing draft、CapCut draft、剪映脚本、带货视频批量。开源工具链（pyJianYingDraft / jy-draftc），MIT 说明文档，无付费依赖。"
description: "原创免费技能（不依赖任何专有实现，不破解剪映、不触及账号权益）。用 Python 把「分镜计划」批量变成剪映专业版可直接打开编辑的草稿工程，构建自动化剪辑 / 混剪流水线。覆盖四条路线的选型与落地：① 版本体检先行——先查剪映版本再决定路线，避免踩 6.0+ 草稿加密与 7.0+ 导出控件隐藏两个大坑；② 从零生成草稿（视频/图片/音频/文本多轨、片段截取、音量淡入淡出、关键帧、转场、入场动画、蒙版、滤镜、SRT 字幕导入）；③ 模板模式（套用已有草稿换素材换文案，含明文与加密两种处理路径）；④ 批量矩阵生产（同一脚本换素材产出 N 条，含断点续跑与失败隔离）；⑤ 导出方案的三条路与其真实边界。附完整可运行的分镜计划生成器与自检清单。免费版，只用本地开源工具，不引用任何付费服务或云端渲染。"
tags:
  - 剪映
  - 剪映草稿
  - 剪映自动化
  - 剪映批量
  - 批量剪辑
  - 批量出片
  - 混剪
  - 自动生成草稿
  - 剪映脚本
  - 剪映导出
  - 批量导出
  - 字幕导入
  - SRT字幕
  - 带货视频
  - 短视频批量
  - 视频自动化
  - 剪映模板
  - 替换素材
  - JianYing
  - CapCut
  - 剪映专业版
  - pyJianYingDraft
  - Python剪辑
  - 开源
  - 免费
license: MIT
allowed-tools:
  - Read
  - Write
  - Bash
trigger:
  - 剪映自动生成草稿
  - 剪映批量剪辑
  - 剪映批量出片
  - 批量生成剪映草稿
  - 自动剪辑剪映
  - 剪映草稿自动化
  - 分镜脚本生成剪映工程
  - 剪映混剪
  - 批量混剪
  - 剪映导入字幕
  - SRT 转剪映字幕
  - 剪映替换素材
  - 剪映换文案
  - 剪映批量导出
  - 带货视频批量生成
  - 电商视频矩阵
  - 剪映草稿加密
  - 剪映版本不兼容
  - 剪映导出失败
  - 剪映
  - 剪映草稿
  - 剪映自动化
  - JianYing draft
  - CapCut draft
  - 批量剪辑
  - 视频批量生产
  - Python 剪映
  - 免费批量剪辑
---

# 剪映草稿自动化·批量剪辑·免费版

## 红线（先读，违反即停）

1. **不破解、不绕过、不获取账号权益**：只对**你自己创建或有合法使用权**的草稿做读写。第三方模板、购买来的草稿、网盘下载的草稿是否可改，取决于其授权，不是技术问题。
2. **加密草稿的解密仅限于你自己的草稿**：`jy-draftc` 一类工具的原理是复用本机剪映自带的 `videoeditor.dll` 加解密函数（即走剪映自己的读写流程），**不要**用于他人草稿、不要用于分发破解版。
3. **素材许可与画面责任分开**：脚本能自动拼素材，不代表素材可商用。音乐、字体、明星肖像、品牌 logo 的授权要单独确认。
4. **不承诺"一键导出"**：剪映 7.0+ 起官方隐藏了自动化控件，自动导出已不可靠。本技能会明确告诉你当前版本能自动到哪一步、哪一步必须人工点。
5. **生成物必须人工过一遍**：脚本产出的是草稿，不是成片。打开、播放、听声音、看字幕对不对轴，这一步不能省。

## 反触发（这些情况不要用本技能）

- 想要"输入一句话直接出 MP4 成片" → 本技能产出的是**剪映可编辑草稿**，最后一步成片仍需在剪映里导出（7.0+ 需手动）。
- 用的是剪映**移动端 / 网页版** → 只支持桌面版（Windows 为主，macOS 可生成草稿但导出仍要回 Windows）。
- 用的 **CapCut 国际版** → 草稿结构不同，用 `pyCapCut`，本技能不适用。
- 完全不想装 Python → 第 6 步之后都做不了，建议直接手工剪。
- 需要剪映云端工程、在线模板、官方素材库下载 → 不支持，也不应支持。

## 先看这里：你属于哪条路线

**剪映版本决定一切。动手前必须先做第 1 步体检，否则后面全是白做。**

| 你的剪映版本 | 从零生成草稿 | 模板模式（改已有草稿） | 自动批量导出 |
|---|---|---|---|
| 5.9 及以下 | ✅ | ✅ 明文直接读 | ✅ `JianyingController` |
| 6.x | ✅ | ⚠️ 需先解密 | ✅（6.8 已测） |
| 7.0 ~ 10.x | ✅ | ⚠️ 需先解密 | ❌ 控件已隐藏 |
| 11.x | ✅ | ⚠️ 需先解密 | ❌ |

**一句话记忆：生成草稿全版本可用；改已有草稿要解密；自动导出只在 6.8 及以下可靠。**

7.0+ 的现实做法是：**脚本批量生成 N 个草稿 → 人在剪映里逐个打开点导出**。仍然比手工剪快一个数量级，因为剪辑（排轨、对轴、加字幕）已经自动化了，只剩点按钮。

## 主流程

### 第 1 步：版本与环境体检（质检闸 A，不做完不许往下走）

查四件事，任何一项不符就先解决：

**① 剪映版本**
剪映 → 右上角设置/关于 → 版本号。记下来，后面全靠它。

**② 草稿目录**
剪映 → 全局设置 → 草稿位置。一般形如：
```
C:\Users\<你>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft
```
**必须**以软件里显示的为准，不要照抄路径——版本和自定义安装都会改它。

**③ Python 版本**
`pyJianYingDraft` 官方推荐 **Python 3.8 或 3.11**。3.12/3.13 可能因 `uiautomation` 依赖装不上或 import 失败。
```bash
python --version
```
不是 3.8/3.11 就建个独立环境：
```bash
# Windows
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install pyJianYingDraft
```

**④ 装没装上**
```bash
python -c "import pyJianYingDraft as draft; print(draft.__version__ if hasattr(draft,'__version__') else 'ok')"
```

**体检输出模板**（把结果填出来再继续）：
```
剪映版本：____   草稿目录：____
Python：____     pyJianYingDraft：可用/不可用
→ 路线：生成草稿（可用）/ 模板模式（需解密）/ 自动导出（可用|不可用）
```

> 常见失败：`pip install` 成功但 `import` 报 `uiautomation` 相关错。解决办法是换 Python 3.11，或先 `pip install uiautomation` 再装。

### 第 2 步：准备素材

- 素材放**同一个目录**下，路径用**绝对路径**。
- 先查素材真实时长，别拍脑袋填：
  ```bash
  ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 input.mp4
  ```
- 图片统一尺寸（如 1080×1920 竖版），分辨率不一致会让缩放位置全乱。
- 音频确认采样率，混剪时不一致会爆音。

### 第 3 步：写分镜计划（质检闸 B）

**不要直接写代码，先写计划 JSON。** 计划是可 review、可复用、可批量变型的中间层——这是自动化能不能规模化的关键。

最小计划格式：
```json
{
  "draft_name": "瓦猫-01",
  "width": 1080, "height": 1920,
  "tracks": [
    {"type": "video", "name": "v1"},
    {"type": "audio", "name": "voice"},
    {"type": "audio", "name": "bgm"},
    {"type": "text",  "name": "caption"}
  ],
  "segments": [
    {"track": "v1",      "kind": "video", "src": "C:/mat/a.mp4", "start": "0s",  "dur": "3s"},
    {"track": "voice",   "kind": "audio", "src": "C:/mat/v1.mp3","start": "0s",  "dur": "3s", "volume": 1.0},
    {"track": "bgm",     "kind": "audio", "src": "C:/mat/bgm.mp3","start": "0s", "dur": "15s","volume": 0.15, "fade_in": "1s", "fade_out": "2s"},
    {"track": "caption", "kind": "text",  "text": "云南瓦猫，守宅千年", "start": "0.5s", "dur": "2.5s"}
  ]
}
```

完整字段规范、时间写法、字幕轨、关键帧与转场，见 `references/plan-schema.md`（含一份**可直接运行的生成器脚本**）。

### 第 4 步：生成草稿

```python
import pyJianYingDraft as draft
from pyJianYingDraft import trange

FOLDER = r"C:\Users\<你>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"

df = draft.DraftFolder(FOLDER)
script = df.create_draft("瓦猫-01", 1080, 1920)

script.append_tracks([
    draft.TrackSpec(draft.TrackType.video, "v1"),
    draft.TrackSpec(draft.TrackType.audio, "voice"),
    draft.TrackSpec(draft.TrackType.audio, "bgm"),
    draft.TrackSpec(draft.TrackType.text,  "caption"),
])

script.add_segment(draft.VideoSegment(r"C:/mat/a.mp4", trange("0s", "3s")), "v1")
script.add_segment(draft.AudioSegment(r"C:/mat/v1.mp3", trange("0s", "3s")), "voice")

bgm = draft.AudioSegment(r"C:/mat/bgm.mp3", trange("0s", "15s"), volume=0.15)
bgm.add_fade("1s", "2s")
script.add_segment(bgm, "bgm")

script.add_segment(
    draft.TextSegment("云南瓦猫，守宅千年", trange("0.5s", "3s")),
    "caption",
)

script.save()
```

**要点**
- `trange("起", "持续时长")` —— 第二个参数是**时长不是结束时间**，这是最高频的错。
- 片段重叠会被检查并报错；同一轨道上要衔接就按顺序累加起止。
- 素材要先能读得到，路径错了不会在生成时报，而是剪映里显示红色感叹号。

### 第 5 步：字幕

两条路：

**A. 有 SRT 直接导入**（推荐，省事且对轴准）
```python
script.import_srt("C:/mat/sub.srt", track_name="caption")   # 轨道不存在会自动创建

# 整体延后 0.3 秒：time_offset 单位是【微秒】，必须用 tim() 换算
from pyJianYingDraft import tim
script.import_srt("C:/mat/sub.srt", track_name="caption", time_offset=tim("0.3s"))
```
⚠️ `time_offset` 单位是**微秒**——写 `0.3` 等于 0.3 微秒，肉眼完全看不出效果。要么用 `tim("0.3s")`，要么写 `300000`。

**B. 从分镜计划逐条生成文本片段**
按配音时间点切分，每句一个 `TextSegment`，时长与语音对齐。

对轴经验：字幕起点比语音**早 0.1–0.2s**、终点**晚 0.2–0.3s**，观感最舒服；单条字幕不超过 15 字，长句拆两段。

### 第 6 步：动效与转场（可选，先做减法）

只加必要的：转场统一用一种（多了廉价）、入场动画统一、BGM 必做淡入淡出。

```python
seg.add_transition(draft.TransitionType.信号故障)   # 转场挂在"前一个"片段上
seg.add_animation(draft.IntroType.斜切)             # 入场动画
```

> 版本差异：部分蒙版在新版剪映（如 10.8）上曾出现不生效，加完要在剪映里实际看一眼。

### 第 7 步：保存并回灌剪映

```python
script.save()          # DraftFolder 管理时用
# 或指定路径：script.dump(r"<草稿工程文件夹>\draft_content.json")
```

**回灌**：剪映的草稿列表不会自动刷新。存完后**重启剪映**，或进入再退出某个已有草稿，新草稿才会出现。

**备份**：`dump` 会覆盖目标 `draft_content.json`。动手前把原文件改名备份，别指望"撤销"。

### 第 8 步：导出（看清边界再选）

| 方案 | 适用 | 做法 |
|---|---|---|
| **自动批量导出** | 剪映 6.8 及以下 + Windows | `JianyingController().export_draft(name, out)`，可循环 |
| **手动导出** | 全部版本（7.0+ 唯一可靠） | 脚本生成 N 个草稿 → 剪映里逐个打开点导出 |
| **UI 自动化自研** | 有能力调试控件树时 | `uiautomation` 自行定位，版本敏感，随时失效 |

6 及以下自动导出示例：
```python
ctrl = draft.JianyingController()
ctrl.export_draft("瓦猫-01", r"D:\out\01.mp4",
                  resolution=draft.ExportResolution.RES_1080P,
                  framerate=draft.ExportFramerate.FR_24)
```
前提是剪映已打开且停在**目录页**。

### 第 9 步：批量矩阵（真正省时间的地方）

一条流水线产 N 条视频，用于电商带货、多语言版本、多素材混剪。核心是**计划与素材解耦**：同一份时间轴，换素材目录就出新片。

见 `references/batch-pipeline.md`，含断点续跑与单条失败隔离（一条挂了不影响其余）。

### 第 10 步：交付自检（每项都要过）

- [ ] 剪映能打开草稿，无"内容已损坏"提示
- [ ] 所有素材正常显示（**没有红色感叹号**）
- [ ] 总时长与计划一致
- [ ] 字幕与语音对得上轴，无遮字、无越界
- [ ] 音量分层正确（人声 > BGM，BGM 不压人声）
- [ ] 转场/动画实际播放正常（不只是时间轴上有图标）
- [ ] 至少完整播放一遍，声音连续无爆音
- [ ] 导出成片后核对帧数与时长

## 常见坑

1. **`trange` 第二参数是时长不是结束点** —— 写 `trange("0s","5s")` 是 0 到 5 秒，不是 0 到 5+5。
2. **Python 3.12/3.13 装不上** —— 用 3.11 建独立环境，别硬扛。
3. **草稿列表不刷新** —— 存完重启剪映。
4. **素材红色感叹号** —— 绝对路径写错，或素材被移动/删除。草稿只记路径，不存文件内容。
5. **`dump` 覆盖无撤销** —— 先备份 `draft_content.json`。
6. **6.0+ 加载模板报 `JSONDecodeError`** —— 草稿已加密，需先解密（见 `references/version-compat.md`）。
7. **7.0+ 自动导出失效** —— 官方隐藏控件，不是你的代码问题，改用手动导出。
8. **图片尺寸不一致** —— 统一预处理尺寸，否则缩放位置全乱。
9. **BGM 盖过人声** —— 音量 0.1~0.2，并做淡入淡出。
10. **字幕轴对不上** —— 用配音实际时长算，不要按字数猜。
11. **剪映自动升级后脚本突然失效** —— 关掉自动更新，或接受每次升级后重新体检。
12. **以为生成即成片** —— 产出的是可编辑草稿，成片仍需导出，这一步不能省。

## 失败降级

| 卡点 | 降级动作 |
|---|---|
| 库装不上 | 换 Python 3.11 venv；仍不行就放弃自动化，手工剪 |
| 6.0+ 读不了模板 | 放弃模板模式，**改走从零生成**（全版本可用） |
| 7.0+ 不能自动导出 | 批量生成草稿 + 手动逐个导出 |
| 草稿打不开 | 检查 `draft_content.json` 是否被覆盖；回退备份；确认剪映版本与草稿字段匹配 |
| 时间轴乱了 | 从最小计划（1 视频 1 音频）重新验证，逐步加轨 |
| 完全跑不通 | 用 FFmpeg + moviepy 走独立管线，彻底脱离剪映（代价：剪映素材库用不了） |

## 参考文件

- `references/plan-schema.md`：分镜计划 JSON 完整规范 + 可运行的生成器脚本 + 字幕轨与关键帧写法
- `references/version-compat.md`：版本兼容矩阵、加密草稿的处理路径、降级与 `fallback_loader` 接法
- `references/batch-pipeline.md`：批量生产流水线（带货矩阵实例、断点续跑、失败隔离、日志与产物清单）

## 依赖

- Python 3.8 或 3.11（推荐 3.11）
- `pip install pyJianYingDraft`（Apache-2.0）
- FFmpeg / ffprobe（查素材时长、预处理尺寸）
- 剪映专业版桌面版（Windows 为主）
- 可选：解密工具 `jy-draftc`（仅用于处理你自己的加密草稿）

## 相关技能推荐

- `video-script-free` — 短视频脚本创作：口播稿、分镜、标题与封面建议，与草稿生成天然衔接（先写脚本，再造草稿）
- `image-prompt-free` — AI 生图提示词，为分镜批量产出画面素材
- `print3d-free` — 3D 打印与 STL 修复；瓦猫一类的实体文创做数字化展示时配套

## 免责

本技能是**操作方法与脚本的原创整理**，不破解剪映、不获取账号权益、不下发任何剪映素材。用到的 `pyJianYingDraft` 为 Apache-2.0 开源项目，版权归原作者；解密类工具仅限处理本人草稿。剪映是字节跳动的产品，其草稿格式可能随版本变更，本技能所述兼容性基于成文时的社区验证情况，请以实际运行的剪映版本为准。素材的著作权、肖像权、音乐与字体授权由使用者自行负责。
