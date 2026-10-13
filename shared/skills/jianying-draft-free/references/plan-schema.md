# 分镜计划 JSON 规范与生成器

## 为什么要有计划层

直接写代码生成草稿，改一条要动代码；写成 JSON 计划后：

- 计划可 review（人看一眼就知道时间轴对不对）
- 计划可复用（同一份时间轴换素材就是新片）
- 计划可批量（一个循环产 N 条）
- 出错可定位（是计划错还是生成错，一眼分清）

**这是自动化能不能规模化的分水岭。**

## 完整字段规范

```jsonc
{
  "draft_name": "瓦猫-01",          // 草稿名，也是草稿文件夹名
  "width": 1080, "height": 1920,    // 画布；竖版 1080x1920，横版 1920x1080，方版 1080x1080
  "fps": 30,                        // 仅记录，实际由导出设置决定

  "tracks": [                       // 轨道声明，name 是后续引用的标识
    {"type": "video", "name": "v1"},
    {"type": "video", "name": "v2"},       // 画中画用第二条视频轨
    {"type": "audio", "name": "voice"},    // 人声
    {"type": "audio", "name": "bgm"},      // 背景音乐
    {"type": "text",  "name": "caption"}   // 字幕
  ],

  "segments": [
    {
      "track": "v1", "kind": "video",
      "src": "C:/mat/clip1.mp4",
      "start": "0s", "dur": "3s",
      "source_start": "2s",         // 可选：从素材第 2 秒开始取，做素材截取
      "volume": 0,                  // 可选：视频原声，0 表示静音（配旁白时常用）
      "speed": 1.0,                 // 可选：变速
      "transition": "叠化",          // 可选：转场，挂在本片段上（作用于与下一片段之间）
      "transition_dur": "0.5s",
      "animation_in": "斜切",        // 可选：入场动画
      "clip": {                     // 可选：画面变换
        "scale_x": 1.0, "scale_y": 1.0,
        "transform_x": 0.0, "transform_y": -0.8,   // 画面位置，字幕常用 -0.8
        "alpha": 1.0, "rotation": 0.0
      }
    },
    {
      "track": "voice", "kind": "audio",
      "src": "C:/mat/vo1.mp3",
      "start": "0s", "dur": "3s",
      "volume": 1.0
    },
    {
      "track": "bgm", "kind": "audio",
      "src": "C:/mat/bgm.mp3",
      "start": "0s", "dur": "15s",
      "volume": 0.15,
      "fade_in": "1s", "fade_out": "2s"
    },
    {
      "track": "caption", "kind": "text",
      "text": "云南瓦猫 守宅千年",
      "start": "0.3s", "dur": "2.7s",
      "style": {                    // 可选：文本样式（描边不在 style 里，见下）
        "color": [1.0, 1.0, 1.0],   // RGB，0~1
        "size": 8.0,                // 字号，剪映相对单位
        "bold": false,
        "align": 1,                 // 0 左 1 中 2 右
        "alpha": 1.0,
        "auto_wrapping": false,
        "max_line_width": 0.82      // 每行最大宽度占屏比，0~1
      },
      "border": {                   // 可选：描边，与 style 平级（不是 style 的子字段）
        "color": [0.0, 0.0, 0.0],   // 黑描边，亮画面必备
        "alpha": 1.0,
        "width": 40.0               // 注意单位：剪映内部量级，默认 40，不是 0~1
      },
      "clip": {"transform_y": -0.7} // 位置：单位为半个画布高，-0.7 约在下三分之一
    }
  ]
}
```

### 时间写法

统一走 `trange()` / `tim()` 支持的自然格式，**不用手算微秒**：

| 写法 | 含义 |
|---|---|
| `"0s"` / `"4.2s"` | 秒 |
| `"1h52m3s"` | 时分秒组合 |
| `"0.15s"` | 小数秒 |
| `trange("0s", "5s")` | 起点 0，持续 5 秒 |

**永远记住：第二个参数是持续时长，不是结束时间。**

### kind 与轨道类型对照

| kind | 轨道 type | 说明 |
|---|---|---|
| video | video | 视频与图片（图片按静态片段处理） |
| audio | audio | 人声、BGM、音效 |
| text | text | 字幕与标题 |

## 生成器脚本（可直接运行）

保存为 `build_draft.py`，改配置即可用。

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分镜计划 -> 剪映草稿
用法:
    python build_draft.py plan.json
    python build_draft.py plan.json --folder "<剪映草稿目录>"
"""
import argparse
import json
import os
import sys

import pyJianYingDraft as draft
from pyJianYingDraft import trange, tim


DEFAULT_FOLDER = r"C:\Users\<你>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"

TRACK_TYPE = {
    "video": draft.TrackType.video,
    "audio": draft.TrackType.audio,
    "text": draft.TrackType.text,
}


def build_segment(seg: dict):
    """把计划里的一个片段描述变成 pyJianYingDraft 的 Segment 对象。"""
    kind = seg["kind"]
    start = seg["start"]
    dur = seg["dur"]

    if kind == "video":
        s = draft.VideoSegment(
            seg["src"], trange(start, dur),
            source_timerange=(trange(seg["source_start"], dur) if seg.get("source_start") else None),
            volume=seg.get("volume", 1.0),
            speed=seg.get("speed", 1.0),
        )
        if seg.get("transition"):
            s.add_transition(seg["transition"], duration=tim(seg.get("transition_dur", "0.5s")))
        if seg.get("animation_in"):
            s.add_animation(seg["animation_in"])

    elif kind == "audio":
        s = draft.AudioSegment(seg["src"], trange(start, dur), volume=seg.get("volume", 1.0))
        if seg.get("fade_in") or seg.get("fade_out"):
            s.add_fade(seg.get("fade_in", "0s"), seg.get("fade_out", "0s"))

    elif kind == "text":
        # 注意：描边 TextBorder 是 TextSegment 的参数，不是 TextStyle 的
        style = None
        if seg.get("style"):
            st = seg["style"]
            style = draft.TextStyle(
                size=st.get("size", 8.0),
                bold=st.get("bold", False),
                italic=st.get("italic", False),
                underline=st.get("underline", False),
                color=tuple(st.get("color", (1.0, 1.0, 1.0))),
                alpha=st.get("alpha", 1.0),
                align=st.get("align", 1),
                auto_wrapping=st.get("auto_wrapping", False),
                max_line_width=st.get("max_line_width", 0.82),
            )
        border = None
        if seg.get("border"):
            b = seg["border"]
            border = draft.TextBorder(
                color=tuple(b.get("color", (0.0, 0.0, 0.0))),
                alpha=b.get("alpha", 1.0),
                width=b.get("width", 40.0),   # 默认 40，不是 0~1
            )
        s = draft.TextSegment(seg["text"], trange(start, dur), style=style, border=border)

    else:
        raise ValueError(f"未知 kind: {kind}")

    # 画面变换（视频与文本都支持）
    if seg.get("clip"):
        c = seg["clip"]
        s.clip_settings = draft.ClipSettings(
            scale_x=c.get("scale_x", 1.0),
            scale_y=c.get("scale_y", 1.0),
            transform_x=c.get("transform_x", 0.0),
            transform_y=c.get("transform_y", 0.0),
            alpha=c.get("alpha", 1.0),
            rotation=c.get("rotation", 0.0),
        )
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--folder", default=DEFAULT_FOLDER)
    ap.add_argument("--dry-run", action="store_true", help="只校验计划不写入")
    args = ap.parse_args()

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)

    # --- 计划校验（先校验再动手，避免生成一半报错）---
    errs = []
    names = {t["name"] for t in plan["tracks"]}
    if len(names) != len(plan["tracks"]):
        errs.append("轨道 name 重复")
    for i, t in enumerate(plan["tracks"]):
        if t["type"] not in TRACK_TYPE:
            errs.append(f"tracks[{i}] 类型非法: {t['type']}")
    for i, s in enumerate(plan["segments"]):
        if s["track"] not in names:
            errs.append(f"segments[{i}] 引用了未声明的轨道: {s['track']}")
        if s["kind"] in ("video", "audio") and not os.path.isfile(s.get("src", "")):
            errs.append(f"segments[{i}] 素材不存在: {s.get('src')}")
    if errs:
        print("计划校验未通过：")
        for e in errs:
            print("  -", e)
        sys.exit(1)

    total = max(tim(s["start"]) + tim(s["dur"]) for s in plan["segments"])
    print(f"计划校验通过 | 草稿 {plan['draft_name']} | 总时长 {total/1e6:.2f}s")
    if args.dry_run:
        return

    # --- 生成 ---
    df = draft.DraftFolder(args.folder)
    script = df.create_draft(plan["draft_name"], plan.get("width", 1080), plan.get("height", 1920))

    script.append_tracks([
        draft.TrackSpec(TRACK_TYPE[t["type"]], t["name"]) for t in plan["tracks"]
    ])

    for i, seg in enumerate(plan["segments"]):
        try:
            script.add_segment(build_segment(seg), seg["track"])
        except Exception as e:
            print(f"[失败] segments[{i}] {seg.get('src') or seg.get('text')}: {e}")
            raise

    script.save()
    print(f"完成：{plan['draft_name']}（{len(plan['segments'])} 个片段）")
    print("提示：重启剪映后草稿才会出现在列表里")


if __name__ == "__main__":
    main()
```

## 字幕轨的两种做法

### A. 从 SRT 导入（有配音稿时推荐）

真实签名（已核对源码，**这是签名说明，不是可执行代码**）：
```text
script.import_srt(
    srt_path: str,          # SRT 文件路径
    track_name: str,        # 导入到哪条文本轨；不存在会自动创建
    *,
    time_offset=0.0,        # 整体时间偏移 —— 单位是【微秒】，不是秒！
    style_reference=None,   # 传一个 TextSegment 作样式参考
    text_style=TextStyle(size=5, align=1, auto_wrapping=True),
    clip_settings=ClipSettings(transform_y=-0.8),
)
```

实用写法：
```python
script.import_srt("C:/mat/sub.srt", track_name="caption")

# 整体延后 0.3 秒 —— 注意要换算成微秒，或用 tim()
from pyJianYingDraft import tim
script.import_srt("C:/mat/sub.srt", track_name="caption", time_offset=tim("0.3s"))

# 自定义样式与描边
script.import_srt(
    "C:/mat/sub.srt", track_name="caption",
    text_style=draft.TextStyle(size=6.0, align=1, color=(1, 1, 1)),
    clip_settings=draft.ClipSettings(transform_y=-0.75),
)
```

**三个易错点**
1. `time_offset` 单位是**微秒**。直接写 `0.3` 等于 0.3 微秒（毫无效果），要用 `tim("0.3s")` 或写 `300000`。
2. 轨道不存在会自动创建并插到视频/文本轨的**前景侧**，不用手动建。
3. 传了 `style_reference` 时，`clip_settings` 仍会覆盖它——想完全用参考片段的位置就显式传 `clip_settings=None`。

SRT 时间轴来自配音，天然对齐，比手敲时间点准得多。

### B. 从配音时长自动切分

拿到每句语音的实际时长，按句生成文本片段：

```python
def captions_from_lines(lines, starts, durs, pad_in=0.15, pad_out=0.25):
    """lines: 文案列表；starts/durs: 每句语音的起点与时长（秒）"""
    out = []
    for text, st, du in zip(lines, starts, durs):
        out.append({
            "track": "caption", "kind": "text", "text": text,
            "start": f"{max(0, st - pad_in)}s",
            "dur": f"{du + pad_in + pad_out}s",
            "style": {"color": [1, 1, 1], "size": 8.0, "align": 1},
            "border": {"color": [0, 0, 0], "alpha": 1.0, "width": 40.0},
            "clip": {"transform_y": -0.7},
        })
    return out
```

对轴经验：
- 起点比语音**早 0.15s**、终点**晚 0.25s**，观感最自然
- 单条不超过 15 字，长句拆两段
- 户外/亮画面**必加黑色描边**，否则白字看不见
- 字幕位置 `transform_y` 约 -0.7 ~ -0.8（画面下方）

## 素材预处理（生成前必做）

```bash
# 查时长
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 in.mp4

# 统一图片尺寸为竖版（避免缩放位置错乱）
ffmpeg -i in.jpg -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black" out.jpg

# 统一音频采样率（混剪避免爆音）
ffmpeg -i in.mp3 -ar 44100 -ac 2 out.wav

# 抽掉视频原声（配旁白时）
ffmpeg -i in.mp4 -an -c:v copy muted.mp4
```

## 计划自检清单

- [ ] 每个 `segments[].track` 都在 `tracks` 里声明过
- [ ] 所有素材路径存在且为绝对路径
- [ ] 同一轨道上片段**不重叠**
- [ ] 总时长符合预期（用脚本算，不要目测）
- [ ] BGM 覆盖全程且音量 0.1~0.2
- [ ] 人声轨音量 1.0，视频原声配旁白时设为 0
- [ ] 字幕不超过 15 字，有描边
- [ ] `--dry-run` 先跑一遍再真生成
