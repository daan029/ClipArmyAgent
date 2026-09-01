"""
End-to-end viral clip pipeline: one long source video -> N ranked, captioned,
vertical clips ready to post — replaces Higgsfield's personal_clipper_create
+ virality_predictor/video_analysis_create for clip *generation* (TikTok
publishing still goes through Higgsfield's connector, unchanged).

Usage:
    python make_viral_clips.py --source video.mp4 --campaign supergaande --n 5
    python make_viral_clips.py --source https://youtube.com/watch?v=... --campaign supergaande --n 5

Output:
    clips/<campaign>/viral/clip_01.mp4 ... clip_0N.mp4
    clips/<campaign>/viral/transcript.json
    clips/<campaign>/viral/report.json
"""
import argparse
import json
from pathlib import Path

from clipper.assemble import assemble_clip
from clipper.captions import build_ass, words_in_range
from clipper.find_moments import DEFAULT_MODEL, find_moments
from clipper.transcribe import save_transcript, transcribe

REPO_ROOT = Path(__file__).resolve().parent


def is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def download_source(url: str, out_dir: Path) -> Path:
    import yt_dlp

    out_dir.mkdir(parents=True, exist_ok=True)
    ydl_opts = {
        "format": "bv*[ext=mp4]+ba[ext=m4a]/mp4/best",
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "merge_output_format": "mp4",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info)).with_suffix(".mp4")
    if not path.exists():
        raise RuntimeError(f"yt-dlp reported success but output file not found: {path}")
    return path


def run(
    source: str,
    campaign: str,
    n: int = 5,
    language: str = "nl",
    whisper_model: str = "small",
    claude_model: str = DEFAULT_MODEL,
    focus_x: float = 0.5,
) -> Path:
    out_dir = REPO_ROOT / "clips" / campaign / "viral"
    out_dir.mkdir(parents=True, exist_ok=True)

    source_path = download_source(source, out_dir / "download") if is_url(source) else Path(source)
    if not source_path.exists():
        raise FileNotFoundError(f"Source video not found: {source_path}")

    print(f"[1/4] Transcribing {source_path.name} (model={whisper_model}, language={language})...")
    lang = None if language == "auto" else language
    transcript = transcribe(str(source_path), model_size=whisper_model, language=lang)
    save_transcript(transcript, out_dir / "transcript.json")
    print(f"      {len(transcript['segments'])} segments, {transcript['duration']:.1f}s")

    print(f"[2/4] Scoring viral moments with {claude_model}...")
    moments = find_moments(transcript, n=n, model=claude_model)
    print(f"      {len(moments)} candidates found")

    print("[3/4] Rendering clips (crop + captions)...")
    report = []
    for i, m in enumerate(moments, start=1):
        clip_words = words_in_range(transcript, m["start"], m["end"])
        duration = m["end"] - m["start"]
        ass_path = out_dir / f"clip_{i:02d}.ass"
        build_ass(clip_words, duration, str(ass_path), hook_text=m.get("hook_text"))

        clip_path = out_dir / f"clip_{i:02d}.mp4"
        assemble_clip(str(source_path), m["start"], m["end"], str(ass_path), str(clip_path), focus_x_ratio=focus_x)
        print(f"      clip_{i:02d}.mp4  score={m['virality_score']}  [{m['start']:.1f}-{m['end']:.1f}]")

        report.append(
            {
                "clip": clip_path.name,
                "start": m["start"],
                "end": m["end"],
                "duration": round(duration, 1),
                "virality_score": m["virality_score"],
                "reason": m["reason"],
                "hook_text": m.get("hook_text"),
            }
        )

    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[4/4] Done -> {out_dir}")
    return out_dir


def main():
    ap = argparse.ArgumentParser(description="Generate ranked, captioned viral clips from a source video.")
    ap.add_argument("--source", required=True, help="Local video path or a video URL (downloaded via yt-dlp)")
    ap.add_argument("--campaign", required=True, help="Campaign folder name under clips/")
    ap.add_argument("--n", type=int, default=5, help="Number of clips to generate")
    ap.add_argument("--language", default="nl", help="ISO language code for transcription, or 'auto'")
    ap.add_argument("--whisper-model", default="small")
    ap.add_argument("--claude-model", default=DEFAULT_MODEL)
    ap.add_argument("--focus-x", type=float, default=0.5, help="0=left, 0.5=center, 1=right crop focus")
    args = ap.parse_args()

    run(
        source=args.source,
        campaign=args.campaign,
        n=args.n,
        language=args.language,
        whisper_model=args.whisper_model,
        claude_model=args.claude_model,
        focus_x=args.focus_x,
    )


if __name__ == "__main__":
    main()
