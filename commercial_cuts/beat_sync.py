"""Compute beat-aligned clip durations for a Commercial Cuts montage body, so
CONFIG.clips' `dur` values land cuts on the music's actual beat grid instead of
being picked "by feel" (the gap Daan flagged 2026-09-08 - see
feedback-commercial-cuts-needs-music-beat-sync in the auto-memory system).

Why this exists as a separate script rather than doing beat detection inside
higgsedit/the sandbox: higgsedit has no audio-analysis API, and mixing a second
audio track isn't supported by p.cut/p.compose (see references/assembly.md,
"video-editing" Higgsfield workflow: "An audio clip cannot share a track with
visual clips ... mix with ffmpeg"). So the real workflow is:
  1. Run this script locally (needs `pip install librosa` - not in requirements,
     install on demand) to get beat-aligned clip durations + which music excerpt
     to use.
  2. Plug the durations into CONFIG.clips in template.edit.jsx as normal, run the
     higgsedit build exactly as before (still no music inside higgsedit).
  3. AFTER the higgsedit render, mix the music excerpt under the rendered video
     with ffmpeg as a post-processing step (same place the AAC re-mux already
     happens) - see the ffmpeg pattern in mix_music_ffmpeg_cmd() below. Match
     sample rates explicitly (aformat) and use amix with normalize=0, or the
     added track gets silently dropped/never gets loud enough to actually hear -
     both real bugs hit and fixed 2026-09-08 building the Moco London video.

Usage:
    python beat_sync.py --music the_descent.mp3 --target-duration 21.3 --clips 6

Prints a suggested CONFIG.clips duration list (beat-aligned, varied per
MASTER_PROMPT.md's "editing rhythm" rule - not uniform beat-counts per clip)
and the music start offset to trim from.
"""
import argparse
import random

import librosa
import numpy as np


def detect_beats(music_path: str):
    y, sr = librosa.load(music_path, sr=22050, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.asarray(tempo).reshape(-1)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return tempo, beat_times


def pick_start_beat(beat_times, skip_intro_sec: float = 8.0) -> int:
    """Skip past a track's intro (skip_intro_sec) to land the excerpt on a
    section with an established groove, not the opening bars."""
    for i, t in enumerate(beat_times):
        if t >= skip_intro_sec:
            return i
    return 0


def beat_aligned_clip_durations(beat_times, start_idx: int, target_duration: float, n_clips: int,
                                 max_clip_duration: float = 2.8, hero_indices: set[int] | None = None,
                                 hero_max_duration: float = 8.0):
    """Assign a varied number of beats per clip (2-6 beats, weighted so not
    every clip gets the same count - MASTER_PROMPT.md's "editing rhythm" rule)
    until the cumulative duration reaches target_duration.

    Every clip is capped at max_clip_duration EXCEPT clips listed in
    hero_indices, which get hero_max_duration instead - MASTER_PROMPT.md
    section 21 says no body shot should run past ~2.5s "unless it's the
    establishing or hero shot", and section 37 explicitly allows generous
    hero/discovery shots when a campaign has few pre-vetted clips to work
    with (true for every real Commercial Cuts campaign so far - each has had
    exactly the clips ClipArmy's brief pre-selected, not an open pool). An
    uncapped last clip silently eating all remaining budget (a real bug hit
    building this) is NOT the same thing as a deliberately chosen hero shot -
    pick hero_indices yourself based on which source clips are actually the
    strongest visuals, don't let the algorithm default into it.

    If nothing is marked hero and max_clip_duration alone can't reach
    target_duration with n_clips clips, actual_total will land short - that's
    fine, the real hard constraint is the FINAL rendered video's total
    duration (20-30s per MASTER_PROMPT.md section 2), not that this body
    sub-total hits its target to the decimal. Mark at least one hero clip
    rather than raising max_clip_duration globally, which would put every
    clip back at risk of the original bug.

    Returns (durations, actual_total, music_end_idx)."""
    beat_choices = [2, 3, 4, 5, 6]
    weights = [2, 3, 3, 2, 1]  # bias toward 3-4 beat cuts, occasional short/long outliers
    hero_indices = hero_indices or set()

    durations = []
    idx = start_idx
    cumulative = 0.0

    for clip_i in range(n_clips):
        remaining_clips = n_clips - clip_i
        remaining_duration = target_duration - cumulative
        remaining_budget_per_clip = remaining_duration / remaining_clips
        is_hero = clip_i in hero_indices
        clip_cap = hero_max_duration if is_hero else max_clip_duration
        # Cap at clip_cap AND at ~1.8x its fair share of whatever's left,
        # whichever is stricter - prevents both a runaway shot and
        # back-loaded overruns, while still letting hero clips breathe.
        cap = min(clip_cap, remaining_budget_per_clip * 1.8)

        if is_hero:
            # Hero shots should actually USE their generous budget, not just
            # avoid exceeding it - target ~90% of the cap by beat count,
            # rather than the same small random pick regular clips get
            # (that was the original bug: heroes came out just as short as
            # everything else because nothing ever grows a pick, only shrinks
            # it). Walk forward beat-by-beat toward the target.
            target_dur = cap * 0.9
            next_idx = idx
            dur = 0.0
            while next_idx < len(beat_times) - 1 and dur < target_dur:
                next_idx += 1
                dur = beat_times[next_idx] - beat_times[idx]
            if dur > cap:
                next_idx -= 1
                dur = beat_times[next_idx] - beat_times[idx]
        else:
            n_beats = random.choices(beat_choices, weights=weights, k=1)[0]
            next_idx = min(idx + n_beats, len(beat_times) - 1)
            dur = beat_times[next_idx] - beat_times[idx]
            while dur > cap and n_beats > 1:
                n_beats -= 1
                next_idx = min(idx + n_beats, len(beat_times) - 1)
                dur = beat_times[next_idx] - beat_times[idx]

        durations.append(round(dur, 2))
        cumulative += dur
        idx = next_idx

    return durations, round(cumulative, 2), idx


def mix_music_ffmpeg_cmd(rendered_video: str, music_file: str, music_start: float, total_duration: float,
                          music_volume: float, out_file: str) -> str:
    """Returns the ffmpeg command string to mix a beat-synced music excerpt
    under a higgsedit render as a post-processing step. Calibrated from real
    trial and error 2026-09-08 (see feedback-triphunters-music-at-publish-not-baked-in):
    - aformat on BOTH inputs is required or amix silently drops the mismatched one
      (a real bug hit mixing 96kHz render audio with a 44.1kHz mp3).
    - normalize=0 on amix, or it auto-ducks the original track's volume too.
    - apad + duration=longest on the base track so short source audio doesn't
      truncate the whole mix early.
    - Tune music_volume by ear via `ffmpeg -af volumedetect` deltas in a quiet
      window, not by guessing - a ~2dB peak bump was inaudible, a ~4dB+ mean
      bump in a quiet window was what actually registered as "there's music now".
    """
    return (
        f'ffmpeg -y -i "{rendered_video}" -i "{music_file}" -filter_complex '
        f'"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,apad[a0];'
        f'[1:a]atrim={music_start}:{music_start + total_duration},'
        f'afade=t=in:st=0:d=1,afade=t=out:st={total_duration - 1}:d=1,'
        f'volume={music_volume},aformat=sample_rates=48000:channel_layouts=stereo[a1];'
        f'[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[aout]" '
        f'-map 0:v -map "[aout]" -t {total_duration} -c:v copy -c:a aac -b:a 192k '
        f'-hide_banner -loglevel error "{out_file}"'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--music", required=True)
    ap.add_argument("--target-duration", type=float, required=True, help="Montage body duration in seconds (video total minus outro)")
    ap.add_argument("--clips", type=int, required=True, help="Number of clips in the montage body")
    ap.add_argument("--skip-intro", type=float, default=8.0)
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducible duration picks")
    ap.add_argument("--hero-indices", type=str, default="", help="Comma-separated 0-based clip indices to treat as hero/establishing shots (higher duration cap), e.g. '0,4'")
    ap.add_argument("--hero-max-duration", type=float, default=8.0)
    ap.add_argument("--max-clip-duration", type=float, default=2.8)
    args = ap.parse_args()
    hero_indices = {int(x) for x in args.hero_indices.split(",") if x.strip()} if args.hero_indices else set()

    if args.seed is not None:
        random.seed(args.seed)

    tempo, beat_times = detect_beats(args.music)
    print(f"Detected tempo: {tempo:.2f} BPM, {len(beat_times)} beats over {beat_times[-1]:.1f}s")

    start_idx = pick_start_beat(beat_times, args.skip_intro)
    start_time = beat_times[start_idx]
    print(f"Starting excerpt at beat {start_idx} ({start_time:.2f}s into the track)")

    durations, actual_total, end_idx = beat_aligned_clip_durations(
        beat_times, start_idx, args.target_duration, args.clips,
        max_clip_duration=args.max_clip_duration, hero_indices=hero_indices, hero_max_duration=args.hero_max_duration,
    )
    print(f"\nSuggested CONFIG.clips durations ({len(durations)} clips, {actual_total:.2f}s total vs {args.target_duration}s target):")
    for i, d in enumerate(durations):
        print(f"  clip_{i:02d}: dur={d}")

    print(f"\nMusic excerpt: start={start_time:.2f}s, end={beat_times[end_idx]:.2f}s (trim the track to this range)")
    print("\nExample post-render mix command:")
    print(mix_music_ffmpeg_cmd("renders/commercial_cuts_final.mp4", args.music, start_time, actual_total, 0.6, "renders/commercial_cuts_final_music.mp4"))


if __name__ == "__main__":
    main()
