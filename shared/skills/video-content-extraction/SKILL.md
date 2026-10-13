---
name: video-content-extraction
version: "1.0.0"
display_name: 视频内容识别与字幕提取
display_name_en: Video Content Extraction
description_zh: 视频内容识别与字幕/剧情提取 Skill。当用户发来一个视频文件（抖音/短剧/录屏/网剧等 mp4/mov/mkv），让我"看、分析、识别、梳理剧情、提取字幕、写解说/分镜脚本"时使用。核心能力：ffmpeg 抽帧 + OCR 提取内嵌字幕 + 剧情梳理。
description_en: A skill for extracting subtitles and storylines from video files (mp4/mov/mkv). Use when the user asks to "watch/analyze/identify/extract subtitles" from a video, such as TikTok short dramas, screen recordings, or web series. Core capabilities include ffmpeg frame extraction, OCR subtitle extraction, and plot summarization.
description: >
  视频内容识别与字幕/剧情提取Skill。当用户发来一个视频文件（抖音/短剧/录屏/网剧等 .mp4/.mov/.mkv），
  让我"看、分析、识别、梳理剧情、提取字幕、写解说/分镜脚本"时使用。核心能力：ffmpeg抽帧 + OCR提取内嵌字幕 + 剧情梳理。
  触发词：看视频、分析视频、识别视频、提取字幕、视频讲什么、短剧剧情、网剧分析、视频转文字、看这个视频。
  本技能沉淀自真实踩坑：抖音短链反爬无法直读、Read读图不支持、ffmpeg缺失、whisper模型下载连环失败、OpenCV中文路径、抖音录屏结构等。
agent_created: true
---

# 视频内容识别与字幕提取（video-content-extraction）

## 一、核心结论（先看这个，别从头踩坑）

1. **链接（抖音短链等）基本无法直接读**：反爬/风控，WebFetch 只能拿到「请在 App 内观看」错误页。→ 让用户**下载成视频文件（mp4）**再处理。
2. **当前模型 Read 读图返回「不支持图像」**（does not support images）。⛔ **绝不允许凭标题/常识脑补视频内容**（本坑真实发生：曾编造过假剧情）。→ 一律走 **OCR 提字幕 / 语音转录** 拿真实文字。
3. **语音转录（whisper）模型下载成本高、连环踩坑**，非必要不走。→ **默认用 OCR 提内嵌字幕**（模型仅十几 MB，官方文字也更准）。
4. **视频可能是「App 录屏 + 循环播放」**：正片嵌界面中间、字幕固定在某一水平线、末尾可能重复第二遍。OCR 前必须先「probe 探帧」摸清结构。

## 二、标准工作流（6 步）

```
1. 拿文件(用户给mp4，非链接) → 2. 探测环境(ffmpeg/cv2) → 3. 装 imageio-ffmpeg → 4. probe探帧定位字幕行
→ 5. 全量抽帧+OCR → 6. 读字幕修正错字 → 梳理剧情/写脚本
```

### Step 1 — 拿文件
- 让用户提供本地视频文件绝对路径（如 `D:\电脑桌面\网剧.mp4`）。
- `ls -la` 确认存在 + 大小。

### Step 2 — 探测环境
```bash
VP="/c/Users/董洋/.workbuddy/binaries/python/envs/p14/Scripts/python.exe"
"$VP" -c "import cv2" 2>&1   # 大概率没有
which ffmpeg                 # 大概率没有
```

### Step 3 — 装 ffmpeg（用 imageio-ffmpeg，自带二进制）
```bash
PIP="/c/Users/董洋/.workbuddy/binaries/python/envs/p14/Scripts/pip.exe"
"$PIP" install -i https://pypi.tuna.tsinghua.edu.cn/simple/ imageio-ffmpeg rapidocr-onnxruntime
```
- **pip 一律走清华源** `-i https://pypi.tuna.tsinghua.edu.cn/simple/`（默认源超时）。
- ffmpeg 路径从代码拿：`import imageio_ffmpeg; ff = imageio_ffmpeg.get_ffmpeg_exe()`。

### Step 4 — probe 探帧（关键！先摸清结构再全量 OCR）
- 先取几个时间点（如每 20s 一帧）**全图 OCR**，判断：
  - 是否 App 录屏（画面里有固定 UI：点赞数、作者、标题）
  - 字幕在哪一条水平线（抖音竖屏录屏常固定在中下部，如 y≈515，**不是底部**）
  - 正片时长 / 是否循环
- 代码要点：**OpenCV imread 不认中文路径**，必须用 `np.fromfile + imdecode`：
```python
import cv2, numpy as np
img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
```

### Step 5 — 全量抽帧 + OCR 字幕
```bash
# 每秒抽 2 帧（10 分钟约 1200 帧，够用）
ff -y -i src -vf "fps=2,scale=432:-1" -q:v 3 out_%04d.jpg
```
- OCR 只裁**字幕行区域**并放大 2x（提升识别率），过滤 UI 干扰。
- RapidOCR 用法（新版返回两个值 `result, elapse`，result 每项 `[box, text, score]`）：
```python
from rapidocr_onnxruntime import RapidOCR
eng = RapidOCR()
res, _ = eng(crop_img)   # res: list of [box, text, score]
```

### Step 6 — 读字幕 → 修正错字 → 梳理剧情
- OCR 结果按时间戳排序，修正常见错字（人名、谐音、竖排误读）。
- 识别循环点（字幕从某处开始重复 → 正片实际时长更短）。
- 输出：完整字幕（带时间轴）+ 剧情脉络（分段），再按需写解说/分镜脚本。

## 三、踩坑清单（含解法，逐个对照）

| # | 坑 | 现象 | 解法 |
|---|---|---|---|
| 1 | 抖音短链反爬 | WebFetch 返回「请在 App 内观看」 | 让用户下载 mp4 本地处理 |
| 2 | Read 读图不支持 | 返回 does not support images | 走 OCR/转录，禁脑补 |
| 3 | 系统无 ffmpeg | `which ffmpeg` 空 | pip 装 imageio-ffmpeg，用 get_ffmpeg_exe() |
| 4 | pip 默认源超时 | 装包卡死/超时 | 加 `-i 清华源` |
| 5 | whisper 模型下载失败 | 代理502 / Xet 401 / SSL超时 / 直连26KB/s | 放弃转录，改 OCR；见下方 whisper 专项 |
| 6 | curl 写中文路径乱码 | 写入 `董洋` 变 `¶­Ñó` 失败 | 用 Python(urllib/requests) 下载 |
| 7 | OpenCV imread 中文路径失败 | 返回 None | np.fromfile + cv2.imdecode |
| 8 | 抖音录屏结构 | 正片嵌中间、字幕在 y≈515、末尾循环 | 先 probe 探帧定位，再全量 OCR |
| 9 | RapidOCR 返回结构变化 | 新版返回 (res, elapse) 二元组 | 解包两个值；res 项是 [box,text,score] |

### whisper 语音转录专项（能不走就不走）
踩坑全记录：`HF_ENDPOINT=hf-mirror.com` 下模型文件走 Xet 协议 401 → `HF_HUB_DISABLE_XET=1` → LFS 重定向到 CDN 后 SSL 握手超时 → curl 走代理能下(206)但中文路径乱码 → Python 直连只有 26KB/s（460MB 需数小时）。
**结论**：模型 460MB + 网络受限，成本远高于 OCR。**除非视频没有内嵌字幕**，否则一律 OCR。真需要转录时：小文件走代理 curl，model.bin 用 Python 断点续传 + 走代理。

## 四、自带脚本（scripts/）

skill 已内置两个参数化脚本，改好路径/参数直接跑：

| 脚本 | 作用 | 用法 |
|---|---|---|
| `scripts/01_probe.py` | 探帧定位字幕行 + 摸清视频结构 | `python 01_probe.py <视频路径>` |
| `scripts/02_extract.py` | 抽帧 + OCR 提字幕一步到位 | `python 02_extract.py <视频路径> [输出目录]` |

- 跑之前按 01_probe 的结果，改 `02_extract.py` 顶部的 `CROP_TOP/CROP_BOTTOM`。
- 运行 Python 用下方「环境速查」里的 p14 venv。
- 依赖包若缺失，按 Step 3 命令重装（走清华源）。

## 五、环境速查（本项目已就绪）

- Python venv：`C:\Users\董洋\.workbuddy\binaries\python\envs\p14\Scripts\python.exe`（已装 imageio-ffmpeg、rapidocr-onnxruntime、python-docx）
- pip：同目录 `pip.exe`，配清华源
- 系统无 ffmpeg（靠 imageio-ffmpeg 二进制）
- 工作区：`C:\Users\董洋\WorkBuddy\2026-09-02-08-56-24\`（临时帧 `.tmp_frames/`、音频 `.tmp_audio/`、生图 `.gen/`）

## 六、产出物链条（本项目实际产出，供复用）

视频 → ①完整字幕修正版.md（带时间轴）→ ②剧情脉络 → ③欧美风分镜脚本.md → ④可视化 Storyboard.html → ⑤完整分镜脚本.docx（含每镜中文 AI 生图提示词 + 结尾钩子）→ ⑥ImageGen 实跑验证关键镜头。
- 分镜脚本 Word 用 python-docx 生成，蓝白商务风，提示词段落加浅蓝底纹。
- 生图走 ImageGen（约 5–10 积分/张），**批量前必须先列清单+积分预算让用户确认**。
