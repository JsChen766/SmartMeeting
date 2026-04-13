from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from backend.app.adapters import (
    adapt_transcript_segments,
    error_response,
    success_response,
    to_api_lang,
    to_internal_lang,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"
OUTPUT_ROOT = DATA_ROOT / "outputs"

SUPPORTED_AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".aac",
    ".webm",
}


class MeetingService:
    def upload_meeting(
        self,
        file: UploadFile,
        *,
        lang_hint: str | None = None,
        file_name: str | None = None,
    ) -> dict[str, Any]:
        safe_name = Path(file_name or file.filename or "meeting_audio").name
        suffix = Path(safe_name).suffix.lower()
        if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
            return error_response(
                "UPLOAD_FILE_TYPE_UNSUPPORTED",
                "file type is not supported",
                {"file_name": safe_name, "supported_extensions": sorted(SUPPORTED_AUDIO_EXTENSIONS)},
            )

        meeting_id = f"mtg_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        meeting_dir = RAW_ROOT / meeting_id
        meeting_dir.mkdir(parents=True, exist_ok=True)
        output_dir = OUTPUT_ROOT / meeting_id
        output_dir.mkdir(parents=True, exist_ok=True)

        storage_path = meeting_dir / safe_name
        with storage_path.open("wb") as target:
            shutil.copyfileobj(file.file, target)

        audio_asset = self._build_audio_asset(
            storage_path=storage_path,
            file_name=safe_name,
            lang_hint=lang_hint,
        )
        now = self._now()
        state = {
            "meeting_id": meeting_id,
            "status": "uploaded",
            "file_name": safe_name,
            "created_at": now,
            "updated_at": now,
            "audio_asset": audio_asset,
            "options": {},
            "available_results": {
                "transcript": False,
                "translation": False,
                "summary": False,
            },
            "transcript": [],
            "alignment_diagnostics": None,
            "summary": None,
            "key_points": [],
            "action_items": [],
            "error": None,
        }
        self._save_state(state)

        return success_response(
            "meeting uploaded successfully",
            {
                "meeting_id": meeting_id,
                "status": "uploaded",
                "file_name": safe_name,
                "audio_asset": audio_asset,
            },
        )

    def start_processing(
        self,
        *,
        meeting_id: str,
        target_lang: str | None = None,
        enable_translation: bool = False,
        translation_target_lang: str | None = None,
        enable_summary: bool = True,
    ) -> dict[str, Any]:
        state = self._load_state(meeting_id)
        if state is None:
            return error_response("MEETING_NOT_FOUND", "meeting_id does not exist", {"meeting_id": meeting_id})

        if state["status"] == "processing":
            return error_response("MEETING_ALREADY_PROCESSING", "meeting is already processing", {"meeting_id": meeting_id})

        if state["status"] == "completed":
            return error_response("MEETING_ALREADY_COMPLETED", "meeting is already completed", {"meeting_id": meeting_id})

        state["status"] = "processing"
        state["updated_at"] = self._now()
        state["error"] = None
        state["options"] = {
            "target_lang": target_lang or state["audio_asset"].get("lang_hint") or "man",
            "enable_translation": enable_translation,
            "translation_target_lang": translation_target_lang,
            "enable_summary": enable_summary,
        }
        self._save_state(state)

        return success_response(
            "meeting processing started",
            {
                "meeting_id": meeting_id,
                "status": "processing",
            },
        )

    def process_meeting(
        self,
        *,
        meeting_id: str,
        target_lang: str | None = None,
        enable_translation: bool = False,
        translation_target_lang: str | None = None,
        enable_summary: bool = True,
    ) -> None:
        state = self._load_state(meeting_id)
        if state is None:
            return

        try:
            audio_asset = state["audio_asset"]
            audio_path = PROJECT_ROOT / audio_asset["storage_path"]
            internal_target_lang = to_internal_lang(target_lang or audio_asset.get("lang_hint"))

            asr_segments = self._run_asr(
                audio_path=str(audio_path),
                target_lang=internal_target_lang,
            )
            speaker_segments = self._run_diarization(state)
            alignment_result = self._run_alignment(
                meeting_id=meeting_id,
                asr_segments=asr_segments,
                speaker_segments=speaker_segments,
            )

            if alignment_result["status"] != "completed":
                error = alignment_result.get("error") or {}
                raise MeetingProcessingError(
                    error.get("code", "ALIGNMENT_FAILED"),
                    error.get("message", "alignment failed"),
                    error.get("details", {}),
                )

            transcript = alignment_result["data"]["aligned_transcript"]
            diagnostics = alignment_result["data"].get("alignment_diagnostics")
            summary = None
            key_points: list[str] = []
            action_items: list[dict[str, Any]] = []

            translated_transcript = transcript
            if enable_translation:
                internal_translation_lang = to_internal_lang(translation_target_lang or "eng")
                translated_transcript = self._run_translation(
                    transcript=transcript,
                    source_lang=internal_target_lang,
                    target_lang=internal_translation_lang,
                )

            if enable_summary:
                summary_result = self._run_summary(translated_transcript)
                summary = summary_result.get("summary", "")
                key_points = summary_result.get("key_points", [])
                action_items = summary_result.get("action_items", [])

            state.update(
                {
                    "status": "completed",
                    "updated_at": self._now(),
                    "transcript": translated_transcript,
                    "alignment_diagnostics": diagnostics,
                    "summary": summary,
                    "key_points": key_points,
                    "action_items": action_items,
                    "available_results": {
                        "transcript": True,
                        "translation": bool(enable_translation),
                        "summary": bool(enable_summary),
                    },
                    "error": None,
                    "options": {
                        "target_lang": to_api_lang(internal_target_lang),
                        "enable_translation": enable_translation,
                        "translation_target_lang": to_api_lang(to_internal_lang(translation_target_lang or "eng"))
                        if enable_translation
                        else None,
                        "enable_summary": enable_summary,
                    },
                }
            )
            self._save_state(state)
        except Exception as exc:
            details: dict[str, Any] = {"meeting_id": meeting_id}
            code = "MEETING_PROCESS_FAILED"
            message = str(exc)
            if isinstance(exc, MeetingProcessingError):
                code = exc.code
                message = exc.message
                details.update(exc.details)
            state["status"] = "failed"
            state["updated_at"] = self._now()
            state["error"] = {
                "code": code,
                "message": message,
                "details": details,
            }
            self._save_state(state)

    def get_meeting(self, meeting_id: str) -> dict[str, Any]:
        state = self._load_state(meeting_id)
        if state is None:
            return error_response("MEETING_NOT_FOUND", "meeting_id does not exist", {"meeting_id": meeting_id})

        return success_response(
            "meeting status fetched successfully",
            {
                "meeting_id": state["meeting_id"],
                "status": state["status"],
                "file_name": state["file_name"],
                "created_at": state["created_at"],
                "updated_at": state["updated_at"],
                "available_results": state["available_results"],
            },
        )

    def get_transcript(
        self,
        meeting_id: str,
        *,
        include_translation: bool = False,
        target_lang: str | None = None,
    ) -> dict[str, Any]:
        state = self._load_state(meeting_id)
        if state is None:
            return error_response("MEETING_NOT_FOUND", "meeting_id does not exist", {"meeting_id": meeting_id})
        if not state["available_results"].get("transcript"):
            return error_response("TRANSCRIPT_NOT_READY", "transcript is not ready", {"meeting_id": meeting_id})

        source_lang = state.get("options", {}).get("target_lang") or state["audio_asset"].get("lang_hint")
        translated = include_translation and state["available_results"].get("translation")
        requested_target_lang = target_lang or state.get("options", {}).get("translation_target_lang")
        transcript = adapt_transcript_segments(
            state.get("transcript", []),
            source_lang=source_lang,
            target_lang=requested_target_lang,
            include_translation=bool(translated),
        )

        return success_response(
            "transcript fetched successfully",
            {
                "meeting_id": meeting_id,
                "status": state["status"],
                "transcript": transcript,
                "alignment_diagnostics": state.get("alignment_diagnostics"),
            },
        )

    def get_summary(self, meeting_id: str) -> dict[str, Any]:
        state = self._load_state(meeting_id)
        if state is None:
            return error_response("MEETING_NOT_FOUND", "meeting_id does not exist", {"meeting_id": meeting_id})
        if not state["available_results"].get("summary"):
            return error_response("SUMMARY_NOT_READY", "summary is not ready", {"meeting_id": meeting_id})

        return success_response(
            "summary fetched successfully",
            {
                "meeting_id": meeting_id,
                "status": state["status"],
                "summary": state.get("summary") or "",
                "key_points": state.get("key_points") or [],
                "action_items": state.get("action_items") or [],
            },
        )

    def _run_asr(self, *, audio_path: str, target_lang: str) -> list[dict[str, Any]]:
        from backend.modules.asr.whisper_service import WhisperService

        return WhisperService().transcribe_with_asr_segments(audio_path, target_lang=target_lang)

    def _run_diarization(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        from backend.modules.diarization.service import run_diarization

        result = run_diarization(
            {
                "meeting_id": state["meeting_id"],
                "audio_asset": {
                    **state["audio_asset"],
                    "lang_hint": to_internal_lang(state["audio_asset"].get("lang_hint")),
                },
            }
        )
        if result["status"] != "completed":
            error = result.get("error") or {}
            raise MeetingProcessingError(
                error.get("code", "DIARIZATION_FAILED"),
                error.get("message", "diarization failed"),
                error.get("details", {}),
            )
        return result["data"]["speaker_segments"]

    def _run_alignment(
        self,
        *,
        meeting_id: str,
        asr_segments: list[dict[str, Any]],
        speaker_segments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        from backend.modules.alignment.service import run_alignment

        return run_alignment(
            {
                "meeting_id": meeting_id,
                "asr_segments": asr_segments,
                "speaker_segments": speaker_segments,
            }
        )

    def _run_translation(
        self,
        *,
        transcript: list[dict[str, Any]],
        source_lang: str,
        target_lang: str,
    ) -> list[dict[str, Any]]:
        from backend.modules.translation.translator import MultiLanguageTranslator

        translated = MultiLanguageTranslator().translate_segments(
            [dict(segment) for segment in transcript],
            source_lang=source_lang,
            target_lang=target_lang,
        )
        for segment in translated:
            if "translated_text" in segment and "translation" not in segment:
                segment["translation"] = segment.pop("translated_text")
            segment["source_lang"] = source_lang
            segment["target_lang"] = target_lang
        return translated

    def _run_summary(self, transcript: list[dict[str, Any]]) -> dict[str, Any]:
        from backend.modules.summarization.summarizer import MeetingSummarizer

        summarizer = MeetingSummarizer()
        return summarizer.generate_summary(summarizer.format_transcript(transcript))

    def _build_audio_asset(
        self,
        *,
        storage_path: Path,
        file_name: str,
        lang_hint: str | None,
    ) -> dict[str, Any]:
        duration = None
        sample_rate = None
        channels = None
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_file(storage_path)
            duration = round(len(audio) / 1000.0, 2)
            sample_rate = audio.frame_rate
            channels = audio.channels
        except Exception:
            pass

        return {
            "file_name": file_name,
            "storage_path": self._relative_path(storage_path),
            "source_type": "uploaded_file",
            "duration": duration,
            "sample_rate": sample_rate,
            "channels": channels,
            "lang_hint": lang_hint or "man",
        }

    def _state_path(self, meeting_id: str) -> Path:
        return OUTPUT_ROOT / meeting_id / "meeting.json"

    def _load_state(self, meeting_id: str) -> dict[str, Any] | None:
        state_path = self._state_path(meeting_id)
        if not state_path.exists():
            return None
        return json.loads(state_path.read_text(encoding="utf-8"))

    def _save_state(self, state: dict[str, Any]) -> None:
        state_path = self._state_path(state["meeting_id"])
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")


class MeetingProcessingError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
