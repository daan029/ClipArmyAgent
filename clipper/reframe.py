"""
Vertical (9:16) reframing filter for source footage of any aspect ratio.

v1: simple, robust center-crop (parametrized by a focus_x_ratio so a future
active-speaker/face-tracking version can drive the same crop_filter() without
changing assemble.py).
"""


def crop_filter(
    focus_x_ratio: float = 0.5,
    target_w: int = 1080,
    target_h: int = 1920,
) -> str:
    """ffmpeg -vf filter string: scale to cover target, then crop centered
    (or offset horizontally by focus_x_ratio, 0=left..1=right)."""
    focus_x_ratio = min(1.0, max(0.0, focus_x_ratio))
    return (
        f"scale=w={target_w}:h={target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h}:"
        f"x='(in_w-{target_w})*{focus_x_ratio}':y='(in_h-{target_h})/2'"
    )
