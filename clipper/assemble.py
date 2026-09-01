"""
Trim a source video to one chosen clip, reframe to 9:16, and burn in the
generated .ass captions — the final ffmpeg step, mirroring the
trim/scale/normalize pattern already used in build_fast_montage.py.
"""
import subprocess
from pathlib import Path

from clipper.reframe import crop_filter


def _escape_ffmpeg_path(path: str) -> str:
    """ffmpeg filter arguments split on ':', so an absolute Windows path
    (C:\\...) needs its drive-letter colon escaped, and backslashes need to
    become forward slashes."""
    p = str(Path(path).resolve()).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def assemble_clip(
    source_path: str,
    start: float,
    end: float,
    ass_path: str,
    out_path: str,
    focus_x_ratio: float = 0.5,
    target_w: int = 1080,
    target_h: int = 1920,
) -> None:
    vf = f"{crop_filter(focus_x_ratio, target_w, target_h)},ass='{_escape_ffmpeg_path(ass_path)}'"
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(source_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out_path),
        "-hide_banner", "-loglevel", "error",
    ]
    subprocess.run(cmd, check=True)
