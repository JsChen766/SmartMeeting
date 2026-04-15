import os
import json
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv
try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    import torch
except ImportError:
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None
    torch = None
from opencc import OpenCC

load_dotenv()

class MultiLanguageTranslator:
    def __init__(self, model_name: str = "facebook/nllb-200-distilled-600M"):
        self.device = "cuda" if torch is not None and torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        # Converters for post-processing if needed
        self.s2t_converter = OpenCC('s2t')
        self.t2s_converter = OpenCC('t2s')
        
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.llm_model = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.5-air:free")

    def _load_model(self):
        # We prefer using LLM (OpenRouter) in this environment for reliability
        if self.openrouter_api_key:
            self.model = "openrouter"
            return

        if self.model is None:
            if AutoModelForSeq2SeqLM is None:
                print("Warning: transformers/torch not installed. Falling back to LLM if possible.")
                # We've already set it to openrouter if key exists, otherwise it stays None
                return
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(self.device)
            except Exception as e:
                print(f"Warning: Could not load local translation model: {e}.")
                self.model = "openrouter" if self.openrouter_api_key else "dummy"

    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        Translate text from source_lang to target_lang.
        Supported lang codes: 'zh' (Mandarin/Simplified), 'en' (English), 'yue' (Cantonese/Traditional).
        Using OpenRouter LLM for high-quality dialectal support.
        """
        self._load_model()
        
        if self.model == "openrouter":
            return self._translate_llm(text, source_lang, target_lang)
        
        if self.model == "dummy":
            return f"[Translated to {target_lang}] {text}"
        
        # Mapping simple codes to NLLB-200 language codes
        lang_map = {
            "zh": "zho_Hans",
            "en": "eng_Latn",
            "yue": "yue_Hant"
        }
        
        src = lang_map.get(source_lang, "zho_Hans")
        tgt = lang_map.get(target_lang, "eng_Latn")

        # Set source language
        self.tokenizer.src_lang = src
        
        # Tokenize
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        
        # Generate translation with forced target language
        # For NLLB, the correct way to get lang id is through the tokenizer's convert_tokens_to_ids
        forced_bos_token_id = self.tokenizer.convert_tokens_to_ids(tgt)
        
        generated_tokens = self.model.generate(
            **inputs, 
            forced_bos_token_id=forced_bos_token_id,
            max_length=512,
            no_repeat_ngram_size=3,  # Prevent repetitive loops like ",,,,,," or "吧 吧 吧"
            num_beams=4,
            early_stopping=True
        )
        
        # Decode
        translated_text = self.tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)[0]
        
        # Post-process for Cantonese: NLLB might still output Simplified if it's confused
        # but with yue_Hant it should be Traditional. Let's ensure it's Traditional for yue.
        if target_lang == "yue":
            translated_text = self.s2t_converter.convert(translated_text)
            # Replace common Mandarin words with Cantonese equivalents if NLLB failed to do so地道化
            # This is a simple heuristic, NLLB should ideally handle this.
            replacements = {
                "我是": "我係",
                "不是": "唔係",
                "的话": "嘅话",
                "那就是": "就係",
                "他是": "佢係",
                "他们": "佢哋",
                "我们": "我哋",
                "什么": "乜嘢",
                "没有": "冇",
            }
            for k, v in replacements.items():
                translated_text = translated_text.replace(k, v)
                
        return translated_text

    def translate_segments(self, segments: List[Dict[str, any]], source_lang: str = "zh", target_lang: str = "en") -> List[Dict[str, any]]:
        """
        Translate a list of transcript segments.
        Optimized to use LLM batching if possible.
        """
        self._load_model()
        
        if self.model != "openrouter":
            # Fallback to sequential for local model or dummy
            translated_segments = []
            for segment in segments:
                original_text = segment.get("text", "")
                if original_text:
                    translated_text = self.translate(original_text, source_lang, target_lang)
                    segment["translated_text"] = translated_text
                translated_segments.append(segment)
            return translated_segments

        # OpenRouter Batch translation
        texts_to_translate = [seg.get("text", "") for seg in segments]
        # We wrap them in a JSON format to ensure the LLM returns the same number of lines/items
        batch_prompt = {
            "source_lang": source_lang,
            "target_lang": target_lang,
            "items": texts_to_translate
        }
        
        lang_names = {
            "en": "English",
            "zh": "Chinese (Mandarin Simplified)",
            "yue": "Cantonese (Traditional)"
        }
        target_name = lang_names.get(target_lang, target_lang)
        source_name = lang_names.get(source_lang, source_lang)

        prompt = (
            f"Translate the following list of texts from {source_name} to {target_name}. "
            "Return the translations as a JSON list of strings, exactly matching the order of input. "
            "Only return the JSON list, no extra text.\n\n"
            f"Input: {json.dumps(texts_to_translate, ensure_ascii=False)}"
        )

        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/SmartMeeting",
                    "X-OpenRouter-Title": "SmartMeeting Translator",
                },
                data=json.dumps({
                    "model": self.llm_model,
                    "messages": [
                        {"role": "system", "content": "You are a precise translator. You only output valid JSON lists of translated strings."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"} if "gpt-4" in self.llm_model else None
                }),
                timeout=60
            )
            
            result = response.json()
            if "choices" in result:
                content = result["choices"][0]["message"]["content"].strip()
                # Try to find the list in the content (LLM might wrap it in ```json)
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                
                translated_texts = json.loads(content)
                if isinstance(translated_texts, dict) and "items" in translated_texts:
                    translated_texts = translated_texts["items"]
                
                if len(translated_texts) == len(segments):
                    for i, seg in enumerate(segments):
                        seg["translated_text"] = translated_texts[i]
                    return segments
                else:
                    raise Exception(f"Batch translation count mismatch: {len(translated_texts)} vs {len(segments)}")
            else:
                raise Exception(f"OpenRouter API error: {result}")
                
        except Exception as e:
            print(f"Batch LLM Translation failed: {e}. Falling back to sequential.")
            # Fallback to sequential
            for seg in segments:
                seg["translated_text"] = self.translate(seg.get("text", ""), source_lang, target_lang)
            return segments

    def _translate_llm(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Helper to call OpenRouter for translation.
        """
        lang_names = {
            "en": "English",
            "zh": "Chinese (Mandarin Simplified)",
            "yue": "Cantonese (Traditional)"
        }
        
        target_name = lang_names.get(target_lang, target_lang)
        source_name = lang_names.get(source_lang, source_lang)
        
        prompt = (
            f"Translate the following text from {source_name} to {target_name}. "
            "Only return the translated text without any explanations or extra characters.\n\n"
            f"Text: {text}"
        )

        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/SmartMeeting",
                    "X-OpenRouter-Title": "SmartMeeting Translator",
                },
                data=json.dumps({
                    "model": self.llm_model,
                    "messages": [
                        {"role": "system", "content": f"You are a professional translator specializing in {source_name} to {target_name}."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                }),
                timeout=20
            )
            
            result = response.json()
            if "choices" in result:
                return result["choices"][0]["message"]["content"].strip()
            else:
                raise Exception(f"OpenRouter API error: {result}")
        except Exception as e:
            print(f"LLM Translation failed: {e}")
            return f"[Error] {text}"
