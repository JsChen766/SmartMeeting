"""
Pyannote Diarization 服务 - 支持真实和模拟模式

如果 Pyannote.audio 安装失败，自动回退到模拟 Diarization
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import random

# 延迟导入，避免在未安装时报错
try:
    from pyannote.audio import Pipeline
    import torch
    PYANNOTE_AVAILABLE = True
except ImportError:
    Pipeline = None
    torch = None
    PYANNOTE_AVAILABLE = False

logger = logging.getLogger(__name__)


class PyannoteService:
    """
    基于 Pyannote.audio 的声纹分离服务

    支持两种模式：
    1. 真实模式：使用 Pyannote.audio 进行准确的说话人分离
    2. 模拟模式：当 Pyannote 不可用时，使用简单的规则模拟分离

    自动检测可用性并选择合适的模式
    """

    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization-3.1",
        device: str = "cuda" if torch and torch.cuda.is_available() else "cpu",
        use_auth_token: Optional[str] = None
    ):
        """
        初始化 Pyannote 服务

        Args:
            model_name: 模型在 HuggingFace Hub 上的名称
            device: 运行设备，"cuda" 或 "cpu"
            use_auth_token: HuggingFace API token
        """
        self.model_name = model_name
        self.device = device
        self.use_auth_token = use_auth_token
        self._pipeline = None
        self._use_mock = not PYANNOTE_AVAILABLE

        # 从环境变量获取 token
        if not self.use_auth_token:
            import os
            self.use_auth_token = os.getenv('HF_TOKEN')

    def _ensure_pipeline_loaded(self):
        """
        确保 Diarization 管道已加载
        """
        if self._pipeline is not None:
            return

        if not PYANNOTE_AVAILABLE:
            logger.warning("Pyannote.audio 未安装，使用模拟 Diarization")
            self._use_mock = True
            return

        try:
            logger.info("正在加载 Pyannote Diarization 模型...")

            if self.use_auth_token:
                self._pipeline = Pipeline.from_pretrained(
                    self.model_name,
                    use_auth_token=self.use_auth_token
                )
            else:
                self._pipeline = Pipeline.from_pretrained(self.model_name)

            # 移动到指定设备
            if hasattr(self._pipeline, 'to'):
                self._pipeline.to(self.device)

            self._use_mock = False
            logger.info("✓ Pyannote Diarization 模型加载成功")

        except Exception as e:
            logger.warning(f"Pyannote 模型加载失败: {e}，使用模拟模式")
            self._use_mock = True

    def diarize(self, audio_path: str) -> List[Tuple[float, float, str]]:
        """
        执行说话人分离

        Args:
            audio_path: 音频文件路径

        Returns:
            List of (start, end, speaker) tuples
        """
        self._ensure_pipeline_loaded()

        if not self._use_mock and self._pipeline:
            return self._diarize_real(audio_path)
        else:
            return self._diarize_mock(audio_path)

    def _diarize_real(self, audio_path: str) -> List[Tuple[float, float, str]]:
        """使用真实的 Pyannote 进行 Diarization"""
        try:
            logger.info(f"使用 Pyannote 处理音频: {audio_path}")

            # 运行 Diarization
            diarization = self._pipeline(audio_path)

            # 转换结果格式
            results = []
            speaker_map = {}  # SPEAKER_00 -> S1, SPEAKER_01 -> S2, etc.
            speaker_counter = 1

            for turn, _, speaker in diarization.itertracks(yield_label=True):
                # 标准化说话人标签
                if speaker not in speaker_map:
                    speaker_map[speaker] = f"S{speaker_counter}"
                    speaker_counter += 1

                standardized_speaker = speaker_map[speaker]
                results.append((turn.start, turn.end, standardized_speaker))

            logger.info(f"Diarization 完成: 检测到 {len(speaker_map)} 个说话人")
            return results

        except Exception as e:
            logger.error(f"Pyannote Diarization 失败: {e}")
            # 回退到模拟模式
            return self._diarize_mock(audio_path)

    def _diarize_mock(self, audio_path: str) -> List[Tuple[float, float, str]]:
        """
        模拟 Diarization - 基于简单规则分配说话人

        规则:
        - 将音频分成 2-4 秒的片段
        - 随机但一致的说话人分配（S1, S2）
        - 模拟真实的说话人切换模式
        """
        try:
            # 尝试获取音频时长
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(audio_path)
                total_duration = len(audio) / 1000.0
            except ImportError:
                # 如果没有 pydub，假设 30 秒
                total_duration = 30.0
                logger.warning("pydub 未安装，使用默认时长 30 秒")

            logger.info(f"使用模拟 Diarization，总时长: {total_duration:.2f}秒")

            # 模拟说话人分离
            segments = []
            current_time = 0.0
            speakers = ["S1", "S2"]
            current_speaker = "S1"

            # 随机片段长度 (2-4 秒)
            while current_time < total_duration:
                segment_duration = random.uniform(2.0, 4.0)
                end_time = min(current_time + segment_duration, total_duration)

                # 说话人切换逻辑（模拟真实的对话模式）
                # 70% 保持当前说话人，30% 切换
                if random.random() < 0.3:
                    current_speaker = "S2" if current_speaker == "S1" else "S1"

                segments.append((current_time, end_time, current_speaker))
                current_time = end_time

            logger.info(f"模拟 Diarization 完成: 生成 {len(segments)} 个片段，{len(set(s[2] for s in segments))} 个说话人")
            return segments

        except Exception as e:
            logger.error(f"模拟 Diarization 失败: {e}")
            # 返回最简单的结果
            return [(0.0, 30.0, "S1")]

    def diarize_with_segments(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        执行说话人分离，返回 DiarizationSegment 格式

        Args:
            audio_path: 音频文件路径

        Returns:
            List of DiarizationSegment dicts
        """
        results = self.diarize(audio_path)

        segments = []
        for start, end, speaker in results:
            segments.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "speaker": speaker
            })

        return segments
    
    def diarize_with_segments(self, audio_path: str) -> List[Dict]:
        """
        对音频进行分离，返回规范格式的 DiarizationSegment 字典列表
        
        符合 docs/modules/diarization_io.md 的输出格式
        
        Args:
            audio_path: 本地音频文件的绝对路径
        
        Returns:
            DiarizationSegment 字典列表，每个包含：
                - start: 开始时间
                - end: 结束时间
                - speaker: 规范化的说话人标签
        """
        from backend.schemas.transcription import DiarizationSegment
        
        raw_results = self.diarize(audio_path)
        
        segments = [
            DiarizationSegment(
                start=start,
                end=end,
                speaker=speaker
            ).model_dump()
            for start, end, speaker in raw_results
        ]
        
        return segments
    
    def get_speakers_count(self, audio_path: str) -> int:
        """
        获取音频中识别到的说话人数量
        
        Args:
            audio_path: 本地音频文件的绝对路径
        
        Returns:
            识别到的不同说话人数量
        """
        results = self.diarize(audio_path)
        speakers = set(speaker for _, _, speaker in results)
        return len(speakers)
