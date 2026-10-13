---
name: auto-video-editor
description: 本地自动剪辑与音频处理引擎，带窗口化操作面板。用 ffmpeg + numpy 在机器本地完成「去静音跳剪、按镜头自动切分、跟着音乐节拍卡点剪辑、批量裁切拼接变速、竖屏裁切」等成片前处理，以及「降噪、低切高切、噪声门、三段 EQ、压缩、立体声处理、响度归一化」等音频处理，全程离线、原素材不上传。自带一个深色剪辑台面板（浏览器窗口打开，时间线/波形/参数/试听/预览/导出齐全）。触发词：剪视频、自动剪辑、批量剪辑、去静音、静音跳剪、口播剪辑、卡点视频、卡点剪辑、按鼓点剪、镜头切分、分镜切分、视频切段、自动剪片、vlog 剪辑、视频压缩、竖屏适配、音频处理、降噪、去底噪、噪声门、响度归一化、LUFS、人声靠前、去人声、伴奏提取、加速静音段、跳剪、cut silence、auto edit video、beat sync、scene split、denoise。
display_name: "自动剪辑台"
display_name_en: "Auto Video Editor"
description_zh: "本地离线完成自动剪辑与音频处理：去静音跳剪、按镜头切分、音乐卡点、降噪、响度归一化，自带深色剪辑台面板，可试听、预览、导出。"
description_en: "Local, offline automatic video editing and audio processing: silence cutting, scene splitting, beat-sync editing, denoising and loudness normalisation, with a built-in dark editing panel."
visibility: "public"
agent_created: true
version: 1.1.0
author: "kyle"
---

# 自动剪辑台

把「成片前处理」这件事自动化：一段素材进去，去掉废话、按节奏切好、音量调平、按平台比例出片。
所有计算在本机完成，用 ffmpeg 做像素和采样，不外传任何文件。

## 何时用 / 何时不用

**用**：口播/教程/访谈去静音、素材按镜头切段、音乐卡点 MV、批量转码压缩、竖屏适配、
响度统一、录音降噪与音色处理、底噪/哼声诊断。

**不用**：
- 用户要精修单帧、调色、加转场特效、做复杂多轨叠加 → 这是 NLE（剪映/PR）的活，本 skill 不替代
- 用户要的不是剪辑而是**设计稿** → 走 Ardot
- 用户要的是**画面素材生成**（文生图/文生视频）→ 走 Miora
- 用户要**真·人声分离**（卡拉OK 级去人声、提取干净伴奏）→ 本 skill 只有 mid-side
  矩阵近似，差一个量级。真分离要上 Demucs 一类模型，本机装不了
  （PyTorch 已停止支持 macOS x86_64）

## 先自检环境

```sh
<SKILL>/run.sh doctor          # 看状态
<SKILL>/run.sh doctor --fix    # 缺什么自动装（ffmpeg 静态包 + numpy）
```

`<SKILL>` = `~/.workbuddy/skills/auto-video-editor`。
依赖只装进 skill 自己目录（`bin/` 放二进制、`.venv/` 放 python 包），**不碰系统目录、不需要 Homebrew、不需要管理员权限**。

## 三条主链路

### 1. 去静音 —— 口播、教程、访谈

```sh
run.sh auto in.mp4 -o out.mp4 --mode silence \
  --noise-db -30 \      # 静音阈值，越低越严格（默认 -30）
  --min-silence 0.35 \  # 短于 0.35s 的停顿不动它，保呼吸感
  --min-keep 0.25       # 最短保留片段，防止成片碎成一地
```

`--silence-mode speed` 改成「静音段加速播放」而不是删掉，适合需要保持时间连续性的场景。
`--silence-speed 4` 控制加速倍率。

### 2. 分镜切分 —— 素材整理、按镜头拆条

```sh
run.sh auto in.mp4 -o out.mp4 --mode scene \
  --threshold 0.30 \    # 0~1，越大越迟钝，只抓硬切
  --min-scene 0.6       # 两个切点最短间隔，滤抖动
```

### 3. 卡点 —— 音乐 MV、快剪

```sh
run.sh auto in.mp4 -o out.mp4 --mode beat --music bgm.mp3 \
  --beats-per-cut 2 \   # 每 2 拍切一次
  --stride 1.35         # 跳剪步进：1=画面连续，>1 有跳跃感
```

多素材素材墙：把目录传进去。

```sh
run.sh auto ./clips/ -o out.mp4 --mode beat --music bgm.mp3
```

## 音频处理

链路上分两段，位置不同、作用不同：

```
素材片段 → 拼接 → 【人声链】→ 与 BGM 混音 → 【母带链】→ 输出
                   降噪/EQ/压缩              响度/限幅/淡入淡出
```

人声链放在拼接**之后**而不是每段之前，是因为降噪和压缩需要连续上下文；
逐段处理会在每个剪辑点留下可听的接缝。母带链放在混音之后，因为它管的是
全片的最终电平。

### 一键预设

```sh
run.sh auto in.mp4 -o out.mp4 --audio-preset voice      # 口播/配音
run.sh auto in.mp4 -o out.mp4 --audio-preset interview  # 访谈/多人
run.sh auto in.mp4 -o out.mp4 --audio-preset outdoor    # 户外/Vlog
run.sh auto in.mp4 -o out.mp4 --audio-preset rescue     # 废片抢救
run.sh auto in.mp4 -o out.mp4 --audio-preset hum        # 电流声/空调嗡嗡声
run.sh auto in.mp4 -o out.mp4 --audio-preset music      # 音乐为主
```

### 手工调

```sh
run.sh auto in.mp4 -o out.mp4 \
  --denoise standard \        # none | light | standard | strong
  --highpass 80 --lowpass 14000 \
  --gate --gate-db -38 \      # 门限必须高于素材实测底噪
  --warmth 1.5 --presence 2 --deess -2 \
  --compress --comp-db -18 --comp-ratio 3 \
  --stereo center_remove \    # keep | center_boost | center_remove | mono
  --gain-db 2
```

### 只出音频 / 量底噪

```sh
run.sh audio in.mp4 -o voice.m4a --denoise standard    # 纯音频处理，不碰画面
run.sh audio in.mp4 --measure                          # 量底噪、信噪比、工频哼声
run.sh audio a.mp4 b.mp4 c.mp4 -o joined.m4a           # 顺带拼成一条
run.sh auto in.mp4 -o out.m4a --audio-only --denoise strong
```

## ⚠️ 音频处理的四条实测结论（都是踩出来的，别推翻）

**1. 「更强的降噪」不存在，加深只会连人声一起削。**
同一素材实测（干净人声已知，算的是真正的输出信噪比增益）：

| afftdn 参数 | SNR 增益 | 底噪降低 |
|---|---|---|
| nr=12 nf=-44 | **+5.0dB** | -2.9dB |
| nr=16 nf=-38 | +3.9dB | -3.7dB |
| nr=20 nf=-36 | +2.8dB | -3.9dB |
| nr=30 nf=-32 | +0.0dB | -4.4dB |
| nr=40 nf=-30 | -1.6dB | -4.7dB |

所以 `standard` 用的是最优的 `nr=12 nf=-44`，而 `strong` **不是**更狠的降噪，
而是「标准降噪 + 一道 -38dB 噪声门」——门只作用于静音段，而底噪正好待在
静音段里，人声根本不经过它。实测代价仅 0.1dB SNR，换来 0.7dB 底噪下降。

**2. 级联两级 afftdn 有害，不要试。** 一级把噪声清空后，二级找不到噪声会
误判并注入伪影——实测「底噪降低」是 **+5dB**，噪声不降反升。

**3. 所有降噪器对工频哼声（50Hz）无效。** 那是频段问题不是噪声问题，
要用 `--highpass` 解决。`hum` 预设因此只做低切、不开降噪。
粉噪（房间底噪）也基本无效，别指望。

**4. 响度必须走两遍 loudnorm。** 单遍是动态模式，增益随时间自适应爬升，
几秒的短片还没收敛就结束了——实测目标 -16 LUFS 跑出 -14.5，偏 1.5dB。
现在是先探测一遍拿实测值，再带 `measured_*` + `linear=true` 走第二遍，
三段测试实测落点 -16.00 / -14.02 / -19.01。

**另外两条容易翻车的：**

- **FFT 滤波器有固有延迟**：afftdn 在 48kHz 下把音轨整体推后 24ms，
  已经到唇音能察觉的量级。链路会自动量出延迟并切掉开头对齐，
  实测残余偏移 +0.6ms。
- **「人声靠前」只在立体声下有效**：它靠 mid/side 矩阵，而折叠成单声道
  就只取 mid，任何对称矩阵都改不动 mid 内部的中置/侧向配比——这是数学
  决定的。单声道想要人声靠前，只能上声源分离。「去人声」不受此限。

## 窗口化面板

```sh
run.sh panel                 # 默认 http://127.0.0.1:8787
run.sh panel --open a.mp4 --open bgm.mp3   # 启动即载入
```

面板能力：拖拽导入 / 粘路径导入 · 波形+静音区+镜头切点+节拍点全画在时间线上 ·
滚轮缩放 · 拖动平移 · 点片段可临时停用 · 低清预览渲染 · 一键导出。
音频区还有：一键预设下拉 · 「自动」按实测底噪填参数 · 「试听处理后的音轨」
（走和成片完全一样的处理链，听到什么成片就是什么）。
服务只监听 `127.0.0.1`，不对外暴露。

## 先出方案再渲染

任何模式都可以只出方案、不动像素，用来先看剪辑点和时长账：

```sh
run.sh auto in.mp4 --mode silence --plan-only --json > plan.json
run.sh render plan.json -o out.mp4      # 之后再渲染
run.sh auto in.mp4 --mode scene --dry-run   # 只打印 filtergraph
```

方案是纯 JSON（`sources` + `segments` + `output`），可以手改片段再渲染。

## 输出与画质

```sh
--crf 20            # 18~23 清晰，26+ 体积小
--preset veryfast
--loudnorm          # 响度归一化到 -16 LUFS（短视频平台通用）
--fade-in 0.5 --fade-out 0.5
--vertical 9:16     # 竖屏；--size 1080x1920 自定义
```

默认输出目录：`~/Movies/avx-output/`。

## 能力边界（别承诺做不到的）

**能**：时间线级的剪辑（切、删、变速、拼接）、基于信号的自动决策（静音/镜头/节拍）、
音频处理（降噪、滤波、EQ、压缩、门、立体声、响度归一化、淡入淡出）、编码与尺寸适配。

**不能**：
- 画面级特效：转场、调色、滤镜、关键帧动画、字幕样式 —— ffmpeg 有但这套引擎没做
- 语义理解：它不知道「这段讲得不好」，只认信号。**自动剪辑出来的是初稿，不是终稿**
- 语音转写/自动字幕 —— 未包含，需要另接 whisper
- 人声/伴奏真分离 —— 面板里的「人声靠前 / 去人声」是 mid-side 矩阵近似，
  不是声源分离。对中置人声的普通立体声混音有效，对已做宽的人声基本无效
- 卡点是主观活，节拍检测再准也要人过一遍

**要跟用户说清楚**：这几条链路产出的都是**粗剪**。省掉的是机械劳动，不是创作判断。

## 实测精度（本机实测，2026-09-16）

| 检测项 | 结果 |
|---|---|
| 静音段 | 6/6 命中，边界误差 ≤ 0.072s |
| 镜头切点 | 3/3 命中，误差 0.000s |
| 节拍点 | 59/59 命中，偏差 ≤ 0.048s，BPM 117.5（实际 120） |
| 处理速度 | 24s 音频全量分析约 1.6s |
| 响度落点 | 目标 -16 / -14 / -19 LUFS → 实测 -16.00 / -14.02 / -19.01 |
| 音画同步 | 全套处理链下残余偏移 +0.6ms |
| 降噪 | 标准档 SNR +7.8dB；强档（=标准+门）SNR +11.8dB |
| 工频哼声判别 | 哼声素材 +22.4dB vs 白噪 -8.1dB，判别间隔 30dB |

复现：`python3 tests/run_tests.py`（会生成带标准答案的测试素材，跑完自动清理）
音频专项：`python3 tests/test_audio_e2e.py`

> `tests/` 是开发期的验证脚本（含参数扫描），**不随市场包分发**——官方包结构只允许
> `SKILL.md` 加 `scripts/` `references/` `templates/` 三个子目录。上面这些数字是发布前
> 在源码目录里跑出来的实测值，不是估的。

## 排查

| 现象 | 处理 |
|---|---|
| `[环境缺失] 未找到 ffmpeg` | `run.sh doctor --fix` |
| 卡点报「需要 numpy」 | `run.sh doctor --fix` |
| 说「没有检测到镜头切换」 | 调低 `--threshold` 到 0.2 附近 |
| 节拍点太少 | 调高 `--sensitivity`；或先听前奏有没有鼓点，用 `--lead-in` 跳过前奏 |
| 成片碎得厉害 | 调大 `--min-keep`（去静音）/ `--min-scene`（分镜）/ `--beats-per-cut`（卡点） |
| 渲染慢 | 提高 `--crf`、用 `--preset veryfast`、或先 `--preview` 验证节奏 |
| 降噪后声音发闷、人声变远 | 降噪过猛了。往下退一档——实测加深降噪只会连人声一起削，别硬加 |
| 噪声门没反应 | 门限低于素材底噪，门关不上。先用 `--measure` 量底噪，门限设在底噪之上 |
| 有嗡嗡声降噪降不掉 | 那是工频哼声，降噪器对它无效。用 `--highpass 100`（或 `--audio-preset hum`） |
| 静音段加速后仍然听到嗡嗡声 | 同理，用低切 |

ffmpeg 也可换成系统自带的：设 `AVX_FFMPEG` / `AVX_FFPROBE` 环境变量指向自己的二进制。

## 代码结构

```
run.sh                  统一入口
scripts/
  avx.py                命令行
  panel.py              本地面板服务
  doctor.py             环境自检/自动安装
  ff.py                 ffmpeg/ffprobe 定位与调用
  model.py              EditPlan / Segment 数据结构
  audio.py              音频处理链 · 预设 · 底噪/响度/延迟测量
  analyze.py            静音 · 镜头 · 节拍 · 波形 · 方案生成
  render.py             filtergraph 编译与渲染
templates/              面板前端（HTML/CSS/JS，无外部依赖）
bin/                    静态 ffmpeg / ffprobe（doctor --fix 自动装，不随包分发）
tests/                  带标准答案的端到端自测 + 参数扫描（开发期用，不随包分发）
```
