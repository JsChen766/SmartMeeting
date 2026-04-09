#!/usr/bin/env python3
"""
测试句子分割功能的脚本
"""

import sys
import os
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sentence_splitting():
    """测试句子分割功能"""
    logger.info("开始测试句子分割功能")

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
            return

        logger.info(f"处理音频文件: {audio_file}")

        # 测试句子分割
        sentences = pipeline.transcribe_by_sentences(audio_file, target_lang="zh")

        logger.info("\n" + "="*60)
        logger.info("句子分割结果:")
        logger.info("="*60)

        for i, sentence in enumerate(sentences, 1):
            logger.info(f"{i:2d}. {sentence}")

        logger.info(f"\n共分割出 {len(sentences)} 个句子")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sentence_splitting()