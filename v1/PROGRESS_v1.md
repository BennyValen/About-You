# PROGRESS — cel-animated recreation of `source/original.mp4`

## Source facts (measured)

| Property | Value |
|---|---|
| Resolution | 1080x1920, SAR 1:1 |
| Frame rate | 24 fps |
| Container duration | 166.88 s (audio stream: AAC LC 44.1 kHz stereo, 128 kb/s, 166.88 s) |
| **Video frames actually decoded** | **4004** (166.833 s) — the brief says 4005 |
| Cadence | The source animates **on twos**: every odd frame repeats the previous frame (mean frame-to-frame diff on odd frames ≈ 0.04, on even frames 3–7) |
| Fade to black at end | **None.** The last 30 frames are bright (mean RGB ≈ 189/158/167). |

**Frame count decision:** the composition is 4005 frames, as the brief requires. That is 166.875 s, which matches the 166.88 s container/audio duration. The source's video track has only 4004 frames, so my last frame (4004) continues the final shot by one frame. Every cut is on the same frame index as the source.

## Scene map (verified against `work/ref/`; cut frames measured by frame differencing in `scripts/cutdetect.py`)

All 11 detected cuts land exactly on the frames in the starter table (differences of 15x–320x the local median). All cuts are hard cuts.
Camera speed comes from phase correlation in `scripts/motion.py` (px per frame at 1080 wide). In every scene the camera follows the traveler "up" the frame, and the background scrolls down.

| # | Frames | Time (s) | Verified content | Camera (bg scroll) | Red thread |
|---|---|---|---|---|---|
| 1 | 0–293 | 0.00–12.25 | Night snowy pine forest from straight above (blue-violet snow, star-shaped conifers with white snow tips). A dark train with 3 carriages sits lower-center (y≈0.52–0.89 of height). Warm orange window light spills onto the snow on both sides. **Correction:** the long white "plume" is the locomotive's **headlight beam / lit mist** lighting the track ahead (up the frame), with the ties visible inside it. Fog banks drift across. A dark frozen pond enters top-left around f200. | follow up, ~6.25 px/f | yes, from the last carriage to the bottom |
| 2 | 294–607 | 12.25–25.33 | Fingerprint-like contour ridges (raised, shadowed) from lime to deep green, with teal-blue patches later. Vertical ballast track with rails and ties at center. White modern train (3 cars, y≈0.51–0.89). Round dark-green bushes, small pale rocks. Rings morph fast until ~f413 (17.2 s), then slowly, with mist passing. | follow up, ~7 px/f | yes |
| 3 | 608–953 | 25.33–39.75 | Dark green pond. Large lily pads (lime to green, with radial veins) crowd left and right, leaving a channel in the middle. Some pads are dark and submerged. Wooden rowboat centered (y≈0.53–0.70), one rower in blue, two oars. Pale koi glide between the pads. | follow up, ~2 px/f | yes, from the stern, wavy |
| 4 | 954–1313 | 39.75–54.75 | **Correction:** a **frozen lake at night**, not open sea. Dark blue ice with thin teal fracture lines, white wind-blown snow drifts (right side), vertical strings of frost bubbles, and a pink/gold aurora reflection band across the upper third. A **skater** in a white coat is centered (y≈0.6), with a shadow to the lower-left and white skate scratches. | follow up, ~5 px/f | yes |
| 5 | 1314–1673 | 54.75–69.75 | Orange sand with dense fine wavy striations. Meandering purple (shadowed) dune bands left and right. **Camel with rider** (y≈0.55–0.66) with a long purple camel shadow cast to the **right**. Two lines of footprints trail down to the bottom. | follow up, ~3 px/f | yes, along the footprints |
| 6 | 1674–2077 | 69.75–86.58 | **Correction:** pale white-cyan sandy shallows with winding deep-turquoise channels. The "islands" are **coral heads** (purple, orange, green clusters). Sea turtles and small starfish. A slate manta ray glides upper-left of the boat. A wooden boat with a white sail (to the right) and a sailor in navy; the boat/sail shadow falls on the seabed to the right; a wake trails behind. | follow up, ~3.5 px/f | yes |
| 7 | 2078–2491 | 86.58–103.83 | Grey-blue rocky terrain, ochre/yellow lichen plateaus, orange rust patches, wispy clouds, winding thin grey tracks. A teal paraglider canopy centered (y≈0.61). Two brown birds upper-right. The glider's shadow falls lower-left. | follow up, ~2 px/f | yes |
| 8 | 2492–2645 | 103.83–110.25 | Pitch-black sea with faint specks. A dark swimmer at center (y≈0.61) with a glowing cyan bioluminescent wake trailing down. | very slow, ~1 px/f | yes, inside the wake |
| 9 | 2646–2981 | 110.25–124.25 | Dark lake on the left (0–0.41 of width), beige path (0.44–0.56), lawn on the right. Big fluffy round trees (lime to green) with dark shadows, lily pads along the shore, a small dock and benches. Cyclist on the path (y≈0.6). | follow up, ~4 px/f | yes |
| 10 | 2982–3315 | 124.25–138.17 | Vertical dirt path. A walker (y≈0.61) with a very long shadow to the lower-left. A harvested golden field top-left with a diagonal row of 5 round hay bales and a tree with a huge shadow. A diagonal dirt road crosses the frame, rising to the right. Sunflower rows right and lower-left. | follow up, ~3 px/f | yes |
| 11 | 3316–3647 | 138.17–152.00 | Peach-lavender cumulus with deep blue-violet gaps (the gaps widen over the scene). **Correction:** a V-formation of **white cranes with black wingtips** (not paper birds). The lead crane is at center (y≈0.62); bird shadows fall on the clouds. | follow up, ~5 px/f, easing out near the end | yes, from the lead crane |
| 12 | 3648–4004 | 152.00–166.88 | **Correction:** pink-lavender **tidal flats**: glossy shallow water with a warm sun glare, sandbars with ripple texture, and purple branching tidal channels. A walker in blue with a long shadow to the lower-left; small white gulls. **From ~f3900 a second figure walks in from the top. The thread runs bottom → traveler → second figure → top edge, and they meet.** **No fade to black** (removed; the source has none). | follow ~8 px/f, then slows and holds | yes, also continues above the traveler at the end |

## Technical path

- **3D path taken (worked on the first attempt):** Remotion 4.0.532 + `@remotion/three` (`ThreeCanvas`) + three.js r186 + `@react-three/postprocessing` 3.1.3, rendered headless with `--gl=angle` on the RTX 3050.
- One `ThreeCanvas` for the whole film. `Main.tsx` picks the scene by frame (hard cuts), and the post chain (Bloom + custom `FinishEffect`) persists across scenes so the grade is continuous.
- Hero objects (trains, boats, figures, animals, gliders, trees, bales) are three.js meshes with `MeshToonMaterial` and a 3-step gradient map, plus an inverted-hull ink pass whose width varies along the line and per drawing, plus planar cel shadows (multiply + stencil).
- Painted backgrounds are world-anchored GLSL planes: flat fills, hard 3-step cel shading of procedural height/normal fields, SDF ink bands, and brush-stroke texture from anisotropic noise masked into strokes.
- On twos: `uBoil` and every character/line-work pose use `onTwos(frame)`. The camera, and the painted backgrounds it moves over, run at 24 fps.
- Gotcha fixed: `EffectComposer` builds asynchronously, so a `WarmupGate` holds each scene's first frame until the composer has drawn.

## Status

| Step | Status |
|---|---|
| Reference extraction + analysis | done (`work/ref/`: one frame per second at exact frame indices, 5 frames around each cut, per-scene sheets) |
| Kit (seeded noise/GLSL lib, toon + ink hull + planar shadow materials, on-twos helper, camera rig, verlet thread, post/grade) | done |
| Scene 1 night train | pass 3 done: forest, corridor, headlight, warm window pools, fog, pond at f≈200, thread |
| Scene 2 contour forest | pass 3 done: fingerprint hedges (smooth-min distance rings), fast morph until local f119 then slow, bushes, rocks, white train, mist, thread |
| Scene 3 lily pads | pass 3 done: layered veined pads (dark submerged + floating), koi under pads, toon rowboat with animated oars (on twos), ripples at the catch, wavy thread |
| Scene 4 frozen lake | pass 2 done: streaky ice, teal cracks, bubble clusters/strings, wind-blown snow, screen-fixed aurora reflection (additive, blooms), skater with stride on twos + long shadow |
| Scene 5 desert | pass 3 done: tanh-warped striation field bunching into purple lee bands, 3D toon camel + rider with walk cycle on twos, tinted planar side-profile shadow (sun from the left), footprints, thread |
| Scene 6 lagoon | pass 3 done: noise zero-set channels with stepped depth, crusty mottled coral heads, starfish, turtles, foam wake, heeled sailboat with billowed sail mesh + hiking sailor, seabed shadows (depth-offset tint), manta gliding upper-left |
| Scene 7 canyon | pass 5 done: lit height-field rock (3-step), lichen plateaus (mottled voronoi), dark valleys, rust, single winding road, cloud wisp layers, crescent canopy of airfoil cells (per-cell colour), birds flapping on twos, glider shadow |
| Scene 8 night swim | pass 2 done: near-black water with twinkling plankton, swimmer-anchored additive wake with flowing turbulence drifting right, hand splash glow, dark swimmer silhouette with stroke on twos |
| Scene 9 lake path | pass 3 done: streaky lawn, beige path, dark lake with reflection strokes + shore reeds + lily pads, dock, fluffy trees from instanced spiky toon clumps with fur shading + planar shadows, benches, cyclist pedalling on twos |
| Scene 10 sunflowers | pass 3 done: sunflower rows on dark soil (petal heads + grey-olive leaves), striped stubble field with a top edge, diagonal road with ruts + stones, straw-edged path, 3D spiral-topped bales, fluffy tree, low-sun long tinted shadows, walker on twos |
| Scene 11 cranes | pass 3 done: cumulus from cel-shaded dome puffs at two scales inside a thinning cover mask (gaps widen), V of 7 toon cranes (broad white wings, black primaries, neck, legs) flapping on twos at measured screen positions, tinted shadows on the cloud tops, camera easing to a stop |
| Scene 12 tidal flats | pass 3 done: lavender glossy flats with wind streaks, ripple sandbars + soft dendritic creeks + pools, screen-fixed warm sun glare (additive), walker in blue on twos, camera eases to rest (local 250→330), second figure walks in from the top (local 262→356) and they meet; three thread segments (bottom→walker→second figure→top edge); gulls; no fade (matches source) |
| Whole-film contact sheet review (stills) | done; fixes after it: lamp-lit fog in scene 1, bigger/whiter cranes in scene 11 |
| Preview render 540x960, every 2nd frame (`work/preview.mp4`) | done, 2003 frames, no errors |
| Cut check on preview (`scripts/check_cuts.py`) | **all 11 cuts detected exactly at 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648** |
| Final render (`work/video_silent.mp4`, h264 CRF 16 yuv420p, `--gl=angle`, concurrency 6) | done in ~8 min, 4005 frames, no errors (1.2 GB: per-frame film grain at CRF 16 compresses poorly) |
| Mux (`-map 0:v -map 1:a -c copy`) -> `out/final.mp4` | done |
| Verification (`scripts/verify.py`) | **ALL PASS**: 1080x1920, 24/1 fps, 4005 frames, video 166.875 s / container 166.8818 s = source 166.8818 s, audio MD5 `91bd76fb53f7c072fcd45c4bf188c0a3` identical on source and final |
| Cut check on final (`scripts/check_cuts.py out/final.mp4`) | all 11 cuts exactly on the source frames |
| Deliverables | `out/final.mp4`, `out/contact_sheet.jpg`, `README.md` |

## Decisions and notes

- **4005 vs 4004 frames:** the composition is 4005 frames as required. The source video stream has 4004, so frame 4004 is a continuation of the final shot (both figures standing together).
- **No fade to black:** the brief's table asked for one, but the source ends on a bright frame, so I followed the source. To add one, set `fade` in `S12TidalFlats.grade()`.
- **Red thread:** present in all 12 scenes, as in the source.
- **On twos vs. the source:** the source is entirely on twos (camera included). Per the brief, my camera and the backgrounds it moves over run at 24 fps; drawings, poses, line boil, thread, creatures and the scene 2 ring morph change every 2nd frame.
- **Camera speeds** were measured per scene by phase correlation, and each recreation follows the measured px/frame.
- **Hard rules:** no text, UI or emoji in the video. No photographic textures and no source pixels (the source is only read by the analysis/comparison scripts under `scripts/`, never by the Remotion project).
