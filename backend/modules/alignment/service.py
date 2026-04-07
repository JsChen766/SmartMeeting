"""Alignment module service.

This module merges ASR segments and speaker segments by timestamp overlap.
It follows docs/modules/alignment_io.md and docs/modules/module_contracts.md.
"""

from __future__ import annotations

import math
import string
from dataclasses import dataclass
from statistics import median
from typing import Any, Dict, List, Optional, Sequence, Tuple


DEFAULT_ALIGNMENT_CONFIG: Dict[str, float] = {
    "epsilon_sec": 0.2,
    "min_overlap_sec": 0.15,
    "min_overlap_ratio": 0.25,
    "near_gap_sec": 0.3,
    "short_seg_sec": 1.0,
}


@dataclass
class AlignmentConfig:
    epsilon_sec: float
    min_overlap_sec: float
    min_overlap_ratio: float
    near_gap_sec: float
    short_seg_sec: float


@dataclass
class ASRSegment:
    segment_id: str
    start: float
    end: float
    text: str
    lang: str

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class SpeakerSegment:
    start: float
    end: float
    speaker: str

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2.0


@dataclass
class Piece:
    start: float
    end: float
    speaker: str
    method: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def run_alignment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point for the alignment module."""
    meeting_id = payload.get("meeting_id")
    if not meeting_id:
        return _failure(
            meeting_id=None,
            code="ALIGNMENT_INVALID_INPUT",
            message="missing meeting_id",
            details={"required": ["meeting_id", "asr_segments", "speaker_segments"]},
        )

    if not isinstance(payload.get("asr_segments"), list):
        return _failure(
            meeting_id=meeting_id,
            code="ALIGNMENT_INVALID_INPUT",
            message="asr_segments must be a list",
            details={"field": "asr_segments"},
        )
    if not isinstance(payload.get("speaker_segments"), list):
        return _failure(
            meeting_id=meeting_id,
            code="ALIGNMENT_INVALID_INPUT",
            message="speaker_segments must be a list",
            details={"field": "speaker_segments"},
        )

    config = _build_config(payload.get("alignment_config"))
    asr_segments = _normalize_asr_segments(payload["asr_segments"])
    speaker_segments = _normalize_speaker_segments(payload["speaker_segments"])

    if not asr_segments:
        return _failure(
            meeting_id=meeting_id,
            code="ALIGNMENT_ASR_SEGMENTS_EMPTY",
            message="no valid asr segments after normalization",
        )

    shifted_speakers = _apply_global_offset(asr_segments, speaker_segments, config)
    aligned_transcript = _align(asr_segments, shifted_speakers, config)

    return {
        "meeting_id": meeting_id,
        "status": "completed",
        "data": {"aligned_transcript": aligned_transcript},
        "error": None,
    }


def compute_alignment_metrics(aligned_transcript: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    """Compute alignment-level metrics for quick quality checks."""
    total = len(aligned_transcript)
    unknown = sum(1 for seg in aligned_transcript if seg.get("speaker") == "UNKNOWN")
    unknown_rate = (unknown / total) if total > 0 else 0.0
    return {
        "segment_count": float(total),
        "unknown_count": float(unknown),
        "unknown_rate": round(unknown_rate, 6),
    }


def compute_assignment_accuracy(
    predicted_segments: Sequence[Dict[str, Any]],
    reference_segments: Sequence[Dict[str, Any]],
) -> Dict[str, float]:
    """Compute duration-weighted assignment accuracy against reference labels."""
    evaluable_duration = 0.0
    correct_duration = 0.0

    for pred in predicted_segments:
        pred_speaker = pred.get("speaker")
        if pred_speaker in (None, "UNKNOWN"):
            continue

        p_start = float(pred["start"])
        p_end = float(pred["end"])
        duration = max(0.0, p_end - p_start)
        if duration <= 0:
            continue

        best_match: Optional[Dict[str, Any]] = None
        best_overlap = 0.0
        for ref in reference_segments:
            overlap = _interval_overlap(
                p_start,
                p_end,
                float(ref["start"]),
                float(ref["end"]),
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = ref

        if best_match is None or best_overlap <= 0:
            continue

        evaluable_duration += duration
        if best_match.get("speaker") == pred_speaker:
            correct_duration += best_overlap

    accuracy = (correct_duration / evaluable_duration) if evaluable_duration > 0 else 0.0
    return {
        "assignment_accuracy": round(accuracy, 6),
        "correct_duration": round(correct_duration, 6),
        "evaluable_duration": round(evaluable_duration, 6),
    }


def _align(
    asr_segments: Sequence[ASRSegment],
    speaker_segments: Sequence[SpeakerSegment],
    config: AlignmentConfig,
) -> List[Dict[str, Any]]:
    if not speaker_segments:
        return [
            _to_output(
                segment_id=seg.segment_id,
                start=seg.start,
                end=seg.end,
                speaker="UNKNOWN",
                text=seg.text,
                lang=seg.lang,
            )
            for seg in asr_segments
        ]

    output: List[Dict[str, Any]] = []
    last_non_unknown_speaker: Optional[str] = None
    prev_output_end: Optional[float] = None

    for seg in asr_segments:
        split_segments = _maybe_split_segment(seg, speaker_segments)
        if split_segments:
            segment_outputs = _build_split_outputs(seg, split_segments)
            output.extend(segment_outputs)
            for item in segment_outputs:
                if item["speaker"] != "UNKNOWN":
                    last_non_unknown_speaker = item["speaker"]
                prev_output_end = item["end"]
            continue

        chosen_speaker = _pick_best_overlap_speaker(seg, speaker_segments, config)
        if chosen_speaker:
            output.append(
                _to_output(
                    segment_id=seg.segment_id,
                    start=seg.start,
                    end=seg.end,
                    speaker=chosen_speaker.speaker,
                    text=seg.text,
                    lang=seg.lang,
                )
            )
            last_non_unknown_speaker = chosen_speaker.speaker
            prev_output_end = seg.end
            continue

        fallback_speaker = _fallback_speaker(
            seg=seg,
            speaker_segments=speaker_segments,
            config=config,
            last_non_unknown_speaker=last_non_unknown_speaker,
            prev_output_end=prev_output_end,
        )
        output.append(
            _to_output(
                segment_id=seg.segment_id,
                start=seg.start,
                end=seg.end,
                speaker=fallback_speaker,
                text=seg.text,
                lang=seg.lang,
            )
        )
        if fallback_speaker != "UNKNOWN":
            last_non_unknown_speaker = fallback_speaker
        prev_output_end = seg.end

    return output


def _maybe_split_segment(
    seg: ASRSegment,
    speaker_segments: Sequence[SpeakerSegment],
) -> List[Piece]:
    intersections: List[Piece] = []
    for spk in speaker_segments:
        overlap = _interval_overlap(seg.start, seg.end, spk.start, spk.end)
        if overlap <= 0:
            continue
        start = max(seg.start, spk.start)
        end = min(seg.end, spk.end)
        intersections.append(Piece(start=start, end=end, speaker=spk.speaker, method="split"))

    intersections.sort(key=lambda item: (item.start, item.end))
    if len(intersections) < 2:
        return []

    pieces: List[Piece] = []
    cursor = seg.start
    for item in intersections:
        if item.start > cursor:
            pieces.append(Piece(start=cursor, end=item.start, speaker="UNKNOWN", method="split"))
        clipped_start = max(cursor, item.start)
        clipped_end = min(seg.end, item.end)
        if clipped_end > clipped_start:
            pieces.append(
                Piece(
                    start=clipped_start,
                    end=clipped_end,
                    speaker=item.speaker,
                    method="split",
                )
            )
            cursor = clipped_end
    if cursor < seg.end:
        pieces.append(Piece(start=cursor, end=seg.end, speaker="UNKNOWN", method="split"))

    merged = _merge_adjacent_pieces(pieces)
    return [piece for piece in merged if piece.duration > 0]


def _build_split_outputs(seg: ASRSegment, pieces: Sequence[Piece]) -> List[Dict[str, Any]]:
    text_parts = _split_text_by_duration(seg.text, pieces)
    outputs: List[Dict[str, Any]] = []
    for idx, piece in enumerate(pieces):
        suffix = _alphabet_suffix(idx)
        outputs.append(
            _to_output(
                segment_id=f"{seg.segment_id}_{suffix}",
                start=piece.start,
                end=piece.end,
                speaker=piece.speaker,
                text=text_parts[idx],
                lang=seg.lang,
            )
        )
    return outputs


def _pick_best_overlap_speaker(
    seg: ASRSegment,
    speaker_segments: Sequence[SpeakerSegment],
    config: AlignmentConfig,
) -> Optional[SpeakerSegment]:
    best_candidate: Optional[SpeakerSegment] = None
    best_overlap = 0.0

    for spk in speaker_segments:
        overlap = _interval_overlap(
            seg.start - config.epsilon_sec,
            seg.end + config.epsilon_sec,
            spk.start,
            spk.end,
        )
        if overlap <= 0:
            continue
        ratio = overlap / seg.duration if seg.duration > 0 else 0.0
        if overlap >= config.min_overlap_sec and ratio >= config.min_overlap_ratio:
            if overlap > best_overlap:
                best_overlap = overlap
                best_candidate = spk

    return best_candidate


def _fallback_speaker(
    seg: ASRSegment,
    speaker_segments: Sequence[SpeakerSegment],
    config: AlignmentConfig,
    last_non_unknown_speaker: Optional[str],
    prev_output_end: Optional[float],
) -> str:
    nearest = _nearest_speaker(seg, speaker_segments)
    if nearest and nearest[1] <= config.near_gap_sec:
        return nearest[0].speaker

    if seg.duration <= config.short_seg_sec and last_non_unknown_speaker is not None:
        previous = _previous_speaker(seg.start, speaker_segments)
        next_item = _next_speaker(seg.end, speaker_segments)
        if previous and next_item and previous.speaker == next_item.speaker:
            return previous.speaker

        if prev_output_end is not None and abs(seg.start - prev_output_end) <= config.near_gap_sec:
            return last_non_unknown_speaker

    return "UNKNOWN"


def _nearest_speaker(
    seg: ASRSegment,
    speaker_segments: Sequence[SpeakerSegment],
) -> Optional[Tuple[SpeakerSegment, float]]:
    best: Optional[Tuple[SpeakerSegment, float]] = None
    for spk in speaker_segments:
        gap = _interval_gap(seg.start, seg.end, spk.start, spk.end)
        if best is None or gap < best[1]:
            best = (spk, gap)
    return best


def _previous_speaker(start: float, speakers: Sequence[SpeakerSegment]) -> Optional[SpeakerSegment]:
    candidates = [spk for spk in speakers if spk.end <= start]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.end, reverse=True)
    return candidates[0]


def _next_speaker(end: float, speakers: Sequence[SpeakerSegment]) -> Optional[SpeakerSegment]:
    candidates = [spk for spk in speakers if spk.start >= end]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.start)
    return candidates[0]


def _apply_global_offset(
    asr_segments: Sequence[ASRSegment],
    speaker_segments: Sequence[SpeakerSegment],
    config: AlignmentConfig,
) -> List[SpeakerSegment]:
    if not speaker_segments:
        return []

    offsets: List[float] = []
    for asr in asr_segments:
        best_overlap = 0.0
        best_speaker: Optional[SpeakerSegment] = None
        for spk in speaker_segments:
            overlap = _interval_overlap(
                asr.start - 1.0,
                asr.end + 1.0,
                spk.start,
                spk.end,
            )
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = spk
        if best_speaker is None:
            continue
        ratio = best_overlap / asr.duration if asr.duration > 0 else 0.0
        if ratio >= 0.5:
            offsets.append(best_speaker.midpoint - ((asr.start + asr.end) / 2.0))

    if len(offsets) < 2:
        return list(speaker_segments)

    offset = -median(offsets)
    if abs(offset) < config.epsilon_sec:
        return list(speaker_segments)

    if abs(offset) > 2.0:
        return list(speaker_segments)

    adjusted: List[SpeakerSegment] = []
    for spk in speaker_segments:
        start = max(0.0, spk.start + offset)
        end = max(start, spk.end + offset)
        if end <= start:
            continue
        adjusted.append(SpeakerSegment(start=start, end=end, speaker=spk.speaker))
    adjusted.sort(key=lambda item: (item.start, item.end))
    return adjusted


def _normalize_asr_segments(raw_segments: Sequence[Dict[str, Any]]) -> List[ASRSegment]:
    normalized: List[ASRSegment] = []
    for idx, raw in enumerate(raw_segments):
        start = _safe_float(raw.get("start"))
        end = _safe_float(raw.get("end"))
        if start is None or end is None or end <= start:
            continue

        segment_id = str(raw.get("segment_id") or f"seg_{idx + 1:04d}")
        text = str(raw.get("text") or "")
        lang = str(raw.get("lang") or "unknown")
        normalized.append(
            ASRSegment(
                segment_id=segment_id,
                start=round(start, 3),
                end=round(end, 3),
                text=text,
                lang=lang,
            )
        )
    normalized.sort(key=lambda item: (item.start, item.end))
    return normalized


def _normalize_speaker_segments(raw_segments: Sequence[Dict[str, Any]]) -> List[SpeakerSegment]:
    normalized: List[SpeakerSegment] = []
    for raw in raw_segments:
        start = _safe_float(raw.get("start"))
        end = _safe_float(raw.get("end"))
        if start is None or end is None or end <= start:
            continue

        speaker = str(raw.get("speaker") or "UNKNOWN")
        normalized.append(
            SpeakerSegment(
                start=round(start, 3),
                end=round(end, 3),
                speaker=speaker,
            )
        )
    normalized.sort(key=lambda item: (item.start, item.end))
    return normalized


def _split_text_by_duration(text: str, pieces: Sequence[Piece]) -> List[str]:
    if not pieces:
        return []
    if len(pieces) == 1:
        return [text]

    safe_text = text or ""
    total_chars = len(safe_text)
    if total_chars == 0:
        return ["" for _ in pieces]

    durations = [max(0.0, piece.duration) for piece in pieces]
    total_duration = sum(durations)
    if total_duration <= 0:
        equal_len = max(1, math.floor(total_chars / len(pieces)))
        parts = []
        cursor = 0
        for idx in range(len(pieces)):
            if idx == len(pieces) - 1:
                parts.append(safe_text[cursor:])
            else:
                parts.append(safe_text[cursor : cursor + equal_len])
                cursor += equal_len
        return parts

    raw_lengths = [(duration / total_duration) * total_chars for duration in durations]
    floors = [int(math.floor(length)) for length in raw_lengths]
    remainders = [raw_lengths[idx] - floors[idx] for idx in range(len(raw_lengths))]
    allocated = list(floors)
    remaining = total_chars - sum(allocated)

    order = sorted(range(len(remainders)), key=lambda i: remainders[i], reverse=True)
    for idx in order:
        if remaining <= 0:
            break
        allocated[idx] += 1
        remaining -= 1

    boundaries = [0]
    for size in allocated:
        boundaries.append(boundaries[-1] + size)
    boundaries[-1] = total_chars

    parts: List[str] = []
    for idx in range(len(pieces)):
        left = boundaries[idx]
        right = boundaries[idx + 1]
        parts.append(safe_text[left:right])
    return parts


def _merge_adjacent_pieces(pieces: Sequence[Piece]) -> List[Piece]:
    if not pieces:
        return []
    merged: List[Piece] = [pieces[0]]
    for piece in pieces[1:]:
        last = merged[-1]
        if piece.speaker == last.speaker and abs(piece.start - last.end) <= 1e-6:
            merged[-1] = Piece(
                start=last.start,
                end=piece.end,
                speaker=last.speaker,
                method=last.method,
            )
        else:
            merged.append(piece)
    return merged


def _build_config(raw_config: Any) -> AlignmentConfig:
    data = dict(DEFAULT_ALIGNMENT_CONFIG)
    if isinstance(raw_config, dict):
        for key in data:
            value = _safe_float(raw_config.get(key))
            if value is not None and value >= 0:
                data[key] = value
    return AlignmentConfig(**data)


def _alphabet_suffix(index: int) -> str:
    letters = string.ascii_lowercase
    result = ""
    i = index
    while True:
        result = letters[i % 26] + result
        i = (i // 26) - 1
        if i < 0:
            break
    return result


def _to_output(
    segment_id: str,
    start: float,
    end: float,
    speaker: str,
    text: str,
    lang: str,
) -> Dict[str, Any]:
    return {
        "segment_id": segment_id,
        "start": round(start, 3),
        "end": round(end, 3),
        "speaker": speaker or "UNKNOWN",
        "text": text,
        "lang": lang,
    }


def _failure(
    meeting_id: Optional[str],
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "meeting_id": meeting_id,
        "status": "failed",
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


def _interval_overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _interval_gap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    if _interval_overlap(start_a, end_a, start_b, end_b) > 0:
        return 0.0
    if end_a <= start_b:
        return start_b - end_a
    return start_a - end_b


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

