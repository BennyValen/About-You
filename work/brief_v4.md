

<pasted_content id="06d4">
You are doing a fix pass on the existing project that produced source/v3.mp4. Do not start over. Keep the project, the renderer and everything that works, and fix what is listed here. Do not ask me questions. Make the best call, log it in PROGRESS.md, keep going. If something fails, fix it and continue. Never say a gate passed without printing its output.

0. What I measured on v3 (so you know exactly what is wrong)

Everything below was measured on source/v3.mp4 against source/original.mp4 (1080x1920, 24 fps, 4004 frames). Pixel values are at 1080 px wide.

Already correct. Do not break it.

Audio is bit-identical to the original (packet MD5 matches). Keep the rule in section 1.
The film is on twos: every other frame is an exact duplicate in every scene. Keep it.
Hard cuts are on the right frames. The ending story beat is right.
Scene 2 (tea garden with pickers), the scene 3 boat model, the scene 4 skate scratches, the scene 7 paraglider and the scene 10 sunflowers are acceptable. Do not regress them while fixing the rest.

To fix (details in section 3):

The paint wiggle is too strong. v3's wiggle is large in patches: where the original's moving paint is fine-grained, v3's moves in big coherent blotches across flat ground (worst in scene 5, the sand). That large-scale warp came from my own spec ("patches roughly 30 to 90 px"). That spec was wrong. Remove it.
Scene 1 is too dark (mean luma 58 against the original's 70; base colors are saturated indigo 
#182052 where the original is slate blue 
#2B324F, 
#3B4160, 
#495175); there is no visible moonlight; the smoke is a big opaque cotton lump; the forest is too dense and the crowns cover the train and rails; the window light on the trees is jagged yellow spikes.
Scene 8 (the new ski scene) is too saturated royal blue and too dark (mean luma 37; dominant color 
#1D2D88, saturation 0.79). The moonlight does not show.
Characters swing left and right instead of traveling straight. The lateral excursion of the thread anchor (where the thread leaves the traveler) within any 4 seconds, median: scene 3 boat 103 px against the original's 17 px (6 times too much; the bow also alternates by about 15 to 20 degrees each stroke); scene 6 boat 42 against 16; scene 5 horse 13 against 9; scene 11 23 against 18. Scenes 9 (28 against 26) and 10 (26 against 42) are fine by this measure. Scene 4's skater in the original does sweep side to side (about 60 px per 4 s) and v3 matches (66), so keep that scene's skating curve. For scenes 7 and 12 my tracker failed on the original, so you must measure those yourself.
Scene 5 horse: the legs, neck, head and body are separate pieces, not attached. The body and shadow shapes are good otherwise.
Scene 6: objects pass through each other (boat, turtles, manta ray, plants, coral), and the manta's body parts sometimes vanish.
Scene 11 clouds are stacks of small circles. The original's clouds are big swirl-painted cumulus with real shading. v3 is also washed out (mean luma 200 against 161; the four pale cream and pink tones cover 74 percent of the frame, and the deep blue gaps only 10 percent, where the original has about 22 percent in gaps and about 40 percent in lavender and violet shadow tones).

Camera speed per drawing (vertical ground shift between consecutive distinct drawings; original / v3). Fix the bold ones. scene 1: 12.3 / 12.9, scene 2: 14.0 / 14.1, scene 3: 4.3 / 4.5, scene 4: 9.8 / 9.8, scene 5: 5.9 / 8.1 (v3 is 37 percent too fast), scene 6: 7.0 / 5.9, scene 7: 3.4 / 2.8, scene 9: 8.2 / 9.3, scene 10: 6.2 / 6.1, scene 11: 9.8 / 3.0 (v3 is 3 times too slow), scene 12: 16.8 / 16.4. Scene 8 is new, so use about 8 px per drawing.

Two of my earlier tools were misleading; use the corrected ones in section 5.

The "motion per drawing" ratio I gave before (mean frame difference) is polluted by the wiggle and by texture. It reported scene 11 as nearly right when its camera is 3 times too slow. Use the phase-correlation camera speed in section 5.
The "paint residual flow" metric I gave before cannot separate paint wiggle from other non-rigid effects, and it says v3's wiggle roughly equals the original's on average (1.0 to 2.9 px against 1.1 to 2.4 px). I (the user) still see it as too strong. Treat that metric as a rough guide only. My eyes win; see section 3.1.
1. Standing rules (unchanged, keep all of them)
Audio untouched. All renders are silent video. The final mux is always ffmpeg -i work/video_silent.mp4 -i source/original.mp4 -map 0:v:0 -map 1:a:0 -c copy -movflags +faststart out/final.mp4. Never re-encode, normalize, trim, fade or add audio. Gate: ffmpeg -i out/final.mp4 -map 0:a -c copy -f md5 - must equal the same command on source/original.mp4 (compare packet MD5 with -c copy, not decoded PCM). Print both in out/gates_report.md after every final mux.
On twos. Render only the even frames and repeat each for 2 frames (12 distinct drawings per second). Every scene, including the new scene 8.
Hard cuts on frames 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648. 4004 frames at 24 fps. No fade at the end.
Story. One traveler (A) is followed through all 12 scenes, always trailing a red thread. In the last scene B enters from the top edge at about 163 s with their own thread trailing up; each thread stays attached to its owner; no third thread; they end a few steps apart, facing each other, still moving.
Look. Hand-painted cel animation with cinematic glow: real constructed detail (leaves, petals, planks, fabric, rock strata), soft light, cast shadows, painterly finish, grain. The paint wiggle layer stays but gentler (section 3.1).
The thread is a real simulated cord (world-space rope, 240 or more segments, wind, drag, friction on sand and ice, floating on water, sway in air), thin and tapered, with a short cast shadow.
Everything is drawn by you. No pixels from the original or from v3 in the output. CC0 assets are allowed; list them in CREDITS.md.
Render fast. Target about 2 hours or less for the full render; see section 6.
2. Order of work
Build the measurement tools in section 5 and run them on v3.mp4 and the original. Save results in work/baseline.json. Print the baseline table.
Fix the hero motion system (item 4) globally, because it affects most scenes.
Recalibrate the wiggle (item 1) globally.
Fix scenes 5, 6, 11, 1 and 8 (items 5, 6, 7, 2, 3).
Fix the camera speeds for scenes 5, 6, 7, 9, 11.
Re-render only what changed (section 6), then mux, run all gates, write the report.
3. The fixes, in depth
3.1 Wiggle: less, finer, and not on big shapes

Goal: the picture should feel hand-painted but calm. If a viewer notices the wiggle as motion before they notice the scene, it is too much.

Rules:

Delete all coarse warping. Displacement patches larger than about 40 px must be zero. The ground, sky, water and big shapes hold still between drawings.
Fine-scale boil only. Displacement patches 8 to 24 px across, with amplitude about 0.8 px mean (2 px peak) in textured regions (foliage, sand ripples, rock, water texture), 0.4 px in flat regions (snow, sky, calm water, cloth), and at most 0.3 px on heroes, the boat, animals, the thread and hard outlines. Edge wobble at most 0.5 px.
Stroke value jitter from drawing to drawing: plus or minus 3 to 4 levels (v3 used 6 to 10). Stroke position jitter 0.5 to 1.5 px.
Everything is still reseeded every new drawing (12 Hz). The canvas texture stays screen-fixed.
Calibrate against v3. Make a boilScale parameter per scene. For scenes 3, 5 and 9, render 12 consecutive drawings with boil off (the floor) and with v3's setting. Choose the new strength so that the extra residual over the floor is about 0.5 to 0.6 times v3's extra. Scene 5 and scene 11 get the lowest strength (they are the worst offenders). Print the floor, v3 and new values.
Judge by flipbook. For scenes 1, 5, 9 and 11, render 12 consecutive drawings at about 540 px wide as a looping clip next to the original's same span. The new one must look calmer than v3 and never like screen shake. Keep the cached clean frames (before boil) so you can re-apply boil in seconds.
3.2 Scene 1: night train. More light, moonlight, real smoke, thinner forest, clear track

Reference numbers for the original (frame about 146): mean luma 69.8, 5th percentile 37, 95th percentile 121. Dominant colors: slate blues 
#2B324F (25 percent), 
#3B4160 (22), 
#495175 (21), 
#1E253E (16), light 
#656C90 (8), warm window light 
#A57861 (4), pale 
#9AA0BE (3). Color saturation of the base blues about 0.46. v3: mean 58.2, p5 31, p95 138, dominant 
#182052 (35 percent), saturation about 0.71.

Targets for v4: mean luma 68 to 74, p5 at least 36, p95 at most 125, base-blue saturation at most 0.5. The p95 drop comes from removing the harsh bright parts, not from darkening the rest.

Brighter, softer base. Raise the canopy and ground values to the slate-blue family above. Lower saturation. Keep it a night scene, not a dark one.
Show the moon. Add a cool silver-blue moon light from the upper left (shadows fall to the lower right, except near the train where the train's own light dominates). Visible effects: pale blue rim light on the lit side of each conifer crown; soft blue-white light pools on the forest floor and fog in the gaps between crowns; long soft cool shadows; fog layers that glow faintly where the moon hits them; frost-bright speckles on needle tips. The moon itself is out of frame.
Train. Six to eight distinct carriages with roofs, joints, vents, a faint cool rim light on the roof edges, and window light strips along both sides. The window light is warm orange (
#E8A24A to 
#A57861), never white, never clipped (highest pixel at most about 235 in the red channel and at most 200 in the green), with smooth Gaussian falloff over about 200 px. No spikes.
Window light on the trees. Soft, not jagged: v3 shows yellow triangular "flames" on the tree edges. Replace them with a soft warm gradient on the needles that face the train, fading with distance, plus the long cool shadows of the trees cast across the lit strip (as in the original).
Smoke or steam. v3's is a large opaque lobed lump that hides the train and trees. Replace it with a real plume: a particle or noise-driven steam plume emitted at the engine, narrow at the source (about 30 to 40 px) and widening to about 140 px over about 700 px, semi-transparent (opacity at most 0.5 at the core, 0.1 to 0.2 at the edges), streaky wisps that drift sideways with the wind and curl slightly, bright core near the source lit warm from below by the train and cool silver from the moon higher up. It must not hide the train or the rails. It lies along the track as in the original.
Forest density. Reduce crown density by about 30 percent. Leave the dark forest floor visible between crowns (v3 has crowns overlapping almost everywhere). Vary crown size and spacing and add two heights of crowns. Keep the frosty needle texture.
Clear corridor. No crown, branch or foliage within 100 px of the outer edge of the lit window strips on either side of the train and rails. Only low mist and a few tiny shrubs there. The crowns that were covering the train must be moved out. Add a gate that checks this on the scene graph (distance from every crown's footprint to the train's footprint).
Camera speed stays about 12.5 px per drawing.
3.3 Scene 8: moonlit ski glide, with the moonlight showing

Original scene 8 is gone; the replacement is a skier gliding down a snow slope at night through pines, seen from above. v3's version is too saturated blue and too dark (mean luma 37, dominant 
#1D2D88, saturation 0.79), the headlamp pool is a flat peach disc, the tree shadows are black-blue spikes, and the skier's skis cross in an X.

Targets for v4: mean luma 90 to 105, p5 at least 28, p95 195 to 215, dominant mid-tone saturation at most 0.45.

Palette (desaturated moonlit snow, not royal blue): lit snow 
#D8E2F0, mid snow 
#93A3C6, shaded snow 
#56648F, deep shadow 
#2C3764, headlamp warm 
#F2C98A. The brightest snow areas should read as snow (near white with a blue tint).
Moonlight must show: broad silver light from one side (shadows of every pine fall long and soft toward the other side), pools of lit snow between the pine shadows, a faint glittering sparkle on the snow, soft blue-white rim light on the pine crowns, drifting powder lit by the moon.
Headlamp: a soft elongated warm light pool on the snow ahead of the skier with a smooth falloff and a faint cone shape, not a flat disc. It adds warm color but does not dominate.
Pines from above: star-shaped crowns of needles with value variation, snow on the lit side, soft shadows. Not black spikes. Moderate density with plenty of open snow.
Skier: helmet with goggles from above, shoulders, arms holding poles trailing back, a forward lean, skis parallel and pointing in the direction of travel (never crossed), a straight run with only tiny corrections (item 4 rules: yaw at most 2 degrees, lateral excursion at most 15 px per 4 s). Two parallel ski tracks behind with soft edges and slightly raised snow ridges; powder spray kicked up and falling back.
The thread streams behind in the wind with tiny ice glints. Camera about 8 px per drawing, on twos.
3.4 Heroes travel straight (all scenes)

Complaint: in every scene the character moves left, right, left, right. They should travel straight along the camera direction, like a real person or vehicle, not robotically rigid but with no snaking.

Causes to remove: any noise-driven "wander" or steering applied to the hero's path, yaw wobble driven by the stroke or gait phase, and lateral bobbing. In v3's boat scene the bow alternates about 15 to 20 degrees each stroke and the boat drifts about 100 px sideways in 4 s.

Rules:

Path: each hero's world path is a straight line parallel to the camera direction, with at most one very gentle bend per scene (radius at least 3000 px). The camera follows with the hero locked to a fixed screen x within about 12 px. Only scene 4 keeps its skating curve (the original's skater sweeps about 60 px per 4 s; match that).
Heading (yaw) stays within the limits in the table. Maximum yaw rate 8 degrees per second.
Body motion that is real and allowed:
Walker (scenes 10, 12): torso counter-rotates about 3 to 5 degrees about the vertical axis with the stride, head faces forward, feet alternate left and right within a 14 to 22 px stride width, hips bob vertically. The body center does not sway sideways.
Rower (scene 3): the boat surges along its length a little with each stroke (about 6 px) and yaws at most about 2.5 degrees. Oars are symmetric.
Horse (scene 5): a four-beat walk, head nods, body rolls slightly, spine stays straight, yaw at most 2 degrees.
Cyclist (scene 9): ride straight with micro steering of at most 2 px.
Paraglider (scene 7): the pendulum swing is fore and aft along the flight direction (about 25 px), not sideways.
Sailboat (scene 6): steady course, heel and pitch in the roll and pitch axes, not yaw.
Skier (scene 8): a straight run.
Birds (scene 11): hold heading, at most 4 degrees of banking sway, stable formation spacing.
Log it. From the scene graph write work/hero_motion.csv with columns frame, scene, hero, x, y, yaw_deg for every drawing (x and y after removing camera motion). Gate: in every 48-frame window, the lateral excursion of x (peak to peak after removing linear drift) and the yaw RMS must be within this table (excursion in px at 1080 wide, yaw RMS in degrees):
Scene	Max excursion per 4 s	Max yaw RMS
1 train	8	0.5
2 train	8	0.5
3 boat	20	2.5
4 skater	60 (S-curve kept)	follow path tangent
5 horse	12	2
6 sailboat	20	2
7 paraglider	20	3
8 skier	15	2
9 cyclist	26	3
10 walker	42	4
11 hanging traveler, birds	20	4
12 A and B	30	4
Measure the original for scenes 7 and 12 with a proper hero tracker (template matching on the hero, seeded from a hand-picked box), since my thread tracker failed there. Save the results and adjust the table if the original moves more than I assumed.
The thread follows the owner. Because the owner no longer snakes, the thread's S-curves must come from wind and from slight gait or stroke pulses, not from the owner weaving. Keep it a flowing cord, never a straight rod.
3.5 Scene 5: the horse must be one connected animal

The body and shadow shapes are good. The problem is that the legs, neck, head and body are separate pieces.

One skinned mesh, one skeleton. Build the horse as a single skinned mesh (or a single connected rig of overlapping parts that share joints), with a spine, neck, head, ears, tail and four legs, each with 3 segments (upper, lower, hoof). Joints sit inside the overlapping parts: shoulders and hips overlap the torso, the neck base overlaps the withers, the head overlaps the neck end, legs attach at the shoulder and hip joints. No gaps in any pose.
Gait: a proper four-beat walk, leg order left hind, left fore, right hind, right fore, each foot planted while it touches the ground. Ground speed of a planted hoof equals the camera speed (slip at most 1 px per drawing). Head nods with the stride, a slight body roll, tail sways. Stride length equals ground speed times cycle time.
Rider: hips on the saddle, thighs along the horse's sides, hat, shoulders, arms reaching the reins, a small stable sway only. All attached.
Shadow: the shadow is projected from this same mesh and rider (keep the current shape quality), so it moves with the legs and stays connected.
Hoofprints: appear exactly where the hooves land, in correct left-right-fore-hind pairs, persistent, softened with distance; the thread leaves a faint groove in the sand.
Camera 5.9 px per drawing (v3 was 8.1).
Connectivity gate: render the horse and rider alone as an alpha mask at 12 gait phases and assert the mask is one connected piece (use the snippet in section 5). The shadow mask must also be one connected piece in every drawing.
3.6 Scene 6: nothing passes through anything

Problems: the boat, turtles, manta ray, aquatic plants and coral islands overlap and pass through each other, and the manta's body parts sometimes vanish.

Depth layers. Put every object on a layer and keep the order consistent:
Layer 0: sea floor (sand, ripples, caustics).
Layer 1: seagrass, plants, coral heads, rocks on the sea floor (submerged, tinted blue-green and slightly blurred by the water above).
Layer 2: swimming creatures (turtles, manta, fish) between the floor and the surface; tinted and slightly blurred by depth.
Layer 3: the water surface effects (ripples, foam, wake, glints).
Layer 4: things on the surface (boat hull, sail, rower, oars, thread).
Layer 5: land (islands above the waterline with sandy rims).
Colliders. Give every object a collider (ellipse or hull polygon) in world XY. Objects on the same layer must never overlap. Creatures steer around coral, islands, plants and the boat with obstacle avoidance (separation distance at least 1.2 times the sum of their radii) and avoid each other. A creature under the boat is allowed only if it is on a lower layer and is then drawn under the hull, occluded by it, tinted by the water.
The boat runs along the deep turquoise channel with at least 50 px clearance from every shallow coral head and island rim. The hull rests on the water: bow wave, V-wake, foam, ripples pushed outward; plants near the hull bend away with the wake. Boom, sail, mast, rower and oars are one connected object with sensible clearances (the boom must not pass through the rower or the sail edge).
The turtles swim with alternating flipper strokes, keep a gap from coral and each other, and dive (darken and blur) when the boat gets close.
The manta ray is one connected skinned shape with wings that undulate as a traveling wave, cephalic fins, tail and a soft shadow on the sand. It must never be hidden by a wrongly sorted layer: it lives on layer 2, coral on layer 1, so coral never covers it. Its wing tips and tail are present in every drawing.
Gates (print the output):
Collider overlap check (snippet in section 5): zero same-layer overlaps in every drawing (touching up to 1 px is allowed).
Manta continuity: its unoccluded silhouette is one connected component, and its area changes by at most 6 percent between consecutive drawings, except for a documented intentional occlusion by the hull.
Visual: scrub scene 6 at 12 drawings per second in a flipbook and confirm no object crosses another.
Camera 7.0 px per drawing (v3 was 5.9). Straight course (item 4).
3.7 Scene 11: real clouds

Original palette (frame about 3482): cream highlight 
#F1E1D7 (22 percent), peach-pink 
#DCC6C2 (16), 
#BFA9B3 (14), lavender 
#9C89A4 (13), violet 
#6F6B96 (13), deep blue gaps 
#475082 (17) and 
#2E3766 (5). Mean luma about 161. v3: four near-identical pale cream and pink tones cover 74 percent of the frame, the blue gaps only 10 percent, mean luma 200. The clouds are stacked circles.

No circles, no spheres. Do not build clouds from instanced discs, spheres or circle strokes. Build a cloud density field with domain-warped fractal noise (fBm with 6 to 7 octaves, billowy plus ridged mix, curl-noise warp), smooth-thresholded to get big irregular masses with a fractal edge whose bumps range from about 400 px down to about 20 px, in a power-law mix (a few large lobes, many small ones). No repeated lobes of the same radius.
Real shading from the density. Treat the cloud top as a height field (smoothed density to a power), derive normals, light them from the upper left: cream-white on the lit side (
#F9E6D8 to 
#F1E1D7), peach-pink mid, lavender and violet in the shaded flanks (
#9C89A4, 
#6F6B96), deep shadow where the cloud is thick and steep (
#475082), plus ambient occlusion from a blurred depth, bright rim light on the lit edges, and darker cores in the hollows. At least 30 percent of the cloud pixels must sit in the lavender and violet shadow range, and mean luma about 160 (plus or minus 12).
Painted look. The original's cloud surface is made of swirling brush strokes that follow the contour of the cloud (strokes along the tangent to the density contours with a curl swirl on top), 25 to 60 px long, 8 to 14 px wide, value-matched to the shading. Reproduce that (it is the cloud version of a painter's impasto), so the clouds read as painted volumes, not flat shapes.
Gaps. Deep blue gaps between clouds showing the sea far below, with subtle painted wave texture, about 20 to 25 percent of the frame, in 
#475082 to 
#2E3766.
Three layers with parallax: far (smaller scale, bluer, lower contrast, slow), middle (the main cumulus with full shading), near wisps (thin streaks, 5 to 15 percent of the area, semi-transparent, fast). Cloud shadows from the upper layer fall on the lower layer, offset along the light direction.
Motion: the clouds drift with the camera at the original's rate; edges churn very slightly at 12 Hz (that is the fine boil only, 3.1).
Camera 9.8 px per drawing, constant to the cut at frame 3648 (v3 was 3.0). Never stalls.
Birds and traveler: keep the current white paper-bird flock and the hanging traveler with a swaying thread, but apply item 4 (stable headings and formation) and keep their soft shadows on the cloud below.
4. Camera and timing fixes for the other scenes

Set these camera speeds (px per drawing, vertical, original values): scene 5 = 5.9, scene 6 = 7.0, scene 7 = 3.4, scene 9 = 8.2, scene 11 = 9.8, scene 8 = 8. Leave scenes 1, 2, 3, 4, 10, 12 unchanged. Gate in section 5.

5. Corrected measurement tools (use these; print the output)

Camera speed per scene by phase correlation (replaces the earlier motion ratio):

python
import cv2, subprocess, numpy as np
def gray_frames(p, start, n=8):
    raw = subprocess.run(["ffmpeg","-v","error","-ss",f"{start/24:.4f}","-i",p,
        "-vf","scale=540:960,format=gray","-frames:v",str(n),"-f","rawvideo","-"],
        capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1,960,540).astype(np.float32)
def distinct_pair(f):
    for i in range(len(f)-1):
        if np.abs(f[i+1]-f[i]).mean() > 0.3: return f[i], f[i+1]
def camera_px_per_drawing(p, start):          # at 1080 px wide
    a, b = distinct_pair(gray_frames(p, start))
    r = [cv2.phaseCorrelate(a[150:850,x0:x1], b[150:850,x0:x1]) for x0,x1 in ((20,170),(370,520))]
    (dx, dy), _ = max(r, key=lambda t: t[1])
    return abs(dy) * 2
cuts=[0,294,608,954,1314,1674,2078,2492,2646,2982,3316,3648,4004]
for i in range(12):
    a, b = cuts[i], cuts[i+1]
    pts = [a + int((b-a)*q) for q in (0.25, 0.55, 0.8)]
    print(i+1, [round(camera_px_per_drawing("out/final.mp4", p), 1) for p in pts])

Gate: each scene's value within 10 percent of the original's (table in section 0).

Connectivity of a rendered hero mask (horse, manta, any hero):

python
def one_piece(alpha):                  # alpha: uint8 mask (0 or 255) of the hero rendered alone
    m = (alpha > 127).astype(np.uint8)
    m = cv2.dilate(m, np.ones((3,3), np.uint8))      # tolerate 1 px seams only
    n, _ = cv2.connectedComponents(m)
    return (n - 1) == 1

Collision gate for scene 6 (log colliders per drawing to work/colliders.csv: frame,id,layer,cx,cy,rx,ry,deg; pip install shapely):

python
import csv, itertools
from shapely.geometry import Point
from shapely import affinity
def ell(cx,cy,rx,ry,deg):
    return affinity.rotate(affinity.scale(Point(cx,cy).buffer(1), rx, ry), deg, origin=(cx,cy))
rows = list(csv.DictReader(open("work/colliders.csv")))
by = {}
for r in rows: by.setdefault((r["frame"], r["layer"]), []).append(r)
bad = 0
for (fr, layer), objs in by.items():
    shp = [(o["id"], ell(*(float(o[k]) for k in ("cx","cy","rx","ry","deg")))) for o in objs]
    for (ia, a), (ib, b) in itertools.combinations(shp, 2):
        if a.buffer(-1).intersects(b.buffer(-1)):    # allow 1 px touching
            bad += 1; print("OVERLAP", fr, layer, ia, ib)
print("overlaps:", bad)

Tone check (mean luma, 5th and 95th percentile, mean saturation) at a mid-scene frame:

python
def tone(p, n):
    raw = subprocess.run(["ffmpeg","-v","error","-ss",f"{n/24:.4f}","-i",p,"-vf","scale=540:960",
        "-frames:v","1","-f","rawvideo","-pix_fmt","bgr24","-"], capture_output=True).stdout
    im = np.frombuffer(raw, np.uint8).reshape(960,540,3)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).ravel()
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).reshape(-1,3)
    sat = hsv[hsv[:,2]>40,1].mean()/255
    return round(float(g.mean()),1), int(np.percentile(g,5)), int(np.percentile(g,95)), round(float(sat),2)

Targets: scene 1 frame 146: mean 68 to 74, p5 at least 36, p95 at most 125. Scene 8 frame 2570: mean 90 to 105, p95 195 to 215, saturation at most 0.45. Scene 11 frame 3482: mean 148 to 172.

Wiggle: see 3.1, item 5. Hero motion: see 3.4, item 4.

6. Render time (keep it short)

I do not want long renders. Target about 2 hours or less in total.

Render even frames only (2002 distinct frames) and repeat each.
Reuse your caches. Keep the cached clean frames (before the wiggle) for every scene. The wiggle change (3.1) is a cheap 2D re-application for scenes that have no other change: re-apply it only to scenes 2, 4, 7, 10, 12 (and any scene where nothing else changes). Re-render the heavy content only for the scenes that changed: 1, 3, 5, 6, 8, 9, 11, plus scenes 4, 10, 12 only if the hero path, camera or yaw changes there (item 4).
Static plates stay baked. Do not re-simulate anything that did not change.
Iterate on 1/4-resolution stills and short 2-second clips. Maximum 3 QA rounds per scene. Render the full film once at the end, in parallel processes with resume.
Benchmark one frame per changed scene first, project the total, and write it in PROGRESS.md.
7. Gates (print every output in out/gates_report.md)
Audio packet MD5 equals the original's.
Cuts on the right frames; 4004 frames; no fade at the end.
On twos (duplicate pairs) in every scene.
Camera speed per scene within 10 percent of the original's (section 5).
Hero motion table (3.4), from work/hero_motion.csv.
Horse mask and shadow mask each one connected piece in every drawing of scene 5 (3.5).
Scene 6: zero same-layer collider overlaps; manta continuity (3.6).
Tone targets for scenes 1, 8 and 11 (section 5), and the scene 1 clear-corridor check (100 px).
Thread: one continuous thread per owner, no pops, in every scene; the ending beat unchanged.
Wiggle calibration printout (3.1, item 5) and the four flipbook clips.
Look checklist: for scenes 1, 5, 6, 8 and 11, view side-by-side 1:1 crops (original left, v4 right) of the hero and the ground and tick every bullet in section 3 for that scene. A bullet you cannot see at 1:1 is not done.
8. Deliverables

out/final.mp4 (silent video muxed with the original audio, -c copy), out/contact_sheet.jpg (original, v3 and v4 for scenes 1, 5, 6, 8 and 11, plus a 1:1 hero crop each), out/flipbook_*.mp4 (the four wiggle clips), out/gates_report.md, CREDITS.md, and an updated PROGRESS.md.

Start now with section 2, step 1.
</pasted_content id="06d4">
