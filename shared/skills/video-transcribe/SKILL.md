---
name: video-transcribe
display_name: 视频转录
display_name_en: Video Transcription
description: Transcribe local video or audio files to text, generating subtitle files (SRT) and plain text (txt). Supports multiple ASR modes including local Whisper, Baidu, SiliconFlow, Alibaba DashScope, and FastWhisper server.
description_zh: 将本地视频或音频文件转录为文字，生成字幕文件（SRT）和纯文本（txt）。支持多种 ASR 模式，包括本地 Whisper、百度、SiliconFlow、阿里百炼和 FastWhisper 服务端。
description_en: Transcribe local video or audio files to text, generating subtitle files (SRT) and plain text (txt). Supports multiple ASR modes including local Whisper, Baidu, SiliconFlow, Alibaba DashScope, and FastWhisper server.
category: productivity
version: 1.1.0
author: yuzhi-jiang
license: MIT
compatibility: 需要 Python 3.12、ffmpeg 可执行文件
required_environment_variables:
  - name: BAIDU_API_KEY
    prompt: "Baidu ASR API Key"
    help: "Only needed for Baidu ASR mode (--use-baidu)"
    required_for: "Baidu ASR mode"
  - name: BAIDU_SECRET_KEY
    prompt: "Baidu ASR Secret Key"
    help: "Only needed for Baidu ASR mode (--use-baidu)"
    required_for: "Baidu ASR mode"
metadata:
  author: "local-workspace"
  version: "1.1"
  openclaw:
    requires:
      env:
        - "FASTWHISPER_SERVER_URL"
        - "FASTWHISPER_SERVER_IP"
        - "FASTWHISPER_SERVER_PORT"
        - "BAIDU_API_KEY"
        - "BAIDU_SECRET_KEY"
    primaryEnv: "FASTWHISPER_SERVER_URL"
  hermes:
    tags: ["media", "video", "transcription"]
    config:
      - key: fastwhisper.server_url
        description: "FastWhisper server URL (priority over IP+PORT)"
        prompt: "Enter FastWhisper server URL"
      - key: fastwhisper.server_ip
        description: "FastWhisper server IP"
        prompt: "Enter FastWhisper server IP (default 127.0.0.1)"
      - key: fastwhisper.server_port
        description: "FastWhisper server port"
        prompt: "Enter FastWhisper server port (default 8000)"
---

# 视频转录 Skill

## 适用场景
- 用户提供本地视频文件，希望生成 `.srt` 字幕文件和 `.txt` 纯文本。
- 优先使用本地 Whisper 进行转录（隐私优先）。
- 支持整段音频直接转录。

## 执行原则
1. **Skill 必须自行管理虚拟环境和依赖**（使用 uv，无需用户手动安装）。
2. 只产出字幕，不执行任何任务分析或总结。
3. 如果识别失败，要输出清晰的错误原因与下一步建议。

## ⚠️ 重要前提条件

### 1. Python 版本要求
**必须使用 Python 3.12**，因为 pydub 库在 Python 3.13+ 上不兼容（缺少 audioop 模块）。

首次运行时需要指定 Python 版本：
```bash
cd <skill目录>
uv sync --python 3.12
```

### 2. 系统依赖
**必须安装 ffmpeg**，用于从视频中提取音频：
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: 下载 ffmpeg 并添加到 PATH

### 3. Whisper CLI（可选）
如果系统安装了 `whisper` 命令行工具，脚本会优先使用它。否则会使用 Python 库（faster-whisper 或 openai-whisper）。

## 标准流程

### 首次使用或依赖缺失时
```bash
cd <skill目录>
# 必须指定 Python 3.12
uv sync --python 3.12
```

### 正常运行流程
1. 校验输入参数：`--video-path` 或 `--audio-path`
2. 提取音频（如输入是视频，需要 ffmpeg）
3. 执行转录（Whisper 或百度 ASR）
4. 检查产物：`results/*.srt` 和 `results/*.txt`
5. 给用户返回：
   - 字幕文件路径
   - 字幕条目数量

## 命令模板

### Whisper 模式（默认）
```bash
cd <skill目录>
uv run python scripts/transcribe.py --video-path "<视频文件路径>" --language zh --model-size base
```

### SiliconFlow 模式（推荐：免费 SenseVoiceSmall）
```bash
cd <skill目录>
# 通过环境变量配置 SILICONFLOW_API_KEY（或 ~/.hermes/.env）
export SILICONFLOW_API_KEY=sk-xxx
uv run python scripts/transcribe.py --video-path "<视频文件路径>" --language zh --use-siliconflow
```
- 调用 `https://api.siliconflow.cn/v1/audio/transcriptions`，模型 `FunAudioLLM/SenseVoiceSmall`（免费，余额为 0 也可用）
- 单次上限：时长 ≤1 小时、文件 ≤50MB
- 适合中文内容；返回整段文本（segment 数为 1，SRT 为单条字幕）
- API key 优先级：`--api-key` > `SILICONFLOW_API_KEY`

### 阿里百炼模式（推荐：中文准确率最高）
```bash
cd <skill目录>
# 通过环境变量配置 DASHSCOPE_API_KEY（或 ~/.hermes/.env）
export DASHSCOPE_API_KEY=sk-xxx
uv run python scripts/transcribe.py --video-path "<视频文件路径>" --language zh --use-alibaba
```
- 调用阿里云百炼 `qwen3-asr-flash`（同步调用，本地文件直接传，无需 OSS）：SDK 会自动把本地文件上传到百炼临时空间，个人使用足够（上传频率限制 100 QPS）
- 中文专有名词准确率明显高于 SenseVoiceSmall（实测"陆沉/莲花冠/崔诚/五梦七星象"等全对）
- 免费额度：`qwen3-asr-flash` 走大模型 ASR 计费，超出后约 0.00022 元/秒；`paraformer-v2` 约 0.00008 元/秒（需异步调用）
- 生产/高并发建议使用自己的 OSS URL 传入
- API key 按模式自动匹配：`--use-alibaba` → `DASHSCOPE_API_KEY`，`--use-siliconflow` → `SILICONFLOW_API_KEY`，`--use-baidu` → `BAIDU_API_KEY`

### 百度 ASR 模式
```bash
cd <skill目录>
# 推荐：通过环境变量配置 BAIDU_API_KEY / BAIDU_SECRET_KEY，无需明文传参
uv run python scripts/transcribe.py --video-path "<视频文件路径>" --use-baidu

# 或通过命令行直接传入
uv run python scripts/transcribe.py --video-path "<视频文件路径>" --use-baidu --api-key "<BAIDU_API_KEY>" --secret-key "<BAIDU_SECRET_KEY>"
```

### 服务端模式（调用 fastwhisper.py）
```bash
cd <skill目录>
uv run python scripts/transcribe.py --video-path "<视频文件路径>" --use-server --server-ip 127.0.0.1 --server-port 8000
```

或通过环境变量指定服务地址：
```bash
# 二选一（FASTWHISPER_SERVER_URL 优先）
set FASTWHISPER_SERVER_URL=http://127.0.0.1:8000
set FASTWHISPER_SERVER_IP=127.0.0.1
set FASTWHISPER_SERVER_PORT=8000

uv run python scripts/transcribe.py --video-path "<视频文件路径>" --use-server
```

也可通过环境变量设置（推荐由 agent client 自动注入）：
```bash
# Linux/macOS
export FASTWHISPER_SERVER_URL=http://127.0.0.1:8000
export BAIDU_API_KEY=your_api_key
export BAIDU_SECRET_KEY=your_secret_key

# Windows PowerShell
$env:FASTWHISPER_SERVER_URL = "http://127.0.0.1:8000"
$env:BAIDU_API_KEY = "your_api_key"
$env:BAIDU_SECRET_KEY = "your_secret_key"
```

### 直接转录音频
```bash
cd <skill目录>
uv run python scripts/transcribe.py --audio-path "<音频文件路径>"
```

### 参数说明
| 参数 | 说明 | 默认值 |
|------|------|--------|
| --video-path | 视频文件路径 | 必填（与 audio-path 二选一） |
| --audio-path | 音频文件路径 | 必填（与 video-path 二选一） |
| --language | 识别语言 | zh |
| --model-size | Whisper 模型 | base |
| --use-baidu | 使用百度 ASR | false |
| --use-siliconflow | 使用 SiliconFlow ASR（SenseVoiceSmall，免费） | false |
| --use-alibaba | 使用阿里百炼 ASR（qwen3-asr-flash，需 DASHSCOPE_API_KEY） | false |
| --use-server | 使用 fastwhisper 服务端 API | false |
| --server-url | 服务端完整地址（最高优先级） | 读取环境变量或回退默认 |
| --server-ip | 服务端 IP/主机名 | 读取 `FASTWHISPER_SERVER_IP` 或 `127.0.0.1` |
| --server-port | 服务端端口 | 读取 `FASTWHISPER_SERVER_PORT` 或 `8000` |
| --server-timeout | 服务端请求超时（秒） | 600 |
| --initial-prompt | 服务端模式提示词 | 新闻播报默认提示词 |
| --api-key | 各模式 API Key（百度 → `BAIDU_API_KEY`，SiliconFlow → `SILICONFLOW_API_KEY`，阿里百炼 → `DASHSCOPE_API_KEY`） | 按模式读取对应环境变量 |
| --secret-key | 百度 Secret Key，也可由环境变量 `BAIDU_SECRET_KEY` 指定 | 读取 `BAIDU_SECRET_KEY` |

> 注意：`--use-baidu`、`--use-siliconflow`、`--use-alibaba`、`--use-server` 四者不能同时启用。

## Whisper 模型选择
| 模型 | 大小 | 推荐场景 |
|------|------|---------|
| tiny | ~75 MB | 快速测试 |
| base | ~140 MB | 推荐日常使用 |
| small | ~480 MB | 更高精度 |
| medium | ~1.5 GB | 最佳精度（需更多显存） |

## 依赖与环境
- **环境管理**：uv
- **依赖**：pyproject.toml
- **系统要求**：`ffmpeg` 可在命令行直接访问

## 输出约定
- 音频：`audio/*.wav`
- 字幕：`results/*.srt`
- 纯文本：`results/*.txt`

## 失败处理
| 错误类型 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 音频提取失败 | 未安装 ffmpeg | 安装 ffmpeg 并添加到 PATH |
| 识别失败 | 模型未下载/音频太短 | 检查网络后重试 |
| 百度 API 失败 | API 密钥无效 | 检查密钥是否正确 |

## uv 使用说明

### 安装 uv（如果未安装）
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 首次运行（必须指定 Python 3.12）
```bash
cd <skill目录>
uv sync --python 3.12
```

### 运行脚本
```bash
cd <skill目录>
uv run python scripts/transcribe.py --video-path "<视频文件路径>"
```

### 如果遇到错误
| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `ModuleNotFoundError: No module named 'audioop'` | Python 版本不兼容 | 使用 `uv sync --python 3.12` |
| `ffmpeg not found` | 未安装 ffmpeg | 安装 ffmpeg 并确保在 PATH 中 |
| `whisper: command not found` | 未安装 whisper CLI | 可忽略，脚本会使用 Python 库 |
