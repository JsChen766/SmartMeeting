from __future__ import annotations

import os
import inspect
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schemas import (
    DiarizationData,
    DiarizationError,
    DiarizationOptions,
    DiarizationRequest,
    DiarizationResponse,
    SpeakerSegment,
)

DEFAULT_MODEL_ID = "pyannote/speaker-diarization@2.1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOCAL_TOKEN_PATH = PROJECT_ROOT / "backend" / ".hf_token"
MERGE_GAP_SECONDS = 0.35
MIN_PSEUDO_SPEAKER_TOTAL_SECONDS = 8.0
MIN_PSEUDO_SPEAKER_SEGMENT_COUNT = 8
MAX_PSEUDO_SPEAKER_AVERAGE_SECONDS = 1.2


class DiarizationModule:
    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        auth_token: str | None = None,
        device: str | None = None,
    ) -> None:
        self._default_model_id = model_id
        self._default_auth_token = (
            auth_token
            or os.getenv("HUGGINGFACE_TOKEN")
            or os.getenv("HF_TOKEN")
            or self._load_local_auth_token()
        )
        self._default_device = device or os.getenv("PYANNOTE_DEVICE") or self._detect_default_device()
        self._pipeline: Any | None = None
        self._loaded_model_id: str | None = None
        self._loaded_auth_token: str | None = None

    def process(self, payload: dict[str, Any]) -> dict[str, Any]:
        meeting_id = str(payload.get("meeting_id", "")).strip()

        try:
            request = DiarizationRequest.model_validate(payload)
        except ValidationError as exc:
            return self._failed_response(
                meeting_id=meeting_id or "UNKNOWN",
                code="DIARIZATION_INVALID_REQUEST",
                message="diarization request payload is invalid",
                details={"errors": exc.errors()},
            )

        try:
            audio_path = self._resolve_audio_path(request.meeting_id, request.audio_asset.storage_path)
            self._validate_duration(request)
            prepared_audio_path = self._prepare_audio_for_pipeline(audio_path)
            pipeline = self._get_pipeline(request.options)
            diarization_result = self._run_pipeline(pipeline, prepared_audio_path, request.options)
            speaker_segments = self._build_speaker_segments(diarization_result)
        except DiarizationProcessingError as exc:
            return self._failed_response(
                meeting_id=request.meeting_id,
                code=exc.code,
                message=exc.message,
                details=exc.details,
            )
        except Exception as exc:  # pragma: no cover - defensive guard for model/runtime failures
            return self._failed_response(
                meeting_id=request.meeting_id,
                code="DIARIZATION_MODEL_FAILED",
                message="speaker diarization pipeline execution failed",
                details={"reason": str(exc)},
            )

        response = DiarizationResponse(
            meeting_id=request.meeting_id,
            status="completed",
            data=DiarizationData(speaker_segments=speaker_segments),
            error=None,
        )
        return response.model_dump(mode="json")

    def _resolve_audio_path(self, meeting_id: str, storage_path: str) -> Path:
        raw_path = Path(storage_path)
        audio_path = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path

        if not audio_path.exists():
            raise DiarizationProcessingError(
                code="DIARIZATION_AUDIO_NOT_FOUND",
                message="audio file does not exist",
                details={"storage_path": storage_path, "resolved_path": str(audio_path)},
            )

        path_meeting_id = self._extract_meeting_id_from_path(audio_path)
        if path_meeting_id is not None and path_meeting_id != meeting_id:
            raise DiarizationProcessingError(
                code="DIARIZATION_MEETING_ID_MISMATCH",
                message="meeting_id does not match the audio asset path",
                details={
                    "meeting_id": meeting_id,
                    "path_meeting_id": path_meeting_id,
                    "storage_path": storage_path,
                },
            )

        return audio_path

    def _validate_duration(self, request: DiarizationRequest) -> None:
        duration = request.audio_asset.duration
        if duration is None:
            return

        if duration <= 0:
            raise DiarizationProcessingError(
                code="DIARIZATION_INVALID_DURATION",
                message="audio duration must be greater than zero",
                details={"duration": duration},
            )

    def _get_pipeline(self, options: DiarizationOptions | None) -> Any:
        model_id = (options.model_id if options and options.model_id else self._default_model_id).strip()
        auth_token = options.auth_token if options and options.auth_token else self._default_auth_token
        revision: str | None = None
        if "@" in model_id:
            model_id, revision = model_id.split("@", 1)
            model_id = model_id.strip()
            revision = revision.strip() or None

        if not auth_token:
            raise DiarizationProcessingError(
                code="DIARIZATION_AUTH_TOKEN_MISSING",
                message="hugging face auth token is required for the gated pyannote diarization model",
                details={
                    "model_id": model_id,
                    "required_models": [
                        "pyannote/speaker-diarization",
                        "pyannote/segmentation",
                    ],
                },
            )

        if (
            self._pipeline is not None
            and self._loaded_model_id == model_id
            and self._loaded_auth_token == auth_token
        ):
            return self._pipeline

        try:
            self._patch_huggingface_hub_auth_compat()
            from pyannote.audio import Pipeline
        except ImportError as exc:
            raise DiarizationProcessingError(
                code="DIARIZATION_DEPENDENCY_MISSING",
                message="pyannote.audio is not installed",
                details={"reason": str(exc)},
            ) from exc

        self._patch_speechbrain_fetch_for_windows()

        try:
            signature = inspect.signature(Pipeline.from_pretrained)
            auth_kwargs = (
                {"use_auth_token": auth_token}
                if "use_auth_token" in signature.parameters
                else {"token": auth_token}
            )
            if revision:
                if "revision" in signature.parameters:
                    auth_kwargs["revision"] = revision
                else:
                    model_id = f"{model_id}@{revision}"
            pipeline = Pipeline.from_pretrained(model_id, **auth_kwargs)
        except Exception as exc:
            raise DiarizationProcessingError(
                code="DIARIZATION_MODEL_LOAD_FAILED",
                message="failed to load the pyannote diarization pipeline",
                details={"model_id": model_id, "reason": str(exc)},
            ) from exc

        self._move_pipeline_to_device(pipeline, options)
        self._pipeline = pipeline
        self._loaded_model_id = model_id
        self._loaded_auth_token = auth_token
        return pipeline

    def _move_pipeline_to_device(self, pipeline: Any, options: DiarizationOptions | None) -> None:
        requested_device = (options.device if options and options.device else self._default_device) or "cpu"

        try:
            import torch
        except ImportError:
            return

        normalized_device = requested_device
        if requested_device == "cuda" and not torch.cuda.is_available():
            normalized_device = "cpu"

        if hasattr(pipeline, "to"):
            pipeline.to(torch.device(normalized_device))

    def _detect_default_device(self) -> str:
        try:
            import torch
        except ImportError:
            return "cpu"

        return "cuda" if torch.cuda.is_available() else "cpu"

    def _prepare_audio_for_pipeline(self, audio_path: Path) -> Path:
        try:
            import soundfile as sf

            sf.info(str(audio_path))
            return audio_path
        except Exception:
            return self._transcode_audio_with_ffmpeg(audio_path)

    def _transcode_audio_with_ffmpeg(self, audio_path: Path) -> Path:
        temp_dir = Path(tempfile.gettempdir()) / "smartmeeting_diarization"
        temp_dir.mkdir(parents=True, exist_ok=True)
        transcoded_path = temp_dir / f"{audio_path.stem}_diarization.wav"

        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(transcoded_path),
        ]

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise DiarizationProcessingError(
                code="DIARIZATION_AUDIO_DECODE_FAILED",
                message="ffmpeg is required to transcode unsupported audio formats",
                details={"audio_path": str(audio_path), "reason": str(exc)},
            ) from exc

        if completed.returncode != 0 or not transcoded_path.exists():
            raise DiarizationProcessingError(
                code="DIARIZATION_AUDIO_DECODE_FAILED",
                message="failed to transcode audio into a diarization-ready wav file",
                details={
                    "audio_path": str(audio_path),
                    "stderr": completed.stderr.strip(),
                },
            )

        return transcoded_path

    def _patch_speechbrain_fetch_for_windows(self) -> None:
        try:
            import speechbrain.pretrained.fetching as fetching_module
            import speechbrain.pretrained.interfaces as interfaces_module
            import speechbrain.utils.parameter_transfer as parameter_transfer_module
            from requests.exceptions import HTTPError
        except ImportError:
            return

        if getattr(fetching_module.fetch, "_smartmeeting_patched", False):
            return

        def fetch_with_copy_fallback(
            filename: str,
            source: Any,
            savedir: str = "./pretrained_model_checkpoints",
            overwrite: bool = False,
            save_filename: str | None = None,
            use_auth_token: bool = False,
            revision: str | None = None,
            cache_dir: str | Path | None = None,
            silent_local_fetch: bool = False,
        ) -> Any:
            if save_filename is None:
                save_filename = filename

            savedir_path = Path(savedir)
            savedir_path.mkdir(parents=True, exist_ok=True)
            fetch_from = None
            if isinstance(source, fetching_module.FetchSource):
                fetch_from, source = source

            sourcefile = f"{source}/{filename}"
            destination = savedir_path / save_filename
            if destination.exists() and not overwrite:
                message = f"Fetch {filename}: Using existing file/symlink in {str(destination)}."
                fetching_module.logger.info(message)
                return destination

            if Path(source).is_dir() and fetch_from not in [
                fetching_module.FetchFrom.HUGGING_FACE,
                fetching_module.FetchFrom.URI,
            ]:
                sourcepath = Path(sourcefile).absolute()
                fetching_module._missing_ok_unlink(destination)
                self._link_or_copy_file(sourcepath=sourcepath, destination=destination)
                message = f"Destination {filename}: local file in {str(sourcepath)}."
                if not silent_local_fetch:
                    fetching_module.logger.info(message)
                return destination

            if (
                str(source).startswith("http:") or str(source).startswith("https:")
            ) or fetch_from is fetching_module.FetchFrom.URI:
                message = f"Fetch {filename}: Downloading from normal URL {str(sourcefile)}."
                fetching_module.logger.info(message)
                try:
                    fetching_module.urllib.request.urlretrieve(sourcefile, destination)
                except fetching_module.urllib.error.URLError as exc:
                    raise ValueError(
                        f"Interpreted {source} as web address, but could not download."
                    ) from exc
            else:
                message = f"Fetch {filename}: Delegating to Huggingface hub, source {str(source)}."
                fetching_module.logger.info(message)
                try:
                    fetched_file = fetching_module.huggingface_hub.hf_hub_download(
                        repo_id=source,
                        filename=filename,
                        use_auth_token=use_auth_token,
                        revision=revision,
                        cache_dir=cache_dir,
                    )
                    fetching_module.logger.info(f"HF fetch: {fetched_file}")
                except TypeError:
                    fetched_file = fetching_module.huggingface_hub.hf_hub_download(
                        repo_id=source,
                        filename=filename,
                        token=use_auth_token,
                        revision=revision,
                        cache_dir=cache_dir,
                    )
                    fetching_module.logger.info(f"HF fetch: {fetched_file}")
                except HTTPError as exc:
                    if "404 Client Error" in str(exc) or "Entry Not Found" in str(exc):
                        raise ValueError("File not found on HF hub") from exc
                    raise
                except Exception as exc:
                    if "404 Client Error" in str(exc) or "Entry Not Found" in str(exc):
                        raise ValueError("File not found on HF hub") from exc
                    raise

                sourcepath = Path(fetched_file).absolute()
                fetching_module._missing_ok_unlink(destination)
                self._link_or_copy_file(sourcepath=sourcepath, destination=destination)

            return destination

        fetch_with_copy_fallback._smartmeeting_patched = True  # type: ignore[attr-defined]
        fetching_module.fetch = fetch_with_copy_fallback
        interfaces_module.fetch = fetch_with_copy_fallback
        parameter_transfer_module.fetch = fetch_with_copy_fallback

    def _link_or_copy_file(self, sourcepath: Path, destination: Path) -> None:
        try:
            destination.symlink_to(sourcepath)
        except OSError:
            if destination.exists():
                destination.unlink()
            shutil.copy2(sourcepath, destination)

    def _patch_huggingface_hub_auth_compat(self) -> None:
        try:
            import huggingface_hub
        except ImportError:
            return

        if getattr(huggingface_hub.hf_hub_download, "_smartmeeting_patched", False):
            return

        original_hf_hub_download = huggingface_hub.hf_hub_download
        signature = inspect.signature(original_hf_hub_download)
        if "use_auth_token" in signature.parameters:
            return

        def hf_hub_download_compat(*args: Any, **kwargs: Any) -> Any:
            if "use_auth_token" in kwargs and "token" not in kwargs:
                kwargs["token"] = kwargs.pop("use_auth_token")
            else:
                kwargs.pop("use_auth_token", None)
            return original_hf_hub_download(*args, **kwargs)

        hf_hub_download_compat._smartmeeting_patched = True  # type: ignore[attr-defined]
        huggingface_hub.hf_hub_download = hf_hub_download_compat

    def _run_pipeline(self, pipeline: Any, audio_path: Path, options: DiarizationOptions | None) -> Any:
        pipeline_kwargs: dict[str, Any] = {}
        if options:
            if options.num_speakers is not None:
                pipeline_kwargs["num_speakers"] = options.num_speakers
            if options.min_speakers is not None:
                pipeline_kwargs["min_speakers"] = options.min_speakers
            if options.max_speakers is not None:
                pipeline_kwargs["max_speakers"] = options.max_speakers

        in_memory_exc: Exception | None = None
        try:
            waveform_input = self._build_in_memory_audio_input(audio_path)
            return pipeline(waveform_input, **pipeline_kwargs)
        except Exception as exc:
            in_memory_exc = exc

        try:
            return pipeline(str(audio_path), **pipeline_kwargs)
        except Exception as exc:
            details: dict[str, Any] = {"audio_path": str(audio_path), "reason": str(exc)}
            if in_memory_exc is not None:
                details["in_memory_reason"] = str(in_memory_exc)
            raise DiarizationProcessingError(
                code="DIARIZATION_MODEL_FAILED",
                message="speaker diarization pipeline execution failed",
                details=details,
            ) from exc

    def _build_in_memory_audio_input(self, audio_path: Path) -> dict[str, Any]:
        try:
            import soundfile as sf
            import torch
        except ImportError as exc:
            raise DiarizationProcessingError(
                code="DIARIZATION_DEPENDENCY_MISSING",
                message="soundfile and torch are required for in-memory diarization input",
                details={"reason": str(exc)},
            ) from exc

        waveform, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=True)
        # pyannote expects shape (channel, time)
        tensor = torch.from_numpy(waveform.T.copy())
        return {
            "waveform": tensor,
            "sample_rate": int(sample_rate),
        }

    def _build_speaker_segments(self, diarization_result: Any) -> list[SpeakerSegment]:
        annotation = self._extract_annotation(diarization_result)
        raw_segments: list[tuple[float, float, str]] = []
        for speech_turn, _, raw_speaker in annotation.itertracks(yield_label=True):
            start = round(float(speech_turn.start), 2)
            end = round(float(speech_turn.end), 2)
            if end <= start:
                continue

            speaker_label = str(raw_speaker).strip() if raw_speaker is not None else "UNKNOWN"
            raw_segments.append((start, end, speaker_label or "UNKNOWN"))

        if not raw_segments:
            raise DiarizationProcessingError(
                code="DIARIZATION_EMPTY_SEGMENTS",
                message="speaker diarization returned no valid speaker segments",
                details=None,
            )

        speaker_mapping: dict[str, str] = {}
        speaker_index = 1
        speaker_segments: list[SpeakerSegment] = []
        for start, end, raw_speaker in raw_segments:
            normalized_speaker = "UNKNOWN"
            if raw_speaker != "UNKNOWN":
                if raw_speaker not in speaker_mapping:
                    speaker_mapping[raw_speaker] = f"S{speaker_index}"
                    speaker_index += 1
                normalized_speaker = speaker_mapping[raw_speaker]

            speaker_segments.append(
                SpeakerSegment(
                    start=start,
                    end=end,
                    speaker=normalized_speaker,
                )
            )

        merged_segments = self._merge_adjacent_segments(speaker_segments)
        cleaned_segments = self._collapse_pseudo_speakers(merged_segments)
        return self._merge_adjacent_segments(cleaned_segments)

    def _extract_annotation(self, diarization_result: Any) -> Any:
        if hasattr(diarization_result, "itertracks"):
            return diarization_result

        for attr_name in ("speaker_diarization", "exclusive_speaker_diarization", "annotation"):
            candidate = getattr(diarization_result, attr_name, None)
            if candidate is not None and hasattr(candidate, "itertracks"):
                return candidate

        raise DiarizationProcessingError(
            code="DIARIZATION_MODEL_FAILED",
            message="speaker diarization output is not supported",
            details={
                "result_type": str(type(diarization_result)),
                "available_attrs": [name for name in dir(diarization_result) if not name.startswith("_")][:30],
            },
        )

    def _extract_meeting_id_from_path(self, audio_path: Path) -> str | None:
        for part in audio_path.parts:
            if part.startswith("mtg_"):
                return part

        return None

    def _load_local_auth_token(self) -> str | None:
        if not LOCAL_TOKEN_PATH.exists():
            return None

        token = LOCAL_TOKEN_PATH.read_text(encoding="utf-8").strip()
        return token or None

    def _merge_adjacent_segments(self, segments: list[SpeakerSegment]) -> list[SpeakerSegment]:
        if not segments:
            return []

        sorted_segments = sorted(segments, key=lambda segment: (segment.start, segment.end))
        merged_segments: list[SpeakerSegment] = [sorted_segments[0]]

        for current_segment in sorted_segments[1:]:
            last_segment = merged_segments[-1]
            if (
                current_segment.speaker == last_segment.speaker
                and current_segment.start - last_segment.end <= MERGE_GAP_SECONDS
            ):
                merged_segments[-1] = SpeakerSegment(
                    start=last_segment.start,
                    end=max(last_segment.end, current_segment.end),
                    speaker=last_segment.speaker,
                )
                continue

            merged_segments.append(current_segment)

        return merged_segments

    def _collapse_pseudo_speakers(self, segments: list[SpeakerSegment]) -> list[SpeakerSegment]:
        if len(segments) < 3:
            return segments

        speaker_stats: dict[str, dict[str, float]] = {}
        for segment in segments:
            if segment.speaker == "UNKNOWN":
                continue

            duration = segment.end - segment.start
            stats = speaker_stats.setdefault(segment.speaker, {"total_duration": 0.0, "count": 0.0})
            stats["total_duration"] += duration
            stats["count"] += 1.0

        pseudo_speakers = {
            speaker
            for speaker, stats in speaker_stats.items()
            if (
                stats["total_duration"] <= MIN_PSEUDO_SPEAKER_TOTAL_SECONDS
                and stats["count"] >= MIN_PSEUDO_SPEAKER_SEGMENT_COUNT
                and (stats["total_duration"] / stats["count"]) <= MAX_PSEUDO_SPEAKER_AVERAGE_SECONDS
            )
        }

        if not pseudo_speakers:
            return segments

        normalized_segments = list(segments)
        for index, segment in enumerate(normalized_segments):
            if segment.speaker not in pseudo_speakers:
                continue

            replacement_speaker = self._pick_replacement_speaker(normalized_segments, index, pseudo_speakers)
            if replacement_speaker is None:
                continue

            normalized_segments[index] = SpeakerSegment(
                start=segment.start,
                end=segment.end,
                speaker=replacement_speaker,
            )

        return normalized_segments

    def _pick_replacement_speaker(
        self,
        segments: list[SpeakerSegment],
        index: int,
        pseudo_speakers: set[str],
    ) -> str | None:
        previous_speaker = None
        next_speaker = None

        if index > 0:
            previous_candidate = segments[index - 1].speaker
            if previous_candidate not in pseudo_speakers and previous_candidate != "UNKNOWN":
                previous_speaker = previous_candidate

        if index + 1 < len(segments):
            next_candidate = segments[index + 1].speaker
            if next_candidate not in pseudo_speakers and next_candidate != "UNKNOWN":
                next_speaker = next_candidate

        if previous_speaker and next_speaker:
            previous_gap = segments[index].start - segments[index - 1].end
            next_gap = segments[index + 1].start - segments[index].end
            return previous_speaker if abs(previous_gap) <= abs(next_gap) else next_speaker

        return previous_speaker or next_speaker

    def _failed_response(
        self,
        meeting_id: str,
        code: str,
        message: str,
        details: dict[str, Any] | None,
    ) -> dict[str, Any]:
        response = DiarizationResponse(
            meeting_id=meeting_id,
            status="failed",
            data=None,
            error=DiarizationError(code=code, message=message, details=details),
        )
        return response.model_dump(mode="json")


class DiarizationProcessingError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def run_diarization(payload: dict[str, Any]) -> dict[str, Any]:
    return DiarizationModule().process(payload)
