---
name: script-to-voice
slug: script-to-voice
displayName: 剧本配音合成器
summary: 把剧本或文稿转成口播配音：自动清洗对白、多音色语速可调、输出MP3，免费音色无需Key。
license: MIT
version: 1.0.0
description: 剧本/文稿转口播配音技能。当用户要求给短视频剧本配音、生成解说旁白、把文字转成语音、制作有声书音频、文本转 MP3、给分镜脚本加配音时使用此技能。支持 JSON 分镜剧本自动清洗（去角色前缀、去动作提示）与纯文稿两种输入，多音色多语速可调，使用免费音色引擎无需任何 API Key。
display_name: "剧本配音合成器"
display_name_en: "Script to Voice Narration"
description_zh: "把剧本或文稿转成口播配音：自动清洗对白、多音色语速可调、输出MP3，免费音色无需Key。"
description_en: "Turn scripts or manuscripts into narration audio: auto-cleaned dialogue, multiple voices and rates, MP3 output, free without any API key."
category: "content-creation"
author: "Frank"
---

# 剧本配音合成器（Script to Voice）

把 AI 生成的分镜剧本（JSON）或任何文稿（txt）转成带情感的人口播音频。基于微软 Edge 免费音色引擎，无需 API Key、无需联网账号。

## 什么时候用

用户说"给剧本配音 / 生成旁白 / 文字转语音 / 做配音 / 朗读这段稿子 / 有声版"等。

## 使用方法

```bash
# JSON 分镜剧本（自动去「角色：」前缀与（动作提示），只念台词）
python <skill-dir>/scripts/script_to_voice.py 剧本.json

# 纯文稿
python <skill-dir>/scripts/script_to_voice.py 文稿.txt -o 解说.mp3

# 换音色（男声解说）+ 放慢语速
python <skill-dir>/scripts/script_to_voice.py 剧本.json --voice male-mature --rate "-10%"

# 指定完整音色名
python <skill-dir>/scripts/script_to_voice.py 文稿.txt --voice zh-CN-YunxiNeural
```

## 依赖安装（一次性）

```bash
pip install edge-tts
```

## 音色预设

| 预设名 | 音色 | 适用 |
| --- | --- | --- |
| `female-lively`（默认） | 晓晓·活泼女声 | 抖音口播、剧情解说 |
| `female-soft` | 晓伊·温柔女声 | 情感文案、助眠内容 |
| `male-standard` | 云希·阳光男声 | 日常口播 |
| `male-mature` | 云健·浑厚男声 | 纪录片式解说、修仙/玄幻旁白 |

也支持 400+ 完整音色名（各地方言、英语、日语等），见 edge-tts 官方列表。

## 输入格式

**格式一：JSON 分镜剧本**（AI 短视频工作流产物）
```json
{
  "scenes": [
    {"dialogue": "老爸：你这是什么表情？\n（推了推眼镜）我看不懂但大受震撼"},
    {"dialogue": "儿子：爸，这叫赛博朋克。"}
  ]
}
```
自动处理：去掉「角色：」前缀 → 去掉（括号动作）→ 逐场景衔接。

**格式二：纯文本**：按空行分段直接朗读，同样自动清理括号提示。

## 工作流建议（Agent 使用时）

1. 确认输入文件与期望风格（口播/解说/情感），选对应音色预设
2. 检查依赖：无则 `pip install edge-tts`
3. 运行脚本；长文稿（>5000字）建议分章节多次合成再拼接
4. 汇报输出文件路径与时长；提醒用户 MP3 可直接导入剪映对轨

## 组合场景

与"剧本创作"类技能/专家配合：剧本 JSON → 本技能配音 → 图片/数字人视频 → 剪映合成，形成完整短视频流水线。

## 边界与注意

- 免费引擎有并发礼貌限制，大量合成时在调用间加 1-2 秒间隔
- 不做音色克隆、不做多角色分别配音（同一文件单音色）；需要多角色时可按角色拆分文件分别合成
