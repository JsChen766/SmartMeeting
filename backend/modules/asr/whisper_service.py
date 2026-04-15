"""
使用 faster-whisper 进行语音识别的服务模块
支持多语言（中文、英文、粤语等），提供针对不同语言的优化提示词
遵循 docs/modules/asr_io.md 规范
"""

import logging
from typing import Optional, Tuple, List, Dict
from pathlib import Path

# 延迟导入，避免在未安装 faster-whisper 时报错
try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

logger = logging.getLogger(__name__)


class WhisperService:
    """
    基于 faster-whisper 的语音识别服务
    
    功能：
    - 使用 large-v3 模型进行高精度语音转录
    - 支持中文、英文、粤语等多种语言
    - 为不同语言提供优化的提示词（initial_prompt）
    - 处理音频切片进行转录
    
    优势：
    - 比原生 OpenAI Whisper 快 5-10 倍
    - 支持 GPU 加速（CUDA）
    - 支持更细粒度的时间戳和词级别信息
    """
    
    # 支持的语言及其配置
    SUPPORTED_LANGUAGES = {
        "zh": {
            "name": "中文（普通话）",
            "code": "zh",
            "initial_prompt": "以下是一段中文对话内容，请用简体中文进行转录："
        },
        "en": {
            "name": "English",
            "code": "en",
            "initial_prompt": "The following is a conversation in English. Please transcribe it in English:"
        },
        "yue": {
            "name": "中文（粤语）",
            "code": "yue",
            "initial_prompt": "以下是一段粤语对话，请用繁体中文输出："
        }
    }
    
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "auto",
        compute_type: str = "float16"
    ):
        """
        初始化 Whisper 服务
        
        Args:
            model_size: Whisper 模型大小
                       "tiny", "base", "small", "medium", "large-v3" 等
                       推荐使用 "large-v3" 获得最好的准确度
            device: 运行设备
                   "cuda" 使用 GPU（如果可用）
                   "cpu" 使用 CPU
                   "auto" 自动选择（如果可用则 GPU，否则 CPU）
            compute_type: 计算精度
                         "float16" 更快但精度略低（推荐）
                         "float32" 更精确但更慢
                         "int8" 内存效率最高但精度最低
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        
        # 确定实际使用的设备和计算类型
        if device == "auto":
            try:
                import torch
                self.actual_device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.actual_device = "cpu"
        else:
            self.actual_device = device
            
        # CPU 不支持 float16，使用 float32
        if self.actual_device == "cpu" and self.compute_type == "float16":
            self.compute_type = "float32"
            logger.info("CPU 设备检测到，使用 float32 计算类型")
        
        self._model_initialized = False
    
    def _ensure_model_loaded(self):
        """
        确保模型已加载
        只在第一次使用时才加载模型，避免重复加载
        """
        if self._model_initialized:
            return
        
        if WhisperModel is None:
            raise ImportError(
                "faster-whisper 未安装。请运行: pip install faster-whisper"
            )
        
        logger.info(f"加载 Whisper 模型: {self.model_size} (设备: {self.actual_device})")
        try:
            self.model = WhisperModel(
                self.model_size,
                device=self.actual_device,
                compute_type=self.compute_type,
                download_root=None  # 使用默认缓存目录
            )
            self._model_initialized = True
            logger.info("Whisper 模型加载成功")
        except Exception as e:
            logger.error(f"加载 Whisper 模型失败: {str(e)}")
            raise
    
    def transcribe(
        self,
        audio_path: str,
        target_lang: str = "zh",
        beam_size: int = 5,
        best_of: int = 5,
        patience: float = 1.0,
        temperature: Tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        language: Optional[str] = None
    ) -> str:
        """
        对音频进行语音转录
        
        Args:
            audio_path: 本地音频文件的绝对路径
                       支持的格式：mp3, wav, ogg, flac, m4a 等
            target_lang: 目标语言
                        "zh" - 中文（普通话）
                        "en" - 英文
                        "yue" - 粤语
                        其他 ISO 639-1 语言代码也被支持
            beam_size: 束搜索的束宽度，越大越精确但越慢（推荐 5）
            best_of: 从 best_of 个解码结果中选择最好的，越大越精确但越慢
            patience: 早停参数，用于加速解码
            temperature: 采样温度元组，对不同重试尝试不同温度
            language: 音频语言代码（ISO 639-1）
                     如果为 None，模型会自动检测
                     一般情况下让模型自动检测即可
        
        Returns:
            转录的文本内容
        
        Raises:
            FileNotFoundError: 音频文件不存在
            ValueError: 不支持的语言代码
            RuntimeError: 模型加载或处理失败
        
        Example:
            >>> service = WhisperService()
            >>> # 转录中文音频
            >>> text = service.transcribe("meeting.wav", target_lang="zh")
            >>> print(text)
            大家好，感谢参加这次会议...
            
            >>> # 转录粤语音频
            >>> text = service.transcribe("cantonese.wav", target_lang="yue")
        """
        # 确保模型已加载
        self._ensure_model_loaded()
        
        # 检查文件存在性
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 验证语言代码
        if target_lang not in self.SUPPORTED_LANGUAGES:
            logger.warning(
                f"'{target_lang}' 不在预定义的语言列表中，"
                f"支持的语言: {list(self.SUPPORTED_LANGUAGES.keys())}"
            )
        
        # 获取语言配置，但不直接使用 initial_prompt，避免提示词被当成输出文本
        lang_config = self.SUPPORTED_LANGUAGES.get(target_lang)
        actual_language = lang_config["code"] if lang_config else language
        
        logger.info(
            f"开始转录音频: {audio_path} "
            f"(目标语言: {target_lang}, 模型: {self.model_size})"
        )
        
        try:
            # 调用 faster-whisper 进行转录
            segments, info = self.model.transcribe(
                str(audio_path),
                language=actual_language,
                beam_size=beam_size,
                best_of=best_of,
                patience=patience,
                temperature=temperature,
                condition_on_previous_text=False
            )
            
            logger.info(f"检测到的语言: {info.language} (可信度: {info.language_probability:.2%})")
            
            # 合并所有段的文本
            full_text = " ".join([segment.text for segment in segments])
            
            logger.info(f"转录完成，文本长度: {len(full_text)} 字符")
            return full_text.strip()
        
        except Exception as e:
            logger.error(f"转录音频失败: {str(e)}")
            raise RuntimeError(f"Whisper 转录失败: {str(e)}")
    
    def transcribe_by_sentences(
        self,
        audio_path: str,
        target_lang: str = "zh",
        beam_size: int = 5,
        best_of: int = 5,
        patience: float = 1.0
    ) -> List[Dict]:
        """
        对音频进行转录并按句子分割返回结果
        
        符合 docs/modules/asr_io.md 的输出格式，返回句子级别的 ASRSegment
        
        Args:
            audio_path: 本地音频文件的绝对路径
            target_lang: 目标语言代码
            beam_size: 束搜索宽度
            best_of: 从多个解码结果中选择最好的
            patience: 早停参数
        
        Returns:
            ASRSegment 字典列表，每个包含：
                - segment_id: 句子唯一标识（sent_0001 等）
                - start: 句子开始时间（近似分配）
                - end: 句子结束时间（近似分配）
                - text: 句子文本
                - lang: 语言代码
                - confidence: 识别置信度
        
        Example:
            >>> service = WhisperService()
            >>> sentences = service.transcribe_by_sentences("meeting.wav")
            >>> for sentence in sentences:
            ...     print(f"{sentence['segment_id']}: {sentence['text']}")
            sent_0001: 大家好，欢迎参加这次会议。
            sent_0002: 今天我们要讨论项目进展。
        """
        from backend.schemas.transcription import ASRSegment
        
        # 先获取带时间戳的原始segments，用于时间分配
        timestamp_segments = self.transcribe_with_timestamps(
            audio_path,
            target_lang=target_lang,
            beam_size=beam_size,
            best_of=best_of,
            patience=patience
        )
        
        # 合并所有文本
        full_text = " ".join([text for _, _, text in timestamp_segments])
        
        # 根据语言进行句子分割
        if target_lang == "zh":
            # 中文句子分割：使用。！？作为分隔符
            import re
            sentences = re.split(r'([。！？])', full_text)
            # 重新组合句子
            result_sentences = []
            current_sentence = ""
            
            for part in sentences:
                current_sentence += part
                if part in ['。', '！', '？']:
                    if current_sentence.strip():
                        result_sentences.append(current_sentence.strip())
                    current_sentence = ""
            
            # 处理最后一个不完整的句子
            if current_sentence.strip():
                result_sentences.append(current_sentence.strip())
                
        elif target_lang == "en":
            # 英文句子分割：使用. ! ?作为分隔符
            import re
            sentences = re.split(r'([.!?])', full_text)
            result_sentences = []
            current_sentence = ""
            
            for part in sentences:
                current_sentence += part
                if part in ['.', '!', '?']:
                    if current_sentence.strip():
                        result_sentences.append(current_sentence.strip())
                    current_sentence = ""
            
            if current_sentence.strip():
                result_sentences.append(current_sentence.strip())
                
        else:
            # 其他语言：简单按标点分割
            import re
            sentences = re.split(r'([.!?。！？])', full_text)
            result_sentences = []
            current_sentence = ""
            
            for part in sentences:
                current_sentence += part
                if part in ['.', '!', '?', '。', '！', '？']:
                    if current_sentence.strip():
                        result_sentences.append(current_sentence.strip())
                    current_sentence = ""
            
            if current_sentence.strip():
                result_sentences.append(current_sentence.strip())
        
        # 过滤掉太短的句子片段
        result_sentences = [s for s in result_sentences if len(s.strip()) > 1]
        
        # 为句子分配时间戳（近似分配）
        total_duration = timestamp_segments[-1][1] if timestamp_segments else 0.0
        sentence_segments = []
        
        for idx, sentence_text in enumerate(result_sentences):
            # 基于句子在列表中的位置分配时间戳
            start_time = (idx / len(result_sentences)) * total_duration
            end_time = ((idx + 1) / len(result_sentences)) * total_duration
            
            sentence_segment = ASRSegment(
                segment_id=f"seg_{idx+1:04d}",  # 按照docs规范使用seg_xxxx格式
                start=round(start_time, 2),
                end=round(end_time, 2),
                text=sentence_text,
                lang=target_lang,
                confidence=0.85  # 句子级别的置信度略低
            ).model_dump()
            
            sentence_segments.append(sentence_segment)
        
        logger.info(f"按句子分割完成，共 {len(sentence_segments)} 个句子")
        return sentence_segments
    
    def transcribe_with_timestamps(
        self,
        audio_path: str,
        target_lang: str = "zh",
        beam_size: int = 5,
        best_of: int = 5,
        patience: float = 1.0
    ) -> List[Tuple[float, float, str]]:
        """
        对音频进行转录并返回带时间戳的段级别结果
        
        Args:
            audio_path: 本地音频文件的绝对路径
            target_lang: 目标语言代码
            beam_size: 束搜索宽度
            best_of: 从多个解码结果中选择最好的
            patience: 早停参数
        
        Returns:
            列表，每个元素是 (start_time, end_time, text) 的元组
            其中 start_time 和 end_time 以秒为单位
        
        Example:
            >>> service = WhisperService()
            >>> segments = service.transcribe_with_timestamps("audio.wav")
            >>> for start, end, text in segments:
            ...     print(f"[{start:.2f}s - {end:.2f}s] {text}")
            [0.00s - 2.50s] 大家好
            [2.50s - 5.80s] 欢迎参加会议
        """
        self._ensure_model_loaded()
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 获取语言配置，但不直接使用 initial_prompt，避免提示词污染输出
        lang_config = self.SUPPORTED_LANGUAGES.get(target_lang)
        actual_language = lang_config["code"] if lang_config else None
        
        logger.info(f"开始转录音频（带时间戳）: {audio_path}")
        
        try:
            segments, _ = self.model.transcribe(
                str(audio_path),
                language=actual_language,
                beam_size=beam_size,
                best_of=best_of,
                patience=patience,
                condition_on_previous_text=False
            )
            
            # 提取带时间戳的结果
            results = []
            for segment in segments:
                results.append((segment.start, segment.end, segment.text.strip()))
            
            logger.info(f"提取到 {len(results)} 个转录段")
            return results
        
        except Exception as e:
            logger.error(f"转录音频失败: {str(e)}")
            raise RuntimeError(f"Whisper 转录失败: {str(e)}")
    
    def transcribe_with_asr_segments(
        self,
        audio_path: str,
        target_lang: str = "zh",
        beam_size: int = 5,
        best_of: int = 5,
        patience: float = 1.0
    ) -> List[Dict]:
        """
        对音频进行转录，返回规范格式的 ASRSegment 字典列表
        
        符合 docs/modules/asr_io.md 的输出格式
        
        Args:
            audio_path: 本地音频文件的绝对路径
            target_lang: 目标语言代码
            beam_size: 束搜索宽度
            best_of: 从多个解码结果中选择最好的
            patience: 早停参数
        
        Returns:
            ASRSegment 字典列表，每个包含：
                - segment_id: 片段唯一标识（seg_0001 等）
                - start: 开始时间
                - end: 结束时间
                - text: 转录文本
                - lang: 语言代码
                - confidence: 识别置信度
        """
        from backend.schemas.transcription import ASRSegment
        
        segments = self.transcribe_with_timestamps(
            audio_path,
            target_lang=target_lang,
            beam_size=beam_size,
            best_of=best_of,
            patience=patience
        )
        
        asr_segments = [
            ASRSegment(
                segment_id=f"seg_{idx+1:04d}",
                start=start,
                end=end,
                text=text,
                lang=target_lang,
                confidence=0.9  # 默认置信度
            ).model_dump()
            for idx, (start, end, text) in enumerate(segments)
        ]
        
        return asr_segments
    
    @staticmethod
    def get_language_by_code(target_lang: str) -> Optional[str]:
        """
        根据语言代码获取语言名称
        
        Args:
            target_lang: 语言代码（如 "zh", "en", "yue"）
        
        Returns:
            语言名称，如果代码不支持返回 None
        """
        if target_lang in WhisperService.SUPPORTED_LANGUAGES:
            return WhisperService.SUPPORTED_LANGUAGES[target_lang]["name"]
        return None