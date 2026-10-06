# Credits

## External assets (v3)

All textures below are from **Poly Haven** (https://polyhaven.com) and are released under **CC0 1.0 Universal** (public domain dedication, https://creativecommons.org/publicdomain/zero/1.0/). They were downloaded at 1k resolution with `scripts/fetch_textures.py` from the Poly Haven API (`https://api.polyhaven.com/files/<id>`). Copies, with a manifest of the exact file URLs, are in `assets/textures/` (`manifest.json`).

The textures never appear as photographs. Their luminance and normal/displacement detail modulates the painted scene palettes (`look.tex_value_detail` / `look.tex_height`) and is then repainted by the stroke layer.

| Asset (Poly Haven id) | Authors | Maps | Used in | Licence |
|---|---|---|---|---|
| Aerial Sand (`aerial_sand`) | Rob Tuytel | diffuse, normal, displacement | scene 12 dune sand grain, scene 5 desert sand | CC0 |
| Aerial Rocks 02 (`aerial_rocks_02`) | Rob Tuytel | diffuse, normal, displacement | scene 7 canyon rock | CC0 |
| Rocky Terrain 03 (`rocky_terrain_03`) | Amal Kumar | diffuse, normal | scene 7 scree / talus | CC0 |
| Snow Field Aerial (`snow_field_aerial`) | Rob Tuytel | diffuse, normal | scene 8 snow slope | CC0 |
| Snow 02 (`snow_02`) | Rob Tuytel | diffuse, normal | scene 4 frost and snow drifts | CC0 |
| Aerial Grass Rock (`aerial_grass_rock`) | Rob Tuytel | diffuse, normal | scene 9 lawn | CC0 |
| Gravel Road (`gravel_road`) | Amal Kumar | diffuse, normal | scene 9 path gravel | CC0 |
| Forest Ground 04 (`forest_ground_04`) | Rob Tuytel, Rico Cilliers | diffuse, normal | scene 10 soil between the sunflowers | CC0 |
| Brown Mud 02 (`brown_mud_02`) | Rob Tuytel | diffuse, normal | scene 10 dirt path | CC0 |
| Coast Sand 01 (`coast_sand_01`) | Rob Tuytel | diffuse, normal | downloaded, not used in the final render | CC0 |
| Pine Bark (`pine_bark`) | Dimitrios Savva | diffuse, normal | downloaded, not used in the final render | CC0 |

Everything else is generated procedurally by the Python scripts in `blender/` and `scripts/post/`, with no models, HDRIs or other image assets:
- geometry: dunes, eroded canyon, plants (leaf-card crowns, sunflowers, shrubs, grass), the horse, humans, boats, train, cranes, manta, fish;
- materials;
- the painted seed-head texture (`seedhead_image`);
- the brush-stroke, canvas and impasto layers.

## v4 changes

The v4 pass adds no external assets: the same CC0 Poly Haven textures as above, nothing else.
- Scene 11's clouds are a procedural density field.
- Scene 1's steam and window light are procedural shaders.
- Scene 5's horse is a procedural skin-modifier mesh.
- Shapely (BSD-3) is used only for the scene 6 collider gate.
- No pixels from the original video or from v3 appear in the output. Those videos are read only by the QA scripts (measurement, comparison crops, flipbooks).

## Software

| Tool | Use | Licence |
|---|---|---|
| Blender 4.5.9 LTS (EEVEE Next, Freestyle, compositor) | rendering | GPL-2.0-or-later |
| FFmpeg 7.1 (static build via `imageio-ffmpeg`) | frame extraction, encoding, muxing | GPL / LGPL |
| Python 3.12, NumPy, OpenCV, SciPy, scikit-image, Pillow | analysis, painting post-process, QA | BSD / Apache-2.0 / HPND |
| demucs (htdemucs) | vocal separation, **analysis only** (output never muxed) | MIT |
| faster-whisper (Whisper medium) | lyric transcription, **analysis only** | MIT |

## Source

`source/original.mp4` is used only as a visual and timing reference by the analysis and QA scripts. Its audio stream is muxed into the final video untouched (`-map 1:a -c copy`; packet MD5 checked in `out/gates_report.md`). No pixels from it appear in the output.
