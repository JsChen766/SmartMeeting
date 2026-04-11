import os
from typing import List, Dict, Optional
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from opencc import OpenCC

class MultiLanguageTranslator:
    def __init__(self, model_name: str = "facebook/nllb-200-distilled-600M"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        # Converters for post-processing if needed
        self.s2t_converter = OpenCC('s2t')
        self.t2s_converter = OpenCC('t2s')

    def _load_model(self):
        if self.model is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name).to(self.device)

    def translate(self, text: str, source_lang: str = "zh", target_lang: str = "en") -> str:
        """
        Translate text from source_lang to target_lang.
        Supported lang codes: 'zh' (Mandarin/Simplified), 'en' (English), 'yue' (Cantonese/Traditional).
        Using NLLB-200 for better dialectal support.
        """
        self._load_model()
        
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
            max_length=256
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
        Expected segment format: {"text": "...", "speaker": "S1", "start": 1.0, "end": 2.0}
        """
        translated_segments = []
        for segment in segments:
            original_text = segment.get("text", "")
            if original_text:
                translated_text = self.translate(original_text, source_lang, target_lang)
                segment["translated_text"] = translated_text
            translated_segments.append(segment)
        return translated_segments
