#!/usr/bin/env python3
"""
演示句子分割功能的脚本
"""

import sys
import os
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def demo_sentence_splitting():
    """演示句子分割功能"""
    logger.info("=== 句子分割功能演示 ===")

    # 添加backend路径
    backend_path = os.path.join(os.path.dirname(__file__), 'backend')
    sys.path.insert(0, backend_path)

    try:
        from pipelines.meeting_pipeline import MeetingTranscriberPipeline

        pipeline = MeetingTranscriberPipeline()

        # 测试音频文件
        audio_file = "test.m4a"
        if not os.path.exists(audio_file):
            logger.error(f"音频文件不存在: {audio_file}")
            logger.info("请确保 test.m4a 文件在项目根目录下")
            return

        logger.info(f"正在处理音频文件: {audio_file}")

        # 1. 先显示普通转录结果（一段话）
        logger.info("\n--- 普通转录结果（一段话） ---")
        full_text = pipeline.whisper_service.transcribe(audio_file, target_lang="zh")
        logger.info(f"完整文本: {full_text}")

        # 2. 再显示句子分割结果
        logger.info("\n--- 句子分割结果 ---")
        sentences = pipeline.transcribe_by_sentences(audio_file, target_lang="zh")

        for i, sentence in enumerate(sentences, 1):
            logger.info(f"{i}. {sentence}")

        logger.info(f"\n共分割出 {len(sentences)} 个句子")

        # 3. 演示句子分割逻辑（用示例文本）
        logger.info("\n--- 句子分割逻辑演示 ---")
        demo_text = "大家好，欢迎参加这次会议。今天我们要讨论项目进展。请大家积极发言。"
        logger.info(f"示例文本: {demo_text}")

        # 手动演示分割逻辑
        import re
        parts = re.split(r'([。！？])', demo_text)
        demo_sentences = []
        current = ""
        for part in parts:
            current += part
            if part in ['。', '！', '？']:
                if current.strip():
                    demo_sentences.append(current.strip())
                current = ""

        logger.info("分割结果:")
        for i, sentence in enumerate(demo_sentences, 1):
            logger.info(f"{i}. {sentence}")

        # 4. 解释差异
        logger.info("\n--- 为什么会有差异 ---")
        logger.info("普通转录: Whisper 按音频自然停顿分割，返回多个片段然后合并")
        logger.info("句子分割: 在普通转录基础上，按标点符号（。！？）进一步分割")
        logger.info("这样可以得到更符合阅读习惯的句子级结果")

    except ImportError as e:
        logger.error(f"导入失败: {e}")
        logger.info("请确保已安装所需的依赖包")
    except Exception as e:
        logger.error(f"演示失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    demo_sentence_splitting()