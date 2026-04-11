import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent.parent)
sys.path.append(project_root)

from backend.pipelines.translation_summarization import TranslationSummarizationPipeline

def test_pipeline():
    # Mock data
    meeting_id = "test_meeting_001"
    
    # Test cases for different language pairs
    test_cases = [
        {
            "name": "Chinese to English",
            "source": "zh",
            "target": "en",
            "segments": [{"text": "大家好我是人不是猪，如果你说我是人的话那我就是猪，如果你说我是猪的话那我就是人。", "speaker": "S1"}]
        },
        {
            "name": "User Feedback Case (Mandarin to Cantonese)",
            "source": "zh",
            "target": "yue",
            "segments": [{"text": "我是人不是猪，如果你说我是人的话那我就是猪，如果你说我是猪的话那我就是人。", "speaker": "S1"}]
        }
    ]
    
    for case in test_cases:
        print(f"\n--- Testing: {case['name']} ({case['source']} -> {case['target']}) ---")
        pipeline = TranslationSummarizationPipeline(meeting_id=meeting_id)
        result = pipeline.process(case['segments'], source_lang=case['source'], target_lang=case['target'])
        
        if result.status == "completed":
            print(f"Summary: {result.data['summary']}")
            for seg in result.data["translated_segments"]:
                print(f"Original: {seg['text']}")
                print(f"Translated: {seg['translated_text']}")
        else:
            print(f"Error: {result.error}")

if __name__ == "__main__":
    test_pipeline()
