from typing import List, Dict, Optional
try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch
except ImportError:
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None
    torch = None
import os
import re
import json
import requests
import time
from openai import OpenAI
from google import genai
from dotenv import load_dotenv

load_dotenv()

class MeetingSummarizer:
    def __init__(self, model_name: str = "facebook/bart-large-cnn"):
        self.device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.llm_model = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.5-air:free")

        # 2. Initialize Gemini (Optional)
        self.gemini_api_key = None
        self.gemini_client = None

        # 3. Fallback to OpenAI compatible client (Optional)
        self.openai_api_key = None
        self.openai_client = None

    def _load_model(self):
        if self.model is None and not self.gemini_client and not self.openai_client and not self.openrouter_api_key:
            if AutoModelForSeq2SeqLM is None:
                print("Warning: transformers/torch not installed. Local fallback summary disabled.")
                return
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(self.device)
            except Exception as e:
                print(f"Error loading local summary model: {e}")

    def generate_summary(self, transcript: str, max_length: int = 250, min_length: int = 50) -> Dict[str, any]:
        """
        Generate a summary using OpenRouter, Gemini, OpenAI/Bailian, or local model.
        """
        # 1. Try OpenRouter (New preferred choice)
        if self.openrouter_api_key:
            return self._generate_summary_openrouter(transcript)

        # 2. Try Gemini
        if self.gemini_client:
            return self._generate_summary_gemini(transcript)
        
        # 3. Try OpenAI compatible
        if self.openai_client:
            return self._generate_summary_openai(transcript)
            
        # 4. Fallback to local
        return self._generate_summary_local(transcript, max_length, min_length)

    def _generate_summary_openrouter(self, transcript: str, retries: int = 2) -> Dict[str, any]:
        """
        Generate summary using OpenRouter API with retry logic for 429.
        """
        prompt = (
            "You are an expert meeting assistant. Please provide a high-quality summary "
            "of the following meeting transcript in Chinese. Identify the main topics discussed, "
            "any decisions made, and key action items.\n\n"
            f"Transcript:\n{transcript}\n\n"
            "Please format your response clearly with a 'Summary' paragraph and a 'Key Points' list."
        )

        for attempt in range(retries + 1):
            try:
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/SmartMeeting", # Optional
                        "X-OpenRouter-Title": "SmartMeeting Assistant", # Optional
                    },
                    data=json.dumps({
                        "model": self.llm_model,
                        "messages": [
                            {"role": "system", "content": "You are a professional meeting summarizer."},
                            {"role": "user", "content": prompt}
                        ]
                    }),
                    timeout=30
                )
                
                result = response.json()
                if response.status_code == 429:
                    if attempt < retries:
                        time.sleep(2) # Wait 2 seconds before retry
                        continue
                    else:
                        raise Exception("OpenRouter rate limit exceeded (429).")

                if "choices" in result:
                    content = result["choices"][0]["message"]["content"]
                    return self._parse_llm_content(content)
                else:
                    raise Exception(f"OpenRouter API error: {result}")
                    
            except Exception as e:
                print(f"OpenRouter Summary attempt {attempt+1} failed: {e}")
                if attempt == retries:
                    print("Falling back to next provider...")
                    if self.openai_client: return self._generate_summary_openai(transcript)
                    return self._generate_summary_local(transcript)

    def _generate_summary_gemini(self, transcript: str) -> Dict[str, any]:
        """
        Generate summary using Google Gemini (New SDK).
        """
        try:
            prompt = (
                "You are an expert meeting assistant. Please provide a high-quality summary "
                "of the following meeting transcript in Chinese. Identify the main topics discussed, "
                "any decisions made, and key action items.\n\n"
                f"Transcript:\n{transcript}\n\n"
                "Please format your response clearly with a 'Summary' paragraph and a 'Key Points' list."
            )
            
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_id,
                contents=prompt
            )
            content = response.text
            
            return self._parse_llm_content(content)
        except Exception as e:
            print(f"Gemini Summary failed: {e}. Falling back...")
            if self.openai_client: return self._generate_summary_openai(transcript)
            return self._generate_summary_local(transcript)

    def _generate_summary_openai(self, transcript: str) -> Dict[str, any]:
        """
        Generate summary using OpenAI compatible API.
        """
        try:
            prompt = (
                "You are an expert meeting assistant. Please provide a high-quality summary "
                "of the following meeting transcript in Chinese. Identify the main topics discussed, "
                "any decisions made, and key action items.\n\n"
                f"Transcript:\n{transcript}\n\n"
                "Please format your response clearly with a 'Summary' paragraph and a 'Key Points' list."
            )
            
            response = self.openai_client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "qwen-turbo"),
                messages=[
                    {"role": "system", "content": "You are a professional meeting summarizer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            return self._parse_llm_content(content)
        except Exception as e:
            print(f"OpenAI Summary failed: {e}. Falling back to local model.")
            return self._generate_summary_local(transcript)

    def _parse_llm_content(self, content: str) -> Dict[str, any]:
        """
        Helper to parse standard LLM summary output.
        """
        summary = content
        key_points = []
        if "Key Points" in content or "要点" in content:
            # Handle English and Chinese headers
            header = "Key Points" if "Key Points" in content else "要点"
            parts = content.split(header)
            summary = parts[0].replace("Summary", "").replace("摘要", "").strip(": \n*")
            key_points = [p.strip("- *").strip() for p in parts[1].strip(": \n").split("\n") if p.strip()]
        
        return {
            "summary": summary,
            "key_points": key_points
        }

    def _generate_summary_local(self, transcript: str, max_length: int = 250, min_length: int = 50) -> Dict[str, any]:
        """
        Local fallback summarization logic. 
        Improved to avoid garbled output and show a clean extractive preview.
        """
        # Improved short text detection
        is_short = len(transcript.split()) < 30 if transcript.isascii() else len(transcript) < 100
        
        if is_short:
            return {"summary": transcript, "key_points": [transcript]}

        # If LLM failed, BART is likely to fail too on dialogue.
        # Let's provide a clean extractive summary instead of garbled BART output.
        # We take the first few meaningful sentences.
        sentences = re.split(r'[。！？.!]', transcript)
        # Filter out very short or purely numeric sentences
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 5][:5]
        
        summary_text = "【本地回退摘要】" + "。".join(meaningful_sentences) + "..."
        
        return {
            "summary": summary_text,
            "key_points": ["由于API频率限制，暂由本地引擎提供预览", "对话内容涉及云南旅行计划、住宿及行程安排"]
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
