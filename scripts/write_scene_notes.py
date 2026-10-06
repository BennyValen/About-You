# Writes work/scene_notes/XX.md from the measurements (camera.json, palettes) and the observations
# made while viewing work/ref4 sheets and the 1:1 crops in work/scene_notes/crops.
import json

cam = {s["scene"]: s for s in json.load(open("work/camera.json"))["scenes"]}
pal = {i: open(f"work/scene_notes/crops/s{i:02d}_palette.txt").read() for i in range(1, 13)}

N = {
    1: dict(
        title="Night train in a snowy pine forest",
        env="""- **Snow ground**: blue-violet snow (#434a6f / #54587a) with long wind-carved drift streaks, matte, painterly strokes.
- **Pine/spruce forest**: very dense conifers seen from straight above. Star-shaped crowns of 12–17 drooping branch tiers, dark navy needles (#1e233d–#2c3351), white snow on the branch tips (#9b92a2 and brighter). Each tree casts a crown-shaped shadow.
- **Track corridor**: cleared strip about 110 px wide at x=540, snowbanks with lit rims, twin dark rails, ties visible inside the headlight beam.
- **Fog banks**: soft white-lilac fog drifting across, thickest from frame 100 to 260.
- **Frozen pond**: a dark ice pond with streaky reflections enters top-left around frame 200.""",
        hero="""- **Train**: three dark graphite carriages (#2a2c3c), rounded roofs with 3–4 dark roof fans each, locomotive first (front at screen y=990), cars to y=1712, gangways between cars, x=540.
- **Window light**: warm orange (#ffb04a) slats of window light thrown sideways onto the snow, 60–90 px each side, broken by trees. Glowing window strips along both sides of every car.
- **Headlight**: a white cone up the track, 900+ px long, lighting the ties and the mist (volumetric).""",
        light="Moonlight from the upper-left (tree shadows fall lower-right, about 0.6 crown radius). Warm practical light from the train windows.",
        thread="Starts at the rear coupler of the last carriage (screen 540, 1712) and runs straight down the track bed to the bottom edge. Short (about 210 px), barely swaying.",
    ),
    2: dict(
        title="Contour-hedge forest and white train",
        env="""- **Hedge 'contour' maze**: tightly packed raised ridges in a fingerprint/topographic pattern. Each ridge is a rounded hedge about 20 px wide at 1080, with dark gaps between. Colours run lime (#b0d19c) → green (#50956b) → deep green (#245135), with teal patches (#3b7955 → teal) growing over the shot. Whorls, deltas and line endings like a fingerprint. Strong relief: ridges lit on top and shadowed on one flank.
- **Morph**: the ridge pattern re-draws **on twos** (every odd frame repeats the even one). It changes fast until about 17.2 s (frame 413), then slowly.
- **Track**: light grey ballast bed about 128 px wide at x=540, grey ties, steel rails; a rust strip on the left edge and a lime grass strip on the right.
- **Round bushes**: dark-green round bushes 30–55 px across, scattered on the hedges, with shadows.
- **Pale rocks**: small off-white angular rocks, some with a green tuft.
- **Mist**: soft white patches drift over in the second half.""",
        hero="**White modern train**: three cream-white cars (#efede6), rounded nose up the frame, roof equipment boxes with paired dark fans, a dark windscreen band at the nose, gangways. Front at screen y=980.",
        light="Daylight from the upper-left (ridge shadows fall lower-right). Soft and slightly hazy.",
        thread="Starts at the rear of the last car and runs down the middle of the track to the bottom edge.",
    ),
    3: dict(
        title="Rowboat between lily pads",
        env="""- **Pond water**: dark green (#1d362b–#2f4f3e), calm, faint ripples and soft reflections. Ring ripples where the oars dip.
- **Lily pads**: many round pads 60–300 px across in **lime (#b3d66f), yellow-green (#95b861) and mid-green (#729b54)**, crowded left and right, leaving a 300–400 px channel in the middle. Radial veins, a V notch, a slightly raised rim. **Dark submerged pads** (#243f32) underneath. Pads overlap and cast soft shadows on the water.
- **Koi/carp**: pale cream fish (#e2d6b4), 100–150 px long, gliding with a body wave under and between the pads.""",
        hero="""- **Rowboat**: wooden skiff (#b98a5a with darker planking), about 330 × 120 px, pointed bow up the frame, three thwarts, oarlocks, two long oars.
- **Rower**: one person sitting facing the stern (back to the direction of travel, as in real rowing), **indigo/purple jacket (#3f3f92)**, dark hair, hands on the oar handles.
- **Stroke**: period 60 frames (2.5 s), measured from the camera surge (camera dy 1.86–2.68 px/f around 2.32). Catch → drive (the boat surges) → release → recovery.""",
        light="Soft daylight from the upper-left; pads cast short shadows to the lower-right.",
        thread="Starts at the boat's **stern** and trails on the water behind the boat, wavy (floating, following the wake), to the bottom edge.",
    ),
    4: dict(
        title="Skater on a frozen lake under an aurora reflection",
        env="""- **Ice**: deep navy ice (#132245 / #20315c / #0d1532), translucent with depth, long painterly streaks, darker patches beneath.
- **Fracture lines**: thin light-cyan cracks (#4f9ec0) crossing at many angles, plus fine hairline cracks.
- **Frozen bubbles**: white/cyan bubble clusters and vertical strings of bubbles frozen in the ice.
- **Snow drifts**: white wind-blown snow patches streaked diagonally, mostly on the right.
- **Aurora reflection**: a broad pink–gold–violet band (#988ca6 / pink / gold) across the upper third, screen-fixed and glowing.
- **Skate marks**: white curved scratches behind the skater, plus older ones scattered around.""",
        hero="**Skater**: adult in a **white puffy coat (#ece9ee)**, **long dark hair** down the back, dark trousers, skates. Arms out for balance; each stride pushes a leg out to the side. Shadow to the lower-left.",
        light="Moon/aurora light from the upper-right; shadows fall lower-left (about 1 body length).",
        thread="Starts at the skater's **waist/back** and trails over the ice to the bottom edge, gently curving.",
    ),
    5: dict(
        title="Camel rider in the desert",
        env="""- **Sand**: warm orange sand (#eca073 / #f0b381 / #e19671) covered in **dense fine ripple lines** (light peach on orange, 8–12 px spacing) that meander and bunch up toward the dune shadows.
- **Dune ridges in shadow**: purple bands (#553b66 / #664874 / #845e86) meandering vertically on the left and right; the ripple lines continue in lavender inside them.
- **Footprints**: two staggered rows of dark oval camel footprints trailing behind.""",
        hero="**Camel and rider**: white/cream dromedary (#ece4dc) seen from above, long neck and small head up the frame, one hump, long legs, a **rider** behind the hump in a dark round hat. The camel's **long purple side-profile shadow** falls to the **right** (sun low on the left) and clearly shows the legs, neck and rider.",
        light="Low sun from the left; shadows fall right, 2–3× the camel's height.",
        thread="Starts at the camel's saddle/tail and **drags on the sand** between the footprint rows to the bottom edge.",
    ),
    6: dict(
        title="Sailboat over a turquoise lagoon",
        env="""- **Shallows**: pale sandy seabed under clear water (#dff6f0 / #c9f4ed), painterly white strokes and caustic streaks.
- **Channels**: winding deep-turquoise channels (#2595ac / #44a2ae / #2f7e90) with soft banks.
- **Coral heads**: crusty, knobbly coral clusters in **purple, olive, ochre/orange and grey-green** (#7c7e6b / #4f6461 ...), many sizes, larger toward the edges.
- **Sea life**: sea turtles swimming, small blue and orange starfish on the sand.
- **Manta ray**: slate-grey manta (#3e4e5e) gliding up-left of the boat, undulating wings, cephalic fins, whip tail, shadow on the seabed.""",
        hero="""- **Sailboat**: wooden dinghy (#c8955c, planked), pointed bow up, mast and boom, **white sail** heeled out to the **right**. Boat and sail shadows fall on the seabed to the right/lower-right.
- **Sailor**: in **navy/indigo**, hiking out over the left gunwale.
- A **wake** of white bubbles behind the stern.""",
        light="Bright sun from the upper-left; seabed shadows offset to the lower-right.",
        thread="Starts at the stern, floats on the surface and follows the wake down to the bottom edge.",
    ),
    7: dict(
        title="Paraglider over grey canyon country",
        env="""- **Rock**: blue-grey terrain (#8c909c / #a1a6b0 / #434c61) with relief, cliff edges and dark valleys.
- **Lichen**: mottled ochre-yellow/orange lichen fields (#c2a983 / #d9c7a0 → saturated yellow and orange) on the plateaus.
- **Rust**: orange-rust patches.
- **Tracks**: thin pale winding tracks/roads with parallel lines.
- **Clouds**: white cloud wisps drifting between camera and ground (parallax).
- **Birds**: two small brown birds upper-right, flapping and gliding.""",
        hero="**Paraglider**: **teal ribbed canopy (#2f9590)** about 420 × 120 px, curved crescent planform, darker leading-edge cells, white undersurface visible at the edges, pilot mostly hidden below. The canopy and pilot shadow falls on the ground far to the lower-left.",
        light="Sun from the upper-right; the glider's ground shadow is offset far to the lower-left.",
        thread="Hangs from the pilot's harness below the canopy and runs down/back to the bottom edge, nearly straight with slight sway.",
    ),
    8: dict(
        title="Night swimmer in bioluminescent water",
        env="""- **Water**: almost black navy (#040912 / #060d1c), faint plankton specks, very subtle streaks.
- **Bioluminescence**: bright cyan glow (#1d495d → #9ff6ff) erupting around the swimmer and trailing as a luminous turbulent wake down the frame, drifting slightly right, with sparkling particles.""",
        hero="**Swimmer**: a real human figure from above, a dark silhouette inside the glow (head, shoulders, one arm reaching forward over the head in a crawl stroke, the other pulling), legs kicking. Brightest glow at the hands and head.",
        light="No sun. The only light is the bioluminescence around the swimmer.",
        thread="Starts at the swimmer's waist/feet and runs down through the glowing wake to the bottom edge, wavy.",
    ),
    9: dict(
        title="Cyclist on a lakeside path",
        env="""- **Lake**: dark green-black water (#102222) on the left 41% of the frame, horizontal reflection streaks, lily pad clusters near the shore, a small wooden dock.
- **Path**: beige gravel path (#d9c99c) about 120 px wide at x=540, with a dark edge line.
- **Lawn**: lush streaky green grass (#396b38 / #4a713f / #588a43) on the right.
- **Trees**: big fluffy trees (#7c924e / #91a858 / #bac86c) with crowns of many spiky tufts, casting deep dappled shadows across the path and lawn to the lower-left.
- **Benches**: small wooden benches beside the path.""",
        hero="**Cyclist**: rider in a **white shirt** with long dark hair, on a dark bicycle, a **straw-yellow basket** at the front. Visible wheels and pedalling legs, contact shadow under the bike.",
        light="Sun from the upper-right; tree shadows fall lower-left, long and dappled.",
        thread="Starts at the rider's waist/rear rack and trails down the path to the bottom edge, slightly left.",
    ),
    10: dict(
        title="Walker between sunflower fields",
        env="""- **Sunflower fields**: rows of individual sunflowers from above: yellow petals (#e6c878 / #d9ba6f), dark brown discs (#442c1d), grey-olive leaves, dark soil (#594128).
- **Harvested field**: golden stubble (#d0ac62 / #bfa265) with fine diagonal row lines, top-left.
- **Hay bales**: a diagonal row of five round bales with spiral ends, each casting a long shadow to the lower-left.
- **Tree**: a single tree with a huge long shadow.
- **Dirt road**: diagonal road across the frame, rising to the right, with ruts and pale stones.
- **Path**: straw-edged dirt path running up the frame.""",
        hero="**Walker**: **white shirt**, dark hair, dark trousers, walking up the path with arms swinging. **Very long shadow to the lower-left.**",
        light="Low warm sun from the upper-right; shadows lower-left, 4–5× body height.",
        thread="Starts at the walker's waist/back and runs down the path to the bottom edge, wavy, lying on the dirt.",
    ),
    11: dict(
        title="Flock of white cranes over cumulus clouds",
        env="""- **Clouds**: peach-lavender cumulus tops (#ecd7ce / #f2e2d8 / #dcc2bf) with violet shadowed folds (#ac95a9 / #9f82a1), painterly swirls, seen from above.
- **Gaps**: deep blue-violet gaps (#384376 / #4a5284 / #60578b) to the world far below, with wind streaks. The gaps widen over the shot.
- **Bird shadows** fall on the cloud tops (lower-left).""",
        hero="**Cranes**: a V of **white cranes / origami-like birds**: broad white wings with **black flight-feather tips**, long neck, dark head, long trailing legs. Lead bird at screen centre (540, 1190); six or more others in a V behind.",
        light="Sun from the upper-right; shadows lower-left on the cloud tops.",
        thread="Hangs from the **lead crane** (under its body) down to the bottom edge, straight with slight sway.",
    ),
    12: dict(
        title="Two travelers meet on pink-lavender tidal flats",
        env="""- **Wet flats**: glossy shallow water (#dfbcb6 / #e4c4b8 / #c9a7b1), horizontal wind streaks, a warm sun glare (#f6d6a2) mid-frame (screen-fixed reflection).
- **Sandbars**: lavender-beige sand islands with dense diagonal **ripple marks**, soft edges.
- **Tidal creeks**: purple branching dendritic channels (#8a7497) carved into the sandbars.
- **Gulls**: small white gulls flying low (top-left), with shadows.""",
        hero="See `work/story_notes.md`. **A**: navy top, slate trousers, dark hair. **B**: pale top, dark hair; enters from the top at about 163.75 s.",
        light="Low warm sun from the upper-right; long violet shadows to the lower-left (3–4 body lengths).",
        thread="A: from the waist/back down to the bottom edge, dragging on the wet sand. B: from the waist/back up to the top edge. Never joined.",
    ),
}

SUBJ = {
    1: "train front (540, 990), last car end (540, 1712); fixed on screen",
    2: "train front (540, 980); fixed",
    3: "boat centre (540, 1180); fixed (camera follows the stroke surge)",
    4: "skater (540, 1160); fixed with small sway",
    5: "camel body (555, 1165); fixed",
    6: "boat centre (555, 1180); fixed",
    7: "canopy centre (540, 1180); fixed with slow pendulum sway",
    8: "swimmer head (545, 1130); fixed",
    9: "cyclist (540, 1180); fixed",
    10: "walker (560, 1200); fixed; framing drifts slowly left (dx -0.06 px/f)",
    11: "lead crane (540, 1190); fixed",
    12: "A at (403, 1297) fixed until the camera stops (~f3966), then A walks up to about (500, 1000); B enters at the top (718, 0) at f3930 and walks down to about (575, 850)",
}
EXTRA = {
    3: "The speed oscillates between 1.86 and 2.68 px/f with a **60-frame period** (rowing stroke surge); the camera follows the boat.",
    8: "Cluster KLT gives about 1.6 px/f (phase correlation is unreliable on the black water). The camera follows the swimmer.",
    11: "**The camera moves at a constant 4.97 px/f right up to the cut** (band-pass and cluster tracker; plain phase correlation wrongly reports a stop in the last 4 s because of a screen-fixed texture).",
    12: "Accelerates from 8.4 px/f (3648–3685) to about 13.5 px/f by 3720, holds 13–14.5 px/f until about 3935, decelerates (8.1 at 3939, 3.5 at 3951, 0.8 at 3963) and is **still from about 3966 to the end** while both people keep walking.",
}
for i, n in N.items():
    c = cam[i]
    per_s = [round(x[1], 2) for x in c["klt_series"][::8]]
    txt = f"""# Scene {i:02d} — {n['title']}

Frames {c['start']}–{c['end'] - 1} ({c['start'] / 24:.2f}–{c['end'] / 24:.2f} s). Reference: `work/ref4/` (4 frames per second); crops: `work/scene_notes/crops/s{i:02d}.jpg` (10/50/90% frames plus 1:1 crops at the subject).

## Environment and materials
{n['env']}

## Hero subject
{n['hero']}

## Screen position (measured)
{SUBJ[i]}

## Light
{n['light']}

## Palette (median-cut, mid frame)
`{pal[i]}`

## Red thread
{n['thread']}

## Camera (work/camera.json)
Straight top-down, travelling **up the frame**. Background flow dy = **{c['dy_klt_median']} px/frame** ({c['dy_klt_median'] * 24:.0f} px/s), dx ≈ 0. Every 2 s: {per_s}.
{EXTRA.get(i, '')}
"""
    open(f"work/scene_notes/{i:02d}.md", "w", encoding="utf8").write(txt)
print("written 12 scene notes")
