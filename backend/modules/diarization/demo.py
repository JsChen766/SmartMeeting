from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__:
    from .service import run_diarization
else:
    CURRENT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = CURRENT_DIR.parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from backend.modules.diarization.service import run_diarization

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_AUDIO_PATH = PROJECT_ROOT / "data" / "raw" / "meeting_01.wav"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local speaker diarization demo.")
    parser.add_argument(
        "--meeting-id",
        default="demo_videoplayback_001",
        help="Meeting identifier used in the diarization request.",
    )
    parser.add_argument(
        "--audio-path",
        default=str(DEFAULT_AUDIO_PATH),
        help="Absolute or project-relative path to the input audio file.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional audio duration in seconds.",
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        help="Optional fixed number of speakers.",
    )
    parser.add_argument(
        "--min-speakers",
        type=int,
        default=None,
        help="Optional lower bound for speaker count.",
    )
    parser.add_argument(
        "--max-speakers",
        type=int,
        default=None,
        help="Optional upper bound for speaker count.",
    )
    return parser.parse_args()


def build_payload(args: argparse.Namespace) -> dict:
    audio_path = Path(args.audio_path)
    resolved_audio_path = audio_path if audio_path.is_absolute() else PROJECT_ROOT / audio_path

    payload = {
        "meeting_id": args.meeting_id,
        "audio_asset": {
            "file_name": resolved_audio_path.name,
            "storage_path": str(resolved_audio_path),
            "duration": args.duration,
        },
    }

    options = {}
    if args.num_speakers is not None:
        options["num_speakers"] = args.num_speakers
    if args.min_speakers is not None:
        options["min_speakers"] = args.min_speakers
    if args.max_speakers is not None:
        options["max_speakers"] = args.max_speakers

    if options:
        payload["options"] = options

    return payload


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    result = run_diarization(payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
