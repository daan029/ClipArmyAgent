// commercial_cuts/template.edit.jsx
//
// The executable version of STYLE_GUIDE.md (same folder) — every Commercial Cuts video is
// built by copying this file, filling in CONFIG, and running it. Everything outside CONFIG
// is fixed house style and shouldn't change per video; if a video genuinely needs a
// structural change, update STYLE_GUIDE.md too so the two stay in sync.
//
// Also read MASTER_PROMPT.md (same folder) before producing any Commercial Cuts video — it's
// the full creative-direction brief (story structure, 20-30s hard duration rule, transitions,
// Ken Burns, music selection/licensing) that this template implements. STYLE_GUIDE.md is the
// Commercial-Cuts-specific brand layer (caption formula, logo, color grade) on top of it.
//
// VERIFIED 2026-09-07 against a real render (Moco Museum Barcelona, 6 clips) inside
// Higgsfield's `higgsedit` sandbox via a Claude Code session's `sandbox_exec` — this does NOT
// run locally, there is no higgsedit CLI on this Windows machine. Real build steps, in order:
//   higgsedit init <projectDir> --size 1080x1920 --fps 30
//   higgsedit fonts add <projectDir> "Anton" "Inter:400" "Inter:600" "Inter:700"
//   higgsedit build <projectDir>/edit.jsx
// (the earlier version of this file only said "run higgsedit build edit.jsx" - init and
// fonts add are required first or the build fails with "no project.json"/font-not-vendored.)
//
// REVISION 2026-09-07 #2 — first real render was REJECTED on review: hard cuts with no
// transitions/zooms in the montage body, only the intro title card and outro logo felt
// designed (see feedback-commercial-cuts-needs-transitions-and-zooms memory). Fixed by wrapping
// the whole montage body in ONE <sequence> (compose.md "sequence" section) with a `transition`
// on every outgoing clip, plus a per-clip Ken Burns push/pull (`animate` on `scale`) on a
// positioned `<group>` wrapping each `<media>`. Also switched CONFIG.clips from short
// (~2s/clip, 16s total) trims to close-to-full cuts.json ranges (~21s body + 3s outro ≈ 24s
// total) to satisfy MASTER_PROMPT.md's hard 20-30s runtime rule — the previous cut was 16s,
// which would fail that rule even before the transitions fix.
//
// Bugs fixed by the original verification pass, both silent/non-obvious:
// 1. `animate` on any node MUST be an array, even for a single animation - a bare object
//    (`animate={{...}}`) is refused ("must be an array of animations - got an object") even
//    though SKILL.md's own inline example shows the bare-object form. Always
//    `animate={[{...}]}`.
// 2. A `<rect>` used as a background scrim must NOT be a child of the flex `<column>` it sits
//    behind - being flex-children, it gets FLOWED (its own height pushes siblings down) rather
//    than just painted behind them, which silently pushed the whole title text (and the "With
//    AI" line) below frame edge, invisible, with no error. Fix: compose the scrim as its own
//    separate `p.compose()` call (paints first/underneath), and keep the column to only the
//    text nodes.
// 3. `<text>` has no `stroke` object prop - build fails hard with "'stroke' is not a text field".
//    Use flat `strokeColor`/`strokeWidth` instead (references/caption-titling.md "Appearance").
//
// Before running, for every clip in CONFIG.clips, pre-extract its audio once with ffmpeg —
// higgsedit's <media> node draws picture only, sound is a separate spine clip kept in sync
// via the same sourceStart offset (see SKILL.md "Footage inside a design"). Extract to a REAL
// .mp3 (libmp3lame) or .m4a and keep the extension honest - Higgsfield's media_upload infers
// content-type from the filename extension, and an AAC stream saved with a .mp3 extension
// still uploads fine but is the wrong container for what the extension claims:
//   ffmpeg -nostdin -i clip_01.mp4 -vn -c:a libmp3lame -q:a 2 clip_01.mp3

// ---------------------------------------------------------------------------
// CONFIG — fill in per video. Nothing below this block should need to change.
// ---------------------------------------------------------------------------
const CONFIG = {
  subject: "Moco Museum Barcelona", // -> title card: "Creating a professional commercial for {subject}"
  useAiTag: true, // show the "With AI" second line? Vary this - see STYLE_GUIDE.md, don't always show it.
  locationLabel: "MOCO MUSEUM - BARCELONA", // Beat 3 lower-third, or null to skip entirely
  // LUT color grade: NOT applied below yet - luts/commercial-cuts.cube still doesn't exist
  // (see STYLE_GUIDE.md "Color grade"). Once a real .cube file exists, add back a `lut` effect
  // on each <media> node in the loop below: effects={[{ kind: "lut", params: { file: lutFile,
  // amount: lutAmount } }]} - lut is a pixel-program effect, valid on <media> nodes only.
  //
  // dur/kenBurns are chosen per clip, not uniform — MASTER_PROMPT.md's "editing rhythm" rule
  // (vary shot duration, don't give every shot the same length) and its 20-30s hard runtime
  // floor (this campaign only has 6 pre-vetted clips, so clip_00/01/03 use most of their real
  // available footage as generous hero/discovery shots rather than being padded or repeated —
  // MASTER_PROMPT.md rule 37). transition is on the OUTGOING edge of this clip (into the next);
  // the last clip has none (it cuts into the separate outro beat with its own fade-in instead).
  clips: [
    { video: "media/clip_00.mp4", audio: "media/clip_00_audio.mp3", sourceStart: 0, dur: 6.6, kenBurns: { from: 1.0, to: 1.1 }, transition: { preset: "fade", duration: 0.45 } },
    { video: "media/clip_01.mp4", audio: "media/clip_01_audio.mp3", sourceStart: 0, dur: 4.8, kenBurns: { from: 1.08, to: 1.0 }, transition: { preset: "grow", duration: 0.35 } },
    { video: "media/clip_02.mp4", audio: "media/clip_02_audio.mp3", sourceStart: 0, dur: 2.9, kenBurns: { from: 1.0, to: 1.07 }, transition: { preset: "slide-left", duration: 0.35 } },
    { video: "media/clip_03.mp4", audio: "media/clip_03_audio.mp3", sourceStart: 0, dur: 4.3, kenBurns: { from: 1.07, to: 1.0 }, transition: { preset: "grow", duration: 0.3 } },
    { video: "media/clip_04.mp4", audio: "media/clip_04_audio.mp3", sourceStart: 0, dur: 1.12, kenBurns: { from: 1.0, to: 1.06 }, transition: { preset: "fade", duration: 0.3 } },
    { video: "media/clip_05.mp4", audio: "media/clip_05_audio.mp3", sourceStart: 0, dur: 1.59, kenBurns: { from: 1.0, to: 1.14 }, transition: null },
    // ...one entry per clip used in the montage. sourceStart is seconds into that clip's own
    // file - 0 if you pre-trimmed each clip to just its used segment (simplest), or the real
    // in-clip offset if you imported longer source files directly.
  ],
  logo: "media/logo.jpg", // gold CC monogram
};

// ---------------------------------------------------------------------------
// Brand constants — fixed. See STYLE_GUIDE.md for the reasoning behind each.
// ---------------------------------------------------------------------------
const W = 1080;
const H = 1920;
const GOLD = "#E0AC4C";
const CHARCOAL = "#1A1A1C";
const TITLE_FONT = "Anton";
const BODY_FONT = "Inter";
const TITLE_CARD_DUR = 3.5; // Beat 2 window: title overlays the first 3.5s of the montage body
const OUTRO_DUR = 3.0; // Beat 4

export default async function edit({ project }) {
  const p = await project({ size: `${W}x${H}`, fps: 30, background: CHARCOAL });

  // Import every clip's picture + its pre-extracted audio, and the logo, once up front.
  const videoHandles = [];
  const audioHandles = [];
  for (const c of CONFIG.clips) {
    videoHandles.push(await p.add(c.video));
    audioHandles.push(await p.add(c.audio));
  }
  const logo = await p.add(CONFIG.logo);

  // ---- Audio spine: one p.cut per clip, kept in sync with the visual sequence below via the
  // same cumulative timeline offset. ----
  let t = 0;
  for (let i = 0; i < CONFIG.clips.length; i++) {
    const c = CONFIG.clips[i];
    p.cut(audioHandles[i], { at: t, from: c.sourceStart, dur: c.dur });
    t += c.dur;
  }
  const bodyEnd = t;

  // ---- Beats 1 + 3: the whole montage body, as ONE <sequence> so cuts get real transitions
  // instead of hard back-to-back p.compose calls (the exact gap Daan called out on review: only
  // the intro/outro looked designed). Each clip is a positioned <group> (origin="center") so a
  // Ken Burns push/pull can animate `scale` around the frame center without revealing edges -
  // fit="cover" on the inner <media> already crops to fill, so scaling up to ~1.06-1.14 stays a
  // pure zoom within that crop margin (compose.md's camera-pan warning about edge content only
  // applies to positionX/Y pans, not this centered scale-only move). No more than 3 distinct
  // transition presets across the whole edit (fade / grow / slide-left) - the "2-4 signature
  // moves per scene" restraint rule in motion-language.md and STYLE_GUIDE.md. ----
  p.compose(
    <sequence>
      {CONFIG.clips.map((c, i) => (
        <group
          name={`clip-${i}`}
          width={W}
          height={H}
          x={0}
          y={0}
          origin="center"
          duration={c.dur}
          transition={c.transition || undefined}
          animate={[{ property: "scale", from: c.kenBurns.from, to: c.kenBurns.to, duration: c.dur, easing: "linear" }]}
        >
          <media file={videoHandles[i]} trimStart={c.sourceStart} x={0} y={0} width={W} height={H} fit="cover" />
        </group>
      ))}
    </sequence>,
    { at: 0, dur: bodyEnd, name: "montage-body" },
  );

  // ---- Beat 2a: title-card scrim, its OWN compose call - never a flex child of the text
  // column (see bug #2 above: a rect child in a <column> gets flowed, not just painted behind). ----
  p.compose(
    <rect
      x={0}
      y={H - 670}
      width={W}
      height={670}
      fill={{
        kind: "linear",
        angle: 90,
        stops: [
          { offset: 0, color: "rgba(0,0,0,0)" },
          { offset: 1, color: "rgba(0,0,0,0.72)" },
        ],
      }}
    />,
    { at: 0, dur: TITLE_CARD_DUR, name: "title-scrim" },
  );

  // ---- Beat 2b: the title text itself, composed on top of the scrim ----
  p.compose(
    <column x={80} y={H - 560} width={W - 160} gap={16}>
      <text
        fontFamily={TITLE_FONT}
        fontSize={80}
        color="#FFFFFF"
        lineHeight={1.08}
        strokeColor="rgba(0,0,0,0.4)"
        strokeWidth={3}
        motion={{ by: "word", from: { y: 40, opacity: 0 }, overlap: 0.6, easing: "house" }}
      >
        {`Creating a professional commercial for ${CONFIG.subject}`}
      </text>
      {CONFIG.useAiTag && (
        <text
          fontFamily={BODY_FONT}
          fontWeight={600}
          fontSize={40}
          color="rgba(255,255,255,0.7)"
          animate={[{ property: "opacity", from: 0, to: 1, at: 0.4, duration: 0.35, easing: "house" }]}
        >
          With AI
        </text>
      )}
    </column>,
    { at: 0, dur: TITLE_CARD_DUR, name: "title-card" },
  );

  // ---- Beat 3 (optional): one calm context label, never in the last 4s of the body ----
  if (CONFIG.locationLabel) {
    const labelAt = Math.min(4.5, Math.max(TITLE_CARD_DUR, bodyEnd - 7));
    p.compose(
      <row x={60} y={H - 220} width={W - 120} padding={16} fill="rgba(0,0,0,0.6)" radius={10} gap={10}>
        <text fontFamily={BODY_FONT} fontWeight={700} fontSize={30} letterSpacing={2} color={GOLD}>
          {CONFIG.locationLabel}
        </text>
      </row>,
      { at: labelAt, dur: 3, name: "location-label" },
    );
  }

  // ---- Beat 4: brand outro - logo assembles, wordmark cascades in, lockup holds. A quick
  // opacity fade-in on the whole outro group substitutes for a sequence transition here (the
  // outro is a separate p.compose call, not part of the body's <sequence>), so the cut from the
  // climax clip into the brand card isn't a jarring hard cut either. ----
  p.compose(
    <group
      name="outro"
      width={W}
      height={H}
      x={0}
      y={0}
      animate={[{ property: "opacity", from: 0, to: 1, duration: 0.25, easing: "house" }]}
    >
      <rect x={0} y={0} width={W} height={H} fill={CHARCOAL} />
      <group
        name="lockup"
        width={520}
        height={420}
        x={(W - 520) / 2}
        y={(H - 420) / 2}
        origin="center"
        animate={[{
          property: "scale",
          keyframes: [
            { at: 0, value: 0.85 },
            { at: 0.5, value: 1.04, easing: "ease-out" },
            { at: 0.7, value: 1 },
          ],
        }]}
      >
        <media file={logo} x={110} y={0} width={300} height={300} fit="contain" />
        <text
          x={0}
          y={330}
          width={520}
          align="center"
          fontFamily={TITLE_FONT}
          fontSize={56}
          letterSpacing={6}
          color="#FFFFFF"
        >
          COMMERCIAL CUTS
        </text>
      </group>
    </group>,
    { at: bodyEnd, dur: OUTRO_DUR, name: "outro" },
  );

  // ---- Proof frames before the real render - look before you render (SKILL.md rule). This
  // is exactly what caught bug #2 above - always actually look at these, don't just check the
  // build exits clean. Sample points now also cover each transition boundary and a mid-zoom
  // frame so the Ken Burns + transitions fix is actually visible, not just present in the code. ----
  await p.frame(0.1, "renders/proof-open.png");
  await p.frame(2.0, "renders/proof-title.png");
  await p.frame(6.4, "renders/proof-t1.png"); // clip_00 -> clip_01 fade
  await p.frame(11.2, "renders/proof-t2.png"); // clip_01 -> clip_02 grow
  await p.frame(14.1, "renders/proof-t3.png"); // clip_02 -> clip_03 slide-left
  await p.frame(19.7, "renders/proof-climax.png"); // clip_05 hero push
  await p.frame(bodyEnd + 1.5, "renders/proof-outro.png");

  await p.render("renders/commercial_cuts_final.mp4", {});

  // The render's audio track comes out as Opus, which some platforms handle inconsistently
  // in an MP4 container. Re-mux to AAC before publishing/uploading:
  //   ffmpeg -y -i renders/commercial_cuts_final.mp4 -c:v copy -c:a aac -b:a 128k renders/commercial_cuts_final_aac.mp4
}
