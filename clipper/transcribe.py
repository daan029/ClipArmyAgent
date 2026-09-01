"""
Transcribe a source video with word-level timestamps using faster-whisper.

Replaces relying on Higgsfield for understanding what's actually said in a
source video — this is the raw material find_moments.py scores for virality.

Usage:
    python -m clipper.transcribe --source video.mp4 --out transcript.json
"""
import argparse
import json
from pathlib import Path


def transcribe(
    source_path: str,
    model_size: str = "small",
    language: str | None = "nl",
    device: str = "cpu",
    compute_type: str = "int8",
) -> dict:
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, info = model.transcribe(
        source_path,
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    out_segments = []
    for seg in segments:
        words = [
            {"word": w.word.strip(), "start": w.start, "end": w.end}
            for w in (seg.words or [])
        ]
        out_segments.append(
            {"start": seg.start, "end": seg.end, "text": seg.text.strip(), "words": words}
        )

    return {
        "source": str(source_path),
        "language": info.language,
        "duration": info.duration,
        "segments": out_segments,
    }


def save_transcript(transcript: dict, out_path: str) -> None:
    Path(out_path).write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Transcribe a video with word-level timestamps.")
    ap.add_argument("--source", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--language", default="nl", help="ISO language code, or 'auto' to detect")
    ap.add_argument("--model", default="small", help="faster-whisper model size")
    args = ap.parse_args()

    language = None if args.language == "auto" else args.language
    transcript = transcribe(args.source, model_size=args.model, language=language)
    save_transcript(transcript, args.out)
    print(f"Saved transcript ({len(transcript['segments'])} segments, {transcript['duration']:.1f}s) -> {args.out}")


if __name__ == "__main__":
    main()
