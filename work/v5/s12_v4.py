"""Scene 12 (frames 3648-4003): pink-lavender dunes at a low sun. A walks up the frame trailing a red thread down
to the bottom edge; at ~3930 (163.75 s) B walks in from the top edge with their own thread trailing up to the top
edge. The camera eases to a stop at ~3966; both keep walking and end a few steps apart, still moving. No third
thread, no joining thread, no fade.

v3: dunes as real geometry (crests, gentle windward slopes, steep lee slip faces in shadow), anisotropic wind
ripples that follow the dune shapes, CC0 sand grain, dry grass tufts and leafless shrubs (instanced, varied) whose
long branching purple shadows lie across the sand, interdune flats with wind streaks and a warm sun glow,
chunky painted figures with planted feet and persistent footprints, gulls, and two world-space ropes.
Positions of A and B come from measured screen tracks (work/s12_track.json, work/story_notes.md)."""
import json, math, os
import numpy as np
import bpy
from kit import core, look, geo, human, plants, rope_io
from kit.look import _n, _l, _math, _mixrgb
from kit.paths import KeyPath

SCENE = 12
PPM = 130.0
SUN_DIR = (0.55, 0.83, 0.25)           # toward the sun: upper-right, low -> long shadows to the lower-left
POST = dict(light_deg=56.0, flow_deg=8.0, stroke_px=12.0, boil_mean=2.0, thread_shadow_px=1.8, repaint=0.55)

# dune bodies authored from the reference mosaic (world metres; camera starts at y = 0): cx, cy, rx, ry, rot
BARS = [(-0.77, -1.82, 3.7, 2.15, 0.15), (-2.92, -5.8, 2.15, 1.85, 0.0), (-3.6, -8.2, 2.5, 2.0, 0.0),
        (1.69, 6.25, 0.8, 0.55, 0.4), (-2.31, 17.9, 3.4, 3.4, 0.3), (-4.2, 21.0, 2.0, 2.4, 0.0),
        (0.15, 24.6, 5.4, 2.5, -0.18), (2.3, 19.6, 2.3, 3.1, 0.2), (2.9, 26.4, 2.6, 1.5, -0.3), (2.0, 33.0, 3.1, 2.15, 0.25), (4.3, 35.2, 2.4, 1.8, 0.0)]
LEE = np.array([-0.55, -0.83])          # lee side (away from the sun / downwind)
CREST_H = 0.34


def dune_field(x, y):
    F = np.full_like(np.asarray(x, float), -1.0)
    for cx, cy, rx, ry, rot in BARS:
        c, s = math.cos(rot), math.sin(rot)
        dx, dy = x - cx, y - cy
        u, v = (c * dx + s * dy) / rx, (-s * dx + c * dy) / ry
        F = np.maximum(F, 1.0 - np.sqrt(u * u + v * v))
    return F + 0.2 * geo.fbm2(x * 0.45, y * 0.45, 4, 7) + 0.07 * geo.fbm2(x * 1.6, y * 1.6, 3, 11)


def dune_height(x, y):
    """asymmetric dunes: gentle windward rise, plateau, steep lee slip face (max over lee-shifted copies)"""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    H = np.zeros_like(x)
    for k, w in ((0.0, 1.0), (0.25, 0.97), (0.5, 0.93), (0.75, 0.88)):
        F = dune_field(x - LEE[0] * k, y - LEE[1] * k)
        t = np.clip((F + 0.04) / 0.5, 0, 1)
        H = np.maximum(H, w * t * t * (3 - 2 * t))
    return CREST_H * H + 0.012 * geo.fbm2(x * 3.0, y * 3.0, 2, 3)


def ground(x, y):
    return np.maximum(dune_height(x, y), 0.0)


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


# measured screen tracks (full-res px). A: dark torso blob (z~1.3). B: head (z~1.55).
A_TRACK = [(3648, 402, 1319), (3672, 403, 1316), (3696, 403, 1300), (3720, 403, 1297), (3800, 403, 1296), (3880, 403, 1296),
           (3920, 403, 1296), (3926, 403, 1295), (3930, 404, 1289), (3934, 404, 1280), (3938, 409, 1270), (3942, 413, 1253),
           (3946, 418, 1237), (3950, 425, 1222), (3954, 433, 1202), (3958, 439, 1181), (3962, 446, 1160), (3966, 452, 1141),
           (3970, 459, 1117), (3976, 470, 1086), (3982, 482, 1052), (3986, 491, 1030), (3990, 495, 1010), (3994, 499, 997),
           (3998, 503, 986), (4002, 506, 979)]
B_TRACK = [(3930, 716, 40), (3934, 703, 140), (3938, 693, 236), (3942, 688, 306), (3948, 676, 410), (3954, 664, 500),
           (3960, 650, 566), (3966, 636, 622), (3972, 622, 662), (3978, 608, 698), (3984, 596, 740), (3990, 584, 778),
           (3996, 575, 800), (4002, 568, 818)]


def ripple_signal(nt, pos):
    """(ripple, streak) sockets: anisotropic wind ripples bending with the dune height (on the dunes),
    fine elongated wind streaks (on the flats)"""
    sz = _n(nt, "ShaderNodeSeparateXYZ", (-1850, -600))
    _l(nt, pos, sz.inputs[0])
    hwarp = _n(nt, "ShaderNodeCombineXYZ", (-1700, -700))
    _l(nt, _math(nt, "MULTIPLY", sz.outputs[2], 4.0, (-1800, -700)), hwarp.inputs[0])
    wn = _n(nt, "ShaderNodeTexNoise", (-1800, -850))
    _l(nt, pos, wn.inputs["Vector"])
    wn.inputs["Scale"].default_value = 0.5
    wn.inputs["Detail"].default_value = 2
    wo = _n(nt, "ShaderNodeVectorMath", (-1650, -850), operation="SCALE")
    _l(nt, wn.outputs["Color"], wo.inputs[0])
    wo.inputs["Scale"].default_value = 0.6
    p2 = _n(nt, "ShaderNodeVectorMath", (-1550, -650), operation="ADD")
    _l(nt, pos, p2.inputs[0])
    _l(nt, hwarp.outputs[0], p2.inputs[1])
    p3 = _n(nt, "ShaderNodeVectorMath", (-1450, -700), operation="ADD")
    _l(nt, p2.outputs[0], p3.inputs[0])
    _l(nt, wo.outputs[0], p3.inputs[1])
    mp = _n(nt, "ShaderNodeMapping", (-1350, -650))
    _l(nt, p3.outputs[0], mp.inputs[0])
    mp.inputs["Rotation"].default_value = (0, 0, -0.62)
    wv = _n(nt, "ShaderNodeTexWave", (-1150, -650), wave_type="BANDS", bands_direction="X", wave_profile="SIN")
    _l(nt, mp.outputs[0], wv.inputs["Vector"])
    wv.inputs["Scale"].default_value = 3.2
    wv.inputs["Distortion"].default_value = 0.6
    wv.inputs["Detail"].default_value = 1.0
    on = _n(nt, "ShaderNodeMapRange", (-1150, -450), clamp=True)
    _l(nt, sz.outputs[2], on.inputs["Value"])
    on.inputs["From Min"].default_value, on.inputs["From Max"].default_value = 0.01, 0.07
    # ripples are crisper on the windward faces, washed out on the steep slip faces
    rip = _math(nt, "MULTIPLY", wv.outputs["Fac"], on.outputs["Result"], (-950, -550))
    st = _n(nt, "ShaderNodeMapping", (-1350, -950))
    _l(nt, pos, st.inputs[0])
    st.inputs["Scale"].default_value = (0.05, 5.5, 1.0)
    sn = _n(nt, "ShaderNodeTexNoise", (-1150, -950))
    _l(nt, st.outputs[0], sn.inputs["Vector"])
    sn.inputs["Scale"].default_value = 1.4
    sn.inputs["Detail"].default_value = 6
    sn.inputs["Roughness"].default_value = 0.62
    streak = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", sn.outputs["Fac"], 0.5, (-1000, -950)),
                   _math(nt, "SUBTRACT", 1.0, on.outputs["Result"], (-950, -1050)), (-850, -950))
    return rip, streak


def sand_material(rig):
    def base(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-2000, 300))
        pos = g.outputs["Position"]
        sz = _n(nt, "ShaderNodeSeparateXYZ", (-1800, 300))
        _l(nt, pos, sz.inputs[0])
        # height bands: lavender flats -> pink mid -> cream crests
        hb = _n(nt, "ShaderNodeMapRange", (-1600, 300), clamp=True, interpolation_type="SMOOTHSTEP")
        _l(nt, sz.outputs[2], hb.inputs["Value"])
        hb.inputs["From Min"].default_value, hb.inputs["From Max"].default_value = 0.0, CREST_H * 0.9
        c = _mixrgb(nt, "MIX", hb.outputs["Result"], core.hexc("#c2a7c6"), core.hexc("#efd2bf"), (-1400, 300))
        # broad colour drift (warmer/cooler patches)
        n1 = _n(nt, "ShaderNodeTexNoise", (-1600, 550))
        _l(nt, pos, n1.inputs["Vector"])
        n1.inputs["Scale"].default_value = 0.22
        n1.inputs["Detail"].default_value = 3
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", n1.outputs["Fac"], 0.35, (-1400, 550)), c, core.hexc("#d6aab8"), (-1200, 400))
        # warm sun glow fixed to the camera (glare on the flats, as in the original)
        tc = _n(nt, "ShaderNodeTexCoord", (-1800, -100), object=rig.obj)
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-1650, -100))
        _l(nt, tc.outputs["Object"], sx.inputs[0])
        dx = _math(nt, "DIVIDE", sx.outputs[0], 5.5, (-1500, -60))
        dy = _math(nt, "DIVIDE", _math(nt, "SUBTRACT", sx.outputs[1], 1.6, (-1500, -140)), 4.6, (-1380, -140))
        r2 = _math(nt, "ADD", _math(nt, "MULTIPLY", dx, dx, (-1250, -60)), _math(nt, "MULTIPLY", dy, dy, (-1250, -140)), (-1100, -100))
        glow = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", r2, -1.0, (-950, -100)), None, (-820, -100))
        c = _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", glow, 0.8, (-700, -100)), c, core.hexc("#f8df9f"), (-600, 200))
        # painted ripple stripes on the dunes and fibrous wind streaks on the flats, in colour (not only bump)
        c = look.mul_color(nt, c, _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", ripple_signal(nt, pos)[0], 0.16, (-700, 900)), (-600, 900)), (-450, 600))
        c = look.mul_color(nt, c, _math(nt, "ADD", 0.98, _math(nt, "MULTIPLY", ripple_signal(nt, pos)[1], 0.55, (-700, 1000)), (-600, 1000)), (-350, 600))
        # CC0 sand grain detail (Poly Haven aerial_sand), in the scene palette
        det = look.tex_value_detail(nt, "aerial_sand", size_m=1.6, amount=0.22, loc=(-1000, 700))
        c = look.mul_color(nt, c, det, (-400, 300))
        return c

    def height(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-2000, -600))
        rip, streak = ripple_signal(nt, g.outputs["Position"])
        grain = look.tex_height(nt, "aerial_sand", size_m=1.6, loc=(-1150, -1250))
        h = _math(nt, "ADD", _math(nt, "MULTIPLY", rip, 0.7, (-750, -600)), _math(nt, "MULTIPLY", streak, 0.3, (-750, -900)), (-600, -700))
        return _math(nt, "ADD", h, _math(nt, "MULTIPLY", grain, 0.25, (-750, -1200)), (-450, -800))

    return look.cel("sand", core.hexc("#d8bab6"), shadow=(0.6, 0.52, 0.78, 1), high=(1.1, 1.05, 0.98, 1), t1=0.36, t2=0.97,
                    paint=0.05, paint_scale=3.0, rough=0.85, base_node=base, height_node=height, bump=0.35, bump_dist=0.015,
                    soft=0.16, ao=0.5, ao_dist=0.4)


def make_gull(name, mat_w, mat_tip, coll):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.035, 0.11, 0.03), verts=bm.verts)
    body = geo.bm_to_object(bm, name, mat_w, coll)
    wings = []
    for side in (-1, 1):
        bm = bmesh.new()
        pts = [(0, 0.03, 0), (0.07 * side, 0.045, 0.01), (0.16 * side, 0.01, 0.0), (0.17 * side, -0.02, 0), (0.06 * side, -0.035, 0.005), (0, -0.03, 0)]
        vs = [bm.verts.new(p) for p in pts]
        f = bm.faces.new(vs if side > 0 else vs[::-1])
        bmesh.ops.solidify(bm, geom=[f], thickness=0.006)
        w = geo.bm_to_object(bm, f"{name}_w{side}", mat_w, coll, smooth=False)
        w.data.materials.append(mat_tip)
        for p in w.data.polygons:
            if abs(p.center.x) > 0.12:
                p.material_index = 1
        w.parent = body
        wings.append(w)
    return body, wings


def footprint_proto(name, mat, coll):
    """a shallow foot-shaped dent: an oval with a heel/toe split, with a baked radial 'r' attribute for soft edges"""
    n = 24
    V = [(0.0, 0.0, 0.0)]
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = 0.05 * math.cos(a), 0.125 * math.sin(a)
        if abs(y) < 0.03:
            x *= 0.82              # waist of the sole
        V.append((x, y, 0.0))
    F = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    ob = geo.mesh_from_arrays(name, np.array(V), F, coll, smooth=True, mat=mat)
    r = np.array([0.0] + [1.0] * n, np.float32)
    a = ob.data.attributes.new("r", "FLOAT", "POINT")
    a.data.foreach_set("value", r)
    return ob


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    amb = 0.24
    core.world_ambient(core.hexc("#b9a6c8"), 0.36)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.8, SUN_DIR, amb), core.hexc("#fff0dc"), angle_deg=2.5)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.35)
    y1 += 4.0
    step = 0.04
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    hg = geo.HeightGrid(ground, x0 - 2, y0 - 2, x1 + 2, y1 + 2, step)
    sand = geo.grid("dunes", x0, y0, x1, y1, nx, ny, hg, env, sand_material(rig))
    dh = hg                                   # fast baked dune height (rope contact, feet, scatter)
    rng = np.random.default_rng(1212)

    # ---------------------------------------------------------------- vegetation (instanced, varied)
    protos = geo.proto_collection("P_veg")
    twig = look.cel("twig", core.hexc("#d8c4c6"), shadow=(0.6, 0.53, 0.78, 1), high=(1.08, 1.05, 1.0, 1), paint=0.04, soft=0.22, ao=0.3)
    straw = look.cel("straw", core.hexc("#f3e2c6"), shadow=(0.66, 0.58, 0.8, 1), high=(1.06, 1.04, 1.0, 1), paint=0.04, soft=0.22,
                     ao=0.4, base_node=look.instancer_palette([core.hexc("#ecd6b4"), core.hexc("#e2c7a8"), core.hexc("#f1dfc2"),
                                                               core.hexc("#d9bba3")]))
    for i in range(5):
        plants.shrub(f"shrub_{i}", twig, protos, seed=40 + i, height=rng.uniform(1.5, 2.1), depth=4, spread=1.15, twig_r=0.02, base_r=0.08)
    for i in range(6):
        plants.grass_tuft(f"tuft_{i}", straw, protos, seed=70 + i, height=rng.uniform(0.18, 0.32))
    # shrubs: on dune flanks and the edges of the flats; grass tufts: on the dunes
    def on_dune(px, py):
        return dh(px, py) > 0.04
    sp = geo.poisson(rng, 26, x0, y0, x1, y1, 3.4, accept=lambda px, py: 0.01 < dh(px, py) < 0.2)
    sp = np.array(sp)
    shrub_pos = np.c_[sp, dh(sp[:, 0], sp[:, 1]) - 0.01]
    geo.instances("shrubs", protos, shrub_pos, rot=np.c_[np.zeros(len(sp)), np.zeros(len(sp)), rng.uniform(0, 6.28, len(sp))],
                  scl=np.repeat(rng.uniform(0.8, 1.4, len(sp))[:, None], 3, 1), variant=rng.integers(0, 5, len(sp)), coll=env)
    # tufts grow in loose clusters on the dunes
    centres = geo.poisson(rng, 60, x0, y0, x1, y1, 1.6, accept=on_dune)
    tp = []
    for cx, cy in centres:
        for k in range(int(rng.integers(1, 5))):
            q = (cx + rng.normal(0, 0.35), cy + rng.normal(0, 0.35))
            if on_dune(*q):
                tp.append(q)
    tp = np.array(tp)
    nt_ = len(tp)
    geo.instances("tufts", protos, np.c_[tp, dh(tp[:, 0], tp[:, 1]) - 0.005],
                  rot=np.c_[np.zeros(nt_), np.zeros(nt_), rng.uniform(0, 6.28, nt_)],
                  scl=np.repeat(rng.uniform(0.7, 1.3, nt_)[:, None], 3, 1), variant=5 + rng.integers(0, 6, nt_),
                  tint=rng.uniform(0, 1, nt_), coll=env)

    # ---------------------------------------------------------------- people
    def mats(prefix, top, legs, hair, skin="#d9ae98", shoes="#d9ae98"):
        return dict(top=look.cel(f"{prefix}_top", core.hexc(top), shadow=(0.55, 0.55, 0.78, 1), high=(1.15, 1.12, 1.08, 1), paint=0.05,
                                 soft=0.22, rim=0.25, hero=True),
                    legs=look.cel(f"{prefix}_legs", core.hexc(legs), shadow=(0.55, 0.55, 0.78, 1), paint=0.04, soft=0.22, hero=True),
                    shoes=look.cel(f"{prefix}_shoes", core.hexc(shoes), paint=0.0, soft=0.2, hero=True),
                    hands=look.cel(f"{prefix}_hands", core.hexc(skin), paint=0.0, soft=0.25, hero=True),
                    skin=look.cel(f"{prefix}_skin", core.hexc(skin), paint=0.0, soft=0.25, hero=True),
                    hair=look.cel(f"{prefix}_hair", core.hexc(hair), shadow=(0.5, 0.5, 0.6, 1), high=(1.3, 1.25, 1.2, 1), paint=0.03,
                                  soft=0.18, rim=0.3, hero=True))
    A = human.Human("A", mats("A", "#4d55a6", "#757a99", "#2e2220"), hair="short", height=1.95, coll=ink,
                    bulk={"top": 1.45, "legs": 1.15, "hands": 1.25})
    B = human.Human("B", mats("B", "#efe9e4", "#d8b6a2", "#2f2224"), hair="long", height=1.9, coll=ink,
                    bulk={"top": 1.25, "legs": 1.08, "hands": 1.15})
    A.hair_scale, B.hair_scale = 1.08, 1.12

    def to_ground(track, z):
        return [(f, *rig.screen_to_world(f, sx, sy, z)[:2]) for f, sx, sy in track]
    pa = KeyPath(to_ground(A_TRACK, 1.45), start - 160, end + 40, sigma=3.0)
    pb = KeyPath(to_ground(B_TRACK, 1.7), start - 40, end + 40, sigma=2.5)
    mot = rope_io.C.owner_motion(SCENE)
    # the owner's own path weave/sway (shared with the rope attach point): the body moves with it
    def pa_pos(t):
        x, y = pa.pos(t)
        return (x + mot(t)[0], y)
    def pb_pos(t):
        x, y = pb.pos(t)
        return (x - 0.6 * mot(t + 37)[0], y)
    gnd = lambda x, y: dh(float(x), float(y))
    wa = human.Walker(pa_pos, pa.heading, start - 140, end + 20, height=1.95, ground=gnd, arm_swing=0.5)
    wb = human.Walker(pb_pos, pb.heading, start - 20, end + 20, height=1.9, ground=gnd, arm_swing=0.45)
    B_START = start + 200

    # footprints: every plant of each foot, appearing when the foot lands, persistent
    fp_mat = look.cel("footprint", core.hexc("#a993b6"), shadow=(0.7, 0.62, 0.82, 1), paint=0.0, soft=0.3, alpha=0.75, ao=0.0,
                      base_node=None)
    def fp_alpha(nt):
        at = _n(nt, "ShaderNodeAttribute", (-400, -300), attribute_type="GEOMETRY", attribute_name="r")
        return _math(nt, "SUBTRACT", 1.0, _math(nt, "POWER", at.outputs["Fac"], 3.0, (-250, -300)), (-100, -300))
    grp = [n for n in fp_mat.node_tree.nodes if n.type == "GROUP"][0]
    _l(fp_mat.node_tree, _math(fp_mat.node_tree, "MULTIPLY", fp_alpha(fp_mat.node_tree), 0.7, (0, -300)), grp.inputs["Alpha"])
    fprotos = geo.proto_collection("P_foot")
    footprint_proto("fp", fp_mat, fprotos)

    def plants_of(walker, t0, t1):
        out = []
        c0, c1 = int(math.floor(walker.cycles(t0))) - 1, int(math.ceil(walker.cycles(t1))) + 1
        for ci in range(c0, c1 + 1):
            for off, lat in ((0.0, -0.1), (0.5, 0.1)):
                tc = walker.time_at_phase(ci + off + walker.duty / 2)
                tland = walker.time_at_phase(ci + off)
                p, hd = walker._plant(ci, off, lat * walker.h / 1.72)
                out.append((tland, p[0], p[1], p[2], hd))
        return out
    prints = plants_of(wa, start - 140, end) + [p for p in plants_of(wb, B_START - 30, end) if p[0] >= B_START - 30]
    prints = np.array(prints)
    nfp = len(prints)
    far = np.array([0.0, -1e4, -50.0])
    fp_obj = geo.instances("footprints", fprotos, np.tile(far, (nfp, 1)), rot=np.c_[np.zeros(nfp), np.zeros(nfp), prints[:, 4]],
                           variant=np.zeros(nfp, int), coll=env)

    # ---------------------------------------------------------------- threads (v3 ropes)
    frames = list(range(start, end, 2))

    def anchor_of(walker):
        return walker.attach
    rope_a = rope_io.Owner("A", SCENE, rig, anchor_of(wa), frames, trail=(0.0, -1.0), ground_fn=dh, warm=150, cfg_motion=False,
                           heading_fn=pa.heading)
    b_frames = [f for f in frames if f >= B_START]
    rope_b = rope_io.Owner("B", SCENE, rig, anchor_of(wb), b_frames, trail=(0.25, 1.0), ground_fn=dh, warm=120, seed_offset=5,
                           heading_fn=pb.heading,
                           cfg_motion=False)

    # ---------------------------------------------------------------- gulls
    gw = look.cel("gull", core.hexc("#f6f3ef"), shadow=(0.72, 0.68, 0.84, 1), paint=0.0, soft=0.2, hero=True)
    gt = look.cel("gull_tip", core.hexc("#55505e"), paint=0.0, hero=True)
    gulls = []
    for i in range(6):
        body, wings = make_gull(f"gull{i}", gw, gt, ink)
        gulls.append(dict(body=body, wings=wings, early=i < 3, ph=rng.uniform(0, 6.28), r=rng.uniform(0.6, 1.4),
                          off=(rng.uniform(-60, 60), rng.uniform(-60, 60))))

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.45, bloom_threshold=0.92, streak=0.08, streak_threshold=1.25,
                         lift=(0.99, 0.985, 1.03), gain=(1.03, 1.0, 0.975), vignette=0.22, ink=0.3,
                         ink_normal=(0.7, 1.6), ink_depth=(0.06, 0.3), saturation=1.1), res_scale=opt.scale)

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        for Hm, wk in ((A, wa), (B, wb)):
            Jw, hd, _ = wk.pose(d)
            Hm.set_world(Jw, hd)
        vis_b = d >= B_START
        for o in B.all_objects():
            o.hide_render = not vis_b
        # footprints that have landed by now (B's only once B is in)
        pos = np.tile(far, (nfp, 1))
        on = prints[:, 0] <= d
        pos[on] = prints[on, 1:4] + np.array([0, 0, 0.004])
        geo.update_points(fp_obj, pos)
        for g in gulls:
            t = d - start
            if g["early"]:
                cx, cy = 230 + g["off"][0] + 70 * math.sin(t * 0.02 * g["r"] + g["ph"]), 1350 + g["off"][1] + 40 * math.cos(t * 0.025 + g["ph"])
                cx -= t * 0.6
                cy += t * 1.2
            else:
                cx, cy = 150 + g["off"][0] + 50 * math.sin(t * 0.02 + g["ph"]), 150 + g["off"][1] + 30 * math.cos(t * 0.03 * g["r"])
            p = rig.screen_to_world(f, cx, cy, 2.2)
            heading = math.atan2(-1.0, 0.4) + 0.4 * math.sin(t * 0.03 + g["ph"])
            g["body"].location = (p[0], p[1], 2.2)
            g["body"].rotation_euler = (0, 0, heading)
            flap = 0.55 * math.sin(d * 0.55 + g["ph"])
            for w, side in zip(g["wings"], (-1, 1)):
                w.rotation_euler = (0, -side * flap, 0)
            vis = (t < 150) if g["early"] else (t > 120)
            for o in [g["body"]] + g["wings"]:
                o.hide_render = not vis
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig

    def finish(out):
        rope_io.export(out, [rope_a, rope_b])
    r.finish = finish
    return r
