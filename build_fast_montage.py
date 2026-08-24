"""
Build a snappy, hard-cut vertical montage from a list of trimmed highlight moments.

Meant to run *after* highlight moments have been picked (e.g. via Higgsfield's
video_analysis_create scene breakdown, which flags the attention-grabbing
scene per clip as "Opening Hook" vs the rest) — this script only does the
ffmpeg trim/normalize/concat part, with hard cuts (no crossfade) so the edit
feels active.

Usage:
    python build_fast_montage.py --cuts cuts.json --out montage.mp4

cuts.json:
[
  {"file": "IMG_3600.MOV", "start": 0.5, "end": 2.2},
  {"file": "IMG_3598.MOV", "start": 0.0, "end": 2.0},
  {"file": "IMG_3573.MOV", "start": 1.0, "end": 3.0}
]
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

CANVAS = "1080:1920"


def trim_and_normalize(src: str, start: float, end: float, out_path: Path) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", src,
        "-vf", f"scale={CANVAS},setsar=1",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        str(out_path),
        "-hide_banner", "-loglevel", "error",
    ]
    subprocess.run(cmd, check=True)


def build_montage(cuts: list[dict], out_path: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        trimmed_paths = []
        for i, cut in enumerate(cuts):
            trimmed = tmp / f"cut_{i:02d}.mp4"
            trim_and_normalize(cut["file"], cut["start"], cut["end"], trimmed)
            trimmed_paths.append(trimmed)

        concat_list = tmp / "concat_list.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in trimmed_paths), encoding="utf-8"
        )

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            out_path,
            "-hide_banner", "-loglevel", "error",
        ]
        subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description="Concatenate trimmed highlight clips into a hard-cut vertical montage.")
    ap.add_argument("--cuts", required=True, help="Path to a JSON file: [{file, start, end}, ...]")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cuts = json.loads(Path(args.cuts).read_text(encoding="utf-8"))
    build_montage(cuts, args.out)
    total = sum(c["end"] - c["start"] for c in cuts)
    print(f"Saved {args.out} ({len(cuts)} cuts, ~{total:.1f}s)")


if __name__ == "__main__":
    main()
