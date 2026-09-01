"""
Score a transcript for the best standalone viral-clip moments using the
Claude API — this replaces Higgsfield's virality_predictor/video_analysis_create.

Sends the full transcript (with timestamps) in one call and asks the model
to pick N self-contained, hook-worthy segments, each snapped to real sentence
boundaries, with a 0-100 virality score, a one-line reason, and a short
on-screen hook line for the first ~3 seconds.

Usage:
    python -m clipper.find_moments --transcript transcript.json --n 5 --out moments.json
"""
import argparse
import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """Je bent een short-form video editor die lange video's doorspit op zoek naar \
de meest viral-waardige momenten voor TikTok/Instagram Reels/YouTube Shorts.

Je krijgt een transcript met tijdstempels per zin. Kies de beste clip-kandidaten volgens deze regels:
- Elke clip moet op zichzelf staan (begrijpelijk zonder de rest van de video te kennen).
- Sterke hook nodig binnen de eerste 2-3 seconden (vraag, opvallende uitspraak, spanning, humor).
- Duur tussen de 15 en 90 seconden.
- start/end MOETEN exact overeenkomen met een zin-grens uit het transcript (gebruik de gegeven tijdstempels, verzin geen nieuwe tijden).
- Clips mogen niet overlappen.
- Sorteer op virality_score aflopend (hoogste eerst).

Antwoord ALLEEN met geldige JSON, geen uitleg eromheen, in dit schema:
{"clips": [{"start": 12.3, "end": 45.6, "virality_score": 82, "reason": "korte reden in het Nederlands", "hook_text": "korte pakkende hooktekst voor op het scherm"}]}
"""


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    key_file = REPO_ROOT / "secrets" / "anthropic_api_key.txt"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    raise RuntimeError(
        "No Anthropic API key found. Set ANTHROPIC_API_KEY or create secrets/anthropic_api_key.txt"
    )


def _transcript_to_prompt(transcript: dict) -> str:
    lines = [f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in transcript["segments"]]
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def _clamp_to_segments(clip: dict, transcript: dict) -> dict:
    duration = transcript["duration"]
    start = max(0.0, min(float(clip["start"]), duration))
    end = max(start, min(float(clip["end"]), duration))
    clip = dict(clip)
    clip["start"], clip["end"] = start, end
    return clip


def find_moments(
    transcript: dict,
    n: int = 5,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key or _get_api_key())
    user_prompt = (
        f"Kies de {n} beste clip-kandidaten uit dit transcript "
        f"(video-duur: {transcript['duration']:.1f}s):\n\n{_transcript_to_prompt(transcript)}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    parsed = _extract_json(text)

    clips = [_clamp_to_segments(c, transcript) for c in parsed["clips"]]
    clips.sort(key=lambda c: c["virality_score"], reverse=True)
    return clips[:n]


def main():
    ap = argparse.ArgumentParser(description="Find and score viral clip candidates from a transcript.")
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    transcript = json.loads(Path(args.transcript).read_text(encoding="utf-8"))
    moments = find_moments(transcript, n=args.n, model=args.model)
    Path(args.out).write_text(json.dumps(moments, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Found {len(moments)} moments -> {args.out}")
    for i, m in enumerate(moments, 1):
        print(f"  {i}. [{m['start']:.1f}-{m['end']:.1f}] score={m['virality_score']} — {m['reason']}")


if __name__ == "__main__":
    main()
