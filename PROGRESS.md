# PROGRESS — v2 rebuild (Blender, cel look over real 3D)

v1 (Remotion/three.js, flat procedural shapes) was rejected. Its notes are in `v1/PROGRESS_v1.md` and the video is `source/v1_recreation.mp4`.

## Hard requirements: how they're met

| Requirement | Approach |
|---|---|
| Audio bit-for-bit | `work/original_audio.m4a` extracted with `-vn -c:a copy` and muxed with `-c copy`. No `-shortest`; the audio keeps its full 166.88 s. Renders are silent. The MD5 and ffprobe audio fields are compared in `out/gates_report.md`. Analysis outputs (demucs stem, transcripts) stay in `work/` and are never muxed. |
| 1080x1920, 24 fps, **4004** frames, cuts at 294 … 3648 | `blender/kit/core.py` CUTS. Each scene renders only its own frame span; `scripts/assemble.py` builds exactly 4004 frames. |
| On twos | The original is entirely on twos: each odd frame repeats the even one (measured, camera included). v2 renders one drawing per even frame and the assembler holds it for two frames. That matches the source and guarantees planted feet. |
| No source pixels | The source is read only by `scripts/` (analysis/QA). The Blender scenes never load it. |
| No text/logos | none |

## Engine decision (benchmark)

Benchmark: scene 3 layout (water, 350 lily pads, boat, rower, Freestyle, compositor) at 1080x1920 on the RTX 3050 Laptop (4 GB):

| Engine | s/frame | Notes |
|---|---|---|
| EEVEE Next, 16 samples, Freestyle + Kuwahara + glare | **1.6 s** | Shader-to-RGB works, so the 3-step toon is possible |
| Cycles, 24 samples + OptiX denoise | 4.7–5.5 s | **No Shader-to-RGB in Cycles**, so no cel banding |

**Chosen: EEVEE Next, 8 samples.** Real scenes measure 3.5–7 s per drawing at full res (scene 12: 4.2 s without Freestyle, 6.4 s with). 2002 drawings ≈ **3–4 h**, plus 15–40 s build per scene. The laptop GPU throttles to about 20–45 W, which accounts for the spread.

Lessons:
- Hundreds of separate objects carrying modifiers cost 80 s per frame, so all scatter uses geometry-nodes instancing.
- Large blurred compositor masks are replaced by analytic masks.
- Relative output paths resolve to the drive root, so the kit uses absolute paths only.

**Preview decision:** a full half-res preview costs nearly as much as the final render (EEVEE overhead dominates). Instead, every scene got short quarter-res **motion calibration windows** (2 s each, `work/calib/`), scene 12 got full half-res passes with all gates, and the gates run again on every final scene render.

## Analysis — done

- `work/ref4/` (4 frames per second, 669 frames) and `work/scene_notes/01–12.md`: environment, materials, subjects, light, palette and thread notes for each scene, with crops in `work/scene_notes/crops/`.
- `work/camera.json`: plain phase correlation is fooled by the source's screen-fixed glare and canvas texture (it falsely reports camera stops in scenes 11 and 12). Final numbers come from band-pass phase correlation plus cluster KLT. The per-frame profiles used by the camera rig are in `work/cam_profile.json`.
  - Scene 3 surges with a 60-frame rowing stroke.
  - **Scene 11 moves at a constant 4.97 px/frame up to the cut.**
  - **Scene 12** runs 8.4 → 13.7 px/frame, then eases to a stop at about frame 3960 while both people keep walking.
- `work/story_notes.md`: your reading is confirmed. B first appears at frame ~3930 (163.75 s). Earlier red at the top edge was viewed and is ballast, sand striations or lichen. Corrections: scene 4 is a skater, scene 5 a camel rider, scene 11 cranes.
- `work/lyrics.txt`: demucs vocal stem → faster-whisper medium. A love song about remembering someone ("…when I need to remember your face… do you think I have forgotten about you?"), with a lyric-to-scene table in the story notes.

## Kit (`blender/kit/`)

| Module | Contents |
|---|---|
| `core.py` | scene reset, sun from a direction vector, top-down camera rig driven by the measured speed profiles (screen↔world per height), resumable render loop |
| `look.py` | **one switchable look pass**. A shared `CelSurface` node group: 3-step Shader-to-RGB toon, brush-stroke paint with per-drawing boil, optional practical-light tint/glow, and an internal `LOOK` value that flips every material to Principled BSDF. Freestyle hero ink: tinted per material, tapered, noise width, line boil re-seeded per drawing. Compositor: anisotropic Kuwahara paint filter, pass-based tinted ink, bloom, anamorphic streaks, edge DOF, CA, lift/gamma/gain, vignette, grain. |
| `thread.py` | 200-segment Verlet cord with ground (friction, surface-dependent), water (buoyancy, drag, flow field) and air (drag, wind) modes, plus currents. Constant 3.4–3.6 px screen thickness. Per-frame endpoint/visibility log. |
| `human.py` | skeleton + skin-modifier garments, head and hair, two-bone IK, **planted-foot walker** (stance feet fixed in world space; stride from speed) |
| `boats.py` | lofted clinker rowboat, oars, rowing solver (catch → drive → release → recovery, feathering), ripple rings at each catch |
| `vehicles.py` | bicycle (wheel ω = v/R, cranks geared 2.6:1, feet on the pedals by IK), train cars (bogies, window strips, roof fans/boxes) |
| `creatures.py` | koi (travelling body wave), manta (travelling wing wave), turtle (flipper strokes), crane (two-segment wings, black primaries, flap cycle) |
| `geo.py`, `paths.py` | numpy meshes, terrain, geometry-nodes instancing with per-instance tint, Poisson scatter, knobbly/spiky organic blobs, stateless wake particles, smoothed key paths |

## Scenes

| # | Script | Key physics/detail | Motion calibration (2 s window ratio) |
|---|---|---|---|
| 1 | s01 | instanced spruces with snow-tipped tiers, train cars with real area window lights (orange light tint), headlight spot + painted beam, drifting fog, cord on the track bed | 1.23 → boil reduced |
| 2 | s02 | **displaced contour-hedge geometry re-drawn on twos** (smooth-min ring field, fast morph to f413 then slow), ballast bed, instanced bushes/rocks, white modern train, mist | 1.17 |
| 3 | s03 | ~900 instanced veined lily pads + submerged dark pads, koi with body wave, clinker rowboat with oars on the rowing solver (stroke 60 f), pitch/roll/heave, catch ripples, floating cord | 1.05 |
| 4 | s04 | translucent ice, cracks, frozen bubbles, snow drifts, camera-locked aurora reflection, skating stride, coat flutter, cord sliding on ice (low friction) | 1.57 → reworked |
| 5 | s05 | asymmetric dune heightfield (windward/lee), meandering ripple striations, camel pace gait with planted feet, rider, persistent footprints, cord dragging | 1.08 |
| 6 | s06 | seabed depth field with channels, caustics, crusty coral, starfish, turtles, manta, heeled sailboat + billowed sail + hiking sailor, wake foam particles, floating cord | 1.14 |
| 7 | s07 | lit terrain, lichen plateaus, rust, tracks, drifting cloud wisps (two layers), crescent ribbed canopy (breathing, pendulum swing), pilot, hawks, cord streaming in the headwind | 0.45 → reworked |
| 8 | s08 | black sea, crawl-stroke swimmer, stateless bioluminescent particles from hands/feet, turbulent glow wake, glow light, floating cord | 6.56 → reworked |
| 9 | s09 | lake with reflections + lily pads, path, lawn, spiky-foliage trees with long dappled shadows, benches, dock, bicycle kinematics | 0.91 |
| 10 | s10 | instanced sunflowers (petals, discs, leaves) facing the low sun and swaying in gusts, stubble field, diagonal road, spiral bales, tree, walker, cord on the path | 0.95 |
| 11 | s11 | cauliflower cumulus heightfield + dome bump, gaps to the world below, boid-integrated V of cranes with flap cycles, cord streaming from the lead crane, constant camera | 1.08 |
| 12 | s12 | A/B choreography from measured tracks, two independent cords (A down, B up, never joined), sandbars from the reference mosaic, dendritic creeks, ripple marks, camera-locked glare, gulls | full gates **PASS** at half res (motion 0.96–1.29 every second; thread 0 issues) |

## Status — complete

- All 12 scenes rendered at 1080x1920 (drawings on twos), assembled to 4004 frames, original audio stream-copied: `out/final.mp4`.
- **Final gates (`out/gates_report.md`): audio PASS (MD5 identical + identical ffprobe audio fields), video PASS (1080x1920, 24/1, 4004 frames), cuts PASS (all 11 on the expected frames), motion PASS (every second 0.75–1.3, no stalls), thread PASS (all 12 scenes).**
- Per-scene gate reports: `work/gates/final_sXX.txt`. Contact sheet: `out/contact_sheet.jpg`.

### Render-time fix
Freestyle builds its view map from every object in the view layer, which made frames take 10–19 s. The hero ink now runs on a separate `INKLAYER` view layer that contains only the INK collection. Occlusion by the environment is restored in the compositor: hero pixels whose main-layer depth is closer than the ink-layer depth are masked, dilated by 4 px. Same look, **1.6–3.2 s per drawing** at full res. Scenes 12, 3, 6 and 10 were rendered before this change, with Freestyle over the full scene; all other scenes use the ink layer.

### Thread gate (v2)
The pixel gate traces each cord in the render, row by row along the crimson line, from its owner's attach point (from the simulation log) to the frame edge where its free end lies. It allows short occlusions (≤ 50 rows: foam, hull, wings, head) and the softened last 45 px at the edge DOF. Any long crimson curve not on a traced cord counts as an unowned thread. The crimson test excludes orange (G ≫ B), so rust and lichen in scene 7 don't register.

### Tuning made during the gate runs
- Scene 2: lower ring contrast, finer rings (0.5 m), hedges cleared from the track corridor, faster early morph, lighter paint filter.
- Scene 4: lower crack/bubble/snow contrast.
- Scene 7: larger-scale terrain with rock mottling, faster cloud wisps, lighter paint filter.
- Scene 8: no grain, calmer wake boil, cord lifted above the glow veil.
- Scene 9: lighter paint filter.
- Scene 11: the cord streams in the flock's relative wind above the cloud tops (it had sunk into the clouds); the tail crane moved off the cord line.
- Scene 1: window light reduced (it blew out).


---

# v3 fix pass (brief: `work/brief_v3.md`)

## Section 0 — audio (done first, 2026-10-05)

- `source/v2.mp4` does not exist in this project. The v2 delivered by this pipeline is `out/final.mp4`, so the repair command was run with it as input:
  `ffmpeg -y -i out/final.mp4 -i source/original.mp4 -map 0:v:0 -map 1:a:0 -c copy -movflags +faststart out/v2_audio_fixed.mp4` → **`out/v2_audio_fixed.mp4` delivered** (video packets identical to v2, MD5 304979a8…).
- Audio packet MD5s (`-map 0:a -c copy -f md5 -`):

  | file | packet MD5 |
  |---|---|
  | source/original.mp4 | 2632a579c1377d79222ccb4e5300ad9e |
  | out/v2_audio_fixed.mp4 | 2632a579c1377d79222ccb4e5300ad9e |
  | out/final.mp4 (v2 as rendered here) | 2632a579c1377d79222ccb4e5300ad9e |
  | work/original_audio.m4a, v1/final_hevc.mp4, source/v1_recreation.mp4 | 2632a579c1377d79222ccb4e5300ad9e |

- **Cause search:** no `-c:a`, `aac`, `-shortest`, fade or normalization anywhere in `scripts/` or `blender/`. Renders are silent PNGs, and the only mux was `-map 0:v -map 1:a -c copy` from a `-c:a copy` extraction of the original. The v2 file in `out/` was already bit-identical. Running the brief's speed/dup script on it also gives **exactly 50% duplicate pairs in every scene**, not "no repeated frames in scenes 1, 2, 5, 6".
  The file that was measured was therefore most likely a lossy re-encode made after delivery: v2 was 881 MB, and the v1 request was for under 400 MB. A re-encode gives about 20 dB audio SNR and re-codes the held drawings so they are no longer near-identical, which also lowers the per-step speed ratio.
- **Hardening anyway:**
  - `scripts/assemble.py` now muxes directly from `source/original.mp4` (`-map 0:v -map 1:a -c copy`, no intermediate .m4a). It re-hashes the audio packets after the mux and exits non-zero on a mismatch.
  - `scripts/verify_final.py` uses packet MD5 (`-c copy -f md5`) and prints both hashes into `out/gates_report.md`.
  - The final delivery will also be kept small enough that nobody needs to re-compress it.
- Speed/dup gate script from the brief saved as `scripts/qa/speed_parity.py`. On v2 (`out/final.mp4`): ratios s1 1.18, s2 1.13, s3 1.23, s4 1.03, s5 1.00, s6 1.25, s7 1.20, s9 1.10, s10 1.29, s11 1.26, s12 1.27; dup 0.50 everywhere. The v3 target of 0.9–1.1 is checked against the actual output file.

## Measurement (section 2) — done
- `work/thread_stats.json` (`scripts/analysis_thread_stats.py`): crimson line mask (local red contrast + crimson hue; a green-darkness variant for the orange sand in scene 5) → bottom-up row trace from the frame edge to the owner → lateral deviation from the owner–exit chord, curvature, inflections, and sway (detrended deviation at 1/2 and 3/4 of the chord, sampled per drawing at 12 Hz).
  Original RMS deviation (px at 1080): s2 2.3, s3 8.0, s4 16.5, s5 3.3, s6 6.5, s7 6.3, s9 3.8, s10 7.7, s11 6.5, s12 10.3. Scenes 1 and 8 are mostly hidden, so they use the film median (6.5 px, 0.30 Hz). Sway is 0.13–0.9 Hz.
- Camera: the measured per-frame profiles (`work/cam_profile.json`) are kept. The rig moves every frame, but only even frames are rendered, so the camera steps at 12 Hz.
- Light directions and subject crops: `work/scene_notes/`. The v3 side-by-side 1:1 crops are written by `scripts/qa/look_crops.py` into `work/v3/crops/`.

## Thread system (section 4) — done
- `blender/kit/rope.py`: world-space rope, 260 segments, length = 2 screen heights.
  - Dynamic follow-the-leader inextensibility with velocity correction.
  - Small bending stiffness, which is not applied where ground friction holds the rope, so a laid trail keeps its shape.
  - Curl-noise wind/current field with gusts and a travelling lateral meander.
  - Contact models: ground (friction), ice (low friction), water (floats, viscous drag toward the current), air (low drag).
- `blender/kit/rope_cfg.py`: per-scene environment and owner motion (gait sway plus path weave / boat yaw / skating S-curve / pendulum swing). The scenes move the hero body with the same weave, so the attach point stays on the body.
- `scripts/tune_rope.py` tunes this offline against the original's RMS and sway frequency. All 12 scenes land within ±40% in the harness (e.g. s3 6.9/8.0 px, 0.17/0.20 Hz; s12 10.4/10.3 px, 0.72/0.67 Hz).
- The thread is drawn in the 2D post (`scripts/post/paint.py`) from the projected rope (`thread.npz`), and hidden only under the owner's hero mask:
  - tapered 4 → 2.5 px, anti-aliased, with a highlight on the lit side;
  - a short offset cast shadow along the scene light (longer where the rope is off the ground);
  - a faint glow in the dark scenes;
  - a tiny per-drawing hand wobble.
- `thread_log.json` per drawing: owner end, free end (always beyond the frame), visible length, max segment jump (pop check), segment count.

## Painting layer and on-twos clock (sections 1, 3b) — done
`scripts/post/paint.py` runs on the distinct drawings only, in parallel on the CPU, and assembly holds each drawing for two frames:
1. A world-anchored stroke layer: cells in surface coordinates from the position pass, so strokes stick to surfaces.
   - Coarse 12 px dabs, oriented along the structure tensor (the form) or the scene's flow direction.
   - Error-driven fine 5.5 px dabs where the coarse layer loses detail.
   - Bristle stripes; edge-aware, so dabs don't paint over a different colour region.
   - Per-drawing jitter: position ±1.8 px, angle ±4°, value ±8 levels, plus persistent value variation.
2. Boil: a smooth displacement field (88/54/32 px patches, ~2 px mean / ~5 px peak), reseeded every drawing. Heroes get 0.35× through the hero AOV mask. Edge wobble 0.55 px. The first drawing after each cut is not boiled.
3. The thread (above).
4. A screen-fixed canvas weave and impasto relief lit by the scene light (never boils), then per-drawing grain.
5. A luminance lock: each drawing's mean luminance equals the clean render's.

## Look changes (section 3)
- CelSurface: soft painted shading (wide shadow/highlight transitions instead of the 3-step toon), ambient occlusion, a rim light on the lit side, and a per-material Hero AOV.
- The compositor writes the hero mask and an encoded world-position pass (half res, 16-bit). Kuwahara is radius 3; grain moved to the post.
- CC0 textures (Poly Haven, 11 sets, `scripts/fetch_textures.py`, listed in CREDITS.md) are shaded through the painted look: sand, rock, scree, snow, bark, grass, soil, gravel, mud.
- Render cost: EEVEE at 2 samples. 8/4/2 samples are indistinguishable after the paint pass; scene 12 went 5.9 → 2.1 s per drawing.

## Scenes rebuilt so far (v3, test drawings checked at 1:1 against the original)
- **12** (dunes): real dune geometry with lee slip faces in shadow; anisotropic ripples bending with the dunes; CC0 grain; instanced dry grass tufts and leafless shrubs whose long branching purple shadows lie across the sand; wind-streaked flats with a warm glow; bulkier A and B (A blue jacket, B white top, long hair) with planted feet and persistent footprints; gulls; two ropes. The ending beat is unchanged.
- **5** (desert rider): a real horse (`kit/animals.py`): barrel, neck, head with ears, mane, swishing tail, four-beat walk with planted hooves, head nod. Seated rider with a wide hat and hands to the reins. The shadow is cast by the real silhouette and moves with the legs; dotted hoofprint pairs persist; dust at the hooves; irregular contour ripples.
- **4** (ice skater): push-glide skater on an S-curve with arms in counter-phase. Each blade cuts paired scratches that persist and fade over ~6 s; ice shavings at push-offs; depth-graded bubbles; crooked branching fractures with light and dark edges; CC0 snow drifts; aurora reflection; a long moonlight shadow.
- **3** (lily pond): the boat model is kept. Veined pads (26 primary and 52 secondary veins, rolled rims, wet sheen), layered and overlapping, pushed aside and bobbing near the boat; pink water lilies and buds; reeds; drifting ripples, sky sheen and glints; swirl puddles at each release; a V-wake of fading foam.
- **9** (lakeside): tree crowns built from ~6–7k individual leaf cards in clumps with light/dark variation, swaying (moving dapple); mowing stripes with CC0 grass; tufts and flower dots; gravel path with wheel marks; fallen leaves; reeds; cyclist with helmet and wobble. A stale-matrix bug (the rider lagging the bike) is fixed.
- **10** (sunflowers): one-mesh sunflowers with a painted phyllotaxis seed disc, 21–29 two-layer petals with value variation, green sepals, heart-shaped drooping leaves. Travelling sway waves; plants part near the walker. CC0 soil and mud; a leaf-card tree; a walker with a straw hat and a long shadow down the path.
- **2** (tea garden): no morph. The contour field is frozen and sampled on a fixed world lattice, so it scrolls rigidly. Leaf-dab hedge tops with dark gaps; leaf-card shade trees. 22 tea pickers (conical straw hats, coloured clothes, baskets, slow walking/bending, reaching arms). Train roof units and a pantograph.
- **1** (night train): 7 carriages with individual glowing window panes (no blown-out bars) and rim-lit dark roofs. Gentle area lights tint and shadow the crowns beside the train. A denser two-layer forest that comes up to the track; frost toned down. A translucent steam plume rising above the canopy and drifting. Headlight beam and fog kept.
- **11** (clouds): cumulus built from instanced billowy lobes (big domes, medium lobes, small cauliflower edge lobes) in three parallax layers, with wisps between and a rippled sea far below. Soft lavender shading, peach rims, AO, slow edge churn. Ten cranes that flap/glide and bank. Camera constant to the cut.
- **8** (new, moonlit ski glide): snow slope with drifts, wind ripples and CC0 snow; scattered pines with long blue moon shadows. Carving S-turn skier (red jacket, helmet, skis, poles with pole plants) with a warm headlamp pool. Persistent twin tracks with moonlit rims; powder spray at the turns with twinkling crystals. The thread has ice-crystal glints. Dark palette, camera 4 px/frame on twos.
- **6** (lagoon): coral heads built from leafy clumps with per-clump coral colours, palm-frond fans and pale sand halos. Manta rebuilt (swept pointed wings, rolled cephalic fins, two-tone body) gliding over the reef. Three swirling fish schools; sail panels; subtler wake.
- **7** (canyon): numpy-eroded heightfield (ridged relief, thermal erosion, D8 flow-accumulation gullies). Strata bands, ochre lichen plateaus, rust, CC0 rock and scree, scrub and boulders, rutted dirt tracks from baked track distance, valley haze, cloud-wisp shadows. Paraglider with suspension lines. The canopy is kept.

## Render benchmark and final render (section 6)
Full resolution, EEVEE 2 samples, two Blender processes in parallel on the RTX 3050 (GPU at 100%, ~39 W). Combined throughput is 0.78 drawings/s, about 45 min for all 2002 drawings plus builds. The painting post runs on the CPU while the next scene renders (~2.5 s per drawing per core, 4 workers per scene). Per-scene timings are in `work/final_render_v3{A,B}.log`. Test-window medians (single process): s12 2.1 s, s5 2.0, s3 1.5–1.9, s9 1.5, s6 1.5, s2 1.3, s1 1.1, s7 1.1, s11 1.1, s4 1.0, s10 1.0, s8 0.9 s per drawing.

## Gate-driven decisions
- **Canvas and impasto are faint (0.0035).** Gate 8's rigid alignment (phase correlation, whitened spectrum) locks onto any clearly visible screen-fixed texture. With the original v3 canvas (0.022/0.028) it found a 1 px "shift" instead of the true 29 px camera step, and the whole camera motion was counted as paint wiggle (12.8 px against the original's 4.0). The original's paper texture is evidently that faint too. Weave 0.004 plus impasto 0.004 plus grain 2.0 still aligns correctly (3.4 px residual at s12 f3826); 0.007 does not. The canvas stays, but faint.
- **Speed parity.** The brief's metric is mean |frame diff| per distinct step at 108x192, so it depends on texture contrast as well as camera speed. The clean renders alone score s12 1.26 and s6 1.02 at the measured camera speeds, and the paint layer adds about 0.15–0.2. Per the brief ("speed up / adjust the camera scroll"), each scene gets a camera speed factor (`work/v3/speed_scale.json`, read by `core.Rig`) from the measured ratio, and only out-of-range scenes are re-rendered.

## Final v3 delivery (2026-10-05)
- `out/final.mp4`: 362 MB, H.264 CRF 18, 1080x1920, 24 fps, 4004 frames. The audio is stream-copied from `source/original.mp4`; packet MD5 2632a579c1377d79222ccb4e5300ad9e for both files.
- 3D render time: ~65–73 min of wall time for all 2002 drawings (two parallel Blender processes), plus re-renders of scenes 12, 6, 7 and 5 at calibrated camera speeds (~45 min). The 2D paint post runs in parallel on the CPU.
- Gates (`out/gates_report.md`): audio PASS, video+cuts PASS, on twos PASS (every held pair is an exact duplicate), stalls PASS. Wiggle passes in 11/12 scenes (scene 12 0.58x). Thread shape is within ±40% in 7/12 scenes. Speed parity passes in scenes 5, 6 and 7 (the calibrated ones) and fails elsewhere.
- **Not finished, by choice (the user asked to finish fast):** camera speed calibration for scenes 1, 2, 3, 4, 9, 10, 11 and 12. The measured factors (s1 x1.31, s2 x0.74, s3 x0.50, s4 x0.76, s9 x0.68) need one more re-render of those scenes (~45 min); scenes 10, 11 and 12 need theirs measured too. With `work/v3/speed_scale.json` filled in, it is `python scripts/render_all.py 1 2 3 4 9 10 11 12`, then `python scripts/assemble.py --crf 18` and `python scripts/verify_final.py`.
- The thread-shape misses are scene 1 (mostly hidden under the train; the trace sees too few points), scene 3 (1.6x more curved), scene 5 (sways too fast, driven by the horse's gait), scene 7 (1.42x) and scene 8 (2.2x the film median; the scene is new).

Speed parity:
```
scene  speed-ratio  dup-orig  dup-ours  exact-pairs(ours)
    1        0.79 !      0.43      0.50      1.00
    2        1.27 !      0.36      0.50      1.00
    3        1.51 !      0.30      0.50      1.00
    4        1.20 !      0.41      0.50      1.00
    5        1.00      0.35      0.50      1.00
    6        1.04      0.38      0.50      1.00
    7        1.00      0.34      0.50      1.00
    8        8.71      0.01      0.50      1.00
    9        1.47 !      0.33      0.50      1.00
   10        1.77 !      0.36      0.50      1.00
   11        0.85 !      0.41      0.50      1.00
   12        1.13 !      0.34      0.50      1.00
```

Thread shape:
```
scene  rms-orig  rms-ours  ratio   sway-orig  sway-ours  ratio  sway-std-ours
    1      6.52     29.41   4.51        0.30       0.00   0.00     0.0 FAIL  (film-median target)
    2      2.26      2.59   1.15        0.41       0.52   1.28     3.7 ok
    3      8.03     12.96   1.61        0.20       0.21   1.04    25.0 FAIL
    4     16.54     16.28   0.98        0.25       0.28   1.10    21.6 ok
    5      3.28      2.91   0.89        0.30       1.15   3.84     6.7 FAIL
    6      6.50      6.85   1.05        0.19       0.19   0.99    11.5 ok
    7      6.29      8.93   1.42        0.72       0.62   0.86    13.5 FAIL
    8      6.52     14.62   2.24        0.30       0.39   1.29    22.0 FAIL  (film-median target)
    9      3.80      4.75   1.25        0.27       0.31   1.16     6.5 ok
   10      7.69      8.89   1.16        0.89       0.68   0.76     7.5 ok
   11      6.53      5.38   0.82        0.31       0.32   1.02     8.8 ok
   12     10.28     11.18   1.09        0.67       0.67   1.00    14.0 ok
```

Wiggle:
```
scene  orig  ours  ratio
    1  2.22  2.12   0.95 ok
    2  2.26  2.37   1.05 ok
    3  1.71  1.56   0.91 ok
    4  1.32  1.32   1.00 ok
    5  2.87  2.68   0.93 ok
    6  2.45  1.96   0.80 ok
    7  1.95  1.53   0.79 ok
    8  1.32  1.33   1.01 ok  (vs. scene 4: scene 8 was replaced)
    9  1.31  1.61   1.23 ok
   10  1.79  1.73   0.96 ok
   11  3.84  3.85   1.00 ok
   12  4.00  2.31   0.58 FAIL
```

---

# v4 fix pass (brief: work/brief_v4.md)

## Step 1 — measurement tools and baseline (`scripts/qa/measure_v4.py`, `work/baseline.json`)
`source/v3.mp4` did not exist, so it is a copy of the delivered v3 (`out/final.mp4`).

| scene | camera px/drawing original | v3 | target |
|---|---|---|---|
| 1 | 12.3 | 13.0 | keep |
| 2 | 14.0 | 14.1 | keep |
| 3 | 4.3 | 4.5 | keep |
| 4 | 9.8 | 9.8 | keep |
| 5 | 6.0 | 8.1 | 5.9 |
| 6 | 7.0 | 5.9 | 7.0 |
| 7 | 3.4 | 2.9 | 3.4 |
| 8 | (replaced) | 8.0 | 8 |
| 9 | 8.2 | 9.3 | 8.2 |
| 10 | 6.2 | 6.1 | keep |
| 11 | 9.8 | 3.0 | 9.8 |
| 12 | 16.8 | 16.4 | keep |

Tone (mean luma, p5, p95, sat): s1 f146 original (71.2, 36, 135, 0.41), v3 (58.6, 30, 136, 0.56). s8 f2570 v3 (36.0, 8, 52, 0.84). s11 f3482 original (158.9, 71, 234, 0.24), v3 (196.4, 73, 229, 0.19).

Hero lateral excursion per 4 s from the template tracker (seeded boxes: s7 canopy at f2300, s12 A at f3700): original s7 2.0 px, s12 2.6 px; v3 31.8 and 20.0. The original's heroes travel almost perfectly straight, more tightly than the brief's table allows (20 and 30 px), so the table is kept as the gate and the original's ~2–3 px is the aim.

The v3 scene 11 camera reads 3.0 px/drawing because the main cloud layer sat 3–30 m below the camera's reference plane, so it scrolled slower than the camera speed. In v4 the main cloud layer is the reference plane.

## Step 2 — wiggle (3.1)
- The coarse warp is gone: `boil_mode=fine` everywhere. `boil_field_fine` uses three cell sizes (24, 14, 8 px). Amplitude is (0.4 + 0.4·texture)·scale px, capped at 0.3 px on heroes, the thread and edges.
- Stroke jitter: value ±3.5, position 1.0 px, angle 2°. Canvas weave 0.0035.
- Calibration (`scripts/qa/wiggle_calib.py`, 12 drawings each), residual flow in px:

  | scene | floor | v3 | new, scale 0.4 → 1.3 |
  |---|---|---|---|
  | 5 | 1.65 | 2.95 | 1.86 → 2.79 |
  | 3 | 1.18 | 1.60 | 1.23–1.25 |
  | 9 | 1.38 | 1.44 | 1.34–1.38 |

  The Farneback residual can't see a sub-pixel fine boil on scenes 3 and 9 (the new curve is flat).
- Decision: boilScale 0.8 everywhere, 0.6 on scenes 5 and 11, which the brief says get the lowest strength. On scene 5, 0.6 gives new extra / v3 extra = 0.29. That is below the 0.5–0.6 aim, but the brief also asks for the lowest strength there; the flipbooks show the result.
- Scenes 2, 4 and 10 are not re-rendered. They were re-painted from the cached clean frames with the v4 wiggle.

## Step 3 — heroes straight (3.4)
- Every rope owner logs `hero_motion.csv` (screen anchor and yaw, from `heading_fn`).
- Scenes 2, 4 and 10 are derived from `thread_log.json`.
- Weave and gait meander are set to 0 in `rope_cfg.MOTION` (scene 4's S-curve is kept).
- Per-scene changes:
  - s3: boat yaw logged.
  - s5: heading 0.
  - s7: pendulum swing is fore-aft only.
  - s8: TURN_A 0.022 m.
  - s9: no yaw wobble.
  - s11: bird noise 0.0002, bank clamped to ±0.04 rad.
  - s12: path headings logged.
  - Walkers: hip sway 0.004.
- Ropes: wind and current fields with curl and gust. Search results are in `V4_ROPE` (rope_cfg). The thread now curves from wind, not from owner weave.
- Measured on the v4 renders:
  - s3: 0.1 px, yaw 0.0°
  - s5: 4.6 px
  - s7: 0.0 px, yaw 0.16°
  - s2: 0.7 px
  - s4: 54 px (limit 60)
  - s10: 31 px (limit 42)

## Step 4 — scene fixes
- **s5 (3.5):** the horse is one skin-modifier mesh, with legs rooted in the chest and croup and a four-beat walk; the rider is parented.
  - Hero mask: 180 of 180 drawings are one piece.
  - Shadow gate (`scripts/qa/s5_shadow_gate.py`, 12 gait phases on flat white ground with the hero hidden from the camera): one piece each.
- **s6 (3.6):**
  - Islands are placed with a clear boat channel (hull + 50 px).
  - A steering simulation (avoidance at 1.2× the summed radii, plus a hard projection) moves the manta, turtles and schools.
  - Colliders are logged per drawing in layers 1–5.
  - Results: 0 same-layer overlaps; manta area change ≤ 1.2% between drawings.
  - The manta mask splits in 6 drawings because the boat's boom crosses its tail (occlusion). The gate counts the occluding boat as hidden manta and prints both numbers.
- **s11 (3.7):**
  - Clouds are a domain-warped fbm density field (7 octaves plus billow and ridge) turned into height-field meshes.
  - Edges are an alpha cut at the density contour (interpolated, so no grid stair-steps).
  - Main layer on the reference plane (cover 0.62), far layer at z −22 (0.42), near wisps at z +1.5. The sun is at the upper left.
  - Long contour strokes: stroke_px 24, elong 3.
  - Test frames 3330–3640: mean 151–159, gaps 0.16–0.27 (mean 0.21), lavender/violet 0.26–0.37 (mean 0.31).
- **s1 (3.2):**
  - Slate palette on the snow (#495175/#656C90) and the needles (#1E253E/#3B4160), sparse frost flecks, moon rim on the crowns.
  - Seven 3 m carriages.
  - Window light is a warm pool (#E8A24A → #A57861, (1−d/200)^2.2 falloff, alpha ≤ 0.62), plus shadowless area lights for the warm gradient on the crowns, so there are no spikes.
  - Steam is a streaky ribbon along the track: 35 → 140 px over 700 px, core opacity ≤ 0.48, edges 0.15. The puffs that drifted over the train are removed.
  - Forest: Poisson spacing 3.23 m (−30%), two heights. Crowns stay ≥ 100 px from the window strips; trees near the cut are scaled down. The scene graph logs `corridor.json` (min 101 px).
  - Test frames 4–290: mean 71.6–74.2, p5 44, p95 ≤ 122, sat 0.45–0.46, max R 224–230, max G ≤ 175.
- **s8 (3.3):**
  - The cel tints act in linear light, so they are set from the palette: snow base #D8E2F0, shadow tint (0.136, 0.167, 0.316) for a shade of #56648F.
  - Neutral fill so the shadows don't turn more saturated.
  - Snow-laden star pines (#2C3764–#454F78 needles, snow on the tips), denser forest so the moon shadows cover most of the slope.
  - Headlamp #F2C98A: an additive cone plus an elongated additive pool (1.1 × 2.4 m, 3.4 m ahead), with a weak spot light.
  - Goggles and strap on the helmet. Poles trail back. Skis share the heading, so they are always parallel.
  - Grooves have ridges on both sides. A light, continuous powder spray comes off both ski tails.
  - Test frames: mean 99.5–103.6, p5 49, p95 202–205, sat 0.42–0.43.

## Step 5 — cameras (section 4)
- The v3 `speed_scale.json` no longer matched what v3 was rendered with: v3's s5 rig ran 7.96 px/drawing at "1.0". So the scales are now set from the rendered rig step and the phase-correlation reading:
  - s5 1.023
  - s6 1.02
  - s7 1.102 (reads 3.5 against 3.4)
  - s9 0.88
  - s11 1.0
- Scenes 5, 6 and 9 had been rendered with a wrong first guess, so they are re-rendered.

## Step 6 — render benchmark (section 6)
Only the changed scenes were re-rendered: 1, 3, 5, 6, 7, 8, 9, 11 and 12. Scenes 2, 4 and 10 were re-painted from the cached clean frames. Two Blender streams ran on the RTX 3050, with the paint pass (3 workers per scene) running behind on the CPU.

| scene | drawings | render (two streams) | median s/drawing |
|---|---|---|---|
| 1 | 147 | 338 s | 1.89 |
| 3 | 173 | 787 s | 3.03 |
| 5 | 180 | 594 s | 3.09 |
| 6 | 202 | 620 s | 3.07 |
| 7 | 207 | 677 s | 3.38 |
| 8 | 77 | 309 s | 3.52 |
| 9 | 168 | 496 s | 2.30 |
| 11 | 166 | 265 s (alone on the GPU) | 1.10 |
| 12 | 178 | 766 s | 2.91 |

- Wall time from the first render to the last paint: 00:22 → 01:34, about 72 minutes, within the 2 h target.
- That includes the wasted first renders of scenes 5, 6 and 9 at the wrong camera scale, and a scene 11 re-render: its camera read 8.83 px/drawing (ratio 0.90, too close to the gate edge). Scene 11 was re-rendered at ×1.08 and now reads 9.2.
- Paint pass: about 1.5 s per drawing per worker.

## Final v4 delivery (2026-10-06)
- `out/final.mp4`, 331.6 MB. The mux uses exactly the brief's command (`-map 0:v:0 -map 1:a:0 -c copy -movflags +faststart`). Audio packet MD5 `2632a579c1377d79222ccb4e5300ad9e` equals the source.
- `out/gates_report.md`: all 11 gates PASS, each with its own printout.
  - Audio packet MD5 matches.
  - 4004 frames; cuts as expected; no fades.
  - On twos in all 12 scenes.
  - Cameras within 0.94–1.06 of target.
  - Hero table all within limits; tracker excursion s7 0.0 px and s12 2.8 px (original 2.0 / 2.6, v3 31.8 / 20.0).
  - Horse and shadow are one piece.
  - Scene 6: 0 overlaps, boat clearance ≥ 70.8 px, manta area change ≤ 0.5 %.
  - Tone: s1 (72.0, 42, 120, 0.46), s8 (102.2, 48, 204, 0.42), s11 mean 153.6 with gaps 0.22 and lavender 0.30. Corridor 101 px. Window light max R 233, G 146.
  - Thread continuous, no pops.
  - Wiggle calibration printed; four flipbooks.
  - Look checklist.
- `out/contact_sheet.jpg`: original, v3 and v4 for scenes 1, 5, 6, 8 and 11, with 1:1 hero crops.
- `out/flipbook_s01/05/09/11.mp4`: original | v3 | v4, 12 drawings, looped three times.
- `out/look/v4_s01/05/06/08/11.jpg`: 1:1 crops.
- Known weak spots:
  - The scene 11 relief is smoother than the original's cauliflower texture.
  - The scene 5 horse reads paler and bulkier than the original's.
  - Scene 8 is much brighter than the original's near-black, by design of the brief.
  - Lavender in scene 11 sits right at the 30 % line (0.30).
