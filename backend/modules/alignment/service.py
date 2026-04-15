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


ASSIGN_REASON_OVERLAP = "overlap"
ASSIGN_REASON_NEARBY = "nearby"
ASSIGN_REASON_CONTINUITY = "continuity"
ASSIGN_REASON_UNKNOWN = "unknown"


DEFAULT_ALIGNMENT_CONFIG: Dict[str, float] = {
    "epsilon_sec": 0.2,
    "min_overlap_sec": 0.15,
    "min_overlap_ratio": 0.25,
    "near_gap_sec": 0.3,
    "short_seg_sec": 1.0,
    "short_hole_fill_sec": 1.0,
    "short_seg_overlap_sec": 1.2,
    "short_seg_min_overlap_ratio": 0.15,
    "short_hole_text_len": 6.0,
    "merge_same_speaker_gap_sec": 0.2,
}


@dataclass
class AlignmentConfig:
    epsilon_sec: float
    min_overlap_sec: float
    min_overlap_ratio: float
    near_gap_sec: float
    short_seg_sec: float
    short_hole_fill_sec: float
    short_seg_overlap_sec: float
    short_seg_min_overlap_ratio: float
    short_hole_text_len: float
    merge_same_speaker_gap_sec: float


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

    include_assign_reason = False
    debug_config = payload.get("alignment_debug")
    if isinstance(debug_config, dict):
        include_assign_reason = bool(debug_config.get("include_assign_reason", False))

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
    aligned_transcript_internal = _align(asr_segments, shifted_speakers, config)
    _apply_short_hole_fill(aligned_transcript_internal, config)
    _fill_remaining_unknowns(aligned_transcript_internal, shifted_speakers)
    _compact_empty_text_segments(aligned_transcript_internal)
    _merge_adjacent_same_speaker_segments(aligned_transcript_internal, config)

    diagnostics = _compute_alignment_diagnostics(
        asr_segments=asr_segments,
        speaker_segments=shifted_speakers,
        aligned_transcript=aligned_transcript_internal,
        config=config,
    )

    aligned_transcript = _finalize_outputs(
        aligned_transcript_internal,
        include_assign_reason=include_assign_reason,
    )

    return {
        "meeting_id": meeting_id,
        "status": "completed",
        "data": {
            "aligned_transcript": aligned_transcript,
            "alignment_diagnostics": diagnostics,
        },
        "error": None,
    }


def compute_alignment_metrics(aligned_transcript: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    """Compute duration-first alignment metrics for quick quality checks."""
    stats = _duration_stats(aligned_transcript)
    return {
        "segment_count": float(stats["segment_count"]),
        "unknown_count": float(stats["unknown_count"]),
        "unknown_rate": round(stats["unknown_rate"], 6),
        "unknown_duration_sec": round(stats["unknown_duration_sec"], 6),
        "total_aligned_duration_sec": round(stats["total_aligned_duration_sec"], 6),
        "unknown_duration_rate": round(stats["unknown_duration_rate"], 6),
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
                assign_reason=ASSIGN_REASON_UNKNOWN,
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
                    assign_reason=ASSIGN_REASON_OVERLAP,
                )
            )
            last_non_unknown_speaker = chosen_speaker.speaker
            prev_output_end = seg.end
            continue

        fallback_speaker, fallback_reason = _fallback_speaker(
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
                assign_reason=fallback_reason,
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
        assign_reason = ASSIGN_REASON_OVERLAP if piece.speaker != "UNKNOWN" else ASSIGN_REASON_UNKNOWN
        outputs.append(
            _to_output(
                segment_id=f"{seg.segment_id}_{suffix}",
                start=piece.start,
                end=piece.end,
                speaker=piece.speaker,
                text=text_parts[idx],
                lang=seg.lang,
                assign_reason=assign_reason,
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
    min_overlap_ratio = _effective_min_overlap_ratio(seg.duration, config)

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
        if overlap >= config.min_overlap_sec and ratio >= min_overlap_ratio:
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
) -> Tuple[str, str]:
    nearest = _nearest_speaker(seg, speaker_segments)
    if nearest and nearest[1] <= config.near_gap_sec:
        return nearest[0].speaker, ASSIGN_REASON_NEARBY

    if seg.duration <= config.short_seg_sec and last_non_unknown_speaker is not None:
        previous = _previous_speaker(seg.start, speaker_segments)
        next_item = _next_speaker(seg.end, speaker_segments)
        if previous and next_item and previous.speaker == next_item.speaker:
            return previous.speaker, ASSIGN_REASON_CONTINUITY

        if prev_output_end is not None and abs(seg.start - prev_output_end) <= config.near_gap_sec:
            return last_non_unknown_speaker, ASSIGN_REASON_CONTINUITY

    return "UNKNOWN", ASSIGN_REASON_UNKNOWN


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


def _apply_short_hole_fill(aligned_transcript: List[Dict[str, Any]], config: AlignmentConfig) -> None:
    if len(aligned_transcript) < 3:
        return

    for idx in range(1, len(aligned_transcript) - 1):
        current = aligned_transcript[idx]
        if current.get("speaker") != "UNKNOWN":
            continue

        duration = max(0.0, float(current["end"]) - float(current["start"]))
        if duration <= 0 or duration > config.short_hole_fill_sec:
            continue
        if _normalized_text_length(current.get("text", "")) > int(config.short_hole_text_len):
            continue

        prev_item = aligned_transcript[idx - 1]
        next_item = aligned_transcript[idx + 1]
        prev_speaker = prev_item.get("speaker")
        next_speaker = next_item.get("speaker")

        if prev_speaker in (None, "UNKNOWN"):
            continue
        if next_speaker in (None, "UNKNOWN"):
            continue
        if prev_speaker != next_speaker:
            continue

        left_gap = abs(float(current["start"]) - float(prev_item["end"]))
        right_gap = abs(float(next_item["start"]) - float(current["end"]))
        if left_gap <= config.epsilon_sec and right_gap <= config.epsilon_sec:
            current["speaker"] = prev_speaker
            current["assign_reason"] = ASSIGN_REASON_CONTINUITY


def _fill_remaining_unknowns(
    aligned_transcript: List[Dict[str, Any]],
    speaker_segments: Sequence[SpeakerSegment],
) -> None:
    if not aligned_transcript or not speaker_segments:
        return

    fallback_speaker = _majority_speaker(aligned_transcript) or speaker_segments[0].speaker

    for idx, current in enumerate(aligned_transcript):
        if current.get("speaker") != "UNKNOWN":
            continue

        prev_item = _nearest_known_output(aligned_transcript, idx, step=-1)
        next_item = _nearest_known_output(aligned_transcript, idx, step=1)
        chosen_speaker: Optional[str] = None
        chosen_reason = ASSIGN_REASON_CONTINUITY

        if prev_item and next_item:
            prev_speaker = str(prev_item.get("speaker"))
            next_speaker = str(next_item.get("speaker"))
            if prev_speaker == next_speaker:
                chosen_speaker = prev_speaker
            else:
                left_gap = abs(float(current["start"]) - float(prev_item["end"]))
                right_gap = abs(float(next_item["start"]) - float(current["end"]))
                chosen_speaker = prev_speaker if left_gap <= right_gap else next_speaker
        elif prev_item:
            chosen_speaker = str(prev_item.get("speaker"))
        elif next_item:
            chosen_speaker = str(next_item.get("speaker"))
        else:
            nearest = _nearest_speaker(
                ASRSegment(
                    segment_id=str(current.get("segment_id", "tmp")),
                    start=float(current["start"]),
                    end=float(current["end"]),
                    text=str(current.get("text", "")),
                    lang=str(current.get("lang", "unknown")),
                ),
                speaker_segments,
            )
            if nearest:
                chosen_speaker = nearest[0].speaker
                chosen_reason = ASSIGN_REASON_NEARBY

        current["speaker"] = chosen_speaker or fallback_speaker
        current["assign_reason"] = chosen_reason


def _compact_empty_text_segments(aligned_transcript: List[Dict[str, Any]]) -> None:
    if len(aligned_transcript) <= 1:
        return

    idx = 0
    while idx < len(aligned_transcript):
        current = aligned_transcript[idx]
        if _normalized_text_length(current.get("text", "")) > 0:
            idx += 1
            continue

        prev_item = aligned_transcript[idx - 1] if idx > 0 else None
        next_item = aligned_transcript[idx + 1] if idx + 1 < len(aligned_transcript) else None

        target = _pick_absorb_target(current, prev_item, next_item)
        if target is prev_item and prev_item is not None:
            prev_item["end"] = max(float(prev_item["end"]), float(current["end"]))
            aligned_transcript.pop(idx)
            continue
        if target is next_item and next_item is not None:
            next_item["start"] = min(float(next_item["start"]), float(current["start"]))
            aligned_transcript.pop(idx)
            continue

        idx += 1


def _merge_adjacent_same_speaker_segments(
    aligned_transcript: List[Dict[str, Any]],
    config: AlignmentConfig,
) -> None:
    if len(aligned_transcript) <= 1:
        return

    merged: List[Dict[str, Any]] = [dict(aligned_transcript[0])]
    for current in aligned_transcript[1:]:
        prev = merged[-1]
        if _can_merge_same_speaker(prev, current, config):
            prev["end"] = max(float(prev["end"]), float(current["end"]))
            prev["text"] = _join_segment_text(
                prev.get("text", ""),
                current.get("text", ""),
                prev.get("lang", current.get("lang", "unknown")),
            )
            if prev.get("assign_reason") != current.get("assign_reason"):
                prev["assign_reason"] = ASSIGN_REASON_CONTINUITY
            continue
        merged.append(dict(current))

    aligned_transcript[:] = merged


def _can_merge_same_speaker(
    prev: Dict[str, Any],
    current: Dict[str, Any],
    config: AlignmentConfig,
) -> bool:
    if str(prev.get("speaker")) != str(current.get("speaker")):
        return False

    prev_end = _safe_float(prev.get("end"))
    cur_start = _safe_float(current.get("start"))
    if prev_end is None or cur_start is None:
        return False

    return cur_start <= prev_end + config.merge_same_speaker_gap_sec


def _join_segment_text(left: Any, right: Any, lang: Any) -> str:
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    if not left_text:
        return right_text
    if not right_text:
        return left_text

    normalized_lang = str(lang or "").lower()
    if normalized_lang.startswith(("zh", "yue", "ja", "ko")):
        return f"{left_text}{right_text}"
    return f"{left_text} {right_text}"


def _pick_absorb_target(
    current: Dict[str, Any],
    prev_item: Optional[Dict[str, Any]],
    next_item: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    current_speaker = current.get("speaker")
    if prev_item and prev_item.get("speaker") == current_speaker:
        return prev_item
    if next_item and next_item.get("speaker") == current_speaker:
        return next_item
    if prev_item is not None:
        return prev_item
    if next_item is not None:
        return next_item
    return None


def _nearest_known_output(
    aligned_transcript: Sequence[Dict[str, Any]],
    index: int,
    step: int,
) -> Optional[Dict[str, Any]]:
    cursor = index + step
    while 0 <= cursor < len(aligned_transcript):
        candidate = aligned_transcript[cursor]
        if candidate.get("speaker") not in (None, "UNKNOWN"):
            return candidate
        cursor += step
    return None


def _majority_speaker(aligned_transcript: Sequence[Dict[str, Any]]) -> Optional[str]:
    durations: Dict[str, float] = {}
    for seg in aligned_transcript:
        speaker = seg.get("speaker")
        if speaker in (None, "UNKNOWN"):
            continue
        start = _safe_float(seg.get("start"))
        end = _safe_float(seg.get("end"))
        if start is None or end is None or end <= start:
            continue
        durations[str(speaker)] = durations.get(str(speaker), 0.0) + (end - start)

    if not durations:
        return None
    return max(durations.items(), key=lambda item: item[1])[0]


def _effective_min_overlap_ratio(seg_duration: float, config: AlignmentConfig) -> float:
    base_ratio = max(0.0, min(1.0, config.min_overlap_ratio))
    short_ratio = max(0.0, min(1.0, config.short_seg_min_overlap_ratio))
    if seg_duration <= config.short_seg_overlap_sec:
        return min(base_ratio, short_ratio)
    return base_ratio


def _normalized_text_length(text: Any) -> int:
    safe_text = str(text or "")
    return len("".join(safe_text.split()))


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


def _compute_alignment_diagnostics(
    asr_segments: Sequence[ASRSegment],
    speaker_segments: Sequence[SpeakerSegment],
    aligned_transcript: Sequence[Dict[str, Any]],
    config: AlignmentConfig,
) -> Dict[str, float]:
    stats = _duration_stats(aligned_transcript)
    coverage_ratio, gap_count = _compute_speaker_coverage_and_gaps(
        asr_segments,
        speaker_segments,
        config.epsilon_sec,
    )

    return {
        "unknown_duration_rate": round(stats["unknown_duration_rate"], 6),
        "speaker_coverage_ratio": round(coverage_ratio, 6),
        "gap_count": float(gap_count),
        "unknown_duration_sec": round(stats["unknown_duration_sec"], 6),
        "total_aligned_duration_sec": round(stats["total_aligned_duration_sec"], 6),
        "segment_count": float(stats["segment_count"]),
        "unknown_count": float(stats["unknown_count"]),
    }


def _compute_speaker_coverage_and_gaps(
    asr_segments: Sequence[ASRSegment],
    speaker_segments: Sequence[SpeakerSegment],
    epsilon_sec: float,
) -> Tuple[float, int]:
    asr_intervals = _merge_intervals([(seg.start, seg.end) for seg in asr_segments])
    speaker_intervals = _merge_intervals([(seg.start, seg.end) for seg in speaker_segments])

    asr_total_duration = sum(max(0.0, end - start) for start, end in asr_intervals)
    if asr_total_duration <= 0:
        return 0.0, 0

    covered_duration = 0.0
    for asr_start, asr_end in asr_intervals:
        for spk_start, spk_end in speaker_intervals:
            if spk_end <= asr_start:
                continue
            if spk_start >= asr_end:
                break
            covered_duration += _interval_overlap(asr_start, asr_end, spk_start, spk_end)

    gap_count = 0
    for asr_start, asr_end in asr_intervals:
        cursor = asr_start
        for spk_start, spk_end in speaker_intervals:
            if spk_end <= cursor:
                continue
            if spk_start >= asr_end:
                break

            if spk_start > cursor:
                gap = min(spk_start, asr_end) - cursor
                if gap > epsilon_sec:
                    gap_count += 1

            cursor = max(cursor, min(asr_end, spk_end))
            if cursor >= asr_end:
                break

        if cursor < asr_end:
            tail_gap = asr_end - cursor
            if tail_gap > epsilon_sec:
                gap_count += 1

    coverage_ratio = max(0.0, min(1.0, covered_duration / asr_total_duration))
    return coverage_ratio, gap_count


def _duration_stats(aligned_transcript: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    segment_count = len(aligned_transcript)
    unknown_count = 0
    total_duration = 0.0
    unknown_duration = 0.0

    for seg in aligned_transcript:
        start = _safe_float(seg.get("start"))
        end = _safe_float(seg.get("end"))
        if start is None or end is None:
            continue

        duration = max(0.0, end - start)
        total_duration += duration
        if seg.get("speaker") == "UNKNOWN":
            unknown_count += 1
            unknown_duration += duration

    unknown_rate = (unknown_count / segment_count) if segment_count > 0 else 0.0
    unknown_duration_rate = (unknown_duration / total_duration) if total_duration > 0 else 0.0

    return {
        "segment_count": float(segment_count),
        "unknown_count": float(unknown_count),
        "unknown_rate": unknown_rate,
        "total_aligned_duration_sec": total_duration,
        "unknown_duration_sec": unknown_duration,
        "unknown_duration_rate": unknown_duration_rate,
    }


def _merge_intervals(intervals: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    valid = [(start, end) for start, end in intervals if end > start]
    if not valid:
        return []

    valid.sort(key=lambda item: (item[0], item[1]))
    merged: List[Tuple[float, float]] = []
    cur_start, cur_end = valid[0]

    for start, end in valid[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))
    return merged


def _finalize_outputs(
    aligned_transcript_internal: Sequence[Dict[str, Any]],
    include_assign_reason: bool,
) -> List[Dict[str, Any]]:
    finalized: List[Dict[str, Any]] = []
    for item in aligned_transcript_internal:
        row = dict(item)
        if not include_assign_reason:
            row.pop("assign_reason", None)
        finalized.append(row)
    return finalized


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
    assign_reason: str,
) -> Dict[str, Any]:
    return {
        "segment_id": segment_id,
        "start": round(start, 3),
        "end": round(end, 3),
        "speaker": speaker or "UNKNOWN",
        "text": text,
        "lang": lang,
        "assign_reason": assign_reason,
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
