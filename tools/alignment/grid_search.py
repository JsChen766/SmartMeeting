#!/usr/bin/env python3
"""Grid search utility for alignment thresholds.

Usage:
  python tools/alignment/grid_search.py \
    --asr-json data/processed/mtg_xxx/asr_segments.json \
    --speaker-json data/processed/mtg_xxx/speaker_segments.json \
    [--reference-json data/processed/mtg_xxx/reference.json] \
    [--output-path data/processed/mtg_xxx/grid_results.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import product
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.alignment.service import compute_assignment_accuracy, run_alignment


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grid search for alignment thresholds.")
    parser.add_argument("--meeting-id", default="grid_search_meeting", help="Meeting id for alignment payload")
    parser.add_argument("--asr-json", required=True, help="Path to ASR JSON")
    parser.add_argument("--speaker-json", required=True, help="Path to speaker JSON")
    parser.add_argument("--reference-json", default=None, help="Optional speaker-labeled reference JSON")
    parser.add_argument(
        "--output-path",
        default="grid_results.json",
        help="Result output JSON path",
    )
    return parser.parse_args()


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_list(payload: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    if isinstance(payload.get(key), list):
        return payload[key]
    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return data[key]
    raise ValueError(f"Cannot find list field '{key}' in payload")


def _extract_reference_segments(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("reference_segments", "aligned_transcript", "speaker_segments"):
        try:
            return _extract_list(payload, key)
        except ValueError:
            continue
    raise ValueError("Cannot find reference segments in reference JSON")


def _score_without_reference(row: Dict[str, Any]) -> tuple:
    return (row["unknown_duration_rate"], row["unknown_count"])


def _score_with_reference(row: Dict[str, Any]) -> tuple:
    return (-row["assignment_accuracy"], row["unknown_duration_rate"], row["unknown_count"])


def main() -> None:
    args = parse_args()
    asr_path = Path(args.asr_json)
    speaker_path = Path(args.speaker_json)
    output_path = Path(args.output_path)

    asr_payload = _load_json(asr_path)
    speaker_payload = _load_json(speaker_path)

    asr_segments = _extract_list(asr_payload, "asr_segments")
    speaker_segments = _extract_list(speaker_payload, "speaker_segments")

    reference_segments: Optional[List[Dict[str, Any]]] = None
    if args.reference_json:
        reference_payload = _load_json(Path(args.reference_json))
        reference_segments = _extract_reference_segments(reference_payload)

    near_gap_values = [0.2, 0.3, 0.4, 0.5]
    min_overlap_values = [0.1, 0.15, 0.2]
    min_overlap_ratio_values = [0.15, 0.25, 0.35]

    rows: List[Dict[str, Any]] = []

    for near_gap_sec, min_overlap_sec, min_overlap_ratio in product(
        near_gap_values,
        min_overlap_values,
        min_overlap_ratio_values,
    ):
        alignment_config = {
            "near_gap_sec": near_gap_sec,
            "min_overlap_sec": min_overlap_sec,
            "min_overlap_ratio": min_overlap_ratio,
        }
        payload = {
            "meeting_id": args.meeting_id,
            "asr_segments": asr_segments,
            "speaker_segments": speaker_segments,
            "alignment_config": alignment_config,
        }
        result = run_alignment(payload)
        diagnostics = result.get("data", {}).get("alignment_diagnostics", {})

        row: Dict[str, Any] = {
            "config": alignment_config,
            "unknown_duration_rate": float(diagnostics.get("unknown_duration_rate", 1.0)),
            "unknown_count": float(diagnostics.get("unknown_count", 0.0)),
            "speaker_coverage_ratio": float(diagnostics.get("speaker_coverage_ratio", 0.0)),
            "gap_count": float(diagnostics.get("gap_count", 0.0)),
        }

        if reference_segments is not None:
            aligned = result.get("data", {}).get("aligned_transcript", [])
            acc = compute_assignment_accuracy(aligned, reference_segments)
            row["assignment_accuracy"] = float(acc.get("assignment_accuracy", 0.0))

        rows.append(row)

    if reference_segments is None:
        rows.sort(key=_score_without_reference)
    else:
        rows.sort(key=_score_with_reference)

    top_k = rows[:5]
    best = rows[0] if rows else None

    output = {
        "meeting_id": args.meeting_id,
        "searched": {
            "near_gap_sec": near_gap_values,
            "min_overlap_sec": min_overlap_values,
            "min_overlap_ratio": min_overlap_ratio_values,
            "count": len(rows),
        },
        "with_reference": reference_segments is not None,
        "best": best,
        "top_k": top_k,
        "grid_results": rows,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Grid search completed")
    print(f"Output: {output_path}")
    if best:
        print("Best config:", json.dumps(best["config"], ensure_ascii=False))
        if "assignment_accuracy" in best:
            print(
                "Best scores:",
                f"assignment_accuracy={best['assignment_accuracy']:.6f}",
                f"unknown_duration_rate={best['unknown_duration_rate']:.6f}",
            )
        else:
            print(
                "Best scores:",
                f"unknown_duration_rate={best['unknown_duration_rate']:.6f}",
                f"unknown_count={best['unknown_count']:.0f}",
            )


if __name__ == "__main__":
    main()
