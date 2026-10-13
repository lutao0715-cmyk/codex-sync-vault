"""音频处理链：降噪、频段清理、噪声门、EQ、动态、立体声、响度、限幅。

设计要点（都是踩过才定下来的）：

1. **链序不是随便排的。** 信号处理的顺序决定结果：
   declick → 降噪 → 高通/低通 → 噪声门 → EQ → 压缩 → 立体声 → 增益
   - 降噪必须在 EQ 之前：EQ 抬起的高频会被降噪当成有用信号保留下来。
   - 噪声门在降噪之后：先让底噪降下来，门限才切得干净。
   - 压缩在 EQ 之后：EQ 决定了什么频段触发压缩。

2. **母带链单独一段。** 响度归一化 / 限幅 / 淡入淡出属于「整条节目」的
   收尾处理，必须排在与人声处理之后、且淡出必须排在 loudnorm 之后——
   loudnorm 是动态增益，排在淡出后面会把淡出重新推上去，听感上就是
   「淡出淡不掉」。

3. **dB → 线性要自己换。** ffmpeg 的 agate / acompressor / alimiter 的
   threshold / limit 参数吃的是线性值（0~1），不是 dB。写 -18 进去会被
   当成 0dB 甚至报错。

4. **alimiter 的 level 默认是开着的**（自动电平），它会把输出重新拉到
   limit 位置，等于把 loudnorm 的结果抹平。必须显式 level=0。
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import ff

# ---------------------------------------------------------------------------
# 基础换算
# ---------------------------------------------------------------------------


def db_to_linear(db: float) -> float:
    """dB -> 线性增益系数。"""
    return float(10.0 ** (float(db) / 20.0))


def linear_to_db(x: float) -> float:
    """线性 -> dB。0 或负值按静音处理。"""
    x = float(x)
    if x <= 1e-12:
        return -240.0
    return float(20.0 * math.log10(x))


# ---------------------------------------------------------------------------
# 参数
# ---------------------------------------------------------------------------

# afftdn 预设：(noise_reduction dB, noise_floor dB)
#
# 这几个数不是拍脑袋定的，是 tests/sweep_denoise3~6.py 用「有标准答案」的
# 素材逐轮扫出来的（干净人声已知，所以能算真正的输出信噪比增益）。
#
# 关键结论一：降噪力度越大，人声损得越多，越不划算。同素材实测——
#     nr=12 nf=-44  ->  SNR +5.0dB   底噪 -2.9dB   ← 最优点
#     nr=16 nf=-38  ->  SNR +3.9dB   底噪 -3.7dB
#     nr=20 nf=-36  ->  SNR +2.8dB   底噪 -3.9dB
#     nr=30 nf=-32  ->  SNR +0.0dB   底噪 -4.4dB
#     nr=40 nf=-30  ->  SNR -1.6dB   底噪 -4.7dB   ← 已经不划算了
# 也就是说，noise_floor 宁低勿高——宁可少降一点，也不要把人声当噪声削。
#
# 关键结论二：级联两级 afftdn 是有害的，不要试。一级把噪声清空之后，
# 二级找不到噪声会误判并注入伪影，实测「底噪降」是 +5dB（噪声不降反升）。
#
# 关键结论三：不要加 track_noise(tn=1)。实测自动跟踪噪声底在这类素材上
# 几乎不动作（只有 -0.5dB），是整轮扫描里最差的一档。
#
# 关键结论四：所有降噪器对 50Hz 交流哼声都无效——那是频段问题不是噪声
# 问题，要靠 highpass 解决。粉噪（房间底噪）也基本无效，别指望。
DENOISE_PRESETS: dict[str, tuple[float, float]] = {
    "light": (8.0, -48.0),
    "standard": (12.0, -44.0),
    # strong 与 standard 用同一组 afftdn 参数，差别在额外挂的那道噪声门，
    # 见 STRONG_GATE_DB。
    "strong": (12.0, -44.0),
}

# strong 档在 afftdn 之外再挂一道噪声门。这不是凑数，是实测选的路线：
# 既然「加深 afftdn」只会连人声一起削，就换一条不碰人声的路。门只作用
# 于静音段，而底噪正好待在静音段里，人声根本不经过它。实测代价极小——
#     afftdn 单用        SNR +5.0dB   底噪 -2.9dB
#     afftdn + 门 -38dB  SNR +4.9dB   底噪 -3.6dB
# 用 0.1dB 的 SNR 换 0.7dB 的底噪，粉噪素材上更是 SNR 无损、底噪多降 1.5dB。
#
# 注意：-38dB 是个起点，不是普适值。门必须设在素材实测底噪之上才关得上，
# 低于底噪的门形同虚设，高太多又会切掉字的尾音。suggest_spec() 会按实测
# 底噪自动算（底噪 + 6dB），这条固定值只是给手工选档时的默认。
STRONG_GATE_DB = -38.0

STEREO_MODES = ("keep", "center_boost", "center_remove", "mono")
DENOISE_MODES = ("none", "light", "standard", "strong")


@dataclass
class AudioSpec:
    """音频处理参数。默认全部关闭——不主动给素材加任何处理。

    默认全关是刻意的：降噪对干净素材只会引入「水声」类伪影，
    处理链该由人决定开，不该默认糊上去。
    """

    preset: str = "off"

    # ── 降噪 ──────────────────────────────────────────────
    denoise: str = "none"          # none | light | standard | strong

    # ── 频段清理 ──────────────────────────────────────────
    highpass: float = 0.0          # Hz，0=关。人声常用 80~120
    lowpass: float = 0.0           # Hz，0=关

    # ── 噪声门 ────────────────────────────────────────────
    gate: bool = False
    gate_db: float = -45.0

    # ── EQ（三段） ────────────────────────────────────────
    warmth: float = 0.0            # dB @ 200Hz，胸腔共鸣
    presence: float = 0.0          # dB @ 3.2kHz，人声清晰度
    deess: float = 0.0             # dB @ 7kHz，齿音（负值=衰减）

    # ── 动态 ──────────────────────────────────────────────
    compress: bool = False
    comp_db: float = -18.0
    comp_ratio: float = 3.0
    comp_makeup: float = 1.0

    # ── 修复 / 立体声 ─────────────────────────────────────
    declick: bool = False
    stereo: str = "keep"           # keep | center_boost | center_remove | mono

    # ── 电平 ──────────────────────────────────────────────
    gain_db: float = 0.0
    true_peak: float = -1.5        # 限幅上限 dBTP
    limiter: bool = True

    # ---------------------------------------------------------------- 序列化
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "AudioSpec":
        d = d or {}
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in valid})

    # ---------------------------------------------------------------- 判定
    def is_active(self) -> bool:
        """是否有任何处理被打开。用于 UI 上标「已生效」和跳过空链。"""
        return bool(
            self.denoise not in ("none", "")
            or self.highpass > 0
            or self.lowpass > 0
            or self.gate
            or self.warmth
            or self.presence
            or self.deess
            or self.compress
            or self.declick
            or self.stereo != "keep"
            or abs(self.gain_db) > 1e-6
        )

    def active_list(self) -> list[str]:
        """当前生效的处理，给人看的短标签。"""
        out: list[str] = []
        if self.declick:
            out.append("削波修复")
        if self.denoise not in ("none", ""):
            out.append({
                "light": "降噪·轻", "standard": "降噪·标准",
                "strong": "降噪·强 + 门",
            }.get(self.denoise, f"降噪·{self.denoise}"))
        if self.highpass > 0:
            out.append(f"低切 {self.highpass:g}Hz")
        if self.lowpass > 0:
            out.append(f"高切 {self.lowpass:g}Hz")
        if self.gate:
            out.append(f"噪声门 {self.gate_db:g}dB")
        if self.warmth:
            out.append(f"厚度 {self.warmth:+g}dB")
        if self.presence:
            out.append(f"清晰度 {self.presence:+g}dB")
        if self.deess:
            out.append(f"齿音 {self.deess:+g}dB")
        if self.compress:
            out.append(f"压缩 {self.comp_ratio:g}:1")
        if self.stereo != "keep":
            out.append({
                "center_boost": "人声靠前",
                "center_remove": "去人声",
                "mono": "单声道",
            }.get(self.stereo, self.stereo))
        if abs(self.gain_db) > 1e-6:
            out.append(f"增益 {self.gain_db:+g}dB")
        return out

    def warnings(self) -> list[str]:
        """会踩坑的组合，提前告诉用户。"""
        warn: list[str] = []
        if self.denoise == "strong" and not self.gate:
            warn.append(
                f"「强降噪」实际是「标准降噪 + 一道固定的 {STRONG_GATE_DB:g}dB 噪声门」，"
                "不是更狠的降噪——实测加深降噪会连人声一起削。"
                f"这道门的阈值是按常见底噪定的：素材底噪明显高于 {STRONG_GATE_DB:g}dB 时"
                "它关不上（无害但也没用），明显低于时它会切掉安静处的尾音。"
                "想稳一点就点「自动」——它按实测底噪算门限，两头都不会错。"
            )
        if self.denoise == "strong" and self.compress:
            warn.append(
                "强降噪 + 压缩同时开，容易把底噪的呼吸声放大成「水声」。"
                "建议先只开降噪听一遍。"
            )
        if self.gate and self.denoise not in ("none", ""):
            warn.append(
                "去静音已经切过一遍停顿了，再叠噪声门容易切掉字的尾音。"
                "除非素材底噪特别大，一般不用同时开。"
            )
        if self.deess and self.deess > 0:
            warn.append("齿音那一项要填负值才是衰减，正值会把齿音推得更尖。")
        if self.stereo == "center_boost":
            warn.append(
                "「人声靠前」靠的是中侧矩阵，只在立体声播放时有效。"
                "导出成单声道（部分平台会这么干）后中侧比无从体现，效果会消失。"
                "要单声道也能靠前，得上声源分离，那是另一套东西。"
            )
        if self.stereo == "center_remove" and self.compress:
            warn.append(
                "去人声会把中置能量整体拿掉，电平掉得比较多，压缩器可能一直在满负荷工作。"
            )
        return warn


# ---------------------------------------------------------------------------
# 按底噪自动选档
# ---------------------------------------------------------------------------


def suggest_spec(
    *,
    noise_floor_db: float | None = None,
    is_music: bool = False,
    has_hum: bool = False,
    outdoor: bool = False,
) -> tuple[AudioSpec, list[str]]:
    """按量出来的底噪给一档建议，返回 (spec, 理由列表)。

    底噪在 -50dB 以下的素材根本不需要降噪——开上去只会引入伪影。
    这条线是根据扫描结果定的：干净素材上 afftdn 的 SNR 增益接近 0，
    但伪影是实打实多出来的。
    """
    spec = AudioSpec()
    why: list[str] = []

    if is_music:
        apply_preset(spec, "music")
        why.append("按音乐内容处理：只做响度与限幅，不套人声链")
        return spec, why

    if noise_floor_db is None:
        apply_preset(spec, "voice")
        why.append("没量到底噪，先给一档通用口播设置")
        return spec, why

    if has_hum:
        spec.highpass = 100.0
        spec.compress = True
        spec.comp_db = -18.0
        spec.comp_ratio = 3.0
        why.append(
            "检出低频哼声：用 100Hz 低切解决。"
            "实测所有降噪器对 50Hz 交流哼声都无效——那是频段问题不是噪声问题"
        )
        return spec, why

    if noise_floor_db < -55.0:
        spec.highpass = 80.0
        spec.presence = 1.0
        why.append(
            f"底噪 {noise_floor_db:.1f}dB，已经很干净。"
            "不开降噪——开了只会多出伪影，换不来信噪比"
        )
    elif noise_floor_db < -45.0:
        apply_preset(spec, "voice")
        why.append(f"底噪 {noise_floor_db:.1f}dB，中等：标准档降噪 + 低切 80Hz")
    elif noise_floor_db < -38.0:
        # 用 standard + 显式门，而不是 strong：strong 的门阈值是固定的
        # -38dB，这里的底噪已经接近它了，固定值会不够贴。量到了就按量到的算。
        spec.denoise = "standard"
        spec.gate = True
        spec.gate_db = round(noise_floor_db + 6.0, 1)
        spec.highpass = 100.0
        spec.presence = 2.0
        spec.compress = True
        why.append(
            f"底噪 {noise_floor_db:.1f}dB 偏高：标准降噪 + 噪声门 "
            f"{spec.gate_db:g}dB（按实测底噪算的门，比固定的 -38dB 更贴合）。"
            "实测「加深降噪」只会连人声一起削，压底噪要靠门"
        )
    else:
        spec.denoise = "standard"
        spec.gate = True
        spec.gate_db = round(noise_floor_db + 6.0, 1)
        spec.highpass = 120.0
        spec.presence = 2.0
        spec.compress = True
        why.append(
            f"底噪 {noise_floor_db:.1f}dB 很高：仍然只用标准降噪 + 噪声门 "
            f"{spec.gate_db:g}dB。"
            "这里刻意不加深降噪——实测 nr=20 的 SNR 增益比 nr=12 还低 "
            "1.8dB，噪声只多降了 0.6dB，是把人声当噪声削。"
            "底噪比 -38dB 还高的素材，降噪的收益已经到顶，"
            "剩下要靠门和低切"
        )

    if outdoor:
        spec.highpass = max(spec.highpass, 120.0)
        spec.gate = True
        spec.gate_db = round(noise_floor_db + 6.0, 1)
        why.append(
            f"户外素材：低切抬到 {spec.highpass:g}Hz，"
            f"噪声门设在 {spec.gate_db:g}dB（比实测底噪高 6dB，"
            "低于底噪的门是关不上的）"
        )
    return spec, why


# ---------------------------------------------------------------------------
# 预设
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict[str, Any]] = {
    "off": {
        "label": "不处理",
        "hint": "原样保留，只做拼接。素材本身干净时选这个。",
    },
    "voice": {
        "label": "口播 / 配音",
        "hint": "室内录的解说、口播。低切 + 标准降噪 + 清晰度 + 压缩。",
        "spec": {
            "denoise": "standard", "highpass": 80.0,
            "presence": 2.0, "warmth": 0.0,
            "compress": True, "comp_db": -18.0, "comp_ratio": 3.0,
        },
    },
    "interview": {
        "label": "访谈 / 多人",
        "hint": "房间反射多、几个人音量不齐。标准降噪 + 噪声门（门道压住换人时的空档）"
                "+ 更狠的压缩与清晰度。",
        "spec": {
            "denoise": "strong", "highpass": 90.0,
            "presence": 3.0, "warmth": -1.5, "deess": -2.0,
            "compress": True, "comp_db": -20.0, "comp_ratio": 3.5,
        },
    },
    "outdoor": {
        "label": "户外 / Vlog",
        "hint": "风噪和持续环境噪。低切抬到 120Hz，加噪声门压住空档。",
        "spec": {
            "denoise": "strong", "highpass": 120.0,
            "presence": 2.0, "gate": True, "gate_db": -42.0,
            "compress": True, "comp_db": -18.0, "comp_ratio": 3.0,
        },
    },
    "rescue": {
        "label": "废片抢救",
        "hint": "底噪大、有削波。先修削波，再降噪+门+压缩+限带宽，"
                "是预设里处理最重的一档，伪影也会最明显。",
        "spec": {
            "declick": True, "denoise": "strong",
            "highpass": 100.0, "lowpass": 14000.0,
            "presence": 2.0, "compress": True,
            "comp_db": -22.0, "comp_ratio": 4.0,
        },
    },
    "music": {
        "label": "音乐为主",
        "hint": "BGM 或音乐内容。不做降噪/EQ，只走响度与限幅。",
        "spec": {"denoise": "none", "compress": False},
    },
    "hum": {
        "label": "电流声 / 空调嗡嗡声",
        "hint": "50Hz 交流哼声、持续低频嗡鸣。实测降噪器对这类噪声完全无效，"
                "该用低切解决——所以这一档只做低切，不开降噪。",
        "spec": {
            "denoise": "none", "highpass": 100.0,
            "compress": True, "comp_db": -18.0, "comp_ratio": 3.0,
        },
    },
}


def apply_preset(spec: AudioSpec, name: str) -> AudioSpec:
    """在 spec 上套一个预设。预设没提到的项保持原值。"""
    entry = PRESETS.get(name)
    if not entry or name == "off":
        return spec
    spec.preset = name
    for k, v in (entry.get("spec") or {}).items():
        if hasattr(spec, k):
            setattr(spec, k, v)
    return spec


def preset_of(spec: AudioSpec) -> str:
    """反查当前参数最接近哪个预设，找不到返回 custom。

    先判「全关」：music 预设的内容恰好等于默认值，不先判 off 的话
    任何一份没动过的参数都会被认成 music。
    """
    default = AudioSpec()
    if not spec.is_active() and all(
        getattr(spec, f) == getattr(default, f) for f in spec.__dataclass_fields__
        if f != "preset"
    ):
        return "off"
    for name, entry in PRESETS.items():
        if name in ("off", "music") or not entry.get("spec"):
            continue
        if all(getattr(spec, k, None) == v for k, v in entry["spec"].items()):
            return name
    return "custom"


# ---------------------------------------------------------------------------
# 链路构建
# ---------------------------------------------------------------------------


def _stereo_chain(mode: str) -> list[str]:
    """立体声矩阵。

    「人声靠前 / 去人声」都是靠 mid-side 矩阵做的近似，不是真正的
    声源分离。对中置人声的普通立体声混音有效，对已经做成宽立体声
    的人声基本无效——这一点在文档里写清楚了，不吹。

    ⚠️ 单声道下「人声靠前」是无效的，这是数学决定的，不是没调好：
    折叠成单声道就是只取 mid（M=(L+R)/2），而任何对称矩阵都只能给
    M、S 各自乘一个系数，改不了 M 内部「中置/侧向」的配比。
    要真的在单声道里把中置提出来，只能做声源分离，那是另一套东西。
    所以这项只在立体声播放时听得到效果（耳机、保留立体声的平台）。
    「去人声」不受此限——它是做差，单声道折叠后中置照样被抵消。
    """
    m = (mode or "keep").lower()
    if m == "mono":
        return ["pan=mono|c0=0.5*c0+0.5*c1"]
    if m == "center_remove":
        # 左右相减：中置内容（L≈R）被抵消，两侧伴奏留下。
        # 两个通道给同一条差信号，避免单边反相听起来「头在飘」。
        return ["pan=stereo|c0=c0-c1|c1=c0-c1"]
    if m == "center_boost":
        # 矩阵按「M 不动、S 衰减到 0.344 倍」反解出来的，即中侧比 ×2.91。
        #
        # 为什么不直接给 M 加权重：M 抬 1.6 倍会让总电平一起涨 1.6 倍，
        # 在没开响度归一化的预览渲染里会削波。改成压 S 一样能拉大中侧比，
        # 而且总电平只降不升，零削波风险——听感上起作用的是比值不是绝对值。
        #
        # （早期版本写的是 c0=1.25*c0+0.45*c1，等价于 M×1.70、S×0.80，
        # 中侧比只放大到 2.13 倍，还白送 1.7 倍电平。）
        return ["pan=stereo|c0=0.6719*c0+0.3281*c1|c1=0.3281*c0+0.6719*c1"]
    return []


def build_voice_chain(spec: AudioSpec) -> list[str]:
    """素材处理链。插在片段拼接之后、与 BGM 混音之前。

    放在拼接之后而不是每段之前，是因为降噪/压缩这类算法需要连续的
    上下文；逐段处理会在每个剪辑点产生可听的接缝。
    """
    if not spec.is_active():
        return []

    out: list[str] = []

    # 1) 削波修复 —— 必须在最前，它是「修复」不是「修饰」
    if spec.declick:
        out.append("adeclip=w=55:o=75:a=8:t=10")

    # 2) 降噪
    if spec.denoise in DENOISE_PRESETS:
        nr, nf = DENOISE_PRESETS[spec.denoise]
        # 不加 tn=1：实测自动跟踪噪声底反而几乎不动作，见上方 DENOISE_PRESETS 注释
        out.append(f"afftdn=nr={nr:g}:nf={nf:g}")

    # 3) 频段清理
    if spec.highpass > 0:
        out.append(f"highpass=f={float(spec.highpass):g}")
    if spec.lowpass > 0:
        out.append(f"lowpass=f={float(spec.lowpass):g}")

    # 4) 噪声门（threshold 是线性值）
    # strong 档自带一道门，阈值取 STRONG_GATE_DB；用户显式开了门就用用户的值。
    gate_db: float | None = None
    if spec.gate:
        gate_db = spec.gate_db
    elif spec.denoise == "strong":
        gate_db = STRONG_GATE_DB
    if gate_db is not None:
        th = min(1.0, max(1e-6, db_to_linear(gate_db)))
        # range 决定最多能压多少：0.002 ≈ -54dB，接近全关
        out.append(
            f"agate=threshold={th:.6f}:range=0.002:ratio=2:attack=10:release=200:makeup=1"
        )

    # 5) EQ 三段
    if abs(spec.warmth) > 1e-6:
        out.append(f"equalizer=f=200:t=q:w=1.0:g={float(spec.warmth):g}")
    if abs(spec.presence) > 1e-6:
        out.append(f"equalizer=f=3200:t=q:w=1.2:g={float(spec.presence):g}")
    if abs(spec.deess) > 1e-6:
        out.append(f"equalizer=f=7000:t=q:w=1.5:g={float(spec.deess):g}")

    # 6) 压缩（threshold 同样是线性值）
    if spec.compress:
        th = min(1.0, max(0.000976563, db_to_linear(spec.comp_db)))
        ratio = min(20.0, max(1.0, float(spec.comp_ratio)))
        makeup = max(1.0, float(spec.comp_makeup or 1.0))
        out.append(
            f"acompressor=threshold={th:.6f}:ratio={ratio:g}"
            f":attack=20:release=250:makeup={makeup:g}:knee=2.83"
        )

    # 7) 立体声矩阵
    out.extend(_stereo_chain(spec.stereo))

    # 8) 静态增益
    if abs(spec.gain_db) > 1e-6:
        out.append(f"volume={db_to_linear(spec.gain_db):.6f}")

    return out


def loudnorm_filter(
    *,
    target_lufs: float,
    true_peak: float,
    measured: dict[str, Any] | None = None,
    probe: bool = False,
) -> str:
    """拼 loudnorm 的参数串。三种模式：探测 / 定标 / 动态。

    单遍 loudnorm 是「动态」模式——它的增益是随时间自适应爬升的，
    对长片没问题，但对几秒的短片，增益还没收敛就结束了，落点会偏
    （实测目标 -16 跑出 -14.5）。所以先跑一遍探测拿到实测值，再带着
    measured_* + linear=true 走第二遍，这才是官方推荐的两遍法。
    """
    base = f"loudnorm=I={float(target_lufs):g}:TP={float(true_peak):g}:LRA=11"
    if probe:
        # 探测模式：只出统计，不改动音频
        return base + ":print_format=json"
    if measured and measured.get("ok"):
        return (
            base
            + f":measured_I={measured['input_i']:.4f}"
            + f":measured_TP={measured['input_tp']:.4f}"
            + f":measured_LRA={measured['input_lra']:.4f}"
            + f":measured_thresh={measured['input_thresh']:.4f}"
            + f":offset={measured['target_offset']:.4f}"
            + ":linear=true"
        )
    return base


def build_master_chain(
    *,
    normalize: bool,
    target_lufs: float,
    true_peak: float,
    limiter: bool,
    fade_in: float,
    fade_out: float,
    total_out: float,
    measured: dict[str, Any] | None = None,
    probe: bool = False,
) -> list[str]:
    """母带链。插在混音之后，是全片的收尾处理。

    顺序固定为：统一格式 → 响度归一化 → 限幅 → 淡入淡出。
    淡出排在响度之后是硬要求，理由见模块文档。

    probe=True 时只到 loudnorm 就截断：探测要量的是「进入 loudnorm 的
    信号」，限幅和淡入淡出都在它下游，不该算进这次测量。淡出尤其不能算，
    它会把结尾的电平拉低，把测出来的响度带偏。
    """
    out: list[str] = [
        "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    ]

    if normalize:
        out.append(loudnorm_filter(
            target_lufs=target_lufs, true_peak=true_peak,
            measured=measured, probe=probe,
        ))
        if probe:
            return out

    if limiter:
        lim = min(1.0, max(0.0625, db_to_linear(true_peak)))
        # level=0 关掉自动电平：否则它会把输出重新拉到 limit，抹平 loudnorm。
        # latency=1 补偿前瞻延迟，不然音轨会相对画面整体后移几个毫秒。
        out.append(
            f"alimiter=limit={lim:.6f}:attack=5:release=50:level=0:latency=1"
        )

    if fade_in > 0:
        out.append(f"afade=t=in:st=0:d={float(fade_in):.3f}")
    if fade_out > 0 and total_out > fade_out:
        out.append(
            f"afade=t=out:st={max(0.0, total_out - float(fade_out)):.3f}"
            f":d={float(fade_out):.3f}"
        )

    return out


# ---------------------------------------------------------------------------
# 测量
# ---------------------------------------------------------------------------

_NULL = "NUL" if os.name == "nt" else "/dev/null"


def parse_loudnorm_json(text: str) -> dict[str, Any]:
    """从 ffmpeg stderr 里刮出 loudnorm 的统计 JSON。

    单独抽成函数是因为两处都要用：measure_loudness() 量素材，
    render 的两遍 loudnorm 量混音结果。两边解析口径必须一致，
    不然第一遍量到的数和第二遍喂进去的数会对不上。
    """
    text = (text or "").strip()
    start = text.rfind("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return {"ok": False, "error": "loudnorm 没有输出可解析的统计"}
    try:
        blob = json.loads(text[start:end + 1])
    except ValueError:
        return {"ok": False, "error": "loudnorm 统计不是合法 JSON"}
    return {
        "ok": True,
        "input_i": float(blob.get("input_i", 0) or 0),
        "input_tp": float(blob.get("input_tp", 0) or 0),
        "input_lra": float(blob.get("input_lra", 0) or 0),
        "input_thresh": float(blob.get("input_thresh", 0) or 0),
        "target_offset": float(blob.get("target_offset", 0) or 0),
    }


def measure_loudness(path: Path | str) -> dict[str, Any]:
    """用 EBU R128 测一段音频的响度与真峰值。

    走一遍 loudnorm 的分析模式（不产出文件），比 ebur128 更好解析。
    """
    proc = ff.run(
        [
            ff.ffmpeg(), "-hide_banner", "-nostdin",
            "-i", str(path),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
            "-f", "null", _NULL,
        ],
        check=False,
        timeout=600,
    )
    return parse_loudnorm_json(proc.stderr or "")


def _hum_score(quiet: "Any", sr: int) -> float:
    """在低频频段找工频哼声，返回「哼声相对邻带高出多少 dB」。

    做法是把 50Hz 及其谐波（50/100/150Hz）的能量，和它们旁边同宽的
    参考带比。用参考带而不是绝对能量，是为了不被「整体低频厚」的素材
    误判——人声、房间隆隆声在低频都有能量，但不会只精准地堆在 50Hz 上。

    必须在安静段上量：哼声在有人声的时候被盖住，在有声段上量不出来。
    所以调用方传进来的是「最安静的那部分」。
    """
    import numpy as np

    n = len(quiet)
    if n < 8192:
        return 0.0
    win = 8192
    frames = quiet[: (n // win) * win].reshape(-1, win)
    if frames.size == 0:
        return 0.0
    # Hann 窗 + 平均功率谱，等价于简易 Welch
    w = np.hanning(win).astype(np.float32)
    spec = np.abs(np.fft.rfft(frames * w, axis=1)) ** 2
    psd = spec.mean(axis=0)
    freqs = np.fft.rfftfreq(win, 1 / sr)

    def band_energy(lo: float, hi: float) -> float:
        m = (freqs >= lo) & (freqs <= hi)
        return float(psd[m].sum()) if m.any() else 0.0

    # 50Hz 工频及其二、三次谐波；参考带取它们之间的空隙
    hum = sum(band_energy(*b) for b in ((48, 52), (98, 103), (148, 154)))
    ref = sum(band_energy(*b) for b in ((62, 88), (112, 138), (162, 190)))
    if ref <= 0 or hum <= 0:
        return 0.0
    return 10.0 * float(np.log10(hum / ref))


def measure_noise_floor(
    path: Path | str,
    *,
    window: float = 0.4,
    percentile: float = 10.0,
    hum_threshold_db: float = 6.0,
) -> dict[str, Any]:
    """估算底噪，顺带判一次有没有工频哼声。

    底噪用「第 percentile 分位的 RMS」，而不是全局最小，是为了不被单帧
    数字静音带偏。默认取第 10 分位。

    哼声检测在同一个函数里做，是为了不重复解码一遍音频——解码是这里
    最贵的一步。检测结果只作提示，降噪器对哼声无效，得靠 highpass。
    """
    info = ff.probe(path)
    if not info.has_audio:
        return {"ok": False, "error": "没有音频流"}

    sr = 48000
    proc = ff.run_bytes(
        [
            ff.ffmpeg(), "-hide_banner", "-nostdin",
            "-i", str(path),
            "-vn", "-ac", "1", "-ar", str(sr),
            "-f", "s16le", "-",
        ],
        check=False,
        timeout=900,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or b"").decode("utf-8", "replace")[-300:]}

    raw = proc.stdout or b""
    if not raw:
        return {"ok": False, "error": "解码出来是空的"}

    import numpy as np

    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    n = max(1, int(sr * window))
    frames = x[: (len(x) // n) * n].reshape(-1, n)
    if frames.size == 0:
        return {"ok": False, "error": "音频太短，切不出一个窗口"}

    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1) + 1e-12)
    floor = float(np.percentile(rms, percentile))
    peak_rms = float(np.percentile(rms, 95))

    # 只拿最安静的那四分之一来判哼声：有人声的时候哼声被盖住
    quiet_cut = float(np.percentile(rms, 25))
    quiet_frames = frames[rms <= quiet_cut]
    quiet = quiet_frames.reshape(-1) if quiet_frames.size else frames[0]
    hum_db = _hum_score(quiet, sr)

    return {
        "ok": True,
        "noise_floor_db": round(20.0 * float(np.log10(max(floor, 1e-9))), 1),
        "signal_db": round(20.0 * float(np.log10(max(peak_rms, 1e-9))), 1),
        "snr_db": round(
            20.0 * float(np.log10(max(peak_rms, 1e-9) / max(floor, 1e-9))), 1
        ),
        "window": window,
        "hum_db": round(hum_db, 1),
        "has_hum": hum_db > hum_threshold_db,
    }


# ---------------------------------------------------------------------------
# 链路延迟
# ---------------------------------------------------------------------------

# 实测（tests/test_sync.py）：afftdn 在 48kHz 下把音轨整体推后约 24ms。
# 24ms 已经到了唇音同步能察觉的量级（ITU-R BT.1359 对音频延迟的容忍约 45ms，
# 但那是上限不是目标），所以渲染时必须把这段补回来。
# 不靠公式推——不同 ffmpeg 版本内部窗口大小不同，跑一次脉冲探针实测最稳。

_LAT_CACHE: dict[tuple[str, ...], float] = {}
_PROBE_SR = 48000
_PROBE_AT = 0.2


def measure_chain_latency(chain: Sequence[str], sr: int = _PROBE_SR) -> float:
    """实测一条音频处理链的固有延迟（秒）。结果按链路缓存。

    做法：造一个第 0.2s 有冲击的静音轨，过一遍链，看冲击跑到哪去了。
    返回 0 表示这条链没有可测延迟。
    """
    key = tuple(chain)
    if not key:
        return 0.0
    if key in _LAT_CACHE:
        return _LAT_CACHE[key]

    import numpy as np

    lat = 0.0
    try:
        n = int(0.6 * sr)
        x = np.zeros(n, dtype=np.float32)
        at = int(_PROBE_AT * sr)
        seg = (
            np.exp(-np.arange(400) / 25.0)
            * np.sin(2 * np.pi * 900 * np.arange(400) / sr)
        ).astype(np.float32)
        x[at:at + len(seg)] += seg * 0.5
        pcm = (np.clip(np.stack([x, x], 1), -1, 1) * 32767).astype("<i2").tobytes()

        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "probe.wav"
            w = ff.run_bytes(
                [ff.ffmpeg(), "-hide_banner", "-v", "error", "-y",
                 "-f", "s16le", "-ar", str(sr), "-ac", "2", "-i", "-", str(src)],
                input_bytes=pcm, check=False, timeout=60,
            )
            if w.returncode != 0:
                raise RuntimeError((w.stderr or b"")[-200:].decode("utf-8", "replace"))
            p = ff.run_bytes(
                [ff.ffmpeg(), "-hide_banner", "-v", "error", "-y", "-i", str(src),
                 "-af", ",".join(chain), "-ar", str(sr), "-ac", "1",
                 "-f", "s16le", "-"],
                check=False, timeout=300,
            )
            if p.returncode == 0 and p.stdout:
                y = np.frombuffer(p.stdout, dtype="<i2").astype(np.float32) / 32768.0
                if y.size:
                    win = 32
                    energy = np.convolve(y ** 2, np.ones(win) / win, mode="same")
                    peak = float(np.argmax(energy)) / sr
                    lat = max(0.0, peak - _PROBE_AT)
    except Exception:  # noqa: BLE001
        # 探针失败不该挡住渲染：退回 0，最多是同步差一点点
        lat = 0.0

    # 量化到 1ms，避免每次算出 0.0239997 这种值导致缓存键漂移
    lat = round(lat, 3)
    _LAT_CACHE[key] = lat
    return lat
