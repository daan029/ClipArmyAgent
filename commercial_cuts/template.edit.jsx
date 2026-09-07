// commercial_cuts/template.edit.jsx
//
// The executable version of STYLE_GUIDE.md (same folder) — every Commercial Cuts video is
// built by copying this file, filling in CONFIG, and running it. Everything outside CONFIG
// is fixed house style and shouldn't change per video; if a video genuinely needs a
// structural change, update STYLE_GUIDE.md too so the two stay in sync.
//
// IMPORTANT — this only runs inside Higgsfield's `higgsedit` sandbox (via a Claude Code
// session's `sandbox_exec`, not on this local Windows machine — there is no higgsedit CLI
// installed locally). It is written against the documented higgsedit 0.7 compose API
// (project/add/cut/compose/render, <column>/<row>/<text>/<rect>/<media>/<group> nodes) but
// has NOT yet been run through a real `higgsedit build`. The first time this template is
// used for a real video: run it, read every refusal (they name the exact node), fix this
// file, and update this comment once it's verified clean. Don't assume it's correct just
// because it reads correctly.
//
// Before running, for every clip in CONFIG.clips, pre-extract its audio once with ffmpeg —
// higgsedit's <media> node draws picture only, sound is a separate spine clip kept in sync
// via the same sourceStart offset (see SKILL.md "Footage inside a design"):
//   ffmpeg -nostdin -i clip_01.mp4 -vn -c:a aac clip_01.m4a

// ---------------------------------------------------------------------------
// CONFIG — fill in per video. Nothing below this block should need to change.
// ---------------------------------------------------------------------------
const CONFIG = {
  subject: "Moco Museum Barcelona", // -> title card: "Creating a professional commercial for {subject}"
  useAiTag: true, // show the "With AI" second line? Vary this - see STYLE_GUIDE.md, don't always show it.
  locationLabel: "MOCO MUSEUM — BARCELONA", // Beat 3 lower-third, or null to skip entirely
  lutFile: "luts/commercial-cuts.cube", // TODO: doesn't exist yet - see STYLE_GUIDE.md "Color grade"
  lutAmount: 0.85,
  // Ordered list of clips for the montage, in cut order. Slot 0 IS the cold-open shot (Beat 1)
  // - pick the single strongest shot from the campaign footage for it, even if you'd otherwise
  // cut it later. sourceStart/dur are seconds into that clip's own source file.
  clips: [
    { video: "media/clip_01.mp4", audio: "media/clip_01.m4a", sourceStart: 4.2, dur: 2.4 },
    { video: "media/clip_02.mp4", audio: "media/clip_02.m4a", sourceStart: 0.0, dur: 1.8 },
    // ...one entry per clip used in the montage
  ],
  logo: "media/commercial_cuts_logo.png", // gold CC monogram, transparent background
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

export default async ({ project }) => {
  const p = await project({ size: `${W}x${H}`, fps: 30, background: CHARCOAL });

  // Import every clip's picture + its pre-extracted audio, and the logo, once up front.
  const videoHandles = {};
  const audioHandles = {};
  for (const c of CONFIG.clips) {
    videoHandles[c.video] = await p.add(c.video);
    audioHandles[c.video] = await p.add(c.audio);
  }
  const logo = await p.add(CONFIG.logo);

  // ---- Beats 1 + 3: the whole montage body. Every visible frame is a composed <media> -
  // required so the brand LUT (a pixel-program effect, media-only per compose.md) can be
  // applied uniformly. Audio is the spine, kept in sync via the same sourceStart per clip. ----
  let t = 0;
  for (let i = 0; i < CONFIG.clips.length; i++) {
    const c = CONFIG.clips[i];
    p.cut(audioHandles[c.video], { at: t, from: c.sourceStart, dur: c.dur });
    p.compose(
      <media
        file={videoHandles[c.video]}
        trimStart={c.sourceStart}
        x={0}
        y={0}
        width={W}
        height={H}
        fit="cover"
        effects={[{ kind: "lut", params: { file: CONFIG.lutFile, amount: CONFIG.lutAmount } }]}
      />,
      { at: t, dur: c.dur, name: `clip-${i}` },
    );
    t += c.dur;
  }
  const bodyEnd = t;

  // ---- Beat 2: title card, composed on top of the opening clip(s), never its own black card ----
  p.compose(
    <column x={80} y={H - 620} width={W - 160} gap={18}>
      <rect
        x={-40}
        y={-40}
        width={W - 80}
        height={480}
        fill={{
          kind: "linear",
          angle: 90,
          stops: [
            { offset: 0, color: "rgba(0,0,0,0)" },
            { offset: 1, color: "rgba(0,0,0,0.72)" },
          ],
        }}
      />
      <text
        fontFamily={TITLE_FONT}
        fontSize={92}
        color="#FFFFFF"
        lineHeight={1.05}
        stroke={{ color: "rgba(0,0,0,0.4)", width: 3 }}
        motion={{ by: "word", from: { y: 40, opacity: 0 }, overlap: 0.6, easing: "house" }}
      >
        {`Creating a professional\ncommercial for ${CONFIG.subject}`}
      </text>
      {CONFIG.useAiTag && (
        <text
          fontFamily={BODY_FONT}
          fontWeight={600}
          fontSize={40}
          color="rgba(255,255,255,0.7)"
          animate={{ property: "opacity", from: 0, to: 1, at: 0.4, duration: 0.35, easing: "house" }}
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
        animate={{
          property: "scale",
          keyframes: [
            { at: 0, value: 0.85 },
            { at: 0.5, value: 1.04, easing: "ease-out" },
            { at: 0.7, value: 1 },
          ],
        }}
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

  // ---- Proof frames before the real render - look before you render (SKILL.md rule) ----
  await p.frame(0.1, "renders/proof-open.png");
  await p.frame(2.0, "renders/proof-title.png");
  await p.frame(bodyEnd + 1.5, "renders/proof-outro.png");

  // Prefer the Node engine for the final render once footage-heavy (see SKILL.md "Sandbox
  // budget") - run `higgsedit render <dir> --engine node --out renders/commercial_cuts_final.mp4`
  // after this build step, rather than rendering through this script's default Chrome engine.
  await p.render("renders/commercial_cuts_final.mp4", {});
};
