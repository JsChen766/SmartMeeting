"""
转录结果的数据模型定义
包含说话人信息、时间戳和转录文本
符合 docs/modules 中的规范要求
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ProcessStatus(str, Enum):
    """处理状态枚举"""
    COMPLETED = "completed"
    FAILED = "failed"
    PROCESSING = "processing"


class ErrorInfo(BaseModel):
    """
    错误信息模型
    
    遵循 docs/modules/module_contracts.md 的错误返回格式规范
    """
    code: str = Field(..., description="稳定可枚举的错误码")
    message: str = Field(..., description="错误说明，用于开发协作与日志")
    details: Optional[Dict[str, Any]] = Field(None, description="可选的附加上下文")


class ASRSegment(BaseModel):
    """
    单个 ASR 转录片段的数据模型
    
    遵循 docs/modules/asr_io.md 的规范
    
    Attributes:
        segment_id: 文本片段唯一标识，例如 "seg_0001"
        start: 文本片段起始时间（单位：秒）
        end: 文本片段结束时间（单位：秒）
        text: 识别出的文本内容
        lang: 该文本片段的语言代码（"zh", "en", "yue" 等）
        confidence: 识别置信度（0-1 之间的浮点数，可选）
    """
    segment_id: str = Field(..., description="文本片段唯一标识")
    start: float = Field(..., description="开始时间（秒）")
    end: float = Field(..., description="结束时间（秒）")
    text: str = Field(..., description="转录文本")
    lang: str = Field(..., description="语言代码")
    confidence: Optional[float] = Field(default=0.9, description="识别置信度")

    class Config:
        json_schema_extra = {
            "example": {
                "segment_id": "seg_0001",
                "start": 0.0,
                "end": 4.82,
                "text": "大家好，我们开始本周例会。",
                "lang": "zh",
                "confidence": 0.97
            }
        }


class DiarizationSegment(BaseModel):
    """
    单个说话人片段的数据模型
    
    遵循 docs/modules/diarization_io.md 的规范
    
    Attributes:
        start: 说话区间起始时间（单位：秒）
        end: 说话区间结束时间（单位：秒）
        speaker: 说话人标识，采用 "S1"、"S2" 等统一命名
    """
    start: float = Field(..., description="开始时间（秒）")
    end: float = Field(..., description="结束时间（秒）")
    speaker: str = Field(..., description="说话人标识，如 S1, S2, S3")

    class Config:
        json_schema_extra = {
            "example": {
                "start": 0.0,
                "end": 6.2,
                "speaker": "S1"
            }
        }


class TranscriptionSegment(BaseModel):
    """
    融合后的转录片段（包含说话人和文本）
    
    这是 ASR 与 Diarization 融合后的结果
    
    Attributes:
        segment_id: 文本片段唯一标识，例如 "seg_0001"
        speaker: 说话人标签（S1, S2, S3 等）
        start: 片段开始时间（单位：秒）
        end: 片段结束时间（单位：秒）
        text: 转录文本内容
        lang: 语言代码
        confidence: 识别置信度
    """
    segment_id: str = Field(..., description="文本片段唯一标识")
    speaker: str = Field(..., description="说话人标签")
    start: float = Field(..., description="片段开始时间（秒）")
    end: float = Field(..., description="片段结束时间（秒）")
    text: str = Field(..., description="转录文本")
    lang: str = Field(default="zh", description="语言代码")
    confidence: Optional[float] = Field(default=0.9, description="识别置信度")

    class Config:
        json_schema_extra = {
            "example": {
                "segment_id": "seg_0001",
                "speaker": "S1",
                "start": 0.5,
                "end": 3.2,
                "text": "大家好，欢迎参加这次会议",
                "lang": "zh",
                "confidence": 0.95
            }
        }


class ASROutput(BaseModel):
    """
    ASR 模块规范输出
    
    遵循 docs/modules/asr_io.md 的输出说明
    """
    asr_segments: List[ASRSegment] = Field(default_factory=list, description="ASR 转录片段列表")


class DiarizationOutput(BaseModel):
    """
    Diarization 模块规范输出
    
    遵循 docs/modules/diarization_io.md 的输出说明
    """
    speaker_segments: List[DiarizationSegment] = Field(default_factory=list, description="说话人片段列表")


class ModuleResponse(BaseModel):
    """
    通用模块响应结构
    
    遵循 docs/modules/module_contracts.md 的统一规范
    """
    meeting_id: str = Field(..., description="会议处理链路唯一标识")
    status: ProcessStatus = Field(default=ProcessStatus.COMPLETED, description="处理状态")
    data: Optional[Dict[str, Any]] = Field(None, description="模块输出数据")
    error: Optional[ErrorInfo] = Field(None, description="错误信息，成功时为 null")

    class Config:
        json_schema_extra = {
            "example": {
                "meeting_id": "mtg_20260402_001",
                "status": "completed",
                "data": {
                    "asr_segments": [
                        {
                            "segment_id": "seg_0001",
                            "start": 0.0,
                            "end": 4.82,
                            "text": "大家好",
                            "lang": "zh",
                            "confidence": 0.97
                        }
                    ]
                },
                "error": None
            }
        }


class MeetingTranscription(BaseModel):
    """
    完整会议转录结果的数据模型（快速版本，保留向后兼容）
    
    Attributes:
        segments: 转录片段列表，包含所有说话人的发言
        total_duration: 音频总时长（单位：秒）
        language: 识别的语言代码（如 "zh"、"en"、"yue" 等）
    """
    segments: List[TranscriptionSegment] = Field(default_factory=list, description="转录片段列表")
    total_duration: float = Field(..., description="音频总时长（秒）")
    language: str = Field(default="zh", description="语言代码")

    class Config:
        json_schema_extra = {
            "example": {
                "segments": [
                    {
                        "speaker": "S1",
                        "start": 0.5,
                        "end": 3.2,
                        "text": "大家好，欢迎参加这次会议",
                        "lang": "zh",
                        "confidence": 0.95
                    },
                    {
                        "speaker": "S2",
                        "start": 3.5,
                        "end": 6.8,
                        "text": "感谢主持人，很高兴参加这次讨论",
                        "lang": "zh",
                        "confidence": 0.93
                    }
                ],
                "total_duration": 120.5,
                "language": "zh"
            }
        }
