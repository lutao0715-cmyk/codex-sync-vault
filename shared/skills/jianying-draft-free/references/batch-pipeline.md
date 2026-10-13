# 批量生产流水线

## 一、核心思路：计划与素材解耦

```
一份时间轴模板  +  N 套素材  →  N 个草稿  →  N 条成片
```

时间轴（几秒切镜、字幕在哪、BGM 音量）只设计**一次**；素材（画面、配音、文案）每套不同。这样改结构只改一处，产出翻倍只加素材。

## 二、目录约定

```
project/
├── template/
│   └── plan.template.json      # 时间轴模板，含 {占位符}
├── items/                      # 每个成品一套素材
│   ├── 001-wamao-red/
│   │   ├── meta.json           # 本条专属：文案、时长
│   │   ├── vo.mp3              # 配音
│   │   ├── bgm.mp3             # 背景音乐（可共用）
│   │   ├── sub.srt             # 字幕
│   │   └── shots/              # 画面
│   │       ├── s1.mp4
│   │       └── s2.png
│   └── 002-wamao-blue/
├── work/
│   ├── drafts/                 # 生成的草稿（中间产物）
│   └── logs/
└── out/                        # 最终成片
```

**命名带序号**，排序即生产顺序，日志好对、断点好续。

## 三、素材准备（上游，AI 流水线衔接）

一条带货视频的最小素材集：

| 素材 | 来源 | 注意 |
|---|---|---|
| 画面 5~8 个 | 实拍 / AI 生图 / 图生视频 | 统一尺寸，竖版 1080×1920 |
| 配音 1 条 | TTS（Edge TTS 等） | 导出同时存 SRT，字幕轴直接用 |
| BGM 1 条 | 自有授权音乐 | 音量 0.1~0.2 |
| 文案 | LLM 生成口播稿 | 单句 ≤15 字，便于切字幕 |

**关键**：配音时必须一并产出带时间轴的 SRT。有了它，字幕轴和画面时长都能自动算，省掉最烦的对轴工作。

```bash
# TTS 同时导出音频与字幕（示例，工具自选）
edge-tts --voice zh-CN-YunxiNeural -f script.txt --write-media vo.mp3 --write-subtitles sub.srt

# 查配音真实时长，用它定总时长
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 vo.mp3
```

## 四、时间轴模板

`plan.template.json` —— 用 `{占位符}`，运行时按套替换：

```jsonc
{
  "draft_name": "{name}",
  "width": 1080, "height": 1920,
  "tracks": [
    {"type": "video", "name": "v1"},
    {"type": "audio", "name": "voice"},
    {"type": "audio", "name": "bgm"},
    {"type": "text",  "name": "caption"}
  ],
  "segments": [
    {"track": "v1", "kind": "video", "src": "{shots}/s1.mp4",
     "start": "0s", "dur": "{d1}", "volume": 0, "transition": "叠化", "transition_dur": "0.4s"},
    {"track": "v1", "kind": "video", "src": "{shots}/s2.png",
     "start": "{d1}", "dur": "{d2}", "volume": 0},
    {"track": "voice", "kind": "audio", "src": "{vo}",
     "start": "0s", "dur": "{total}", "volume": 1.0},
    {"track": "bgm", "kind": "audio", "src": "{bgm}",
     "start": "0s", "dur": "{total}", "volume": 0.15, "fade_in": "1s", "fade_out": "2s"}
  ]
}
```

字幕轨由 SRT 导入，不写死在模板里——每句时长不同，写死必然错轴。

## 五、批量脚本（断点续跑 + 失败隔离）

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成剪映草稿：一件一草稿，单件失败不影响其余，支持断点续跑。
用法: python batch_build.py project/
"""
import json
import os
import sys
import time
import traceback

import pyJianYingDraft as draft
from pyJianYingDraft import trange

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_draft import build_segment, TRACK_TYPE   # 复用单件生成器

DRAFT_FOLDER = r"C:\Users\<你>\AppData\Local\JianyingPro\User Data\Projects\com.lveditor.draft"


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def render_plan(tpl, item_dir, meta):
    """把模板 + 一套素材渲染成具体计划。"""
    shots = os.path.join(item_dir, "shots")
    vo = os.path.join(item_dir, "vo.mp3")
    bgm = os.path.join(item_dir, "bgm.mp3")
    if not os.path.isfile(bgm):
        bgm = os.path.join(os.path.dirname(item_dir), "common", "bgm.mp3")

    mapping = {
        "name": meta["name"],
        "shots": shots,
        "vo": vo,
        "bgm": bgm,
        "total": meta["total"],
        **{f"d{i+1}": d for i, d in enumerate(meta["shot_durs"])},
    }

    txt = json.dumps(tpl, ensure_ascii=False)
    for k, v in mapping.items():
        txt = txt.replace("{" + k + "}", str(v))
    if "{" in txt:
        raise ValueError(f"模板仍有未替换占位符: {txt[txt.index('{'):txt.index('{')+40]}")
    return json.loads(txt)


def build_one(plan, folder):
    df = draft.DraftFolder(folder)
    script = df.create_draft(plan["draft_name"], plan.get("width", 1080), plan.get("height", 1920))
    script.append_tracks([draft.TrackSpec(TRACK_TYPE[t["type"]], t["name"]) for t in plan["tracks"]])
    for seg in plan["segments"]:
        script.add_segment(build_segment(seg), seg["track"])
    script.save()


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    tpl = load_json(os.path.join(root, "template", "plan.template.json"))
    items_dir = os.path.join(root, "items")
    done_log = os.path.join(root, "work", "logs", "done.txt")

    os.makedirs(os.path.dirname(done_log), exist_ok=True)
    done = set()
    if os.path.isfile(done_log):
        done = set(l.strip() for l in open(done_log, encoding="utf-8") if l.strip())

    items = sorted(d for d in os.listdir(items_dir)
                   if os.path.isdir(os.path.join(items_dir, d)))
    ok, fail = 0, []
    err_log = open(os.path.join(root, "work", "logs", "errors.txt"), "a", encoding="utf-8")

    for it in items:
        if it in done:
            print(f"[跳过] {it}")
            continue
        item_dir = os.path.join(items_dir, it)
        try:
            meta = load_json(os.path.join(item_dir, "meta.json"))
            plan = render_plan(tpl, item_dir, meta)
            build_one(plan, DRAFT_FOLDER)
            with open(done_log, "a", encoding="utf-8") as f:
                f.write(it + "\n")
            ok += 1
            print(f"[完成] {it} -> 草稿 {plan['draft_name']}")
        except Exception as e:
            fail.append(it)
            err_log.write(f"{time.strftime('%F %T')}\t{it}\t{e}\n")
            err_log.write(traceback.format_exc() + "\n")
            err_log.flush()
            print(f"[失败] {it}: {e}（已记录，继续下一条）")
        time.sleep(0.5)   # 别把剪映目录写爆，也给异常留缓冲

    err_log.close()
    print(f"\n完成 {ok} 条，失败 {len(fail)} 条")
    if fail:
        print("失败清单:", fail)
        print("修好后重跑本脚本即可续跑（已完成项自动跳过）")


if __name__ == "__main__":
    main()
```

**三个设计要点**
1. **断点续跑**：`done.txt` 记录已完成项，重跑自动跳过
2. **失败隔离**：单条 try/except，挂一条不影响其余，错误写日志
3. **占位符严格校验**：有没替换的 `{xxx}` 直接报错，避免生成出半成品

## 六、带货矩阵实例：一个产品出 N 条

同一产品换**角度**而不是换内容，是矩阵的正解：

| 变体维度 | 举例 |
|---|---|
| 卖点角度 | 工艺 / 寓意 / 摆放场景 / 开箱 / 对比 |
| 开头钩子 | 提问式 / 数字式 / 场景式 / 反差式 |
| 结尾引导 | 点关注 / 评论区 / 主页链接 |
| 画面风格 | 实拍 / AI 图 / 混剪 |
| 语言版本 | 中文 / 英文（TikTok）/ 多语种 |

**做法**：文案与配音变，时间轴不变。一次设计模板，批量产出十几条，挑数据好的加大投放。

`meta.json` 示例：
```json
{
  "name": "瓦猫-工艺篇",
  "total": "15.4s",
  "shot_durs": ["3.2s", "3.0s", "3.1s", "3.0s", "3.1s"]
}
```
`shot_durs` 之和要等于 `total`——**用脚本算，不要手填**。

## 七、时长自动计算

```python
import subprocess, json

def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())

def split_shots(total, n, jitter=0.15):
    """把总时长切成 n 段，带轻微抖动避免机械感，最后校正到精确等于 total"""
    import random
    base = total / n
    durs = [base * (1 + random.uniform(-jitter, jitter)) for _ in range(n)]
    scale = total / sum(durs)
    durs = [d * scale for d in durs]
    return [f"{d:.2f}s" for d in durs]
```

## 八、产出与验收

**产物清单**（每批都要留）：
```
out/
├── manifest.csv      # 成品名 / 草稿名 / 时长 / 日期
├── drafts.txt        # 生成的草稿名列表（便于在剪映里逐个导出）
└── logs/
    ├── done.txt
    └── errors.txt
```

**验收流程**（7.0+ 必须人工这一步）：
1. 重启剪映，确认草稿全部出现
2. 逐个打开：看有无红色感叹号（素材丢失）
3. 完整播放一遍：听声音连续、看字幕对轴
4. 导出成片，核对时长与帧数
5. 抽查 20% 的画面质量

**不要跳第 3 步。** 脚本产的是草稿，成片观感只能人来判断。

## 九、效率账（心里有数）

| 环节 | 手工 | 脚本化后 |
|---|---|---|
| 排轨、对轴、加字幕 | 每条 20~40 分钟 | 0（自动生成） |
| 导出成片（7.0+） | — | 每条约 1~2 分钟（人工点） |
| 换素材出新版本 | 重做一遍 | 改 meta.json 重跑 |

所以真实收益是：**把"剪辑"的时间归零，只留"点导出"**。10 条片从半天压到 20 分钟。

## 十、常见批量故障

| 现象 | 原因 | 处理 |
|---|---|---|
| 草稿名冲突 | 同名草稿被覆盖 | 草稿名带序号+日期 |
| 部分素材红感叹号 | 路径含中文/空格/相对路径 | 全用绝对路径，路径别带特殊符号 |
| 批量跑一半卡住 | 剪映正在占用草稿目录 | 生成时**退出剪映**，生成完再打开 |
| 时长对不上 | `shot_durs` 之和 ≠ total | 用脚本算，别手填 |
| 字幕整体偏移 | SRT 与配音不同步 | 重新导出 SRT，或统一加偏移量 |
| 重跑重复生成 | done.txt 没写进去 | 检查写权限，或手动补记已完成项 |
