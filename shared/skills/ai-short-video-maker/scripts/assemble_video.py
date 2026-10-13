#!/usr/bin/env python3
"""
Assemble AI-generated short video from clips + TTS + subtitles.

Reads a `video_config.json` from the project directory and outputs
`<title>_成片.mp4`.

Example video_config.json:
{
  "title": "乐乐12岁生日祝福",
  "clips": [
    {"video": "clip01_rooftop.mp4", "audio": "s1.mp3", "text": "乐乐！听说今天是你的大日子！"},
    {"video": "clip02_cake.mp4", "audio": "s2.mp3", "text": "看我的——通灵之术·生日蛋糕！"},
    {"video": "clip03_fireworks.mp4", "audio": "s3.mp3", "text": "12岁，向着火影的道路，全速前进！"}
  ],
  "end_card": {
    "image": "scene03_fireworks.png",
    "audio": "s4.mp3",
    "text_big": "乐乐 生日快乐",
    "text_small": "永远做自己的忍者"
  }
}
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

from imageio_ffmpeg import get_ffmpeg_exe


def ensure_font(project_dir):
    """Copy a Chinese font into the project dir so ffmpeg drawtext paths stay simple."""
    candidates = [
        (r'C:\Windows\Fonts\msyh.ttc', 'msyh.ttc'),
        (r'C:\Windows\Fonts\simhei.ttf', 'simhei.ttf'),
    ]
    for src, name in candidates:
        dst = os.path.join(project_dir, name)
        if os.path.exists(dst):
            return name
        if os.path.exists(src):
            shutil.copy(src, dst)
            return name
    raise RuntimeError('No suitable Chinese font found in C:\\Windows\\Fonts')


def probe_size(ffmpeg, path):
    cmd = [ffmpeg, '-i', path]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        out = e.stderr
    else:
        out = ''
    m = re.search(r'Video: .*? (\d{3,})x(\d{3,})', out)
    if not m:
        raise RuntimeError(f'Could not probe video size: {out[:500]}')
    return int(m.group(1)), int(m.group(2))


def build_segment(ffmpeg, project_dir, font, idx, w, h, clip_cfg):
    vin = os.path.join(project_dir, clip_cfg['video'])
    ain = os.path.join(project_dir, clip_cfg['audio'])
    out = os.path.join(project_dir, f'seg{idx:02d}.mp4')
    text = clip_cfg['text']
    etext = text.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
    drawtext = (
        f"drawtext=fontfile='{font}':text='{etext}':fontcolor=white:"
        f"fontsize={int(h*0.06)}:borderw=2:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.78:enable='between(t,0,4.8)'"
    )
    cmd = [
        ffmpeg, '-y', '-i', vin, '-i', ain,
        '-vf', drawtext,
        '-af', 'volume=1.2',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k', '-shortest', out
    ]
    print('SEG:', ' '.join(cmd))
    subprocess.run(cmd, check=True)
    return out


def build_end_card(ffmpeg, project_dir, font, idx, w, h, end_cfg):
    img = os.path.join(project_dir, end_cfg['image'])
    ain = os.path.join(project_dir, end_cfg['audio'])
    out = os.path.join(project_dir, f'seg{idx:02d}.mp4')
    big = end_cfg['text_big'].replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
    small = end_cfg['text_small'].replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
        "drawbox=x=0:y=0:w=iw:h=ih:color=black@0.4:t=fill,"
        f"drawtext=fontfile='{font}':text='{big}':fontcolor=#FFD700:"
        f"fontsize={int(h*0.12)}:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h*0.35,"
        f"drawtext=fontfile='{font}':text='{small}':fontcolor=white:"
        f"fontsize={int(h*0.06)}:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.55"
    )
    cmd = [
        ffmpeg, '-y', '-loop', '1', '-i', img, '-i', ain,
        '-vf', vf,
        '-t', '3', '-r', '24',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k', '-shortest', out
    ]
    print('END:', ' '.join(cmd))
    subprocess.run(cmd, check=True)
    return out


def main():
    parser = argparse.ArgumentParser(description='Assemble AI short video')
    parser.add_argument('--dir', required=True, help='Project directory containing video_config.json and assets')
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)
    config_path = os.path.join(project_dir, 'video_config.json')
    if not os.path.exists(config_path):
        print(f'ERROR: {config_path} not found', file=sys.stderr)
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    ffmpeg = get_ffmpeg_exe()
    font = ensure_font(project_dir)
    first_video = os.path.join(project_dir, cfg['clips'][0]['video'])
    w, h = probe_size(ffmpeg, first_video)
    print(f'Video size: {w}x{h}, font: {font}')

    segment_files = []
    for i, clip_cfg in enumerate(cfg['clips'], 1):
        seg = build_segment(ffmpeg, project_dir, font, i, w, h, clip_cfg)
        segment_files.append(seg)

    end_seg = build_end_card(ffmpeg, project_dir, font, len(segment_files)+1, w, h, cfg['end_card'])
    segment_files.append(end_seg)

    list_path = os.path.join(project_dir, 'concat_list.txt')
    with open(list_path, 'w', encoding='utf-8') as f:
        for seg in segment_files:
            f.write(f"file '{seg.replace(chr(92), '/')}'\n")

    title = cfg.get('title', 'output')
    final_out = os.path.join(project_dir, f'{title}_成片.mp4')
    cmd = [
        ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
        '-c:a', 'aac', '-b:a', '192k', '-r', '24', final_out
    ]
    print('FINAL:', ' '.join(cmd))
    subprocess.run(cmd, check=True)
    print('FINISHED:', final_out)


if __name__ == '__main__':
    main()
