from __future__ import annotations

import unittest

from backend.modules.alignment.service import compute_alignment_metrics, run_alignment


class AlignmentServiceTest(unittest.TestCase):
    def test_compute_alignment_metrics_duration_first(self) -> None:
        aligned = [
            {"segment_id": "a", "start": 0.0, "end": 2.0, "speaker": "S1", "text": "", "lang": "zh"},
            {"segment_id": "b", "start": 2.0, "end": 3.0, "speaker": "UNKNOWN", "text": "", "lang": "zh"},
            {"segment_id": "c", "start": 3.0, "end": 3.5, "speaker": "UNKNOWN", "text": "", "lang": "zh"},
        ]

        metrics = compute_alignment_metrics(aligned)

        self.assertAlmostEqual(metrics["unknown_duration_rate"], 1.5 / 3.5, places=6)
        self.assertAlmostEqual(metrics["unknown_rate"], 2.0 / 3.0, places=6)
        self.assertEqual(metrics["segment_count"], 3.0)
        self.assertEqual(metrics["unknown_count"], 2.0)

    def test_alignment_diagnostics_coverage_and_gap_count(self) -> None:
        payload = {
            "meeting_id": "m1",
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 0.0, "end": 10.0, "text": "hello", "lang": "en"}
            ],
            "speaker_segments": [
                {"start": 1.0, "end": 3.0, "speaker": "S1"},
                {"start": 6.0, "end": 8.0, "speaker": "S2"},
            ],
        }

        result = run_alignment(payload)
        diagnostics = result["data"]["alignment_diagnostics"]

        self.assertAlmostEqual(diagnostics["speaker_coverage_ratio"], 0.4, places=6)
        self.assertEqual(diagnostics["gap_count"], 3.0)
        self.assertAlmostEqual(diagnostics["unknown_duration_rate"], 0.0, places=6)

    def test_assign_reason_hidden_by_default(self) -> None:
        payload = {
            "meeting_id": "m2",
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 0.0, "end": 2.0, "text": "hello", "lang": "en"}
            ],
            "speaker_segments": [{"start": 0.0, "end": 2.0, "speaker": "S1"}],
        }

        result = run_alignment(payload)
        segment = result["data"]["aligned_transcript"][0]

        self.assertNotIn("assign_reason", segment)

    def test_assign_reason_debug_overlap_and_nearby(self) -> None:
        overlap_payload = {
            "meeting_id": "m3",
            "alignment_debug": {"include_assign_reason": True},
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 0.0, "end": 2.0, "text": "a", "lang": "en"}
            ],
            "speaker_segments": [{"start": 0.0, "end": 2.0, "speaker": "S1"}],
        }
        nearby_payload = {
            "meeting_id": "m4",
            "alignment_debug": {"include_assign_reason": True},
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 2.1, "end": 2.2, "text": "b", "lang": "en"}
            ],
            "speaker_segments": [{"start": 0.0, "end": 2.0, "speaker": "S1"}],
        }
        overlap_seg = run_alignment(overlap_payload)["data"]["aligned_transcript"][0]
        nearby_seg = run_alignment(nearby_payload)["data"]["aligned_transcript"][0]

        self.assertEqual(overlap_seg["assign_reason"], "overlap")
        self.assertEqual(nearby_seg["assign_reason"], "nearby")

    def test_short_hole_fill_turns_unknown_into_continuity(self) -> None:
        payload = {
            "meeting_id": "m6",
            "alignment_debug": {"include_assign_reason": True},
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 0.0, "end": 3.0, "text": "abcdef", "lang": "en"}
            ],
            "speaker_segments": [
                {"start": 0.0, "end": 1.2, "speaker": "S1"},
                {"start": 1.5, "end": 3.0, "speaker": "S1"},
            ],
        }

        result = run_alignment(payload)
        segments = result["data"]["aligned_transcript"]
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["speaker"], "S1")
        self.assertAlmostEqual(segments[0]["start"], 0.0, places=6)
        self.assertAlmostEqual(segments[0]["end"], 3.0, places=6)

    def test_short_segment_uses_dynamic_overlap_ratio(self) -> None:
        payload = {
            "meeting_id": "m7",
            "alignment_debug": {"include_assign_reason": True},
            "alignment_config": {"near_gap_sec": 0.0},
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 0.0, "end": 1.0, "text": "短句", "lang": "zh"}
            ],
            "speaker_segments": [{"start": 0.95, "end": 1.1, "speaker": "S1"}],
        }

        result = run_alignment(payload)
        segment = result["data"]["aligned_transcript"][0]
        self.assertEqual(segment["speaker"], "S1")
        self.assertEqual(segment["assign_reason"], "overlap")

    def test_short_hole_fill_skips_long_text_but_is_force_assigned(self) -> None:
        payload = {
            "meeting_id": "m8",
            "alignment_debug": {"include_assign_reason": True},
            "asr_segments": [
                {
                    "segment_id": "seg_0001",
                    "start": 0.0,
                    "end": 3.0,
                    "text": "x" * 120,
                    "lang": "en",
                }
            ],
            "speaker_segments": [
                {"start": 0.0, "end": 1.0, "speaker": "S1"},
                {"start": 2.0, "end": 3.0, "speaker": "S1"},
            ],
        }

        result = run_alignment(payload)
        segments = result["data"]["aligned_transcript"]
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["speaker"], "S1")
        self.assertAlmostEqual(segments[0]["start"], 0.0, places=6)
        self.assertAlmostEqual(segments[0]["end"], 3.0, places=6)

    def test_no_speaker_segments_keeps_unknown(self) -> None:
        payload = {
            "meeting_id": "m9",
            "alignment_debug": {"include_assign_reason": True},
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 0.0, "end": 1.0, "text": "hello", "lang": "en"}
            ],
            "speaker_segments": [],
        }

        result = run_alignment(payload)
        segment = result["data"]["aligned_transcript"][0]
        self.assertEqual(segment["speaker"], "UNKNOWN")
        self.assertEqual(segment["assign_reason"], "unknown")

    def test_compact_empty_text_segments(self) -> None:
        payload = {
            "meeting_id": "m10",
            "alignment_debug": {"include_assign_reason": True},
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 0.0, "end": 2.0, "text": "ab", "lang": "en"}
            ],
            "speaker_segments": [
                {"start": 0.0, "end": 0.5, "speaker": "S1"},
                {"start": 1.0, "end": 1.5, "speaker": "S2"},
            ],
        }

        result = run_alignment(payload)
        segments = result["data"]["aligned_transcript"]
        self.assertTrue(all(seg["text"].strip() for seg in segments))

    def test_merge_adjacent_same_speaker_segments(self) -> None:
        payload = {
            "meeting_id": "m11",
            "alignment_debug": {"include_assign_reason": True},
            "alignment_config": {"merge_same_speaker_gap_sec": 0.2},
            "asr_segments": [
                {"segment_id": "seg_0001", "start": 0.0, "end": 1.0, "text": "你好", "lang": "zh"},
                {"segment_id": "seg_0002", "start": 1.05, "end": 2.0, "text": "今天", "lang": "zh"},
            ],
            "speaker_segments": [{"start": 0.0, "end": 2.0, "speaker": "S1"}],
        }

        result = run_alignment(payload)
        segments = result["data"]["aligned_transcript"]
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["speaker"], "S1")
        self.assertAlmostEqual(segments[0]["start"], 0.0, places=6)
        self.assertAlmostEqual(segments[0]["end"], 2.0, places=6)
        self.assertEqual(segments[0]["text"], "你好今天")


if __name__ == "__main__":
    unittest.main()
