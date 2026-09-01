"""
Build word-by-word "pop" karaoke-style captions (.ass) from whisper word
timestamps — the CapCut/TikTok caption style that research shows lifts
completion rate ~40%. Also renders an optional hook-text overlay for the
first few seconds, since 63% of viral shorts deliver their hook there.
"""
from pathlib import Path

WHITE = "&H00FFFFFF&"
GOLD = "&H0000D7FF&"
BLACK = "&H00000000&"

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Arial Black,84,{white},{white},{black},{black},-1,0,0,0,100,100,0,0,1,6,0,2,60,60,380,1
Style: Hook,Arial Black,104,{white},{white},{black},{black},-1,0,0,0,100,100,0,0,1,7,0,8,60,60,160,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""".format(w="{w}", h="{h}", white=WHITE, black=BLACK)


def words_in_range(transcript: dict, start: float, end: float) -> list[dict]:
    """Words overlapping [start, end], timestamps rebased to 0 at `start`."""
    out = []
    for seg in transcript["segments"]:
        for w in seg.get("words", []):
            if not w["word"] or w["end"] <= start or w["start"] >= end:
                continue
            out.append(
                {
                    "word": w["word"].replace("{", "").replace("}", ""),
                    "start": max(0.0, w["start"] - start),
                    "end": max(0.0, min(w["end"], end) - start),
                }
            )
    return out


def _group_phrases(words: list[dict], max_words: int = 4, max_gap: float = 0.6) -> list[list[dict]]:
    phrases: list[list[dict]] = []
    current: list[dict] = []
    for w in words:
        if current:
            gap = w["start"] - current[-1]["end"]
            ends_sentence = current[-1]["word"][-1:] in ".!?"
            if len(current) >= max_words or gap > max_gap or ends_sentence:
                phrases.append(current)
                current = []
        current.append(w)
    if current:
        phrases.append(current)
    return phrases


def _highlighted_text(phrase: list[dict], active_idx: int) -> str:
    parts = []
    for i, w in enumerate(phrase):
        if i == active_idx:
            parts.append("{\\c" + GOLD + "}" + w["word"] + "{\\c" + WHITE + "}")
        else:
            parts.append(w["word"])
    return " ".join(parts)


def _fmt_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(
    words: list[dict],
    clip_duration: float,
    out_path: str,
    hook_text: str | None = None,
    hook_duration: float = 2.5,
    video_w: int = 1080,
    video_h: int = 1920,
    words_per_phrase: int = 4,
) -> None:
    phrases = _group_phrases(words, max_words=words_per_phrase)

    lines = [ASS_HEADER.replace("{w}", str(video_w)).replace("{h}", str(video_h))]
    for pi, phrase in enumerate(phrases):
        next_phrase_start = phrases[pi + 1][0]["start"] if pi + 1 < len(phrases) else clip_duration
        for i, w in enumerate(phrase):
            seg_start = w["start"]
            if i + 1 < len(phrase):
                # Hard boundary set by the next word's own start — never
                # extend past it, or two caption lines briefly overlap.
                seg_end = phrase[i + 1]["start"]
            else:
                seg_end = min(w["end"] + 0.2, clip_duration, next_phrase_start)
                seg_end = max(seg_end, seg_start + 0.05)
                seg_end = min(seg_end, clip_duration, next_phrase_start)
            text = _highlighted_text(phrase, i)
            lines.append(f"Dialogue: 0,{_fmt_time(seg_start)},{_fmt_time(seg_end)},Caption,,0,0,0,,{text}")

    if hook_text:
        clean_hook = hook_text.replace("{", "").replace("}", "")
        end = min(hook_duration, clip_duration)
        lines.append(f"Dialogue: 1,{_fmt_time(0)},{_fmt_time(end)},Hook,,0,0,0,,{clean_hook}")

    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
