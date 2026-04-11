import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parent.parent)
sys.path.append(project_root)

from backend.pipelines.translation_summarization import TranslationSummarizationPipeline

def test_pipeline_with_json():
    # File path for the input JSON
    json_path = os.path.join(project_root, "data", "raw", "alignment_b78ca05_force_merge_compact_v2.json")
    
    if not os.path.exists(json_path):
        print(f"Error: JSON file not found at {json_path}")
        return

    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    meeting_id = json_data.get("meeting_id", "test_meeting")
    segments = json_data.get("data", {}).get("aligned_transcript", [])
    
    if not segments:
        print("Error: No transcript segments found in JSON.")
        return

    # Test cases: Translation to English and Cantonese
    languages = [
        {"name": "Chinese to English", "target": "en"},
        {"name": "Chinese to Cantonese", "target": "yue"}
    ]
    
    for lang in languages:
        print(f"\n--- Testing: {lang['name']} (zh -> {lang['target']}) ---")
        pipeline = TranslationSummarizationPipeline(meeting_id=meeting_id)
        
        # Process all segments from the JSON
        test_segments = segments 
        print(f"Processing {len(test_segments)} segments...")
        
        result = pipeline.process(test_segments, source_lang="zh", target_lang=lang.get("target"))
        
        if result.status == "completed":
            print(f"\n--- Final Summary ({lang['name']}) ---")
            print(result.data['summary'])
            print(f"\n--- Full Translated Transcript ({len(result.data['translated_segments'])} segments) ---")
            for seg in result.data["translated_segments"]:
                print(f"  [{seg['speaker']}] {seg['translated_text']}")
        else:
            print(f"Error: {result.error}")

if __name__ == "__main__":
    test_pipeline_with_json()
