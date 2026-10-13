---
name: ai-short-video-maker
description: Build short custom videos (birthday greetings, children's stories,
  store promos) from a text brief using AI image/video generation, offline TTS,
  and ffmpeg post-production. Use when the user asks for an AI-generated
  narrative short video, animated greeting, or wants to prototype a faceless
  video-delivery service.

version: "1.0.0"
display_name: "AI 短视频生成器"
display_name_en: "AI Short Video Maker"
description_zh: "从一段文字简介生成 15-30 秒叙事短视频：AI 生图/生视频 + 离线 TTS 配音 + ffmpeg 后期合成，自带中文字幕，全程无真人出镜（faceless）。适用于生日祝福、儿童故事、门店开业/活动宣传、节日问候等定制短片，可在单个 WorkBuddy 工作区内运行。"
description_en: "Turn a one-paragraph brief into a 15-30s narrative short video: AI image/video generation + offline TTS voice-over + ffmpeg post-production, with Chinese subtitles, fully faceless. For birthday greetings, kids' stories, store/event promos, festival messages. Runs inside a single WorkBuddy workspace."
agent_created: true
---

# AI Short Video Maker

## Overview

Turn a one-paragraph brief into a 15–30 second narrative short video with original characters, Japanese-anime/cinematic style, Chinese subtitles, and synthetic voice-over. The pipeline is fully faceless, uses only local/offline tools for audio assembly, and is designed to be run inside a single WorkBuddy workspace.

Typical outputs:
- Custom birthday greeting videos for kids (e.g. "Naruto-style ninja boy, name Lele, 12 years old")
- Animated children's bedtime stories
- Short store-opening / event promotional clips
- Personalized festival / anniversary greetings

## Dependencies

- **ffmpeg** must be available. The bundled `scripts/assemble_video.py` uses `imageio-ffmpeg` to locate the ffmpeg binary — install with `pip install imageio-ffmpeg`, or ensure `ffmpeg` is on PATH.
- **Offline TTS**: `pip install pyttsx3` (Windows ships a `zh-CN` voice; macOS/Linux fall back to any system voice or a silent subtitle-only version).
- Image/video generation uses the host's `ImageGen` / `VideoGen` tools — no extra install.

## Trigger Conditions

Use this skill when the user requests:
- "帮我做一个生日祝福视频"
- "用 AI 生成一段动画/短视频"
- "给我打个样：XX 风格，主角叫 XX"
- Any request to prototype a faceless AI video-delivery service on a platform like Xianyu/Taobao/Fiverr

## Required Inputs

Before starting production, confirm with the user (or infer from context):

1. **Recipient / protagonist** (name, age, gender if relevant)
2. **Theme / style** (e.g. ninja/anime/fantasy/space/cute)
3. **IP constraints** — never generate copyrighted characters (Naruto, Disney, etc.). Use "XX-style original character" wording instead.
4. **Total length target** — default 15–20 seconds (3–4 clips of ~5s each + end card)
5. **Language of subtitles / voice** — default Simplified Chinese with Microsoft Huihui offline TTS
6. **Output directory** — default `<workspace>/produce/<project-slug>/`

## Production Pipeline

### Step 1: Create output directory and write storyboard

1. Create `<out_dir>`.
2. Write `<out_dir>/分镜脚本.md` with:
   - 3–4 scenes, each ~5 seconds
   - Subtitle text per scene (keep under 20 Chinese characters for readability)
   - End card text (big + small line)
   - Note: All Chinese text is added in post-production; do not ask the image/video model to render text.

### Step 2: Character design image

Use `ImageGen` to generate a **character sheet** (full-body, neutral pose) matching the requested style. Requirements:
- Mention "original character" and avoid any copyrighted names/symbols.
- Use `size: 1024x1536` for the character sheet.
- Save to `<out_dir>/character_sheet.png`.

### Step 3: Scene keyframes (image-to-image locked to character sheet)

Generate one 16:9 keyframe per scene using `ImageGen` with `image: character_sheet.png` and `input_fidelity: high`. Save as:
- `scene01_<slug>.png`
- `scene02_<slug>.png`
- `scene03_<slug>.png`

If two parallel generations produce the same timestamp filename and overwrite each other, re-run the overwritten scene afterward.

### Step 4: Video clips (image-to-video)

Use `VideoGen` in **image-to-video** mode for each keyframe:
- `seconds: 5`
- `resolution: 720P`
- **Do NOT pass `aspect_ratio`** — the backend rejects `"16:9"` and returns HTTP 400.
- Prompt should describe subtle, cinematic motion consistent with the scene.
- Save clips as `clip01.mp4`, `clip02.mp4`, `clip03.mp4`.

### Step 5: TTS audio

Use offline TTS so the pipeline does not depend on network services:

```python
import pyttsx3
engine = pyttsx3.init()
engine.setProperty('voice', r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ZH-CN_HUIHUI_11.0')
engine.setProperty('rate', 170)
engine.save_to_file(text, 's1.mp3')
engine.runAndWait()
```

Generate one audio file per subtitle line plus the end card line.

If the target environment lacks the Huihui voice, fall back to any `zh-CN` system voice or produce a silent subtitle-only version and tell the user.

### Step 6: Assembly with ffmpeg

Use the bundled script `scripts/assemble_video.py`:

```bash
python <skill_dir>/scripts/assemble_video.py --dir <out_dir>
```

The script expects:
- `clip01.mp4`, `clip02.mp4`, `clip03.mp4`
- `s1.mp3`, `s2.mp3`, `s3.mp3`, `s4.mp3`
- `scene03_<slug>.png` (used for the 3-second end card background)
- `msyh.ttc` or `simhei.ttf` copied into `<out_dir>` (the script will try to copy it from `C:/Windows/Fonts/` automatically)

The script outputs `<out_dir>/<title>_成片.mp4`.

## Critical Pitfalls (learned from production)

| Issue | Fix |
|---|---|
| `VideoGen` rejects `aspect_ratio: "16:9"` | Omit `aspect_ratio` entirely; default works. |
| AI-generated Chinese text is garbled | Never ask the model to draw text. Add all text via ffmpeg `drawtext`. |
| Windows font path breaks ffmpeg filter parsing | Copy the font file into the output directory and reference it by filename only. |
| Still-image end card has different fps/timebase than video clips | Force `-r 24` when generating the end card segment. |
| Video clips have different lengths due to audio trimming | Use `-shortest` per segment; final concat with `concat` demuxer handles it. |
| Copyright strike on commercial platforms | Use "XX-style original character" never "Naruto/Spider-Man/Disney character". |

## Cost Benchmark

Typical 15–20 second video:
- 1 character sheet + 3 keyframes ≈ 30–50 image-gen credits
- 3 × 5-second video clips ≈ 150–300 video-gen credits
- ffmpeg assembly ≈ 0 credits

## Quality Bar for Commercial Use

Before listing the service on a trading platform, verify:
- Character consistency across all scenes (no face/clothing drift)
- Subtitles render correctly in Chinese
- Audio is intelligible and synced
- Total render cost leaves healthy margin at the chosen price (recommended ¥49–199 per video)

## Resources

- `scripts/assemble_video.py` — full ffmpeg assembly pipeline (subtitle burn-in, audio mix, end card, concat).
