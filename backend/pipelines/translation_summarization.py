from typing import List, Dict, Optional
from dataclasses import dataclass
from backend.modules.translation.translator import MultiLanguageTranslator
from backend.modules.summarization.summarizer import MeetingSummarizer

@dataclass
class PipelineResult:
    status: str
    data: Optional[Dict[str, any]] = None
    error: Optional[str] = None

class TranslationSummarizationPipeline:
    def __init__(self, meeting_id: str):
        self.meeting_id = meeting_id
        self.translator = MultiLanguageTranslator()
        self.summarizer = MeetingSummarizer()

    def process(self, segments: List[Dict[str, any]], source_lang: str = "zh", target_lang: str = "en") -> PipelineResult:
        try:
            # 1. Translate segments
            print(f"Translating {len(segments)} segments to {target_lang}...")
            translated_segments = self.translator.translate_segments(segments, source_lang, target_lang)
            
            # 2. Prepare full transcript for summarization
            # We summarize the original text for better context, or the translated one?
            # Usually summarization is better in the source language or a common language like English.
            # Given the summarizer is configured to summarize in Chinese, we use original text.
            full_transcript = "\n".join([f"{seg['speaker']}: {seg['text']}" for seg in segments])
            
            # 3. Generate summary
            print("Generating summary...")
            summary_result = self.summarizer.generate_summary(full_transcript)
            
            return PipelineResult(
                status="completed",
                data={
                    "translated_segments": translated_segments,
                    "summary": summary_result["summary"],
                    "key_points": summary_result["key_points"]
                }
            )
        except Exception as e:
            return PipelineResult(
                status="failed",
                error=str(e)
            )
