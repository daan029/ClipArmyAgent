# Commercial Cuts — production style guide

Read this before making any video for the Commercial Cuts YouTube/TikTok account. It's the
fixed house style — every video follows this structure and these rules so the channel builds
a consistent, recognizable identity, the way a real ad agency's reel would. Pairs with
`template.edit.jsx` in this folder (the executable version of this guide, built for
Higgsfield's `higgsedit` — run inside a Claude session with `sandbox_exec`, not locally).

## Concept

Commercial Cuts takes real ClipArmy campaign footage and re-cuts it to look like a
professional ad agency made it — a polished "commercial" for whatever the campaign is
actually promoting (a museum, a brand, an event). Same source clips as the raw ClipArmy
submission, much heavier post: color grading, motion graphics, deliberate pacing, brand
outro. The contrast between "this is just B-roll from a campaign" and "this looks like a
$50k agency spot" is the entire hook.

## Caption / title formula (fixed, every video)

On-screen title card text AND the social caption/description both follow this exact pattern:

```
Creating a professional commercial for [SUBJECT]
```

`[SUBJECT]` = the thing the campaign is actually about, phrased as a real client name would
be — e.g. "Moco Museum Barcelona", "a Michelin-star restaurant", "a Barcelona travel brand".
Pull this from the campaign name/brief, don't just paste the raw ClipArmy campaign title
verbatim if it reads awkwardly as a client name.

A second, shorter line is used **sometimes, not always** — vary it video to video, don't make
it a permanent tag:

```
With AI
```

When used, it appears as a smaller/lighter second line under the main title, landing about
0.4s after the main line settles (see Beat 2 below). When the video is a pure practical edit
with no AI-assisted step (e.g. no AI-generated overlay, no synthetic voice), leave the line
out rather than showing it every time — it should read as an honest, occasional disclosure,
not a slogan.

## Structure — 5 fixed beats

Every video is built from these beats in this order. Total runtime is flexible (15–45s
depending on how much good footage a campaign has), but the beat *order* and *roles* never
change. This is deliberately close to higgsedit's "Logo assemble and lockup" +
"Kinetic type beats" + "Video → graphic pivot" blueprints (see `references/shot-blueprints.md`
in the `video-editing` Higgsfield workflow) — reproduce those shapes, don't reinvent timing
from scratch per video.

### Beat 1 — Cold open (0–1.2s)

Footage starts immediately, full-bleed, no title yet, no logo yet. This is the single most
important rule: **never open on a title card or logo.** A real commercial doesn't announce
itself before it starts — it just starts. Pick the single strongest, most visually striking
shot from the campaign's footage as the opening frame, even if it's not the shot you'd
otherwise cut first.

### Beat 2 — Title card overlay (1.2s–3.5s)

The caption-formula text lands **over the still-playing footage**, not on a black card —
bottom-third placement, dark gradient scrim behind the text for readability (a `<rect>` with
a linear gradient fill, low opacity, sitting between the footage and the text). Use the
**kinetic beat slam** rule (`references/motion-language.md`): the main line slams/scales in
as one phrase, `house` easing, then (if used) "With AI" rises in beneath it ~0.4s later,
smaller weight, 70% opacity. Hold both through 3.5s, then let them exit with a quick fade —
never a hard cut of the text, the footage keeps rolling underneath.

Typography: display type at **180–240px** at 1080×1920 (matches the "180–320px at 1080p"
craft default) — never smaller, undersized title text is the most common way a build reads
as amateur. Use **Anton** or **Archivo Black**, all caps, tight letter-spacing, white text
with a subtle dark stroke or shadow for legibility over bright footage.

### Beat 3 — Montage body (3.5s to final-3s)

The actual best clips from the campaign, cut on rhythm — not evenly-spaced cuts, cut *on
motion* (a whip-pan, a gesture completing, a scene change) the way a real editor would. This
is where 80%+ of the runtime lives. Rules:

- **Global color grade** applies here (and for the whole video — see Color grade below), not
  per-clip. Consistency across cuts is what reads as "graded," not "filtered."
- At most **one** lower-third/context label in this section (e.g. "MOCO MUSEUM — BARCELONA"),
  using the **calm title landing** rule: one restrained entrance, long hold, no secondary
  motion competing with it. Skip it entirely if the subject is already obvious from the
  footage — don't force a label onto every video.
- Cut duration per shot: no shot longer than ~2.5s in the body unless it's the establishing
  or hero shot. Faster cutting reads as more "commercial," slower reads as amateur B-roll.
- No more than 2–3 distinct "signature moves" total across the whole edit (per
  `motion-language.md`'s atomic-rule contract: 2–4 rules per scene, not more). Restraint is
  what separates this from a TikTok-native fast-flash edit — Commercial Cuts should feel
  *controlled*, not chaotic.

### Beat 4 — Brand outro (final 3s)

**Logo assemble and lockup** blueprint. The Commercial Cuts mark (the gold interlocking-C
logo, see brand assets below) assembles/springs into frame center — never a plain fade-in,
the logo should look like it's *forming*, not appearing. Wordmark "COMMERCIAL CUTS" lands
underneath via word cascade, small tracking-heavy caption weight. Final lockup (logo +
wordmark together) holds for the last ~1s — this is the frame the platform freezes on for
scrubbing/thumbnails, so it must be clean and centered.

### Beat 5 — Final hold

Not a separate visual beat — just the discipline that Beat 4's lockup doesn't cut away early.
Render out with the lockup as the literal last frame.

## Color grade

One consistent grade across every video — this is a brand identity, not a per-video choice.
Warm, slightly desaturated, lifted blacks — the "premium travel/lifestyle commercial" look
(think a warm amber/charcoal palette matching the logo, not a cold blue-teal blockbuster
grade). Apply it as a **single full-frame `<adjustment>` node** spanning the entire timeline
(see `template.edit.jsx`) rather than grading each clip individually — one grade, one place,
guarantees every video actually matches instead of drifting per-editor/per-session.

**Open item, needs a real asset before this can render as designed**: the template references
`luts/commercial-cuts.cube`, which doesn't exist yet. Either source a warm cinematic `.cube`
LUT (many free/cheap ones fit this brief — search "warm cinematic teal orange alternative" or
"amber film look LUT") and drop it at that path, or ask a Claude session with Higgsfield
access to build an equivalent grade from primitive color adjustments if no LUT file is
supplied. Don't skip the grade to avoid this step — it's the single biggest visual signal
that separates "professional" from "raw clip."

## Brand assets

- Logo (profile picture): gold interlocking-"CC" monogram on dark charcoal, generated
  2026-09-07. Use the same mark in the Beat 4 lockup as on the channel avatar — don't
  redesign it per video.
- Brand color: warm gold/amber (approx. `#D9A441`–`#E8B84B` range, matches the logo gradient)
  on dark charcoal/near-black (`#1A1A1C` range).
- Fonts: **Anton** (display/title), **Inter** (any body/lower-third text) — both are
  higgsedit built-in fonts, no font-loading step needed.

## Technical spec

- Vertical, `1080x1920`, `30fps` — TikTok and YouTube Shorts both want this.
- Runtime: 15–45s, driven by how much usable footage the campaign actually has. Never pad
  with slow-motion or repeated shots just to hit a target length.
- Audio: keep the original clip audio as ambient bed under the montage (lightly ducked, not
  muted — see `worker.py`'s ffmpeg `loudnorm` pattern for one precedent on fixing a video
  whose audio was too quiet to notice at all). Add trending TikTok sound only if it doesn't
  fight the footage's own ambient sound — Commercial Cuts is not TripHunters; leaning on a
  trending-audio hook is not house style here the way it is for TripHunters.

## What this is NOT

- Not a place for the fast-cut, meme-caption, TripHunters/klipje TikTok style — no POV
  captions, no comedic zoom-punch edits.
- Not fully hands-off. Every video needs at least one real editorial decision (which shot
  opens, whether "With AI" is honest to include, whether a location label is warranted) — the
  template is a scaffold, not a render-and-forget button.
