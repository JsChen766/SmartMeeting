from typing import List, Dict, Optional, Any
from backend.modules.translation.translator import MultiLanguageTranslator
from backend.modules.summarization.summarizer import MeetingSummarizer
from backend.schemas.base import ModuleResponse, TranslationItem, SummarizationResult

class TranslationSummarizationPipeline:
    def __init__(self, meeting_id: str):
        self.meeting_id = meeting_id
        self.translator = MultiLanguageTranslator()
        self.summarizer = MeetingSummarizer()

    def process(self, segments: List[Dict[str, Any]], source_lang: str = "zh", target_lang: str = "en") -> ModuleResponse:
        """
        Execute both translation and summarization on a list of meeting segments.
        Expected segment format: {"text": "...", "speaker": "S1", "start": 1.0, "end": 2.0}
        """
        try:
            # 1. Translate segments
            translated_segments = self.translator.translate_segments(
                segments, 
                source_lang=source_lang, 
                target_lang=target_lang
            )
            
            # 2. Format transcript for summarization
            # We summarize the translated transcript if target_lang is English
            # because most summarization models are better at English.
            formatted_transcript = self.summarizer.format_transcript(translated_segments)
            
            # 3. Generate summary
            summary_result = self.summarizer.generate_summary(formatted_transcript)
            
            # 4. Construct response
            data = {
                "translated_segments": translated_segments,
                "summary": summary_result["summary"],
                "key_points": summary_result["key_points"],
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            return ModuleResponse(
                meeting_id=self.meeting_id,
                status="completed",
                data=data
            )
            
        except Exception as e:
            return ModuleResponse(
                meeting_id=self.meeting_id,
                status="failed",
                error=str(e)
            )
