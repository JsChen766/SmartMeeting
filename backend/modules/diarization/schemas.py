from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DiarizationError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class AudioAsset(BaseModel):
    model_config = ConfigDict(extra="allow")

    file_name: str
    storage_path: str
    duration: float | None = None
    source_type: str | None = None
    sample_rate: int | None = None
    channels: int | None = None
    lang_hint: str | None = None


class DiarizationOptions(BaseModel):
    model_config = ConfigDict(extra="allow")

    auth_token: str | None = None
    model_id: str | None = None
    device: str | None = None
    num_speakers: int | None = Field(default=None, ge=1)
    min_speakers: int | None = Field(default=None, ge=1)
    max_speakers: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_speaker_bounds(self) -> "DiarizationOptions":
        if (
            self.min_speakers is not None
            and self.max_speakers is not None
            and self.min_speakers > self.max_speakers
        ):
            raise ValueError("min_speakers must be less than or equal to max_speakers")

        return self


class DiarizationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    meeting_id: str
    audio_asset: AudioAsset
    options: DiarizationOptions | None = None


class SpeakerSegment(BaseModel):
    start: float
    end: float
    speaker: str


class DiarizationData(BaseModel):
    speaker_segments: list[SpeakerSegment]


class DiarizationResponse(BaseModel):
    meeting_id: str
    status: str
    data: DiarizationData | None
    error: DiarizationError | None
