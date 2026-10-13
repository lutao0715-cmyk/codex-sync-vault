#!/usr/bin/env python3
"""本地剪辑面板的服务端。

只监听 127.0.0.1，只读写本机文件，不联网、不上传。
用线程跑渲染任务，前端轮询进度。
"""

from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import socket
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze as A  # noqa: E402
import audio as AU  # noqa: E402
import ff, render as R  # noqa: E402
from audio import AudioSpec  # noqa: E402
from model import EditPlan, OutputSpec, Segment, ensure_dir  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_ROOT / "templates"

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm", ".flv", ".wmv", ".mpg", ".mpeg", ".ts"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
MEDIA_EXT = VIDEO_EXT | AUDIO_EXT


# ---------------------------------------------------------------------------
# 会话状态
# ---------------------------------------------------------------------------


class Session:
    """一个面板会话：一份素材 + 一份当前方案 + 若干任务。"""

    def __init__(self, workdir: Path):
        self.id = uuid.uuid4().hex[:12]
        self.workdir = ensure_dir(workdir)
        ensure_dir(self.workdir / "thumbs")
        ensure_dir(self.workdir / "preview")
        ensure_dir(self.workdir / "audition")

        self.media: Path | None = None
        self.music: Path | None = None
        self.analysis: dict | None = None
        self.audio_probe: dict | None = None
        self.audition: Path | None = None
        self.plan: EditPlan | None = None
        self.jobs: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def stats(self) -> dict:
        return {
            "media": str(self.media) if self.media else None,
            "media_name": self.media.name if self.media else None,
            "music": str(self.music) if self.music else None,
            "has_analysis": self.analysis is not None,
            "has_plan": self.plan is not None,
            "audio_probe": self.audio_probe,
            "has_audition": self.audition is not None and self.audition.is_file(),
            "workdir": str(self.workdir),
        }


def default_workdir() -> Path:
    home = Path.home()
    for parent in (home / "Movies", home / "Videos", home):
        if parent.exists():
            return parent / "avx-output"
    return Path(home) / "avx-output"


# ---------------------------------------------------------------------------
# 音频处理
# ---------------------------------------------------------------------------

# 前端要用的枚举与文案都由服务端给，避免两边各写一份、改了一边忘另一边。
def audio_preset_catalog() -> dict[str, Any]:
    """给前端用的枚举与文案，外加每个预设展开后的完整参数。

    这里回的是「从默认值套上该预设」的完整 spec，而不是只回预设覆盖的那几项。
    理由是切预设时表单必须能整份重填：如果只回覆盖项，从 interview 切到
    voice 时会残留 interview 才有的参数（比如 deess），看起来像官方预设
    带了脏数据。服务端回完整值，前端直接照着填，两边不会各有一套合并逻辑。
    """
    presets = [
        {
            "id": k,
            "label": v["label"],
            "hint": v["hint"],
            "spec": AU.apply_preset(AudioSpec(), k).to_dict(),
        }
        for k, v in AU.PRESETS.items()
    ]
    return {
        "presets": presets,
        "denoise": [
            {"id": "none", "label": "不降噪"},
            {"id": "light", "label": "轻"},
            {"id": "standard", "label": "标准"},
            {"id": "strong", "label": "强（= 标准 + 噪声门）"},
        ],
        "stereo": [
            {"id": "keep", "label": "保持原样"},
            {"id": "center_boost", "label": "人声靠前（仅立体声有效）"},
            {"id": "center_remove", "label": "去人声（伴奏）"},
            {"id": "mono", "label": "合到单声道"},
        ],
        "defaults": AudioSpec().to_dict(),
        "strong_gate_db": AU.STRONG_GATE_DB,
        "field_help": {
            "highpass": "低切。削掉这个频率以下的隆隆声，人声常用 80~120Hz",
            "lowpass": "高切。削掉这个频率以上的嘶声，一般 14k~16kHz",
            "gate_db": "噪声门阈值。必须高于素材实测底噪才关得上，"
                       "高太多又会切掉字的尾音。点「测量底噪」会按实测值给建议",
            "warmth": "200Hz 附近的厚度，正值为胸腔共鸣",
            "presence": "3.2kHz 附近的清晰度，正值为咬字更清楚",
            "deess": "7kHz 附近的齿音，负值才是衰减，别填正值",
            "comp_db": "压缩阈值。越低压得越狠",
        },
    }


# ---------------------------------------------------------------------------
# HTTP 处理
# ---------------------------------------------------------------------------


class Handler(BaseHTTPRequestHandler):
    server_version = "AVXPanel/1.0"
    session: Session

    # ---------------------------------------------------------------- 基础
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002
        if os.environ.get("AVX_VERBOSE"):
            sys.stderr.write("[panel] " + (fmt % args) + "\n")

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, data: Any, code: int = 200) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _err(self, msg: str, code: int = 400) -> None:
        self._json({"ok": False, "error": msg}, code)

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _json_body(self) -> dict:
        raw = self._body()
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    # ---------------------------------------------------------------- 路由
    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)
        try:
            if path in ("/", "/index.html"):
                return self._serve_file(TEMPLATES / "panel.html")
            if path.startswith("/templates/"):
                name = os.path.basename(unquote(path))
                if ".." in path or not name:
                    return self._err("非法路径", 400)
                return self._serve_file(TEMPLATES / name)
            if path == "/api/state":
                return self._json({"ok": True, **self.session.stats()})
            if path == "/api/media":
                return self._serve_media()
            if path == "/api/music":
                return self._serve_media(music=True)
            if path == "/api/thumb":
                return self._thumb(q)
            if path == "/api/analysis":
                return self._json({"ok": True, "analysis": self.session.analysis})
            if path == "/api/audio/presets":
                # 展开而不是塞进 presets 键：catalog 自己已经带 presets 字段了，
                # 再包一层会变成 {"presets":{"presets":[...]}}
                return self._json({"ok": True, **audio_preset_catalog()})
            if path == "/api/audio":
                return self._serve_audition()
            if path == "/api/plan":
                return self._json({"ok": True, "plan": self.session.plan.to_dict()
                                   if self.session.plan else None})
            if path.startswith("/api/job/"):
                jid = path.rsplit("/", 1)[-1]
                job = self.session.jobs.get(jid)
                if not job:
                    return self._err("任务不存在", 404)
                return self._json({"ok": True, **job})
            if path.startswith("/api/result/"):
                return self._serve_result(path.rsplit("/", 1)[-1])
            if path == "/api/doctor":
                from doctor import doctor_report  # noqa: PLC0415

                return self._json(doctor_report())
            if path == "/favicon.ico":
                return self._send(204, b"", "image/x-icon")
            return self._err("未知接口", 404)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            return self._err(f"{type(exc).__name__}: {exc}", 500)

    def do_POST(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)
        try:
            if path == "/api/attach":
                return self._attach()
            if path == "/api/upload":
                return self._upload(q)
            if path == "/api/analyze":
                return self._analyze()
            if path == "/api/audio/probe":
                return self._audio_probe()
            if path == "/api/audio/suggest":
                return self._audio_suggest()
            if path == "/api/audio/audition":
                return self._audition()
            if path == "/api/plan":
                return self._make_plan()
            if path == "/api/render":
                return self._render()
            if path == "/api/reset":
                self.session.media = None
                self.session.analysis = None
                self.session.audio_probe = None
                self.session.audition = None
                self.session.plan = None
                return self._json({"ok": True})
            return self._err("未知接口", 404)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            return self._err(f"{type(exc).__name__}: {exc}", 500)

    # ---------------------------------------------------------------- 静态
    def _serve_file(self, p: Path) -> None:
        if not p.is_file():
            return self._err(f"文件不存在：{p.name}", 404)
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        if p.suffix in (".html", ".css", ".js", ".json"):
            ctype += "; charset=utf-8"
        self._send(200, p.read_bytes(), ctype)

    # ---------------------------------------------------------------- 媒体
    def _media_path(self, *, music: bool = False) -> Path | None:
        return self.session.music if music else self.session.media

    def _serve_media(self, *, music: bool = False) -> None:
        """带 Range 支持的媒体流，浏览器里能拖进度条。"""
        p = self._media_path(music=music)
        if not p or not p.is_file():
            return self._err("还没有素材", 404)

        size = p.stat().st_size
        ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
        rng = self.headers.get("Range")

        if not rng:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with open(p, "rb") as fh:
                shutil.copyfileobj(fh, self.wfile, 512 * 1024)
            return

        m = re.match(r"bytes=(\d*)-(\d*)", rng)
        if not m:
            return self._err("非法 Range", 416)
        start = int(m.group(1)) if m.group(1) else 0
        end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end:
            return self._err("非法 Range", 416)

        length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(length))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with open(p, "rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(512 * 1024, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                remaining -= len(chunk)

    def _serve_result(self, job_id: str) -> None:
        job = self.session.jobs.get(job_id)
        if not job or not job.get("output"):
            return self._err("结果不存在", 404)
        p = Path(job["output"])
        if not p.is_file():
            return self._err("结果文件已被移动或删除", 404)
        data = p.read_bytes()
        self._send(200, data, mimetypes.guess_type(str(p))[0] or "video/mp4",
                   {"Content-Disposition": f'attachment; filename="{p.name}"'})

    def _thumb(self, q: dict) -> None:
        p = self.session.media
        if not p:
            return self._err("还没有素材", 404)
        try:
            t = float(q.get("t", ["0"])[0])
            w = int(q.get("w", ["220"])[0])
        except ValueError:
            return self._err("参数错误")
        cache = self.session.workdir / "thumbs" / f"t{int(t * 100):08d}_w{w}.jpg"
        if not cache.exists():
            got = A.extract_thumb(p, t, cache, width=w)
            if not got:
                return self._err("截帧失败", 500)
        self._send(200, cache.read_bytes(), "image/jpeg",
                   {"Cache-Control": "public, max-age=3600"})

    # ---------------------------------------------------------------- 素材
    def _resolve(self, raw: str) -> Path:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p)
        return p.resolve()

    def _attach(self) -> None:
        data = self._json_body()
        raw = str(data.get("path") or "").strip()
        if not raw:
            return self._err("缺少 path")
        p = self._resolve(raw)
        if not p.is_file():
            return self._err(f"文件不存在：{p}", 404)
        if p.suffix.lower() not in MEDIA_EXT:
            return self._err(f"不支持的文件类型：{p.suffix}")

        music = str(data.get("music") or "").strip()
        with self.session.lock:
            self.session.media = p
            self.session.analysis = None
            self.session.plan = None
            if music:
                mp = self._resolve(music)
                self.session.music = mp if mp.is_file() else None
        return self._json({"ok": True, "attached": str(p), **self.session.stats()})

    def _upload(self, q: dict) -> None:
        name = unquote(q.get("name", ["upload.mp4"])[0])
        name = os.path.basename(name) or "upload.mp4"
        suffix = Path(name).suffix.lower()
        if suffix not in MEDIA_EXT:
            return self._err(f"不支持的文件类型：{suffix}")

        dest = self.session.workdir / name
        n = 2
        while dest.exists():
            dest = self.session.workdir / f"{Path(name).stem}_{n}{suffix}"
            n += 1

        total = int(self.headers.get("Content-Length") or 0)
        got = 0
        with open(dest, "wb") as fh:
            while True:
                chunk = self.rfile.read(min(1024 * 1024, max(1, total - got)) if total else 1024 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                got += len(chunk)
                if total and got >= total:
                    break

        if dest.stat().st_size == 0:
            dest.unlink(missing_ok=True)
            return self._err("上传内容为空")

        with self.session.lock:
            self.session.media = dest
            self.session.analysis = None
            self.session.plan = None
        return self._json({"ok": True, "attached": str(dest), **self.session.stats()})

    # ---------------------------------------------------------------- 分析
    def _analyze(self) -> None:
        p = self.session.media
        if not p:
            return self._err("还没有素材")
        d = self._json_body()
        result = A.analyze(
            p,
            do_silence=bool(d.get("silence", True)),
            do_scenes=bool(d.get("scenes", True)),
            do_beats=bool(d.get("beats", True)),
            silence_kwargs={
                "noise_db": float(d.get("noise_db", -30.0)),
                "min_duration": float(d.get("min_silence", 0.35)),
            },
            scene_kwargs={
                "threshold": float(d.get("threshold", 0.30)),
                "min_scene": float(d.get("min_scene", 0.6)),
            },
            beat_kwargs={"sensitivity": float(d.get("sensitivity", 1.0))},
            wave_buckets=int(d.get("wave_buckets", 1000)),
        )
        self.session.analysis = result
        return self._json({"ok": True, "analysis": result})

    # ---------------------------------------------------------------- 音频
    def _audio_probe(self) -> None:
        """量素材的底噪，顺带判一次工频哼声。结果缓存进会话。"""
        p = self.session.media
        if not p:
            return self._err("还没有素材")
        probe = AU.measure_noise_floor(p)
        if not probe.get("ok"):
            return self._err(f"测量失败：{probe.get('error', '未知原因')}")
        self.session.audio_probe = probe
        return self._json({"ok": True, "probe": probe})

    def _audio_suggest(self) -> None:
        """按实测底噪给一档建议。返回 spec + 理由，前端只填表不改判断。"""
        p = self.session.media
        if not p:
            return self._err("还没有素材")
        d = self._json_body()

        probe = self.session.audio_probe
        if not probe or not probe.get("ok"):
            probe = AU.measure_noise_floor(p)
            if not probe.get("ok"):
                return self._err(f"测量失败：{probe.get('error', '未知原因')}")
            self.session.audio_probe = probe

        spec, why = AU.suggest_spec(
            noise_floor_db=float(probe["noise_floor_db"]),
            is_music=bool(d.get("is_music", False)),
            has_hum=bool(probe.get("has_hum", False)),
            outdoor=bool(d.get("outdoor", False)),
        )
        return self._json({
            "ok": True, "spec": spec.to_dict(), "why": why, "probe": probe,
        })

    def _audition(self) -> None:
        """只渲染音轨，用来快速试听音频处理效果。

        走的是和成片完全一样的剪辑与处理链，所以听到什么，成片就是什么。
        不改成预览参数——试听的意义就在于它和成片一致。
        """
        p = self.session.media
        if not p:
            return self._err("还没有素材")

        d = self._json_body()
        if isinstance(d.get("plan"), dict):
            plan = EditPlan.from_dict(d["plan"])
        elif self.session.plan is not None:
            plan = EditPlan.from_dict(self.session.plan.to_dict())
        else:
            plan = EditPlan(sources=[str(p)], segments=[Segment(0.0, ff.probe(p).duration)])
        if not plan.sources:
            plan.sources = [str(p)]

        # 试听时前端可能只传了音频参数，没传整份方案
        if "audio" in d:
            plan.audio = AudioSpec.from_dict(d["audio"])

        out = ensure_dir(self.session.workdir / "audition") / "audition.m4a"
        try:
            R.render_audio(plan, out)
        except ff.FFmpegError as exc:
            return self._err(f"试听渲染失败：{str(exc)[-400:]}")

        self.session.audition = out
        return self._json({
            "ok": True,
            "url": f"/api/audio?t={int(time.time() * 1000)}",
            "size": out.stat().st_size,
            "active": plan.audio.active_list(),
            "warnings": plan.audio.warnings(),
        })

    def _serve_audition(self) -> None:
        """把试听音轨以内联方式吐出去，<audio> 标签才能直接播。"""
        p = self.session.audition
        if not p or not p.is_file():
            return self._err("还没有试听音频", 404)
        self._send(
            200, p.read_bytes(),
            mimetypes.guess_type(str(p))[0] or "audio/mp4",
            {"Cache-Control": "no-store"},
        )

    # ---------------------------------------------------------------- 方案
    def _make_plan(self) -> None:
        p = self.session.media
        if not p:
            return self._err("还没有素材")
        d = self._json_body()
        mode = str(d.get("mode") or "silence")

        if mode == "silence":
            plan = A.plan_from_silence(
                p,
                noise_db=float(d.get("noise_db", -30.0)),
                min_silence=float(d.get("min_silence", 0.35)),
                padding=float(d.get("padding", 0.06)),
                min_keep=float(d.get("min_keep", 0.25)),
                silence_mode=str(d.get("silence_mode", "cut")),
                silence_speed=float(d.get("silence_speed", 4.0)),
            )
        elif mode == "scene":
            plan = A.plan_from_scenes(
                p,
                threshold=float(d.get("threshold", 0.30)),
                min_scene=float(d.get("min_scene", 0.6)),
                drop_shorter_than=float(d.get("drop_shorter_than", 0.0)),
            )
        elif mode == "beat":
            music = self.session.music
            if music is None and str(d.get("music") or "").strip():
                mp = self._resolve(str(d["music"]))
                if mp.is_file():
                    music = mp
                    self.session.music = mp
            plan = A.plan_from_beats(
                p,
                music=music,
                sensitivity=float(d.get("sensitivity", 1.0)),
                beats_per_cut=max(1, int(d.get("beats_per_cut", 1))),
                stride=float(d.get("stride", 1.35)),
                lead_in=float(d.get("lead_in", 0.0)),
            )
        elif mode == "manual":
            plan = EditPlan(sources=[str(p)], mode="manual", title=p.stem)
            plan.segments = [Segment(0.0, ff.probe(p).duration)]
        else:
            return self._err(f"未知模式：{mode}")

        plan.output = OutputSpec.from_dict(d.get("output") or {})
        # 音频处理参数跟着方案一起存，这样「生成方案」和「试听」「出片」
        # 三条路走的是同一份参数，不会出现试听好听、成片却是别的设置。
        if isinstance(d.get("audio"), dict):
            plan.audio = AudioSpec.from_dict(d["audio"])
        if music := self.session.music:
            plan.meta["music"] = str(music)
            if "audio_source" not in plan.meta:
                plan.meta["audio_source"] = "music" if mode == "beat" else "concat"

        # 前端可以传回手动调整过的片段
        segs = d.get("segments")
        if isinstance(segs, list) and segs:
            plan.segments = [Segment.from_dict(s) for s in segs]
            plan.normalize()

        self.session.plan = plan
        return self._json({"ok": True, "plan": plan.to_dict()})

    # ---------------------------------------------------------------- 渲染
    def _render(self) -> None:
        p = self.session.media
        if not p:
            return self._err("还没有素材")
        d = self._json_body()

        if isinstance(d.get("plan"), dict):
            plan = EditPlan.from_dict(d["plan"])
        elif self.session.plan is not None:
            plan = EditPlan.from_dict(self.session.plan.to_dict())
        else:
            return self._err("还没有剪辑方案，先点「生成方案」")

        if not plan.sources:
            plan.sources = [str(p)]

        preview = bool(d.get("preview"))
        out_dir = ensure_dir(self.session.workdir / ("preview" if preview else "output"))
        stamp = time.strftime("%m%d_%H%M%S")
        stem = f"{Path(plan.sources[0]).stem}_{plan.mode}_{stamp}"
        out_path = out_dir / f"{stem}{'.mp4' if not preview else '_preview.mp4'}"

        music = self.session.music
        if music is None and plan.meta.get("music"):
            mp = Path(str(plan.meta["music"]))
            if mp.is_file():
                music = mp

        job_id = uuid.uuid4().hex[:10]
        job: dict[str, Any] = {
            "id": job_id, "status": "running", "percent": 0.0,
            "output": None, "error": None, "preview": preview,
            "started": time.time(), "message": "准备中",
        }
        self.session.jobs[job_id] = job

        def worker() -> None:
            def on_progress(ev: dict) -> None:
                if ev.get("event") == "progress":
                    job["percent"] = ev["percent"]
                    job["done"] = ev.get("done")
                    job["total"] = ev.get("total")
                    job["speed"] = ev.get("speed")
                    job["message"] = f"渲染中 {ev['percent']:.0f}%"
                elif ev.get("event") == "done":
                    job["percent"] = 100.0

            try:
                if preview:
                    R.render_preview(plan, out_path, music=music, progress=on_progress)
                else:
                    R.render(plan, out_path, music=music, progress=on_progress)
                job["status"] = "done"
                job["output"] = str(out_path)
                job["name"] = out_path.name
                job["size"] = out_path.stat().st_size
                job["message"] = "完成"
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                job["status"] = "error"
                job["error"] = str(exc)
                job["message"] = "渲染失败"
            finally:
                job["elapsed"] = round(time.time() - job["started"], 1)

        threading.Thread(target=worker, daemon=True).start()
        return self._json({"ok": True, "job": job_id})


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------


def _pick_port(preferred: int) -> int:
    for port in range(preferred, preferred + 40):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit("端口都被占用了，换一个 --port 吧。")


def serve(
    port: int = 8787,
    *,
    open_browser: bool = True,
    workdir: str | None = None,
    attach: list[str] | None = None,
) -> int:
    wd = Path(workdir).expanduser() if workdir else default_workdir()
    session = Session(wd)

    for raw in attach or []:
        p = Path(raw).expanduser()
        if p.is_file() and p.suffix.lower() in MEDIA_EXT:
            if p.suffix.lower() in AUDIO_EXT and session.music is None and session.media is not None:
                session.music = p.resolve()
            else:
                session.media = p.resolve()

    Handler.session = session
    port = _pick_port(port)
    url = f"http://127.0.0.1:{port}/"

    try:
        ff.ffmpeg()
        ff.ffprobe()
    except ff.FFmpegNotFound:
        print("提示：还没找到 ffmpeg，先跑一下  python3 scripts/doctor.py --fix")

    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True

    print("=" * 56)
    print("  自动剪辑面板已启动")
    print(f"  {url}")
    print(f"  工作目录：{wd}")
    print("  Ctrl+C 退出")
    print("=" * 56, flush=True)

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已关闭。")
    finally:
        httpd.server_close()
    return 0


def main() -> int:
    import argparse  # noqa: PLC0415

    ap = argparse.ArgumentParser(description="自动剪辑面板")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--workdir")
    # action="extend" 才能让重复出现的 --open 累加；
    # 单纯用 nargs="*" 时后一次会覆盖前一次，只留下最后一个路径。
    ap.add_argument("--open", nargs="*", action="extend", default=[],
                    help="启动时载入的素材（可重复传入，视频在前音乐在后）")
    args = ap.parse_args()
    return serve(args.port, open_browser=not args.no_open,
                 workdir=args.workdir, attach=args.open)


if __name__ == "__main__":
    raise SystemExit(main())
