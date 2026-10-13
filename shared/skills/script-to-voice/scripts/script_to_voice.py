#!/usr/bin/env python3
"""Convert a script (JSON storyboard or plain text) into narration audio.

Supports two input formats:
  1. JSON script with {"scenes": [{"dialogue": "..."}]} structure (AI video script)
  2. Plain text file (each paragraph becomes part of the narration)

Usage:
    python script_to_voice.py script.json -o narration.mp3 --voice zh-CN-XiaoxiaoNeural
    python script_to_voice.py story.txt --rate "+10%"

Dependencies:
    pip install edge-tts
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path


def _get_edge_tts():
    """Lazy-import edge_tts so that importing this module never crashes."""
    try:
        import edge_tts
        return edge_tts
    except ImportError:
        print("缺少依赖 edge-tts，请先安装：pip install edge-tts", file=sys.stderr)
        sys.exit(1)

# 常用中文音色（微软 Edge TTS，免费无 Key）
VOICE_PRESETS = {
    "female-lively": "zh-CN-XiaoxiaoNeural",   # 女声·活泼（口播常用）
    "female-soft": "zh-CN-XiaoyiNeural",        # 女声·温柔
    "male-standard": "zh-CN-YunxiNeural",       # 男声·阳光
    "male-mature": "zh-CN-YunjianNeural",       # 男声·浑厚（解说常用）
}


def clean_dialogue(dialogue: str) -> str:
    """Clean one dialogue block: drop role prefixes and (action hints), join lines."""
    parts = []
    for line in dialogue.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "：" in line:  # drop role prefixes like 「老爸：」
            line = line.split("：", 1)[1]
        elif ":" in line:  # half-width prefix, e.g. "Narrator: ..." (avoid URLs)
            prefix, rest = line.split(":", 1)
            if len(prefix) <= 12 and "/" not in prefix and " " not in prefix and not rest.startswith("//"):
                line = rest
        line = re.sub(r"[（(][^)）]*[)）]", "", line)  # drop (action hints)
        line = line.strip()
        if line:
            parts.append(line)
    return "。".join(parts)


def extract_text(input_path: Path) -> str:
    """Extract narration text from JSON script or plain text file."""
    content = input_path.read_text(encoding="utf-8")

    if input_path.suffix.lower() == ".json":
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}", file=sys.stderr)
            sys.exit(1)
        scenes = data.get("scenes")
        if scenes and isinstance(scenes, list):
            blocks = []
            for scene in scenes:
                dialogue = scene.get("dialogue") if isinstance(scene, dict) else None
                if dialogue:
                    blocks.append(clean_dialogue(str(dialogue)))
            if blocks:
                return "。".join(blocks)
        # 兜底：JSON 但无 scenes 结构，视为纯文本
        print("提示: JSON 无 scenes[].dialogue 结构，按纯文本处理", file=sys.stderr)

    # 纯文本：按空行分段，段内 clean（同样去括号提示）
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    cleaned = [clean_dialogue(p).replace("\n", "。") for p in paragraphs]
    return "。".join(cleaned)


async def synthesize(text: str, out_path: Path, voice: str, rate: str, volume: str = "+0%"):
    edge_tts = _get_edge_tts()
    print(f"音色: {voice} | 语速: {rate} | 文本长度: {len(text)} 字")
    comm = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await comm.save(str(out_path))
    print(f"已保存: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="剧本/文稿转口播音频（免费音色，无需 API Key）")
    parser.add_argument("input", help="输入文件：JSON 剧本或 txt 文稿")
    parser.add_argument("-o", "--output", help="输出 mp3 路径（默认与输入同名 .mp3）")
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural",
                        help=f"音色名称或预设（预设: {', '.join(VOICE_PRESETS)}）")
    parser.add_argument("--rate", default="+0%", help="语速调整，如 +10%% 或 -15%%（默认 +0%%）")
    parser.add_argument("--volume", default="+0%", help="音量调整，如 +20%%（默认 +0%%）")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"输入文件不存在: {input_path}", file=sys.stderr)
        sys.exit(1)

    voice = VOICE_PRESETS.get(args.voice, args.voice)  # 支持预设别名
    out_path = Path(args.output) if args.output else input_path.with_suffix(".mp3")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    text = extract_text(input_path)
    if not text.strip():
        print("未提取到有效文本", file=sys.stderr)
        sys.exit(1)

    asyncio.run(synthesize(text, out_path, voice, args.rate, args.volume))


if __name__ == "__main__":
    main()
