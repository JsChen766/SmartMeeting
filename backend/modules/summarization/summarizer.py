from typing import List, Dict, Optional
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch

class MeetingSummarizer:
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.tokenizer = None
        self.model = None

    def _load_model(self):
        if self.model is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(self.device)

    def generate_summary(self, transcript: str, max_length: int = 150, min_length: int = 20) -> Dict[str, any]:
        """
        Generate a summary of the transcript.
        """
        # If text is too short, don't summarize, just return it or a simple version
        if len(transcript.split()) < 30:
            return {
                "summary": transcript,
                "key_points": [transcript]
            }

        self._load_model()
        
        inputs = self.tokenizer(transcript, max_length=1024, return_tensors="pt", truncation=True).to(self.device)
        
        summary_ids = self.model.generate(
            inputs["input_ids"], 
            max_length=max_length, 
            min_length=min_length, 
            length_penalty=2.0, 
            num_beams=4, 
            no_repeat_ngram_size=3,
            early_stopping=True
        )
        
        summary_text = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        
        # Clean up common hallucinations like repeating speaker IDs if they appear at the start
        import re
        summary_text = re.sub(r'^(S\d+:\s*)+', '', summary_text).strip()
        
        # If after cleaning the summary is too short or empty, use a fallback
        if len(summary_text) < 5:
            summary_text = transcript[:200] + "..." if len(transcript) > 200 else transcript
        
        # Simple extraction of key points (this could be improved)
        key_points = summary_text.split(". ")
        
        return {
            "summary": summary_text,
            "key_points": [p.strip() for p in key_points if p.strip()]
        }

    def format_transcript(self, segments: List[Dict[str, any]]) -> str:
        """
        Format segments into a single string for summarization.
        Expected format: "Speaker S1: Hello. Speaker S2: Hi."
        """
        formatted_lines = []
        for seg in segments:
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "")
            formatted_lines.append(f"{speaker}: {text}")
        return " ".join(formatted_lines)
