"""
会议转录的核心处理管道
整合 Pyannote（声纹分离）和 Whisper（语音识别）功能
流程：音频 -> 声纹分离 -> 音频切片 -> 语音识别 -> 结果组装
遵循 docs/modules 中的契约规范
"""

import logging
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
import traceback

# 音频处理相关导入
try:
    from pydub import AudioSegment
    from pydub.exceptions import CouldNotDecodeError
except ImportError:
    AudioSegment = None
    CouldNotDecodeError = None

# 项目内部导入
from backend.modules.diarization.pyannote_service import PyannoteService
from backend.modules.asr.whisper_service import WhisperService
from backend.schemas.transcription import (
    TranscriptionSegment, 
    MeetingTranscription,
    ModuleResponse,
    ProcessStatus,
    ErrorInfo,
    ASRSegment,
    DiarizationSegment
)

logger = logging.getLogger(__name__)


class AudioSlicer:
    """
    基于时间戳的音频切片工具
    根据 Pyannote 返回的时间戳，将音频切分为多个片段
    """
    
    @staticmethod
    def slice_audio(
        audio_path: str,
        start_time: float,
        end_time: float,
        output_path: str
    ) -> bool:
        """
        从音频文件中切出指定时间段
        
        Args:
            audio_path: 源音频文件路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            output_path: 输出音频文件路径
        
        Returns:
            bool: 切片成功返回 True，失败返回 False
        """
        try:
            if AudioSegment is None:
                raise ImportError(
                    "pydub 未安装。请运行: pip install pydub"
                )
            
            # 加载音频文件
            audio = AudioSegment.from_file(audio_path)
            
            # 获取指定时间段（将秒转换为毫秒）
            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)
            
            sliced = audio[start_ms:end_ms]
            
            # 确保输出目录存在
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 导出切片后的音频
            sliced.export(output_path, format="wav")
            
            logger.debug(f"音频切片成功: {start_time:.2f}s - {end_time:.2f}s -> {output_path}")
            return True
        
        except CouldNotDecodeError:
            logger.error(f"无法解码音频文件: {audio_path}")
            return False
        except Exception as e:
            logger.error(f"音频切片失败: {str(e)}\n{traceback.format_exc()}")
            return False
    
    @staticmethod
    def slice_audio_batch(
        audio_path: str,
        segments_info: List[tuple],
        output_dir: str,
        prefix: str = "segment"
    ) -> dict:
        """
        批量切片音频
        
        Args:
            audio_path: 源音频文件路径
            segments_info: 片段信息列表，每个元素是 (start_time, end_time, speaker_label)
            output_dir: 输出目录
            prefix: 输出文件名前缀
        
        Returns:
            字典，键为片段索引，值为输出文件路径
            如果某个片段切片失败，对应的路径为 None
        
        Example:
            >>> diar_results = [(0.5, 3.2, "SPEAKER_00"), (3.5, 6.8, "SPEAKER_01")]
            >>> slices = AudioSlicer.slice_audio_batch("audio.wav", diar_results, "output/")
            >>> for idx, path in slices.items():
            ...     if path:
            ...         print(f"Segment {idx}: {path}")
        """
        sliced_paths = {}
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        
        for idx, (start_time, end_time, speaker) in enumerate(segments_info):
            output_file = output_dir_path / f"{prefix}_{idx:04d}_{speaker}.wav"
            
            success = AudioSlicer.slice_audio(audio_path, start_time, end_time, str(output_file))
            sliced_paths[idx] = str(output_file) if success else None
        
        return sliced_paths


class MeetingTranscriberPipeline:
    """
    会议转录的核心管道
    
    工作流程：
    1. 接收本地音频路径和目标语言
    2. 使用 Pyannote 进行声纹分离，得到时间戳和说话人标签
    3. 根据时间戳使用 pydub 切分音频
    4. 将每个切片送入 Whisper 进行语音识别
    5. 将结果组装成 MeetingTranscription 对象返回
    
    特点：
    - 完全本地处理，无网络依赖
    - 支持多语言（中文、英文、粤语）
    - 模块化设计，易于扩展和维护
    """
    
    def __init__(
        self,
        diarization_model: str = "pyannote/speaker-diarization-3.1",
        whisper_model_size: str = "large-v3",
        device: str = "auto",
        whisper_compute_type: str = "float16",
        temp_dir: Optional[str] = None,
        keep_temp_files: bool = False
    ):
        """
        初始化会议转录管道
        
        Args:
            diarization_model: Pyannote 模型名称（默认使用最新的 3.1）
            whisper_model_size: Whisper 模型大小（推荐 "large-v3"）
            device: 运行设备（"cuda"/"cpu"/"auto"）
            whisper_compute_type: Whisper 计算精度（"float16"/"float32"）
            temp_dir: 临时文件保存目录，如果为 None 则使用系统临时目录
            keep_temp_files: 是否保留临时音频文件（用于调试）
        """
        self.diarization_model_name = diarization_model
        self.whisper_model_size = whisper_model_size
        self.device = device
        self.whisper_compute_type = whisper_compute_type
        self.temp_dir = temp_dir or "./temp_audio_slices"
        self.keep_temp_files = keep_temp_files
        
        # 初始化服务
        logger.info("初始化 Pyannote 服务...")
        self.pyannote_service = PyannoteService(
            model_name=diarization_model,
            device=device
        )
        
        logger.info("初始化 Whisper 服务...")
        self.whisper_service = WhisperService(
            model_size=whisper_model_size,
            device=device,
            compute_type=whisper_compute_type
        )
        
        logger.info("会议转录管道初始化完成")
    
    def _validate_audio_file(self, audio_path: str) -> bool:
        """
        验证音频文件是否存在且有效
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            文件有效返回 True，否则返回 False
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            logger.error(f"音频文件不存在: {audio_path}")
            return False
        
        if audio_file.stat().st_size == 0:
            logger.error(f"音频文件为空: {audio_path}")
            return False
        
        return True
    
    def _cleanup_temp_files(self, temp_dir: str):
        """
        清理临时文件
        
        Args:
            temp_dir: 临时文件目录
        """
        if not self.keep_temp_files:
            try:
                import shutil
                temp_path = Path(temp_dir)
                if temp_path.exists():
                    shutil.rmtree(temp_path)
                    logger.debug(f"临时文件已清理: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")
    
    def transcribe(
        self,
        audio_path: str,
        target_lang: str = "zh",
        save_temp_files: Optional[bool] = None,
        meeting_id: Optional[str] = None
    ) -> MeetingTranscription:
        """
        处理音频文件，返回完整的会议转录结果
        
        **这是管道的主入口方法**
        
        Args:
            audio_path: 本地音频文件的绝对路径
                       支持的格式：mp3, wav, ogg, flac, m4a 等
            target_lang: 目标语言
                        "zh" - 中文（普通话）
                        "en" - 英文
                        "yue" - 粤语
            save_temp_files: 是否保存临时音频文件（覆盖初始化参数）
            meeting_id: 会议 ID（可选，用于规范响应）
        
        Returns:
            MeetingTranscription 对象，包含：
            - segments: 转录片段列表
            - total_duration: 音频总时长
            - language: 识别的语言
        
        Raises:
            FileNotFoundError: 音频文件不存在
            RuntimeError: 处理过程中出现错误
        
        Process Flow:
            1. 验证输入音频文件
            2. 使用 Pyannote 进行声纹分离 (Diarization)
            3. 获取音频总时长
            4. 根据分离结果切片音频
            5. 使用 Whisper 对每个切片进行转录
            6. 组装最终结果
        
        Example:
            >>> pipeline = MeetingTranscriberPipeline()
            >>> 
            >>> # 处理普通话会议
            >>> result = pipeline.transcribe("meeting_chinese.wav", target_lang="zh")
            >>> for segment in result.segments:
            ...     print(f"{segment.speaker}: {segment.text}")
            >>> print(f"总时长: {result.total_duration}秒")
            >>> 
            >>> # 处理粤语会议
            >>> result = pipeline.transcribe("meeting_cantonese.wav", target_lang="yue")
            >>> 
            >>> # 保存并处理临时文件
            >>> result = pipeline.transcribe(
            ...     "meeting.wav",
            ...     target_lang="zh",
            ...     save_temp_files=True
            ... )
        """
        logger.info(f"=== 开始处理音频 ===")
        logger.info(f"音频文件: {audio_path}")
        logger.info(f"目标语言: {target_lang}")
        
        # 验证音频文件
        if not self._validate_audio_file(audio_path):
            raise FileNotFoundError(f"无效的音频文件: {audio_path}")
        
        audio_path = str(Path(audio_path).absolute())
        
        try:
            # 1. 使用 Pyannote 进行声纹分离
            logger.info("\n[第 1 步] 声纹分离 (Diarization)...")
            diarization_results = self.pyannote_service.diarize(audio_path)
            
            if not diarization_results:
                logger.warning("未检测到任何说话人分离结果")
                diarization_results = []
            else:
                logger.info(f"检测到 {len(diarization_results)} 个分离片段")
            
            # 2. 获取音频总时长
            logger.info("\n[第 2 步] 获取音频信息...")
            total_duration = self._get_audio_duration(audio_path)
            logger.info(f"音频总时长: {total_duration:.2f} 秒")
            
            # 3. 切分音频
            logger.info("\n[第 3 步] 切分音频...")
            sliced_paths = AudioSlicer.slice_audio_batch(
                audio_path,
                diarization_results,
                self.temp_dir,
                prefix="segment"
            )
            
            successful_slices = sum(1 for path in sliced_paths.values() if path)
            logger.info(f"成功切分 {successful_slices}/{len(diarization_results)} 个片段")
            
            # 4. 进行语音识别
            logger.info(f"\n[第 4 步] 语音识别 (目标语言: {target_lang})...")
            transcription_segments = []
            
            for idx, (start_time, end_time, speaker) in enumerate(diarization_results):
                slice_path = sliced_paths.get(idx)
                
                if not slice_path or not Path(slice_path).exists():
                    logger.warning(f"片段 {idx} 的音频文件不存在，跳过")
                    continue
                
                try:
                    # 转录该片段
                    text = self.whisper_service.transcribe(
                        slice_path,
                        target_lang=target_lang
                    )
                    
                    if text.strip():  # 只保存非空文本
                        segment = TranscriptionSegment(
                            speaker=speaker,  # 现在已经是 S1, S2 等规范格式
                            start=start_time,
                            end=end_time,
                            text=text.strip(),
                            lang=target_lang,
                            confidence=0.9  # 默认置信度
                        )
                        transcription_segments.append(segment)
                        logger.debug(
                            f"片段 {idx} ({speaker}): [{start_time:.2f}s - {end_time:.2f}s] "
                            f"文本长度: {len(text)}"
                        )
                    else:
                        logger.debug(f"片段 {idx} ({speaker}) 转录结果为空")
                
                except Exception as e:
                    logger.error(f"处理片段 {idx} 失败: {str(e)}")
                    continue
            
            logger.info(f"成功转录 {len(transcription_segments)} 个片段")
            
            # 5. 组装最终结果
            logger.info("\n[第 5 步] 组装最终结果...")
            result = MeetingTranscription(
                segments=transcription_segments,
                total_duration=total_duration,
                language=target_lang
            )
            
            logger.info("=== 处理完成 ===")
            logger.info(f"最终结果: {len(result.segments)} 个转录片段")
            
            return result
        
        except Exception as e:
            logger.error(f"处理音频时发生错误: {str(e)}\n{traceback.format_exc()}")
            raise RuntimeError(f"会议转录处理失败: {str(e)}")
        
        finally:
            # 清理临时文件
            keep_temp = save_temp_files if save_temp_files is not None else self.keep_temp_files
            if not keep_temp:
                self._cleanup_temp_files(self.temp_dir)
    
    def process_asr_only(
        self,
        audio_path: str,
        target_lang: str = "zh",
        meeting_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        仅进行 ASR 处理（不进行说话人分离）
        
        返回符合 docs/modules/asr_io.md 规范的响应结构
        
        Args:
            audio_path: 本地音频文件路径
            target_lang: 目标语言
            meeting_id: 会议 ID
        
        Returns:
            符合规范的 ModuleResponse 字典
        """
        try:
            asr_segments = self.whisper_service.transcribe_with_asr_segments(
                audio_path,
                target_lang=target_lang
            )
            
            response = ModuleResponse(
                meeting_id=meeting_id or "unknown",
                status=ProcessStatus.COMPLETED,
                data={"asr_segments": asr_segments},
                error=None
            )
            
            return response.model_dump()
        
        except Exception as e:
            logger.error(f"ASR 处理失败: {str(e)}")
            error_info = ErrorInfo(
                code="ASR_PROCESS_FAILED",
                message=str(e),
                details={"audio_path": audio_path}
            )
            response = ModuleResponse(
                meeting_id=meeting_id or "unknown",
                status=ProcessStatus.FAILED,
                data=None,
                error=error_info
            )
            return response.model_dump()
    
    def process_diarization_only(
        self,
        audio_path: str,
        meeting_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        仅进行 Diarization 处理（不进行语音识别）
        
        返回符合 docs/modules/diarization_io.md 规范的响应结构
        
        Args:
            audio_path: 本地音频文件路径
            meeting_id: 会议 ID
        
        Returns:
            符合规范的 ModuleResponse 字典
        """
        try:
            speaker_segments = self.pyannote_service.diarize_with_segments(audio_path)
            
            response = ModuleResponse(
                meeting_id=meeting_id or "unknown",
                status=ProcessStatus.COMPLETED,
                data={"speaker_segments": speaker_segments},
                error=None
            )
            
            return response.model_dump()
        
        except Exception as e:
            logger.error(f"Diarization 处理失败: {str(e)}")
            error_info = ErrorInfo(
                code="DIARIZATION_PROCESS_FAILED",
                message=str(e),
                details={"audio_path": audio_path}
            )
            response = ModuleResponse(
                meeting_id=meeting_id or "unknown",
                status=ProcessStatus.FAILED,
                data=None,
                error=error_info
            )
            return response.model_dump()
    
    def process_combined_with_standards(
        self,
        audio_path: str,
        target_lang: str = "zh",
        meeting_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        进行完整的 ASR + Diarization 处理
        
        返回符合规范的响应结构（包含规范化的 speaker 标签）
        
        Args:
            audio_path: 本地音频文件路径
            target_lang: 目标语言
            meeting_id: 会议 ID
        
        Returns:
            符合规范的 ModuleResponse 字典
        """
        try:
            result = self.transcribe(audio_path, target_lang)
            
            # 转换为字典格式（规范的 TranscriptionSegment 列表）
            segments_data = [seg.model_dump() for seg in result.segments]
            
            response = ModuleResponse(
                meeting_id=meeting_id or "unknown",
                status=ProcessStatus.COMPLETED,
                data={
                    "segments": segments_data,
                    "total_duration": result.total_duration,
                    "language": result.language
                },
                error=None
            )
            
            return response.model_dump()
        
        except Exception as e:
            logger.error(f"组合处理失败: {str(e)}")
            error_info = ErrorInfo(
                code="COMBINED_PROCESS_FAILED",
                message=str(e),
                details={"audio_path": audio_path, "target_lang": target_lang}
            )
            response = ModuleResponse(
                meeting_id=meeting_id or "unknown",
                status=ProcessStatus.FAILED,
                data=None,
                error=error_info
            )
            return response.model_dump()
    
        """
        获取音频文件的总时长
        
        Args:
            audio_path: 音频文件路径
        
        Returns:
            音频时长（秒）
        """
        try:
            if AudioSegment is None:
                logger.warning("pydub 未安装，无法获取精确的音频时长")
                return 0.0
            
            audio = AudioSegment.from_file(audio_path)
            duration = len(audio) / 1000.0  # 从毫秒转换为秒
            return duration
        
        except Exception as e:
            logger.warning(f"获取音频时长失败: {str(e)}")
            return 0.0
    
    def transcribe_to_dict(
        self,
        audio_path: str,
        target_lang: str = "zh"
    ) -> dict:
        """
        处理音频并将结果转换为字典格式
        
        便于序列化为 JSON 或其他格式
        
        Args:
            audio_path: 本地音频文件路径
            target_lang: 目标语言
        
        Returns:
            包含转录结果的字典
        
        Example:
            >>> pipeline = MeetingTranscriberPipeline()
            >>> result_dict = pipeline.transcribe_to_dict("meeting.wav", "zh")
            >>> import json
            >>> print(json.dumps(result_dict, ensure_ascii=False, indent=2))
        """
        result = self.transcribe(audio_path, target_lang)
        return result.model_dump()
    
    def transcribe_to_json(
        self,
        audio_path: str,
        target_lang: str = "zh",
        output_path: Optional[str] = None
    ) -> str:
        """
        处理音频并将结果保存为 JSON 文件
        
        Args:
            audio_path: 本地音频文件路径
            target_lang: 目标语言
            output_path: 输出 JSON 文件路径
                        如果为 None，则返回 JSON 字符串而不保存
        
        Returns:
            JSON 格式的字符串
        
        Example:
            >>> pipeline = MeetingTranscriberPipeline()
            >>> pipeline.transcribe_to_json(
            ...     "meeting.wav",
            ...     target_lang="zh",
            ...     output_path="result.json"
            ... )
        """
        import json
        
        result = self.transcribe(audio_path, target_lang)
        json_str = json.dumps(
            result.model_dump(),
            ensure_ascii=False,
            indent=2
        )
        
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_str)
            logger.info(f"结果已保存到: {output_path}")
        
        return json_str

    def transcribe_by_sentences(
        self,
        audio_path: str,
        target_lang: str = "zh"
    ) -> List[Dict]:
        """
        对音频进行转录并按句子分割返回结果
        
        返回符合 docs/modules/asr_io.md 规范的句子级别 ASRSegment
        
        Args:
            audio_path: 音频文件路径
            target_lang: 目标语言代码
        
        Returns:
            ASRSegment 字典列表，每个包含：
                - segment_id: 句子唯一标识
                - start: 开始时间
                - end: 结束时间
                - text: 句子文本
                - lang: 语言代码
                - confidence: 置信度
        
        Example:
            >>> pipeline = MeetingTranscriberPipeline()
            >>> sentences = pipeline.transcribe_by_sentences("meeting.wav")
            >>> for sentence in sentences:
            ...     print(f"{sentence['segment_id']}: {sentence['text']}")
        """
        logger.info(f"开始按句子转录音频: {audio_path}")
        
        try:
            sentence_segments = self.whisper_service.transcribe_by_sentences(
                audio_path, target_lang
            )
            
            logger.info(f"按句子转录完成，共 {len(sentence_segments)} 个句子")
            return sentence_segments
            
        except Exception as e:
            logger.error(f"按句子转录失败: {e}")
            raise

    def process_combined_with_standards_new(
        self,
        audio_path: str,
        target_lang: str = "zh"
    ) -> Dict[str, Any]:
        """
        完整的标准格式处理流程：ASR + Diarization + Alignment

        返回符合 docs 规范的 ModuleResponse 格式

        Args:
            audio_path: 音频文件路径
            target_lang: 目标语言

        Returns:
            ModuleResponse dict
        """
        import uuid
        from datetime import datetime

        meeting_id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

        try:
            logger.info(f"=== 开始标准格式处理 ===")
            logger.info(f"会议 ID: {meeting_id}")
            logger.info(f"音频文件: {audio_path}")
            logger.info(f"目标语言: {target_lang}")

            # 验证音频文件
            if not self._validate_audio_file(audio_path):
                raise FileNotFoundError(f"音频文件不存在或无效: {audio_path}")

            # 步骤 1: ASR 处理
            logger.info("步骤 1: 执行 ASR 转录...")
            asr_segments = self.whisper_service.transcribe_with_asr_segments(audio_path, target_lang)

            # 步骤 2: Diarization 处理
            logger.info("步骤 2: 执行说话人分离...")
            diarization_segments = self.pyannote_service.diarize_with_segments(audio_path)

            # 步骤 3: Alignment - 融合 ASR 和 Diarization 结果
            logger.info("步骤 3: 执行时间戳对齐...")
            aligned_segments = self._align_segments(asr_segments, diarization_segments)

            # 计算总时长
            total_duration = max(
                (seg['end'] for seg in asr_segments),
                default=0.0
            )

            # 构建标准响应
            full_text_with_speaker = self._build_full_text_with_speaker(aligned_segments)
            response_data = {
                "total_duration": round(total_duration, 2),
                "language": target_lang,
                "segments": aligned_segments,
                "full_text": full_text_with_speaker
            }

            response = ModuleResponse(
                meeting_id=meeting_id,
                status=ProcessStatus.COMPLETED,
                data=response_data,
                error=None
            )

            logger.info("✓ 标准格式处理完成")
            logger.info(f"  • 总时长: {response_data['total_duration']:.2f}秒")
            logger.info(f"  • 语言: {response_data['language']}")
            logger.info(f"  • 片段数: {len(response_data['segments'])}")
            
            # 输出详细的分段信息（含 speaker）
            self._log_segments_with_speaker(response_data['segments'])

            return response.model_dump()

        except Exception as e:
            logger.error(f"标准格式处理失败: {e}")
            error_info = ErrorInfo(
                code="PROCESSING_FAILED",
                message=f"处理失败: {str(e)}",
                details={"traceback": traceback.format_exc()}
            )

            return ModuleResponse(
                meeting_id=meeting_id,
                status=ProcessStatus.FAILED,
                data=None,
                error=error_info.model_dump()
            ).model_dump()

    def _align_segments(
        self,
        asr_segments: List[Dict[str, Any]],
        diarization_segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将 ASR 片段和 Diarization 片段进行时间戳对齐

        Args:
            asr_segments: ASR 结果片段
            diarization_segments: Diarization 结果片段

        Returns:
            对齐后的 TranscriptionSegment 列表
        """
        aligned_segments = []

        # 简单的对齐策略：为每个 ASR 片段找到最匹配的说话人
        for asr_seg in asr_segments:
            asr_start = asr_seg['start']
            asr_end = asr_seg['end']
            asr_center = (asr_start + asr_end) / 2

            # 找到包含 ASR 中心点的 Diarization 片段
            matched_speaker = "S1"  # 默认值
            max_overlap = 0

            for dia_seg in diarization_segments:
                dia_start = dia_seg['start']
                dia_end = dia_seg['end']

                # 计算重叠时间
                overlap_start = max(asr_start, dia_start)
                overlap_end = min(asr_end, dia_end)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > max_overlap:
                    max_overlap = overlap
                    matched_speaker = dia_seg['speaker']

            # 创建对齐后的片段
            aligned_segment = TranscriptionSegment(
                speaker=matched_speaker,
                start=round(asr_start, 2),
                end=round(asr_end, 2),
                text=asr_seg['text'].strip(),
                lang=asr_seg['lang'],
                confidence=asr_seg['confidence']
            )

            aligned_segments.append(aligned_segment.model_dump())

        logger.info(f"Alignment 完成: {len(aligned_segments)} 个对齐片段")
        return aligned_segments

    def _build_full_text_with_speaker(self, segments: List[Dict[str, Any]]) -> str:
        """
        构建包含说话人信息的完整文本
        
        Args:
            segments: 对齐后的转录片段列表
        
        Returns:
            格式化的文本字符串，每个片段前面有说话人标签
            格式: 【S1】文本1 【S2】文本2 【S1】文本3...
        """
        if not segments:
            return ""
        
        formatted_texts = []
        for seg in segments:
            speaker = seg.get('speaker', 'UNKNOWN')
            text = seg.get('text', '').strip()
            if text:
                formatted_texts.append(f"【{speaker}】{text}")
        
        return " ".join(formatted_texts)

    def _log_segments_with_speaker(self, segments: List[Dict[str, Any]]) -> None:
        """
        输出详细的分段信息到日志（包含说话人标签）
        
        Args:
            segments: 对齐后的转录片段列表
        """
        logger.info("\n【转录结果详情】")
        logger.info("-" * 80)
        
        # 按说话人分组统计
        speakers = {}
        for seg in segments:
            speaker = seg.get('speaker', 'UNKNOWN')
            if speaker not in speakers:
                speakers[speaker] = 0
            speakers[speaker] += 1
        
        logger.info(f"说话人统计: {speakers}")
        logger.info("-" * 80)
        
        # 输出逐段信息
        for i, seg in enumerate(segments, 1):
            speaker = seg.get('speaker', 'UNKNOWN')
            start = seg.get('start', 0)
            end = seg.get('end', 0)
            text = seg.get('text', '')
            segment_id = seg.get('segment_id', f'seg_{i:04d}')
            
            duration = end - start
            logger.info(
                f"[{i:3d}] {speaker} | {start:7.2f}s - {end:7.2f}s ({duration:5.2f}s) | {segment_id}"
            )
            logger.info(f"      {text}")
        
        logger.info("-" * 80 + "\n")
