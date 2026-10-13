"""剪辑计划的数据结构。

一次剪辑 = 一组有序 Segment（每段指向某个源文件的时间区间，可带变速），
按顺序拼起来就是成片。分析模块产出 Segment 列表，渲染模块消费它。
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

# audio 只依赖 ff，不依赖本模块，所以这里直接引不会有循环导入
from audio import AudioSpec

# Segment.label 的取值
LABEL_KEEP = "keep"
LABEL_SILENCE = "silence"
LABEL_SCENE = "scene"
LABEL_BEAT = "beat"
LABEL_BROLL = "broll"


@dataclass
class Segment:
    """一段被保留（或变速保留）的素材区间。"""

    start: float
    end: float
    speed: float = 1.0
    label: str = LABEL_KEEP
    source: int = 0
    note: str = ""

    def __post_init__(self) -> None:
        if self.end < self.start:
            self.start, self.end = self.end, self.start

    @property
    def duration(self) -> float:
        """区间在源里的原始时长。"""
        return max(0.0, self.end - self.start)

    @property
    def out_duration(self) -> float:
        """变速后在成片里占的时长。"""
        sp = self.speed if self.speed > 0 else 1.0
        return self.duration / sp

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": round(self.start, 4),
            "end": round(self.end, 4),
            "speed": round(self.speed, 4),
            "label": self.label,
            "source": self.source,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Segment":
        return cls(
            start=float(d.get("start", 0.0)),
            end=float(d.get("end", 0.0)),
            speed=float(d.get("speed", 1.0) or 1.0),
            label=str(d.get("label", LABEL_KEEP)),
            source=int(d.get("source", 0)),
            note=str(d.get("note", "")),
        )


@dataclass
class OutputSpec:
    """成片输出参数。"""

    width: int = 0          # 0 = 跟随源
    height: int = 0
    fps: float = 0.0        # 0 = 跟随源
    crf: int = 20
    preset: str = "veryfast"
    audio_bitrate: str = "192k"
    container: str = "mp4"
    normalize_loudness: bool = False
    target_lufs: float = -16.0
    fade_in: float = 0.0
    fade_out: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "OutputSpec":
        d = d or {}
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in valid})


@dataclass
class EditPlan:
    """一份完整的剪辑方案。"""

    sources: list[str] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    output: OutputSpec = field(default_factory=OutputSpec)
    audio: AudioSpec = field(default_factory=AudioSpec)
    mode: str = "manual"          # silence | scene | beat | manual
    title: str = ""
    warnings: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------------- 统计
    @property
    def total_source_duration(self) -> float:
        """所有片段实际消耗的源时长。"""
        return sum(s.duration for s in self.segments)

    @property
    def total_out_duration(self) -> float:
        """成片总时长（变速折算后）。"""
        return sum(s.out_duration for s in self.segments)

    @property
    def media_duration(self) -> float:
        """原始素材总时长，作为「砍了多少」的基准。

        片段只覆盖素材的一部分，拿片段之和当基准会把砍掉的部分算丢，
        所以优先用 meta.duration（分析阶段记下的真实素材时长）。
        """
        try:
            d = float(self.meta.get("duration") or 0.0)
        except (TypeError, ValueError):
            d = 0.0
        return d if d > 0 else self.total_source_duration

    @property
    def removed_duration(self) -> float:
        return max(0.0, self.media_duration - self.total_source_duration)

    def stats(self) -> dict[str, Any]:
        src = self.media_duration
        used = self.total_source_duration
        out = self.total_out_duration
        removed = max(0.0, src - used)
        labels: dict[str, int] = {}
        for s in self.segments:
            labels[s.label] = labels.get(s.label, 0) + 1
        return {
            "segment_count": len(self.segments),
            "source_duration": round(src, 3),
            "used_duration": round(used, 3),
            "output_duration": round(out, 3),
            "removed_duration": round(removed, 3),
            "removed_ratio": round(removed / src, 4) if src > 0 else 0.0,
            "compression": round(out / src, 4) if src > 0 else 1.0,
            "labels": labels,
        }

    # ---------------------------------------------------------------- 校验
    def normalize(self, *, min_duration: float = 0.0) -> "EditPlan":
        """排序、丢弃非法/过短片段、收拢首尾。原地修改并返回 self。"""
        cleaned: list[Segment] = []
        for s in self.segments:
            if s.duration <= 1e-6:
                continue
            s.speed = float(s.speed or 1.0)
            if s.speed < 0.1:
                s.speed = 0.1
            if s.speed > 100.0:
                s.speed = 100.0
            if min_duration > 0 and s.duration < min_duration:
                continue
            cleaned.append(s)

        cleaned.sort(key=lambda x: (x.source, x.start))
        # 修复同一源内的区间重叠
        by_source: dict[int, float] = {}
        fixed: list[Segment] = []
        for s in cleaned:
            cursor = by_source.get(s.source, 0.0)
            if s.start < cursor - 1e-6 and s.label != LABEL_BROLL:
                s.start = cursor
                if s.end - s.start <= 1e-6:
                    continue
            by_source[s.source] = s.end
            fixed.append(s)

        self.segments = fixed
        return self

    def slices(self, max_gap: float = 0.0) -> list[tuple[int, float, float]]:
        """把相邻可合并的片段并成粗粒度区间，用于展示。"""
        return [(s.source, s.start, s.end) for s in self.segments]

    # ---------------------------------------------------------------- 序列化
    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "title": self.title,
            "sources": self.sources,
            "segments": [s.to_dict() for s in self.segments],
            "output": self.output.to_dict(),
            "audio": self.audio.to_dict(),
            "warnings": self.warnings,
            "meta": self.meta,
            "stats": self.stats(),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EditPlan":
        return cls(
            sources=[str(x) for x in (d.get("sources") or [])],
            segments=[Segment.from_dict(x) for x in (d.get("segments") or [])],
            output=OutputSpec.from_dict(d.get("output")),
            audio=AudioSpec.from_dict(d.get("audio")),
            mode=str(d.get("mode") or "manual"),
            title=str(d.get("title") or ""),
            warnings=[str(x) for x in (d.get("warnings") or [])],
            meta=dict(d.get("meta") or {}),
        )

    @classmethod
    def from_json(cls, text: str) -> "EditPlan":
        return cls.from_dict(json.loads(text))

    def save(self, path: os.PathLike | str) -> Path:
        p = Path(path)
        p.write_text(self.to_json(), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: os.PathLike | str) -> "EditPlan":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 分析结果
# ---------------------------------------------------------------------------


@dataclass
class SilenceRegion:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict[str, float]:
        return {
            "start": round(self.start, 4),
            "end": round(self.end, 4),
            "duration": round(self.duration, 4),
        }


@dataclass
class SceneCut:
    time: float
    score: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {"time": round(self.time, 4), "score": round(self.score, 4)}


def ranges_to_segments(
    ranges: Sequence[tuple[float, float]],
    *,
    source: int = 0,
    label: str = LABEL_KEEP,
) -> list[Segment]:
    return [Segment(a, b, label=label, source=source) for a, b in ranges]


def complement(
    regions: Sequence[tuple[float, float]],
    total: float,
    *,
    gap: float = 0.0,
) -> list[tuple[float, float]]:
    """求 [0,total] 内这些区间的补集（即"要保留"的部分）。

    gap: 每个切除区间两端额外多切掉的时间，避免残留尾音。
    """
    if not regions:
        return [(0.0, total)]

    merged: list[list[float]] = []
    for a, b in sorted(regions, key=lambda x: x[0]):
        a = max(0.0, a - gap)
        b = min(total, b + gap)
        if b <= a:
            continue
        if merged and a <= merged[-1][1] + 1e-6:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])

    out: list[tuple[float, float]] = []
    cursor = 0.0
    for a, b in merged:
        if a - cursor > 1e-6:
            out.append((cursor, a))
        cursor = max(cursor, b)
    if total - cursor > 1e-6:
        out.append((cursor, total))
    return out


def merge_short(
    ranges: Sequence[tuple[float, float]],
    min_len: float,
    *,
    total: float,
) -> list[tuple[float, float]]:
    """把短于 min_len 的保留段并入相邻段，避免成片碎成渣。"""
    if min_len <= 0 or not ranges:
        return list(ranges)

    work = [[a, b] for a, b in ranges]
    changed = True
    while changed and len(work) > 1:
        changed = False
        for i, seg in enumerate(work):
            if seg[1] - seg[0] >= min_len:
                continue
            # 优先并进前一段，否则并进后一段
            if i > 0:
                work[i - 1][1] = seg[1]
            elif i + 1 < len(work):
                work[i + 1][0] = seg[0]
            else:
                break
            work.pop(i)
            changed = True
            break
    return [(a, min(b, total)) for a, b in work if b - a > 1e-6]


def ensure_dir(p: os.PathLike | str) -> Path:
    """确保目录存在并返回它。

    不直接用 Path.mkdir(exist_ok=True)：某些运行环境（带文件系统代理的沙箱 /
    IDE 运行时）会把「目录已存在」报成 PermissionError 而不是 FileExistsError，
    而 mkdir 的 exist_ok 只捕获后者，异常会直接冒到调用方把流程炸掉。
    这里一律以 is_dir() 为准，任何 OSError 只要目录确实在了就放行。
    """
    path = Path(p)
    if path.is_dir():
        return path
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        if not path.is_dir():
            raise
    return path


def find_free_path(directory: Path, stem: str, suffix: str) -> Path:
    """在目录下找一个不冲突的文件名。"""
    ensure_dir(directory)
    cand = directory / f"{stem}{suffix}"
    i = 2
    while cand.exists():
        cand = directory / f"{stem}_{i}{suffix}"
        i += 1
    return cand
