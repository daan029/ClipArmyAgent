// commercial_cuts/template.edit.jsx
//
// The executable version of STYLE_GUIDE.md (same folder) — every Commercial Cuts video is
// built by copying this file, filling in CONFIG, and running it. Everything outside CONFIG
// is fixed house style and shouldn't change per video; if a video genuinely needs a
// structural change, update STYLE_GUIDE.md too so the two stay in sync.
//
// VERIFIED 2026-09-07 against a real render (Moco Museum Barcelona, 6 clips, 16s) inside
// Higgsfield's `higgsedit` sandbox via a Claude Code session's `sandbox_exec` — this does NOT
// run locally, there is no higgsedit CLI on this Windows machine. Real build steps, in order:
//   higgsedit init <projectDir> --size 1080x1920 --fps 30
//   higgsedit fonts add <projectDir> "Anton" "Inter:400" "Inter:600" "Inter:700"
//   higgsedit build <projectDir>/edit.jsx
// (the earlier version of this file only said "run higgsedit build edit.jsx" - init and
// fonts add are required first or the build fails with "no project.json"/font-not-vendored.)
//
// Two real bugs fixed by that verification pass, both silent/non-obvious:
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
  clips: [
    { video: "media/clip_00.mp4", audio: "media/clip_00.mp3", sourceStart: 0, dur: 4.0 },
    { video: "media/clip_01.mp4", audio: "media/clip_01.mp3", sourceStart: 0, dur: 2.2 },
    // ...one entry per clip used in the montage. sourceStart is seconds into that clip's own
    // file - 0 if you pre-trimmed each clip to just its used segment (simplest), or the real
    // in-clip offset if you imported longer source files directly.
  ],
  logo: "media/logo.png", // gold CC monogram
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

  // ---- Beats 1 + 3: the whole montage body. Every visible frame is a composed <media> -
  // required so the brand LUT (a pixel-program effect, media-only per compose.md) can be
  // applied uniformly once a real LUT file exists. Audio is the spine, kept in sync via the
  // same sourceStart per clip. ----
  let t = 0;
  for (let i = 0; i < CONFIG.clips.length; i++) {
    const c = CONFIG.clips[i];
    p.cut(audioHandles[i], { at: t, from: c.sourceStart, dur: c.dur });
    p.compose(
      <media
        file={videoHandles[i]}
        trimStart={c.sourceStart}
        x={0}
        y={0}
        width={W}
        height={H}
        fit="cover"
      />,
      { at: t, dur: c.dur, name: `clip-${i}` },
    );
    t += c.dur;
  }
  const bodyEnd = t;

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
        stroke={{ color: "rgba(0,0,0,0.4)", width: 3 }}
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

  // ---- Beat 4: brand outro - logo assembles, wordmark cascades in, lockup holds ----
  p.compose(
    <group name="outro" width={W} height={H} x={0} y={0}>
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
  // build exits clean. ----
  await p.frame(0.1, "renders/proof-open.png");
  await p.frame(2.0, "renders/proof-title.png");
  await p.frame(bodyEnd + 1.5, "renders/proof-outro.png");

  await p.render("renders/commercial_cuts_final.mp4", {});

  // The render's audio track comes out as Opus, which some platforms handle inconsistently
  // in an MP4 container. Re-mux to AAC before publishing/uploading:
  //   ffmpeg -y -i renders/commercial_cuts_final.mp4 -c:v copy -c:a aac -b:a 128k renders/commercial_cuts_final_aac.mp4
}
