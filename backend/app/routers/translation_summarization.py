from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from backend.pipelines.translation_summarization import TranslationSummarizationPipeline
from backend.schemas.base import ModuleResponse

router = APIRouter(
    prefix="/nlp",
    tags=["nlp"]
)

@router.post("/translate-summarize", response_model=ModuleResponse)
async def translate_summarize(
    meeting_id: str,
    segments: List[Dict[str, Any]],
    source_lang: str = "zh",
    target_lang: str = "en"
):
    """
    Endpoint for multi-language translation and summarization.
    - meeting_id: Unique identifier for the meeting.
    - segments: List of transcript segments to process.
    - source_lang: Language of the input segments.
    - target_lang: Language for translation output.
    """
    pipeline = TranslationSummarizationPipeline(meeting_id=meeting_id)
    result = pipeline.process(segments, source_lang, target_lang)
    
    if result.status == "failed":
        raise HTTPException(status_code=500, detail=result.error)
        
    return result
