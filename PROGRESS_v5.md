# v5 fix pass: six targeted fixes (scenes 3, 6, 10, 11, 12)

Started 2026-10-06 ~12:05 (after the v4 delivery). The brief is in the conversation; this log records causes, decisions and every gate number.

## Approach (section 0 rules)
- **Untouched scenes (1, 2, 4, 5, 7, 8, 9):** not re-rendered and not re-encoded. The v4 silent video has an IDR keyframe on every cut (keyframes at 0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, …).
  - `scripts/splice_v5.py` stream-copies v4's segments [0, 608), [954, 1674) and [2078, 2982).
  - It encodes only the changed ranges, 608–953, 1674–2077 and 2982–4003, from the new drawings, with the v4 encoder settings (libx264 slow, CRF 18, yuv420p, 24 fps; same SPS/PPS).
  - It concatenates with stream copy, then runs the brief's mux exactly: `ffmpeg -i work/video_silent.mp4 -i source/original.mp4 -map 0:v:0 -map 1:a:0 -c copy out/final.mp4`.
- **Changed scenes:** re-rendered whole, on twos, with the same drawing pairing (even frames from each scene start). Every cached input is reused: camera speeds, rope configs except the scene 10 wind near the owner, grade, boil (`work/v4/calib`), grain. EEVEE and the paint pass are deterministic, so everything outside the edited elements reproduces v4. The regression gate measures that.
  - Rendering only the changed layers would need a compositing split the pipeline does not have. A whole-scene re-render of the five scenes takes about 20 minutes in three parallel streams. Three, not five: the 4 GB GPU cannot hold five EEVEE instances.
- **Test clips:** 1 s clips of each problem moment were rendered at half resolution and viewed before the single full-resolution pass.

## Fix 4: scene 11 birds face left for the first drawings
**Cause found.**
- `slots(f)` used `rig.screen_to_world(f, …)`, and `core.Rig` clamps every frame before the scene start to the start camera position.
- So during the 48-frame flock warm-up the target slots stood still, and the boids settled at zero world velocity.
- At frame 3316 the camera, and with it the slots, start moving at 10.7 px/drawing. The birds lag below their slots and accelerate.
- Each bird's heading was `atan2` of a single 2-frame position difference, so in the first drawings the separation forces and noise set it: 20–30° to the left.
- The catch-up motion also read as a layout jump between drawings 1 and 2. The camera itself was already constant (rig step 10.74 px every drawing).

**Fix.**
- 3 s warm-up (72 frames) with the camera extrapolated backwards at its scene speed, so the flock is in steady state at drawing 0.
- Initial velocity set to the slot velocity.
- Headings from velocity smoothed with a 0.35 s time constant, initialised forward. The bank is derived from the smoothed heading.
- The thread anchor and the logged hero heading use the same smoothed headings.
- Formation, bird models, flapping, clouds and thread physics are unchanged.

**Test clip (half resolution, first 12 drawings):**
- max |heading| 0.56° (v4: 20–30°).
- Cloud patches move 8–10 px/drawing (main layer 10.7 at 1080; the far layer is slower).
- Filmstrip: `work/gates/s11_start.jpg` (v4 top, v5 bottom).

## Fix 3: scene 10 walker sway and splay
**Causes.**
- `rope_cfg.MOTION[10]` still had `gait=(0.10, 0.9)`: a 0.10 m (12 px) sideways body sinusoid at 0.9 Hz. Scene 10 was not re-rendered in v4.
- The Walker used a 0.42 rad arm swing and speed-dependent steps (about 0.6 m), so an arm and a foot reached about 45 px ahead or out on alternate drawings.
- The rope wind had a 0.9 Hz lateral term that echoed the sway.

**Fix.** Walker options were added, with defaults that keep every other scene's walk:
- MOTION[10] gait set to 0.
- One slow bow of 6 px over the scene.
- `step_len` 0.29 m (35 px). At the walker's 73 px/s ground speed that is 2.1 steps/s, the rate at which stance feet stay planted. The brief's "about 1.8 steps/s" would need 40 px steps; 28–36 px steps at this speed need 2.0–2.6 steps/s, so 2.1 was chosen.
- `foot_lat` 0.081 (10 px).
- Small shoes: toe 0.045 m, shoe bulk 0.8, about 14 × 9 px.
- Swinging foot pitched toe-down, so it foreshortens.
- Arms hang inward and swing 0.14 rad along the path.
- Shoulders counter-rotate ±3°.
- Hat bob is a ±1.5 % scale change.
- The sideways wind on the first ~40 px of thread is halved (`rope_io.Owner(wind_wrap=…)`).

**Test clip:** feet ≤ 11.2 px and hands ≤ 17.4 px from the centre line; hat x drifts 1.3 px over 1 s. Filmstrip: `work/gates/walker_s10.jpg`.

## Fix 6: scene 12 character A runs
New `human.Runner` (Walker and B unchanged):
- Planted-foot run: stance 3/8 of the stride cycle per foot, giving two flight phases per cycle.
- In flight the body lifts 12 mm (the shadow detaches about 6 px) and is drawn up to 4 % larger.
- Lean 0.2 rad.
- Elbows held back (upper arm −0.73 rad), bent about 90°; hands pump −6…+26 px about the shoulder.
- Shoulders counter-rotate ±6°.
- Heel kick and forward reach in the swing.
- Feet 9.5 px off the centre line; dark shoes about 11 × 8 px.
- Each foot strike makes a dust puff (4 specks, 40 %, 0.4 s, 4 → 10 px) and leaves a footprint (≈8 × 10 px, 25 %, fading after 6 s), in its own object; B's prints are unchanged.
- A's thread: sideways wind scaled 0.4 → 1.0 over the first ~120 px, so it streams straight behind. The hip yaw moves the anchor about 4 px at the stride rate.
- Run → walk blend over 1 s, 3930–3954: A is still walking at the end.

**Speed vs. stride.** A's ground speed in the approved scene is 141 px/s at the start, 220 px/s for most of the shot, and 77–126 px/s at the end. With the brief's rule (keep the speed, adjust the stride within 46–60 px, nominal 52 px at 3.0 steps/s), the stride is clamp(v / 3, 46, 60):
- 47–52 px at 3.0 steps/s at the start (an 8-drawing cycle);
- 60 px at 3.7 steps/s at 220 px/s (a 6.5-drawing cycle; every drawing a distinct pose).

Keeping a strict 8-drawing cycle at 220 px/s would need a 73 px stride, outside the allowed range.

## Fix 5: scene 12 small birds
- Six small pale gulls, one loose group, present from the first drawing (3 s warm-up), flying up and a little left at 66–78 px/s over the ground. v4 had two groups of three that switched on and off at t = 120 and t = 150, which was the blink.
- Each bird is one mesh: body ellipse, tail, two 3-segment wing chains. Poses come from a stylised 1.5 Hz beat (8 drawings per cycle, ±6 % per bird, random phase) with the outer wing folding back on the upstroke, so no two poses in a cycle repeat. Span varies about 40–45 %.
- Flap-and-glide: 4–6 beats, then 0.8–1.4 s of gliding, independently per bird. Body bob ±3 %; speed pulse 8 %.
- Steering:
  - slow wander, turn rate ≤ 12°/s;
  - separation (repulsion inside 60 px);
  - cohesion beyond 140 px;
  - screen-space avoidance of A, B, both threads and the shrubs.
- The camera outruns 55–80 px/s birds, so the group drifts down the left side and leaves smoothly through the edge. No bird pops in or out.
- Shadows: a draped copy of the same pose, 17 px down-left along the scene's light, 25 %. The real sun is 14° high, so a true shadow from 2.2 m would land about 1,100 px away, which is why the shadow is faked.

## Fix 2: scene 6 manta and turtles swim
New `blender/kit/swim.py`: `chain_angles`, a travelling-wave hinge chain, plus two rigs.
- **MantaRig:**
  - Same planform mesh, colours and size.
  - Six wing ribs per side flap at 0.45 Hz with a 0.12-cycle delay per rib; span foreshortens about 11 %.
  - Wing tip trails 8–14 px. Trailing-edge ripple 6.5 px travels to the tip.
  - "tilt" attribute: +8 % lighter up, −6 % darker down.
  - Bank ≤ 0.12 rad. Body sway 2.5°. The head leads turns, body 0.17 s later, tail delayed further.
  - Cephalic fins curl ±10° at 0.2 Hz.
  - 8-segment whip tail, tapering 5 → 1.5 px, following the turn history with a travelling sway.
  - Two 1.2 s glides (at 5.5 s and 15.0 s) with ramps.
  - Forward speed ±10 % with the beat, applied as an along-track offset, so the approved steering paths, and with them the fish schools, are untouched.
  - Heading rate limited to 18°/s.
- **Two fixes found by viewing the test clips:**
  - The wing tips first rose up to 0.5 m and broke the water surface (the manta swims 12 cm down), which showed as a dark blob. The upward travel is now soft-capped at 8 cm; the top-down read comes from foreshortening.
  - The cel shadow band snapped on at the tilted tips. The manta's band is now disabled; tilt shading comes from the attribute.
- **TurtleRig:**
  - Same shell.
  - 3-joint front flippers: power stroke 45 % (+5° → −70°), recovery 55 % feathered to 40 % width.
  - Hind paddles ±12°, half a cycle out of phase.
  - Head bob 4 px lagged 0.15 cycle. Shell yaw ±3°. Opposite flipper lagged 0.05 cycle.
  - Outer flipper 1.2× and inner 0.7× in turns.
  - Speed pulse 55–145 % as an along-track offset.
  - Heading lag 0.3 s.
  - Three faint wake dashes per stroke.

## Fix 1: scene 3 lily pads
**Cause.** The pads overlap heavily (placement allows a centre distance down to 0.58 × the summed radii), and their heights were random, only 0–7 cm apart. Near the boat each pad also bobbed up to ±12 mm, tilted ±0.03 rad (up to 5 cm at the rim) and was pushed up to 25 px on its own. Overlapping neighbours interpenetrated, swapped order and slid through each other.

**Fix.** No change to colours, textures, sizes, flowers, koi, water, boat or thread:
- **Relaxation:** a deterministic position-based solver. It uses no RNG, so the scene's random sequence and every other placed object stay identical. Overlap depth is limited to 22 % of the smaller radius, and pads are kept clear of the boat's swept corridor (hull + 40 px each side) and of every oar-blade position in the shot.
- **Stacking:**
  - a fixed integer layer index per pad (seeded permutation, stored in `pads.json`);
  - levels from the overlap DAG, 4.8 cm per level, which casts a 4 px contact shadow at this 47.7° sun (real sun shadow plus AO);
  - the existing lighter rolled rim kept.
- **Motion:**
  - pads fixed in the world;
  - a shared 1 px/s drift down the frame;
  - a bob of yaw ≤ 0.8° and ≤ 0.5 px, with a spatially smooth phase so neighbours differ by < 15°.
- **Pushes:** the bow-wave pushes were dropped. The corridor is now clear, and individual pushes would break the 1.5 px pair rule. The brief makes the push optional ("may be").
- **Flowers** ride on their pad, at that pad's level.

**Test clip:** pad gate PASS (max depth 0.220, 0 wrong-order pairs, order stable, pair vectors ≤ 0.33 px).

## Full render, first gate run, and fixes (13:26 → 14:00)
- Five scenes rendered at full resolution in three parallel streams (12+11, 3, 6+10). Render wall time: s3 487 s, s6 ≈ 600 s, s10 543 s, s11 729 s, s12 ≈ 700 s. All done by 14:00, including the paint pass.
- First splice and gate run: audio, cuts, ffprobe and both regressions for untouched scenes PASS. Fixes 1, 3, 4 and 5 PASS. Three items failed:
  1. **Fix 2, manta area change 7.1 %** between drawings 1808 → 1810. The glide ramp-down took only 7 frames, so the wings snapped to the glide pose. Both ramps are now 18 frames (0.75 s); scene 6 was re-rendered.
  2. **Fix 6:**
     - On twos, some stride cycles showed 0–1 flight drawings, because at 220 px/s a flight lasted only 0.8 drawings. Run stance is now 0.30 of the cycle (flight ≥ 1.3 drawings even at 6.5 drawings per cycle); scene 12 was re-rendered.
     - The gate measured the step diagonally between left and right plants (62.9 px); it now measures along the path (60 px at top speed).
     - The B crop used frames where B is still above the frame edge (empty crops, NaN); it now uses fully visible crops only.
  3. **Regression outside the edits, scenes 10 and 11 (1.6–1.8 in a few drawings):**
     - The clean renders differ from v4 by only 0.2–0.4 outside the edits. The paint pass, however, draws its strokes in a data-dependent random order, so any local change reshuffles strokes across the whole frame, by 1–2 levels.
     - Fix: `scripts/post/layer_composite.py`, i.e. "replace only the changed layers". Inside a feathered (8 px) mask of the edited elements the new painted drawing is used; outside it the approved v4 painted drawing is kept.
       - Scene 10's mask: the walker's hero layer (v4 ∪ v5, dilated 45 px), the thread and its shadow, a 200 px disc for the sunflowers that part around the walker, and the walker's long shadow down the frame (about 17 % of the frame).
       - Scene 11's mask: the birds, their shadows on the clouds 20–260 px down-right, and the thread (about 30 %).
     - Output is 4:4:4 JPEG at quality 100. Outside the masks the result equals v4 to 0.09–0.11 levels (JPEG rounding). The boundary was checked at 1:1 and shows no seam.
     - The first composite run used a "red" test that also caught orange sunflower petals (a 60 % mask). The test was tightened to the thread's red (G and B < 100); the same fix went into the gate.

## Re-render (14:14 → 14:38) and final gate run: all PASS
Scenes 6 (manta ramps) and 12 (run stance 0.30) were re-rendered in parallel (603 s and 596 s plus paint), scenes 10 and 11 were composited, then spliced, muxed and gated again. Full printout: `work/v5/gates_run2.txt`.

| gate | result | numbers |
|---|---|---|
| Fix 4: s11 start | PASS | bird heading max 0.56° in the first 24 drawings, incl. d0 and d1 (limit 6); RMS 0.22° over the scene. Cloud scroll 0→1, 1→2, 2→3: rig 10.74 px/drawing each (+9.6 % vs 9.8); main cloud layer measured 10.77 / 10.85 / 10.86. Constant, no jump. |
| Fix 3: s10 walker | PASS | hat deviation from the best-fit line max 0.16 px (limit 14); p2p after a degree-3 fit 1.47 px (3); yaw RMS 0.00° (2.5); feet ≤ 11.49 px (14); hands ≤ 17.43 px (20) |
| Fix 6: s12 runner | PASS | 48-frame excursion 15.9 px (30); yaw RMS 2.47° (4); step-rate lateral p2p 1.34 px (3); cadence 3.0–3.67 steps/s (median 3.67); step 46.6–60.0 px along the path; plant speed 140–220 px/s; slip ≤ 0.30 px/drawing (1); cycles of 6/7/8 drawings, all distinct poses, 2 flights in every cycle; B crop diff max 0.25 (1.0); B's thread log identical to v4 |
| Fix 5: s12 birds | PASS | span p2p ≥ 42 % per bird (35); 13 of 15 pairs desynchronised (≥ 3); turn ≤ 12.0°/s (12); min spacing 44.6 px (28) |
| Fix 2: s6 swimming | PASS | manta beat 2.25 s measured from the tip rib angle (2.2); turtle stroke 2.83 s (2.8); wingspan 315–358 px, p2p 11.9 % (10–14); tail tip off the spine line up to 32.5 px (≥ 8); mask one piece in every drawing (9 drawings split only by the boat crossing the tail, one piece with the occluder counted); max area change 4.0 % (6); 0 same-layer overlaps; outside the creatures diff 0.18–0.30 (1.0) |
| Fix 1: s3 pads | PASS | 317 pads, 613 overlapping pairs, max depth ratio 0.220 (0.22), 0 lower-index-on-top pairs, pair order identical in 20 frames (upper pads ≥ 4.6 cm above), pair vectors stable to 0.33 px (1.5); outside the pads diff 0.53–0.76 (1.0) |
| untouched scenes | PASS | decoded frames identical to v4: s1 294/294, s2 314/314, s4 360/360, s5 360/360, s7 414/414, s8 154/154, s9 336/336 |
| changed scenes outside the edits | PASS | s3 0.53–0.76, s6 0.18–0.30, s10 0.10–0.11 (before compositing 0.36–1.72), s11 0.09–0.10 (before 0.15–1.6), s12 0.06–0.19 |
| cuts | PASS | diff 40.7–86.5 on all 11 cut frames; the neighbours are 0 (on-twos duplicates) or ≤ 15.1 |
| ffprobe | PASS | h264, 1080×1920, 24/1, 4004 frames, video 166.833 s, audio aac 166.882 s |
| audio | PASS | `ffmpeg -i out/final.mp4 -map 0:a -c copy -f md5 -` → MD5=2632a579c1377d79222ccb4e5300ad9e |

Viewed before finishing:
- `work/gates/s11_start.jpg`
- `walker_s10.jpg`
- `runner_s12.jpg`
- `birds_s12.jpg`
- `swim_manta.jpg`
- `swim_turtle.jpg`
- `out/v5_changes.jpg`

## Known deviations (stated, not hidden)
- **Pixel format:** `yuvj420p`, as in v4 (JPEG frame input flags full range). The approved scenes are stream copies, so the new segments must carry the identical SPS.
- **Runner cadence:** at A's approved 220 px/s, the 46–60 px stride rule gives 3.67 steps/s, i.e. 6.5 drawings per stride cycle instead of 8. At the start speed the cycle is 8 drawings. Every drawing is a distinct pose and every cycle has two flight drawings.
- **A's final walk:** in the last 2 s (from 3950, turning about 20° toward B) A walks with a normal walking arm swing; hands reach about 30 px from the centre line. The 17 px arm limit is met while running (15–18 px).
- **Runner flight softness:** the shadow detaches about 6 px in flight (real shadow, 12 mm lift) and the figure grows up to 4 %. "20 % softer, 15 % lighter" is not implemented: it would change the sun for every shadow in the scene.
- **Scene 11 scroll:** the camera stays the approved v4 setting (×1.08): rig 10.74 px/drawing, +9.6 % of 9.8. The image measurement reads 10.77–10.86.
- **Scene 3 channel:** clearing the oar-blade sweep and the hull corridor (rule 4) moved pads out of the channel edges, so the open channel reads wider than in v4. Pad colours, veins, sizes, flowers, koi, water, boat and thread are unchanged.
- **Scene 12 birds:** the camera (137–220 px/s) outruns birds flying 55–80 px/s over the ground. The group drifts down the left side and leaves smoothly by the edge in the second half; none pop in or out. Bird shadows are a draped copy offset 17 px, because the real 14° sun would put them about 1,100 px away.
- **Contact shadows on pads:** they are the scene's real cast shadow (4 px offset) plus AO, at the scene's normal shadow strength, not 35–45 % opacity. A separate decal would also darken the water around every pad.

## Deliverables
- `out/final.mp4` (331.6 MB)
- `out/v5_changes.jpg`
- `work/gates/s11_start.jpg`, `walker_s10.jpg`, `runner_s12.jpg`, `birds_s12.jpg`, `swim_manta.jpg`, `swim_turtle.jpg`
- `work/hero_motion_s10.csv`, `work/hero_motion_s12.csv`
- `pad_overlap_report.csv`
- this file

Code:
- `blender/kit/swim.py`
- `human.Runner` and the Walker options
- `rope_io` `wind_wrap`
- patches in `work/v5/patch_*.py` (v4 copies of every touched file are in `work/v5/*_v4.py`)
- `scripts/splice_v5.py`
- `scripts/post/layer_composite.py`
- `scripts/qa/gates_v5.py`, `scripts/qa/pads_gate.py`

## Wall time
- Total: about 12:05 → 14:40, **about 2 h 35 min**, well over the 45–60 min target.
- Most of it went into writing the rigs (swim module, runner, bird meshes, pad relaxation) and two gate-driven fixes: manta glide ramps and runner flight sampling, re-rendering scenes 6 and 12 once each.
- Rendering itself: about 20 min for five scenes in three streams, plus 17 min for the two re-renders. The splice and mux take under 2 min, because the approved scenes are stream-copied, not re-encoded.
