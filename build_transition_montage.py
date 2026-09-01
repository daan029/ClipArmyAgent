"""
Fast-cut vertical montage with xfade transitions between clips and an
optional burned-in title bar for the opening seconds. Companion to
build_fast_montage.py (which does plain hard cuts) — use this one when the
edit calls for punchier "vette overgangen" instead of a straight cut.

Usage:
    python build_transition_montage.py --cuts cuts.json --out montage.mp4 \\
        --title-line1 "MOCO MUSEUM AMSTERDAM" --title-line2 "Dit moet je gezien hebben"

cuts.json:
[
  {"file": "IMG_7395.MOV", "start": 3.0, "end": 5.2, "transition": "fadewhite"},
  {"file": "IMG_1957.MOV", "start": 7.2, "end": 9.4, "transition": "zoomin"}
]
"transition" is optional per-cut (applies to the transition INTO the next clip);
defaults cycle through a preset list if omitted.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from clipper.reframe import crop_filter

CANVAS_W, CANVAS_H = 1080, 1920
DEFAULT_TRANSITIONS = ["fadewhite", "zoomin", "smoothleft", "circlecrop", "fadewhite", "smoothright"]

WHITE = "&H00FFFFFF&"
NAVY_BG = "&H004E2B09&"  # Klipje brand navy #092B4E, BGR order for ASS

TITLE_ASS_TEMPLATE = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TitleBar,Arial Black,64,{white},{white},{navy},{navy},-1,0,0,0,100,100,0,0,3,24,0,8,40,40,140,1
Style: TitleSub,Arial,44,{white},{white},{navy},{navy},0,0,0,0,100,100,0,0,3,18,0,8,40,40,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{end},TitleBar,,0,0,0,,{{\\fad(150,300)}}{line1}
Dialogue: 0,0:00:00.00,{end},TitleSub,,0,0,0,,{{\\fad(150,300)}}{line2}
"""


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _escape_ffmpeg_path(path: str) -> str:
    p = str(Path(path).resolve()).replace("\\", "/")
    return p.replace(":", "\\:")


def _normalize_cut(src: str, start: float, end: float, out_path: Path, focus_x: float) -> None:
    vf = f"{crop_filter(focus_x, CANVAS_W, CANVAS_H)},fps=30,format=yuv420p"
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", src,
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        str(out_path),
        "-hide_banner", "-loglevel", "error",
    ]
    subprocess.run(cmd, check=True)


def build_transition_montage(
    cuts: list[dict],
    out_path: str,
    focus_x: float = 0.5,
    transition_duration: float = 0.18,
    title_line1: str | None = None,
    title_line2: str | None = None,
    title_duration: float = 2.5,
) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        normalized = []
        for i, cut in enumerate(cuts):
            out = tmp / f"cut_{i:02d}.mp4"
            _normalize_cut(cut["file"], cut["start"], cut["end"], out, focus_x)
            normalized.append((out, cut["end"] - cut["start"]))

        inputs = []
        for path, _ in normalized:
            inputs += ["-i", str(path)]

        filter_parts = []
        label = "0:v"
        cumulative = normalized[0][1]
        for i in range(1, len(normalized)):
            dur = normalized[i][1]
            transition = cuts[i - 1].get("transition") or DEFAULT_TRANSITIONS[(i - 1) % len(DEFAULT_TRANSITIONS)]
            offset = cumulative - transition_duration
            out_label = f"v{i}"
            filter_parts.append(
                f"[{label}][{i}:v]xfade=transition={transition}:duration={transition_duration}:offset={offset:.3f}[{out_label}]"
            )
            label = out_label
            cumulative = cumulative + dur - transition_duration

        final_label = label
        if title_line1:
            ass_path = tmp / "title.ass"
            ass_path.write_text(
                TITLE_ASS_TEMPLATE.format(
                    w=CANVAS_W, h=CANVAS_H, white=WHITE, navy=NAVY_BG,
                    end=_fmt_time(title_duration),
                    line1=title_line1.replace("{", "").replace("}", ""),
                    line2=(title_line2 or "").replace("{", "").replace("}", ""),
                ),
                encoding="utf-8",
            )
            filter_parts.append(f"[{final_label}]ass='{_escape_ffmpeg_path(str(ass_path))}'[vout]")
            final_label = "vout"

        filter_complex = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", filter_complex,
            "-map", f"[{final_label}]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-movflags", "+faststart",
            str(out_path),
            "-hide_banner", "-loglevel", "error",
        ]
        subprocess.run(cmd, check=True)

    return cumulative


def main():
    ap = argparse.ArgumentParser(description="Build a fast-cut vertical montage with xfade transitions.")
    ap.add_argument("--cuts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--focus-x", type=float, default=0.5)
    ap.add_argument("--transition-duration", type=float, default=0.18)
    ap.add_argument("--title-line1")
    ap.add_argument("--title-line2")
    args = ap.parse_args()

    cuts = json.loads(Path(args.cuts).read_text(encoding="utf-8"))
    total = build_transition_montage(
        cuts, args.out,
        focus_x=args.focus_x,
        transition_duration=args.transition_duration,
        title_line1=args.title_line1,
        title_line2=args.title_line2,
    )
    print(f"Saved {args.out} ({len(cuts)} cuts, ~{total:.1f}s)")


if __name__ == "__main__":
    main()
