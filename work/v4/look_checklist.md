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
