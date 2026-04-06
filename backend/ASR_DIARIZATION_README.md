# 语音转文字与说话人识别模块

本模块提供会议音频的自动转录与多人识别能力，核心功能完全基于本地处理，无需网络 API 调用。

## 核心功能

- **语音识别 (ASR)** - 基于 OpenAI Whisper，支持中文、英文、粤语等多语言
- **说话人分离 (Diarization)** - 基于 Pyannote，自动识别谁在说话
- **音频切片** - 基于说话人时间戳精确切分音频
- **结果组装** - 生成结构化的转录结果，包含说话人标签、时间戳、文本内容

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `openai-whisper` - 语音识别
- `pyannote.audio` - 说话人分离
- `pydub` - 音频处理
- `pydantic` - 数据验证

### 2. 基本使用

```python
from backend.pipelines.meeting_pipeline import MeetingTranscriberPipeline

# 初始化处理管道
pipeline = MeetingTranscriberPipeline()

# 处理音频文件（支持 wav, mp3, m4a, ogg, flac 等格式）
result = pipeline.process_combined_with_standards_new(
    audio_file="meeting.m4a",
    target_lang="zh"  # 目标语言: zh/en/yue
)

# result 是字典格式，包含以下信息：
# {
#   "meeting_id": "uuid",
#   "status": "success",
#   "error": None,
#   "data": {
#     "segments": [
#       {
#         "segment_id": "seg_0001",
#         "speaker": "S1",
#         "start": 0.5,
#         "end": 5.2,
#         "text": "转录的文本内容",
#         "lang": "zh",
#         "confidence": 0.95
#       },
#       ...
#     ],
#     "total_duration": 123.45,
#     "language": "zh",
#     "full_text": "完整的转录文本"
#   }
# }
```

## 核心 API

### MeetingTranscriberPipeline

主处理管道类，支持多种处理模式。

#### __init__

```python
pipeline = MeetingTranscriberPipeline(
    asr_model="base",  # Whisper 模型: tiny/base/small/medium/large
    language="auto",   # 语言检测: auto/zh/en/yue
    use_gpu=False      # 是否使用 GPU
)
```

#### process_combined_with_standards_new(audio_file, target_lang="zh")

**推荐使用** - 完整的标准格式处理（说话人分离 + 语音识别 + 结果组装）

**参数：**
- `audio_file` (str) - 音频文件路径
- `target_lang` (str) - 目标语言代码 (zh/en/yue)

**返回：** 标准格式的 `ModuleResponse` 字典

#### process_asr_only(audio_file)

仅进行语音识别，不做说话人分离

**参数：**
- `audio_file` (str) - 音频文件路径

**返回：** ASR 结果字典

#### process_diarization_only(audio_file)

仅进行说话人分离，不做语音识别

**参数：**
- `audio_file` (str) - 音频文件路径

**返回：** Diarization 结果字典

## 数据模型

所有结果遵循统一的数据结构（定义在 `backend/schemas/transcription.py`）：

### ModuleResponse - 标准响应格式

```python
{
    "meeting_id": "string",           # 会议 ID（UUID）
    "status": "success|error",        # 处理状态
    "error": None | ErrorInfo,        # 错误信息（仅在失败时）
    "data": {                         # 数据部分（仅在成功时）
        "segments": [TranscriptionSegment],
        "total_duration": float,
        "language": string,
        "full_text": string
    }
}
```

### TranscriptionSegment - 转录片段

```python
{
    "segment_id": "seg_0001",         # 片段 ID
    "speaker": "S1",                  # 说话人标签 (S1/S2/S3...)
    "start": 0.5,                     # 开始时间（秒）
    "end": 5.2,                       # 结束时间（秒）
    "text": "转录文本",               # 识别的文本
    "lang": "zh",                     # 语言代码
    "confidence": 0.95                # 识别置信度（0-1）
}
```

## 关键类和工具

### PyannoteService (backend/modules/diarization/)

说话人分离服务

```python
from backend.modules.diarization.pyannote_service import PyannoteService

service = PyannoteService()
diarization_result = service.diarize(audio_file)
```

### WhisperService (backend/modules/asr/)

语音识别服务

```python
from backend.modules.asr.whisper_service import WhisperService

service = WhisperService(model_name="base")
asr_result = service.transcribe(audio_file)
```

### AudioSlicer (backend/pipelines/)

音频切片工具

```python
from backend.pipelines.meeting_pipeline import AudioSlicer

# 切出单个片段
AudioSlicer.slice_audio(
    audio_path="meeting.m4a",
    start_time=0.5,
    end_time=5.2,
    output_path="segment.wav"
)

# 批量切片
segments = [(0.5, 5.2), (5.3, 10.1)]
AudioSlicer.slice_audio_batch(
    audio_path="meeting.m4a",
    segments_info=segments,
    output_dir="slices/"
)
```

## 支持的音频格式

- WAV (.wav)
- MP3 (.mp3)
- M4A (.m4a)
- OGG (.ogg)
- FLAC (.flac)

## 环境要求

- Python 3.8+
- PyTorch（用于 Pyannote 和 Whisper）
- FFmpeg（用于 pydub 处理音频）

### Mac 安装 FFmpeg

```bash
brew install ffmpeg
```

### Linux 安装 FFmpeg

```bash
sudo apt-get install ffmpeg
```

## 配置系统代理（可选）

如果需要通过代理下载模型：

```python
import os
os.environ['http_proxy'] = 'http://127.0.0.1:7897'
os.environ['https_proxy'] = 'http://127.0.0.1:7897'
```

## 项目结构

```
backend/
├── modules/
│   ├── asr/
│   │   ├── __init__.py
│   │   └── whisper_service.py          # 语音识别服务
│   └── diarization/
│       ├── __init__.py
│       └── pyannote_service.py         # 说话人分离服务
├── pipelines/
│   ├── __init__.py
│   └── meeting_pipeline.py             # 核心处理管道
├── schemas/
│   ├── __init__.py
│   └── transcription.py                # 数据模型定义
└── utils/
```

## 详细文档

- **交互/集成设计** - 见 `docs/modules/module_contracts.md`
- **ASR 输入输出规范** - 见 `docs/modules/asr_io.md`
- **Diarization 输入输出规范** - 见 `docs/modules/diarization_io.md`
- **Alignment 规范** - 见 `docs/modules/alignment_io.md`
- **管道处理流程** - 见 `docs/architecture/pipeline_design.md`

## 错误处理

所有操作返回统一的 `ModuleResponse` 格式：

```python
result = pipeline.process_combined_with_standards_new("meeting.m4a")

if result['status'] == 'success':
    segments = result['data']['segments']
    # 处理转录结果
else:
    error = result['error']
    print(f"错误代码: {error['code']}")
    print(f"错误信息: {error['message']}")
    print(f"详情: {error['details']}")
```

## 许可证

项目许可证见根目录 LICENSE 文件
