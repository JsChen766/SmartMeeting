from pydantic import BaseModel, Field
from typing import Any, Optional, List

class ModuleResponse(BaseModel):
    meeting_id: str
    status: str = "completed"
    data: Any = Field(default_factory=dict)
    error: Optional[str] = None

class TranslationItem(BaseModel):
    source_text: str
    target_text: str
    source_lang: str
    target_lang: str

class SummarizationResult(BaseModel):
    summary: str
    key_points: List[str] = Field(default_factory=list)
