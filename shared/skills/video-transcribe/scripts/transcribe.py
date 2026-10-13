#!/usr/bin/env python3
"""视频转录主脚本"""
import argparse
import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import ffmpeg
import requests
from pydub import AudioSegment

DEFAULT_WORK_DIR = Path(__file__).resolve().parent.parent


def check_cuda() -> bool:
    """检查 CUDA 是否可用"""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            print(f"[INFO] CUDA 可用，GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("[INFO] CUDA 不可用，将使用 CPU")
        return cuda_available
    except ImportError:
        print("[INFO] PyTorch 未安装，将使用 CPU")
        return False


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def extract_audio(video_path: Path, audio_dir: Path) -> Path:
    """从视频中提取音频"""
    ensure_dir(audio_dir)

    audio_path = audio_dir / f"{video_path.stem}.wav"
    print(f"[1/5] 正在提取音频: {video_path} -> {audio_path}")

    ffmpeg.input(str(video_path)).output(
        str(audio_path),
        acodec='pcm_s16le',
        ac=1,
        ar='16000'
    ).overwrite_output().run(quiet=True)

    print(f"音频提取完成: {audio_path}")
    return audio_path


def get_baidu_access_token(api_key: str, secret_key: str) -> str:
    """获取百度 API Access Token"""
    token_url = (
        'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials'
        f'&client_id={api_key}&client_secret={secret_key}'
    )
    response = requests.get(token_url, timeout=30)
    response.raise_for_status()
    access_token = response.json().get('access_token')
    if not access_token:
        raise RuntimeError('获取百度 API Access Token 失败')
    return access_token


def resolve_fastwhisper_server_url(
    server_url: Optional[str] = None,
    server_ip: Optional[str] = None,
    server_port: Optional[int] = None,
) -> str:
    """解析 fastwhisper 服务地址（支持命令行与环境变量）"""
    if server_url:
        return server_url.rstrip('/')

    env_url = os.getenv('FASTWHISPER_SERVER_URL', '').strip()
    if env_url:
        return env_url.rstrip('/')

    resolved_ip = (server_ip or os.getenv('FASTWHISPER_SERVER_IP') or '127.0.0.1').strip()
    resolved_port = server_port
    if resolved_port is None:
        env_port = os.getenv('FASTWHISPER_SERVER_PORT', '').strip()
        if env_port:
            try:
                resolved_port = int(env_port)
            except ValueError:
                raise ValueError('环境变量 FASTWHISPER_SERVER_PORT 必须是整数')
        else:
            resolved_port = 8000

    return f'http://{resolved_ip}:{resolved_port}'


def transcribe_with_fastwhisper_server(
    audio_path: Path,
    language: str,
    server_url: str,
    timeout_seconds: int = 600,
) -> Dict[str, Any]:
    """通过 fastwhisper 服务端 API 进行转录"""
    endpoint = f"{server_url.rstrip('/')}/transcribe/"
    print(f"[INFO] 使用 fastwhisper 服务端: {endpoint}")

    try:
        with open(audio_path, 'rb') as audio_file:
            response = requests.post(
                endpoint,
                files={'file': (audio_path.name, audio_file, 'audio/wav')},
                data={
                    'language': language,
                },
                timeout=timeout_seconds,
            )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f'调用 fastwhisper 服务失败: {exc}') from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError('fastwhisper 服务返回了无法解析的 JSON') from exc

    recognized_text = str(payload.get('text', '')).strip()
    if not recognized_text:
        raise RuntimeError('fastwhisper 服务返回内容为空')

    duration_sec = len(AudioSegment.from_wav(str(audio_path))) / 1000.0
    return {
        'text': recognized_text,
        'segments': [
            {
                'id': 0,
                'start': 0.0,
                'end': duration_sec,
                'text': recognized_text,
            }
        ],
    }


def transcribe_with_whisper(audio_path: Path, model_size: str, language: str) -> Dict[str, Any]:
    """使用 Whisper 进行转录"""
    # 检查是否有本地 whisper 命令
    import shutil
    whisper_cmd = shutil.which("whisper")

    if whisper_cmd:
        print("[INFO] 使用本地 whisper 命令行工具")
        return transcribe_with_cli(audio_path, model_size, language)

    # 优先尝试使用 faster-whisper（支持 GPU 加速）
    try:
        from faster_whisper import WhisperModel

        use_cuda = check_cuda()
        device = "cuda" if use_cuda else "cpu"
        compute_type = "float16" if use_cuda else "int8"

        print(f"[INFO] 使用 faster-whisper，设备: {device}, 计算类型: {compute_type}")
        model = WhisperModel(model_size, device=device, compute_type=compute_type)

        segments, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5
        )

        # 转换为 whisper 格式
        result_segments = []
        for i, segment in enumerate(segments):
            result_segments.append({
                'id': i,
                'start': segment.start,
                'end': segment.end,
                'text': segment.text.strip()
            })

        return {
            'text': ' '.join([s['text'] for s in result_segments]),
            'segments': result_segments,
        }

    except ImportError:
        # 没有 faster-whisper，使用普通 whisper
        import whisper
        use_cuda = check_cuda()
        device = "cuda" if use_cuda else "cpu"

        # 尝试加载模型
        try:
            model = whisper.load_model(model_size, device=device)
        except Exception as e:
            print(f"[WARN] 无法加载 {device} 模型，尝试 CPU: {e}")
            model = whisper.load_model(model_size, device="cpu")

        print(f"[INFO] 使用设备: {model.device}")
        return model.transcribe(str(audio_path), language=language, verbose=False)


def transcribe_with_cli(audio_path: Path, model_size: str, language: str) -> Dict[str, Any]:
    """使用 whisper 命令行工具进行转录"""
    import subprocess
    import shutil
    import tempfile

    # 检查 CUDA
    use_cuda = check_cuda()

    # 创建临时输出目录
    output_dir = Path(tempfile.mkdtemp())

    # 构建命令
    cmd = [
        "whisper",
        str(audio_path),
        "--model", model_size,
        "--language", language,
        "--output_dir", str(output_dir),
        "--output_format", "json",
    ]

    if use_cuda:
        cmd.append("--device")
        cmd.append("cuda")

    print(f"[INFO] 执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            print(f"[WARN] whisper CLI 失败: {result.stderr}")
            # 回退到 Python 库
            raise Exception("whisper CLI failed")

        # 读取输出 JSON
        json_files = list(output_dir.glob("*.json"))
        if json_files:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 转换为标准格式
            segments = []
            for i, seg in enumerate(data.get('segments', [])):
                segments.append({
                    'id': i,
                    'start': seg.get('start', 0),
                    'end': seg.get('end', 0),
                    'text': seg.get('text', '').strip()
                })

            return {
                'text': data.get('text', ''),
                'segments': segments,
            }

        raise Exception("No output JSON generated")

    finally:
        # 清理临时目录
        import shutil as sh
        if output_dir.exists():
            try:
                sh.rmtree(output_dir)
            except:
                pass


def transcribe_with_siliconflow(
    audio_path: Path,
    language: str,
    api_key: str,
    base_url: str = 'https://api.siliconflow.cn/v1',
    model: str = 'FunAudioLLM/SenseVoiceSmall',
    timeout_seconds: int = 600,
) -> Dict[str, Any]:
    """使用 SiliconFlow 语音识别 API 进行转录（免费 SenseVoiceSmall）"""
    endpoint = f"{base_url.rstrip('/')}/audio/transcriptions"
    print(f"[INFO] 使用 SiliconFlow ASR: {endpoint} (model={model})")

    language_map = {'zh': 'zh', 'en': 'en', 'ja': 'ja', 'ko': 'ko', 'yue': 'yue', 'auto': 'auto'}
    lang = language_map.get(language, 'auto')

    try:
        with open(audio_path, 'rb') as audio_file:
            response = requests.post(
                endpoint,
                headers={'Authorization': f'Bearer {api_key}'},
                files={'file': (audio_path.name, audio_file, 'audio/wav')},
                data={'model': model, 'language': lang},
                timeout=timeout_seconds,
            )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f'调用 SiliconFlow 服务失败: {exc}') from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError('SiliconFlow 服务返回了无法解析的 JSON') from exc

    recognized_text = str(payload.get('text', '')).strip()
    if not recognized_text:
        raise RuntimeError('SiliconFlow 服务返回内容为空')

    duration_sec = len(AudioSegment.from_wav(str(audio_path))) / 1000.0
    return {
        'text': recognized_text,
        'segments': [
            {
                'id': 0,
                'start': 0.0,
                'end': duration_sec,
                'text': recognized_text,
            }
        ],
    }


def transcribe_with_alibaba(
    audio_path: Path,
    language: str,
    api_key: str,
    model: str = 'qwen3-asr-flash',
    timeout_seconds: int = 600,
) -> Dict[str, Any]:
    """使用阿里云百炼（DashScope）语音识别进行转录（同步调用，本地文件直接传，SDK 自动上传，无需 OSS）"""
    import dashscope
    from dashscope import MultiModalConversation

    dashscope.api_key = api_key
    print(f"[INFO] 使用阿里百炼 ASR: model={model}")

    # 本地文件路径转 file:// URI（Path.as_uri 正确处理 Windows 盘符与空格转义）
    file_uri = audio_path.resolve().as_uri()
    messages = [{'role': 'user', 'content': [{'audio': file_uri}]}]

    language_hint = 'zh' if language.startswith('zh') else (language or None)
    asr_options = {}
    if language_hint:
        asr_options['language'] = language_hint

    try:
        response = MultiModalConversation.call(
            model=model,
            messages=messages,
            result_format='message',
            asr_options=asr_options or None,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        raise RuntimeError(f'调用阿里百炼 ASR 失败: {exc}') from exc

    if response.status_code != 200:
        raise RuntimeError(f'阿里百炼 ASR 返回错误: status={response.status_code}, {str(response)[:300]}')

    # 提取文本（qwen3-asr 返回 choices[0].message.content[].text）
    recognized_text = ''
    try:
        content = response.output['choices'][0]['message']['content']
        for item in content:
            if isinstance(item, dict) and item.get('text'):
                recognized_text += item['text']
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f'阿里百炼 ASR 响应解析失败: {exc}, raw={str(response)[:300]}') from exc

    recognized_text = recognized_text.strip()
    if not recognized_text:
        raise RuntimeError('阿里百炼 ASR 返回内容为空')

    duration_sec = len(AudioSegment.from_wav(str(audio_path))) / 1000.0
    return {
        'text': recognized_text,
        'segments': [
            {
                'id': 0,
                'start': 0.0,
                'end': duration_sec,
                'text': recognized_text,
            }
        ],
    }


def transcribe_with_baidu(audio_path: Path, language: str, api_key: str, secret_key: str) -> Dict[str, Any]:
    """使用百度 ASR 进行转录"""
    access_token = get_baidu_access_token(api_key, secret_key)

    with open(audio_path, 'rb') as file:
        audio_bytes = file.read()

    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    payload = {
        'format': 'wav',
        'rate': 16000,
        'channel': 1,
        'cuid': 'video-skill',
        'token': access_token,
        'speech': audio_base64,
        'len': len(audio_bytes),
        'dev_pid': 1537 if language.startswith('zh') else 1737,
    }

    response = requests.post(
        'https://vop.baidu.com/server_api',
        headers={'Content-Type': 'application/json'},
        data=json.dumps(payload),
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()

    if result.get('err_no', 0) != 0:
        raise RuntimeError(f"百度识别失败: {result.get('err_msg', '未知错误')}")

    recognized_text = ''.join(result.get('result', []))
    duration_sec = len(AudioSegment.from_wav(str(audio_path))) / 1000.0
    return {
        'text': recognized_text,
        'segments': [
            {
                'id': 0,
                'start': 0.0,
                'end': duration_sec,
                'text': recognized_text,
            }
        ],
    }


def format_srt_time(seconds: float) -> str:
    """格式化 SRT 时间"""
    total_ms = max(0, int(round(seconds * 1000)))
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    millis = total_ms % 1000
    return f'{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}'


def generate_srt(transcript_result: Dict[str, Any], output_base_path: Path) -> Path:
    """生成 SRT 字幕文件"""
    srt_path = output_base_path.with_suffix('.srt')
    segments = transcript_result.get('segments', []) or []

    if not segments:
        text = transcript_result.get('text', '').strip()
        segments = [{'id': 0, 'start': 0.0, 'end': 3.0, 'text': text or '...'}]

    lines: List[str] = []
    for index, segment in enumerate(segments, start=1):
        start_ts = format_srt_time(float(segment.get('start', 0.0)))
        end_ts = format_srt_time(float(segment.get('end', 0.0)))
        text = str(segment.get('text', '')).strip() or '...'
        lines.extend([str(index), f'{start_ts} --> {end_ts}', text, ''])

    srt_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"[4/5] 字幕文件生成成功: {srt_path}")

    # 生成纯文本字幕
    txt_path = output_base_path.with_suffix('.txt')
    txt_lines: List[str] = []
    for segment in segments:
        text = str(segment.get('text', '')).strip()
        if text and text != '...':
            txt_lines.append(text)
    txt_path.write_text('\n'.join(txt_lines), encoding='utf-8')
    print(f"[4/5] 文本字幕生成成功: {txt_path}")

    return srt_path


def transcribe_audio(
    audio_path: Path,
    model_size: str = 'base',
    language: str = 'zh',
    use_whisper: bool = True,
    use_server: bool = False,
    use_siliconflow: bool = False,
    use_alibaba: bool = False,
    server_url: Optional[str] = None,
    server_ip: Optional[str] = None,
    server_port: Optional[int] = None,
    server_timeout: int = 600,
    api_key: Optional[str] = None,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """转录音频"""
    print('[3/5] 开始语音转文字...')
    if use_siliconflow:
        if not api_key:
            raise ValueError('使用 SiliconFlow API 时必须提供 api_key（--api-key 或 SILICONFLOW_API_KEY）')
        return transcribe_with_siliconflow(
            audio_path=audio_path,
            language=language,
            api_key=api_key,
            timeout_seconds=server_timeout,
        )

    if use_alibaba:
        if not api_key:
            raise ValueError('使用阿里百炼 API 时必须提供 api_key（--api-key 或 DASHSCOPE_API_KEY）')
        return transcribe_with_alibaba(
            audio_path=audio_path,
            language=language,
            api_key=api_key,
            timeout_seconds=server_timeout,
        )

    if use_server:
        resolved_url = resolve_fastwhisper_server_url(
            server_url=server_url,
            server_ip=server_ip,
            server_port=server_port,
        )
        return transcribe_with_fastwhisper_server(
            audio_path=audio_path,
            language=language,
            server_url=resolved_url,
            timeout_seconds=server_timeout,
        )

    if use_whisper:
        return transcribe_with_whisper(audio_path, model_size, language)

    if not api_key or not secret_key:
        raise ValueError('使用百度 API 时必须提供 api_key 与 secret_key')
    return transcribe_with_baidu(audio_path, language, api_key, secret_key)


def process_transcribe(
    video_path: Optional[Path] = None,
    audio_path: Optional[Path] = None,
    use_baidu: bool = False,
    use_server: bool = False,
    use_siliconflow: bool = False,
    use_alibaba: bool = False,
    server_url: Optional[str] = None,
    server_ip: Optional[str] = None,
    server_port: Optional[int] = None,
    server_timeout: int = 600,
    api_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    model_size: str = 'base',
    language: str = 'zh',
    work_dir: Path = Path('.'),
) -> Dict[str, Any]:
    """处理转录流程"""
    work_dir = Path(work_dir).resolve()
    audio_dir = work_dir / 'audio'
    results_dir = work_dir / 'results'

    try:
        ensure_dir(results_dir)
    except PermissionError as exc:
        raise PermissionError(
            f"无法创建输出目录: {results_dir}。请使用 --work-dir 指定可写目录后重试。"
        ) from exc

    # 确定音频来源
    if audio_path and audio_path.exists():
        # 使用本地音频
        input_audio_path = audio_path
        audio_title = audio_path.stem
        print(f'[1/5] 使用本地音频: {audio_path.name}')
    elif video_path and video_path.exists():
        # 从视频提取音频
        input_audio_path = extract_audio(video_path, audio_dir)
        audio_title = video_path.stem
    else:
        raise ValueError('必须提供 --video-path 或 --audio-path，且文件存在')

    audio = AudioSegment.from_wav(str(input_audio_path))
    duration_sec = len(audio) / 1000.0
    print(f"音频时长: {duration_sec:.2f} 秒")

    use_whisper = not (use_baidu or use_siliconflow or use_alibaba)
    transcript_result = transcribe_audio(
        audio_path=input_audio_path,
        model_size=model_size,
        language=language,
        use_whisper=use_whisper,
        use_server=use_server,
        use_siliconflow=use_siliconflow,
        use_alibaba=use_alibaba,
        server_url=server_url,
        server_ip=server_ip,
        server_port=server_port,
        server_timeout=server_timeout,
        api_key=api_key,
        secret_key=secret_key,
    )

    srt_path = generate_srt(transcript_result, results_dir / audio_title)
    print(f"[5/5] 字幕片段数量: {len(transcript_result.get('segments', []))}")
    print('[5/5] 转录产出完成')

    summary = {
        'video_path': str(video_path) if video_path else None,
        'audio_path': str(audio_path) if audio_path else None,
        'audio_extracted': str(input_audio_path.resolve()) if video_path else None,
        'srt_path': str(srt_path.resolve()),
        'txt_path': str(srt_path.with_suffix('.txt').resolve()),
        'segment_count': len(transcript_result.get('segments', [])),
        'server_url': resolve_fastwhisper_server_url(server_url, server_ip, server_port) if use_server else None,
    }

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='视频转录工具：生成字幕文件（SRT）和纯文本（txt）')
    parser.add_argument('--video-path', default=None, help='视频文件路径')
    parser.add_argument('--audio-path', default=None, help='音频文件路径')
    parser.add_argument('--language', default='zh', help='识别语言，默认 zh')
    parser.add_argument('--model-size', default='base', help='Whisper 模型：tiny/base/small/medium/large')
    parser.add_argument('--use-baidu', action='store_true', help='启用百度语音识别（默认使用 Whisper）')
    parser.add_argument('--use-siliconflow', action='store_true', help='启用 SiliconFlow 语音识别（SenseVoiceSmall，免费）')
    parser.add_argument('--use-alibaba', action='store_true', help='启用阿里百炼语音识别（qwen3-asr-flash，需 DASHSCOPE_API_KEY）')
    parser.add_argument('--use-server', action='store_true', help='启用服务端模式（调用 fastwhisper.py API）')
    parser.add_argument('--server-url', default=None, help='服务端完整地址，例如 http://127.0.0.1:8000（优先级最高）')
    parser.add_argument('--server-ip', default=None, help='服务端 IP 或主机名，可由 FASTWHISPER_SERVER_IP 指定')
    parser.add_argument('--server-port', type=int, default=None, help='服务端端口，可由 FASTWHISPER_SERVER_PORT 指定，默认 8000')
    parser.add_argument('--server-timeout', type=int, default=600, help='服务端请求超时（秒），默认 600')
    parser.add_argument('--api-key', default=None, help='各模式 API Key（百度 BAIDU_API_KEY / SiliconFlow SILICONFLOW_API_KEY / 阿里百炼 DASHSCOPE_API_KEY，也可由对应环境变量指定）')
    parser.add_argument('--secret-key', default=None, help='百度 Secret Key，也可由环境变量 BAIDU_SECRET_KEY 指定')
    parser.add_argument(
        '--work-dir',
        default=str(DEFAULT_WORK_DIR),
        help='工作目录（输出 audio/results），默认使用 Skill 根目录',
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    # 校验参数
    if not args.video_path and not args.audio_path:
        print('错误: 必须提供 --video-path 或 --audio-path')
        build_parser().print_help()
        return

    if args.use_baidu and args.use_server:
        raise ValueError('--use-baidu 与 --use-server 不能同时启用')
    if args.use_baidu and args.use_siliconflow:
        raise ValueError('--use-baidu 与 --use-siliconflow 不能同时启用')
    if args.use_baidu and args.use_alibaba:
        raise ValueError('--use-baidu 与 --use-alibaba 不能同时启用')
    if args.use_siliconflow and args.use_server:
        raise ValueError('--use-siliconflow 与 --use-server 不能同时启用')
    if args.use_siliconflow and args.use_alibaba:
        raise ValueError('--use-siliconflow 与 --use-alibaba 不能同时启用')
    if args.use_alibaba and args.use_server:
        raise ValueError('--use-alibaba 与 --use-server 不能同时启用')

    video_path = Path(args.video_path) if args.video_path else None
    audio_path = Path(args.audio_path) if args.audio_path else None

    # 从环境变量兜底（按模式取对应 key）
    if args.use_baidu:
        api_key = args.api_key or os.getenv('BAIDU_API_KEY')
    elif args.use_siliconflow:
        api_key = args.api_key or os.getenv('SILICONFLOW_API_KEY')
    elif args.use_alibaba:
        api_key = args.api_key or os.getenv('DASHSCOPE_API_KEY')
    else:
        api_key = args.api_key or os.getenv('BAIDU_API_KEY')
    secret_key = args.secret_key or os.getenv('BAIDU_SECRET_KEY')

    result = process_transcribe(
        video_path=video_path,
        audio_path=audio_path,
        use_baidu=args.use_baidu,
        use_server=args.use_server,
        use_siliconflow=args.use_siliconflow,
        use_alibaba=args.use_alibaba,
        server_url=args.server_url,
        server_ip=args.server_ip,
        server_port=args.server_port,
        server_timeout=args.server_timeout,
        api_key=api_key,
        secret_key=secret_key,
        model_size=args.model_size,
        language=args.language,
        work_dir=Path(args.work_dir),
    )

    print('\n处理结果摘要:')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
