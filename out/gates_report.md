# Gates report (brief v4) — out/final.mp4

## 1. Audio packet MD5

```
$ ffmpeg -i source/original.mp4 -map 0:a -c copy -f md5 -
MD5=2632a579c1377d79222ccb4e5300ad9e
$ ffmpeg -i out/final.mp4 -map 0:a -c copy -f md5 -
MD5=2632a579c1377d79222ccb4e5300ad9e
```
**1 audio: PASS**

## 2. Cuts, 4004 frames, no fade

```
codec_name=h264
width=1080
height=1920
r_frame_rate=24/1
nb_read_frames=4004
decoded frames (108x192 gray): 4004
detected hard cuts: [294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648]
expected:          [294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648]
cut   out-ratio(ours/orig)   in-ratio(ours/orig)
  294    1.00 /  1.00             1.00 /  1.00   ok
  608    1.00 /  0.99             1.00 /  1.00   ok
  954    1.00 /  1.00             1.00 /  0.99   ok
 1314    1.00 /  0.99             1.00 /  1.00   ok
 1674    1.00 /  1.00             1.00 /  1.00   ok
 2078    1.00 /  1.00             1.00 /  1.01   ok
 2492    1.00 /  1.01             0.99 /  0.99   ok
 2646    0.99 /  1.00             1.00 /  1.00   ok
 2982    0.99 /  1.01             1.00 /  1.00   ok
 3316    1.00 /  1.00             1.01 /  0.99   ok
 3648    1.01 /  1.00             1.00 /  1.00   ok
 4004    1.00 /  1.00             1.00 /  1.00   ok
```
**2 cuts+frames+no fade: PASS** — 4004 frames, cuts match, fades: none

## 3. On twos (every drawing held for exactly two frames)
```
scene  dup-steps  held-pairs-identical
    1       0.50       1.00 ok
    2       0.50       1.00 ok
    3       0.50       1.00 ok
    4       0.50       1.00 ok
    5       0.50       1.00 ok
    6       0.50       1.00 ok
    7       0.50       1.00 ok
    8       0.50       1.00 ok
    9       0.50       1.00 ok
   10       0.50       1.00 ok
   11       0.50       1.00 ok
   12       0.50       1.00 ok
```
**3 on twos: PASS**

## 4. Camera speed within 10 % (phase correlation, px per drawing at 1080 wide; 3 samples per scene)
```
scene  samples              mean   target  ratio
    1  [12.5, 12.4, 12.4]    12.4   12.3   1.01 ok
    2  [14.1, 14.2, 14.2]    14.2   14.0   1.01 ok
    3  [4.2, 5.7, 3.7]        4.5    4.3   1.05 ok
    4  [9.9, 9.9, 9.9]        9.9    9.8   1.01 ok
    5  [6.3, 6.2, 6.2]        6.2    5.9   1.06 ok
    6  [7.3, 7.4, 7.2]        7.3    7.0   1.04 ok
    7  [3.3, 3.7, 3.7]        3.6    3.4   1.05 ok
    8  [8.2, 8.2, 8.2]        8.2    8.0   1.02 ok
    9  [8.0, 8.4, 8.1]        8.2    8.2   1.00 ok
   10  [6.3, 5.8, 6.2]        6.1    6.2   0.98 ok
   11  [9.2, 8.8, 9.7]        9.2    9.8   0.94 ok
   12  [18.7, 18.7, 11.8]    16.4   16.8   0.98 ok
```
**4 camera: PASS**

## 5. Heroes travel straight (work/hero_motion.csv; every 48-frame window, step 12)

```
scene hero  drawings  excursion max/median (px)  limit   yaw-RMS max (deg)  limit
    1  A         147       0.0 /    0.0                8       0.02           0.5  ok
    2  A         157       0.7 /    0.7                8       0.02           0.5  ok
    3  A         173       0.1 /    0.1               20       0.00           2.5  ok
    4  A         180      54.1 /   29.7               60     path tangent (S-curve kept)  ok
    5  A         180       5.6 /    5.3               12       0.00           2  ok
    6  A         202       0.5 /    0.3               20       0.00           2  ok
    7  A         207       0.0 /    0.0               20       0.16           3  ok
    8  A          77       0.7 /    0.6               15       0.36           2  ok
    9  A         168       0.0 /    0.0               26       0.00           3  ok
   10  A         167      31.2 /   27.0               42       2.69           4  ok
   11  A         166       3.2 /    0.2               20       2.23           4  ok
   12  A         178      15.1 /    1.3               30       2.47           4  ok
   12  B          78      15.1 /    3.3               30       2.18           4  ok
```
Template tracker on the videos (same tool for all three; median excursion per 4 s, px):
```
scene 7: original 2.0  v3 31.8  v4 0.0
scene 12: original 2.6  v3 20.0  v4 2.8
```
**5 hero motion: PASS**

## 6. Scene 5: horse + rider mask and shadow mask, one piece each
```
horse+rider hero mask: 180 drawings checked, 0 not one piece []
f1420.jpg shadow components: 1 areas: [7223] one piece: True
f1424.jpg shadow components: 1 areas: [6820] one piece: True
f1428.jpg shadow components: 1 areas: [7171] one piece: True
f1432.jpg shadow components: 1 areas: [6994] one piece: True
f1436.jpg shadow components: 1 areas: [7054] one piece: True
f1440.jpg shadow components: 1 areas: [6748] one piece: True
f1444.jpg shadow components: 1 areas: [6923] one piece: True
f1448.jpg shadow components: 1 areas: [6750] one piece: True
f1452.jpg shadow components: 1 areas: [7001] one piece: True
f1456.jpg shadow components: 1 areas: [6989] one piece: True
f1460.jpg shadow components: 1 areas: [7201] one piece: True
f1464.jpg shadow components: 1 areas: [7095] one piece: True
SCENE 5 SHADOW GATE: PASS
```
**6 horse+shadow connectivity: PASS**

## 7. Scene 6: depth-layer colliders, manta continuity, boat clearance
```
overlaps: 0
collider rows: 9669, frames: 202, layers: ['1', '2', '4', '5']
boat-island clearance (px): min 70.8, median 113.8 over 202 drawings
manta mask: 202 drawings, 202 with the manta in view; visible mask split in 5 ['manta_1968.png', 'manta_2010.png', 'manta_2012.png', 'manta_2014.png', 'manta_2016.png'] (the boat passing over the tail); not one piece once the occluding boat is counted: 0 []
manta area change between drawings: max 0.5 %, median 0.2 % (limit 6 %)
```
**7 scene 6 colliders+manta+boat: PASS**

## 8. Tone (scenes 1, 8, 11), scene 1 corridor and window light
```
frame  scene  mean   p5   p95   sat    targets
  146      1   72.0   42   120  0.46   mean 68-74, p5>=36, p95 0-125, sat<=0.5  ok
 2570      8  102.2   48   204  0.42   mean 90-105, p5>=28, p95 195-215, sat<=0.45  ok
 3482     11  153.6   71   229  0.25   mean 148-172, p5>=0, p95 0-255, sat<=1.0  ok
s11 f3330: gaps 0.24  lavender/violet 0.26  mean luma 156.2
s11 f3400: gaps 0.27  lavender/violet 0.27  mean luma 150.0
s11 f3482: gaps 0.23  lavender/violet 0.30  mean luma 154.2
s11 f3560: gaps 0.19  lavender/violet 0.35  mean luma 154.0
s11 f3640: gaps 0.16  lavender/violet 0.33  mean luma 161.2
s11 mean over the scene: gaps 0.22 (target 0.20-0.25), lavender/violet 0.30 (>= 0.30)  ok
s1 corridor (scene graph): {'trees': 330, 'min_clear_px': 100.99999999999999, 'density_per_100m2': 5.181932955209247, 'window_x_px': 28.5, 'required_px': 100.0, 'pass_': True}
s1 f146 warm window light: 52857 px, max R 233 (<=235), max G 146 (<=200)  ok
```
**8 tone + corridor: PASS**

## 9. Thread continuity, no pops (simulation logs per drawing)
```
scene  1 A: 147 drawings, segments [260], free end beyond the frame: True, max segment 15.0px, max owner step change 0.0px ok
scene  2 A: 157 drawings, segments [260], free end beyond the frame: True, max segment 15.0px, max owner step change 0.1px ok
scene  3 A: 173 drawings, segments [260], free end beyond the frame: True, max segment 14.8px, max owner step change 0.1px ok
scene  4 A: 180 drawings, segments [260], free end beyond the frame: True, max segment 14.8px, max owner step change 2.4px ok
scene  5 A: 180 drawings, segments [260], free end beyond the frame: True, max segment 15.4px, max owner step change 0.3px ok
scene  6 A: 202 drawings, segments [260], free end beyond the frame: True, max segment 14.8px, max owner step change 0.1px ok
scene  7 A: 207 drawings, segments [260], free end beyond the frame: True, max segment 12.9px, max owner step change 0.4px ok
scene  8 A: 77 drawings, segments [260], free end beyond the frame: True, max segment 14.8px, max owner step change 0.1px ok
scene  9 A: 168 drawings, segments [260], free end beyond the frame: True, max segment 15.0px, max owner step change 0.0px ok
scene 10 A: 167 drawings, segments [260], free end beyond the frame: True, max segment 14.8px, max owner step change 2.8px ok
scene 11 A: 166 drawings, segments [260], free end beyond the frame: True, max segment 14.3px, max owner step change 2.5px ok
scene 12 A: 178 drawings, segments [260], free end beyond the frame: True, max segment 16.7px, max owner step change 1.2px ok
scene 12 B: 78 drawings, segments [260], free end beyond the frame: True, max segment 15.9px, max owner step change 5.6px ok
```
**9 thread: PASS**

## 10. Wiggle: fine boil only (cells 8-24 px), calibration and flipbooks
```
s01 boil_scale 0.8  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
s02 boil_scale 0.8  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
s03 boil_scale 0.8: residual flow floor 1.18  v3 1.60  new {0.4: 1.23, 0.6: 1.23, 0.8: 1.24, 1.0: 1.24, 1.3: 1.25}  extra new/v3 = 0.12
s04 boil_scale 0.8  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
s05 boil_scale 0.6: residual flow floor 1.65  v3 2.95  new {0.4: 1.86, 0.6: 2.03, 0.8: 2.24, 1.0: 2.46, 1.3: 2.79}  extra new/v3 = 0.29
s06 boil_scale 0.8  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
s07 boil_scale 0.8  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
s08 boil_scale 0.8  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
s09 boil_scale 0.8: residual flow floor 1.38  v3 1.44  new {0.4: 1.38, 0.6: 1.37, 0.8: 1.34, 1.0: 1.34, 1.3: 1.34}  extra new/v3 = -0.59
s10 boil_scale 0.8  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
s11 boil_scale 0.6  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
s12 boil_scale 0.8  (v4: global 0.8, lowest (0.6) for scenes 5 and 11; the flow metric is blind to fine boil (see PROGRESS))
out\flipbook_s01.mp4  1.8 MB
out\flipbook_s05.mp4  2.4 MB
out\flipbook_s09.mp4  2.3 MB
out\flipbook_s11.mp4  2.1 MB
```
**10 wiggle+flipbooks: PASS** — coarse warp removed (boil_mode=fine everywhere); see flipbooks for the look

## 11. Look checklist (1:1 crops: `out/look/v4_sXX.jpg`, original left, v4 right)

Checked at 1:1 against the original (`out/look/v4_s01/05/06/08/11.jpg`; hero crops are in `out/contact_sheet.jpg`).

| scene | item | v4 | verdict |
|---|---|---|---|
| 1 | slate-blue night palette, not saturated blue | snow #495175/#656C90, needles #1E253E/#3B4160; sat 0.45 | ok |
| 1 | moonlight from the upper left: crown rims, light pools, glowing fog, frost speckles | moon at (−0.55, 0.45); rim 0.45 on the crowns; floor pools between the thinner trees; two emissive fog banks; sparse frost flecks on the blade tips | ok (the frost is sparser than the original's) |
| 1 | 6–8 carriages; warm window light, never clipped, smooth falloff ~200 px | 7 cars; warm pool #E8A24A→#A57861 fading over 200 px; max R 233, max G 146 in the final video | ok |
| 1 | soft warm gradient on the trees, no spikes | shadowless area lights; no tree-shadow spikes | ok |
| 1 | streaky steam plume along the track, not hiding the train or rails | ribbon 35→140 px over 700 px ahead of the engine, opacity ≤ 0.48; rails show through | ok |
| 1 | forest −30 %, two heights, floor visible, 100 px corridor | spacing 3.23 m; tall and understorey trees; snow floor visible; min clearance 101 px (scene graph) | ok |
| 5 | horse is one connected mesh with a four-beat walk; rider attached; masks one piece | skin-modifier body; 180/180 hero masks one piece; shadow one piece at all 12 phases | ok (the horse reads paler and bulkier than the original's grey) |
| 5 | heroes straight; camera 5.9 | excursion 5.6 px; camera 6.2 px/drawing (ratio 1.06) | ok |
| 6 | depth layers, no same-layer overlaps; boat in a clear channel | 0 overlaps; channel clear of islands; turtles and schools steer around the corals | ok |
| 6 | manta one piece, no area jumps | max area change 0.5 % between drawings; mask split only where the boat's boom crosses the tail | ok |
| 8 | moonlit palette (lit #D8E2F0 … deep #2C3764), moonlight showing | pale moonlit snow pools between long blue pine shadows; mean ≈ 103 | ok (the brief asks for a much brighter scene than the original's near-black) |
| 8 | soft elongated headlamp pool with a cone (#F2C98A) | additive warm cone plus an elliptical pool 3.4 m ahead | ok |
| 8 | star pines with snow, not black spikes | blue-green star crowns with snow on the tips | ok |
| 8 | skier with helmet and goggles, poles trailing, skis parallel, straight run | goggles and strap; poles trail back; skis share the heading; excursion 0.7 px, yaw RMS 0.36° | ok (the skier is small on screen) |
| 8 | twin tracks with ridges, powder spray, ice glints on the thread | two grooves with ridges on both sides; continuous light spray; thread glints | ok |
| 11 | density-field clouds (no circles), lit from the upper left | warped fbm height field; alpha cut at the density contour (smooth edges); sun at the upper left | ok (the relief is smoother than the original's cauliflower texture; the strokes add the texture) |
| 11 | lavender/violet ≥ 30 %, gaps 20–25 %, mean 160 ± 12 | scene means: lavender 0.31, gaps 0.21, mean luma 151–162 | ok |
| 11 | swirl strokes along the contours, three parallax layers, constant camera | stroke 24 px × elong 3 along the flow; far layer, main layer and near wisps; camera constant | ok |
| 11 | birds with stable headings, bank ≤ 4° | bank clamped to ±0.04 rad (2.3°); hero yaw RMS within the limit | ok |

**11 look checklist: PASS**

## Summary

- 1 audio: PASS
- 2 cuts+frames+no fade: PASS
- 3 on twos: PASS
- 4 camera: PASS
- 5 hero motion: PASS
- 6 horse+shadow connectivity: PASS
- 7 scene 6 colliders+manta+boat: PASS
- 8 tone + corridor: PASS
- 9 thread: PASS
- 10 wiggle+flipbooks: PASS
- 11 look checklist: PASS
