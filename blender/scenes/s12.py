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
    A = human.Human("A", mats("A", "#4d55a6", "#757a99", "#2e2220", shoes="#2a2630"), hair="short", height=1.95, coll=ink,
                    bulk={"top": 1.45, "legs": 1.15, "hands": 1.25, "shoes": 0.65})
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
    # v5: A runs (stride = clamp(speed / 3 steps/s, 46, 60) px, two flight phases per cycle) until the meeting point,
    # then slows to a walk over 1 s (3930 -> 3954) and is still walking when the film ends
    RUN_END0, RUN_END1 = 3930, 3954

    def run_amt(t):
        u = min(max((t - RUN_END0) / (RUN_END1 - RUN_END0), 0.0), 1.0)
        return 1.0 - u * u * (3 - 2 * u)
    wa = human.Runner(pa_pos, pa.heading, start - 140, end + 20, height=1.95, ground=gnd, ppm=PPM, run=run_amt)
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
    prints = [p for p in plants_of(wb, B_START - 30, end) if p[0] >= B_START - 30]
    prints = np.array(prints)
    nfp = len(prints)
    far = np.array([0.0, -1e4, -50.0])
    fp_obj = geo.instances("footprints", fprotos, np.tile(far, (nfp, 1)), rot=np.c_[np.zeros(nfp), np.zeros(nfp), prints[:, 4]],
                           variant=np.zeros(nfp, int), coll=env)
    fpa_mat = look.cel("footprint_a", core.hexc("#8a74a2"), shadow=(0.7, 0.62, 0.82, 1), paint=0.0, soft=0.3, alpha=0.5, ao=0.0)
    ga_ = [n for n in fpa_mat.node_tree.nodes if n.type == "GROUP"][0]
    ia_ = _n(fpa_mat.node_tree, "ShaderNodeAttribute", (-400, -500), attribute_type="INSTANCER", attribute_name="tint")
    _l(fpa_mat.node_tree, _math(fpa_mat.node_tree, "MULTIPLY", fp_alpha(fpa_mat.node_tree), ia_.outputs["Fac"], (0, -400)), ga_.inputs["Alpha"])
    fpa_protos = geo.proto_collection("P_foot_a")
    fpa = footprint_proto("fpa", fpa_mat, fpa_protos)
    for v_ in fpa.data.vertices:                     # 0.06 x 0.078 m -> about 8 x 10 px
        v_.co.x *= 0.6
        v_.co.y *= 0.31
    a_prints = np.array(wa.plants(start - 140, end))
    nfa = len(a_prints)
    fpa_obj = geo.instances("footprints_a", fpa_protos, np.tile(far, (nfa, 1)),
                            rot=np.c_[np.zeros(nfa), np.zeros(nfa), a_prints[:, 4]], tint=np.zeros(nfa), coll=env)
    # dust at every foot strike: 4 sand-coloured specks, 40 % opacity, 0.4 s, spreading 4 -> 10 px
    dust_m = look.cel("dust", core.hexc("#ecd8c4"), paint=0.0, soft=0.4, alpha=0.5, ao=0.0)
    gd_ = [n for n in dust_m.node_tree.nodes if n.type == "GROUP"][0]
    id_ = _n(dust_m.node_tree, "ShaderNodeAttribute", (-400, -300), attribute_type="INSTANCER", attribute_name="tint")
    _l(dust_m.node_tree, id_.outputs["Fac"], gd_.inputs["Alpha"])
    dprot = geo.proto_collection("P_dust")
    import bmesh as _bm
    bm_ = _bm.new()
    _bm.ops.create_icosphere(bm_, subdivisions=1, radius=0.012)
    geo.bm_to_object(bm_, "speck", dust_m, dprot)
    ND = 4
    nd = nfa * ND
    drng = np.random.default_rng(1203)
    d_ang = drng.uniform(0, 2 * math.pi, nd)
    d_rad = drng.uniform(0.7, 1.0, nd)
    dust_obj = geo.instances("dust", dprot, np.tile(far, (nd, 1)), tint=np.zeros(nd), coll=env)
    for o_ in (fpa_obj, dust_obj):
        o_.visible_shadow = False

    # ---------------------------------------------------------------- threads (v3 ropes)
    frames = list(range(start, end, 2))

    def anchor_of(walker):
        return walker.attach
    def calm_near_runner(wind):
        def w(P, t):
            out = wind(P, t)
            dist = np.linalg.norm(P[:, :2] - P[0, :2], axis=1)
            k_ = np.clip(dist / 0.92, 0.0, 1.0) * 0.6 + 0.4          # 0.4 at the anchor -> 1.0 beyond ~120 px
            out[:, 0] *= k_
            return out
        return w
    rope_a = rope_io.Owner("A", SCENE, rig, anchor_of(wa), frames, trail=(0.0, -1.0), ground_fn=dh, warm=150, cfg_motion=False,
                           heading_fn=pa.heading, wind_wrap=calm_near_runner)
    b_frames = [f for f in frames if f >= B_START]
    rope_b = rope_io.Owner("B", SCENE, rig, anchor_of(wb), b_frames, trail=(0.25, 1.0), ground_fn=dh, warm=120, seed_offset=5,
                           heading_fn=pb.heading,
                           cfg_motion=False)

    # ---------------------------------------------------------------- birds (v5)
    # six small pale gulls in a loose group at the top left, present from the first drawing, flying up and a little left
    # at 55-80 px/s over the ground (the camera outruns them, so they drift down the left side and leave by the edge).
    # Each bird is one mesh: body, tail, and two 3-segment wing chains posed per drawing from a stylised 1.5 Hz beat
    # (8 drawings per cycle, desynchronised, +-6 %), flap-and-glide (4-6 beats, then 0.8-1.4 s gliding), bob, speed pulse.
    # Steering: slow wander, separation >= 28 px, cohesion, avoidance of A, B, threads and shrubs in screen space,
    # turn rate <= 12 deg/s. Shadows: a draped copy of the same pose, 17 px along the light direction, 25 %.
    gw = look.cel("gull", core.hexc("#f6f3ef"), shadow=(0.72, 0.68, 0.84, 1), paint=0.0, soft=0.2, hero=True)
    gt = look.cel("gull_tip", core.hexc("#55505e"), paint=0.0, hero=True)
    gshadow = look.emissive("gull_shadow", core.hexc("#6c5884"), 1.0, alpha=0.25)
    NB, BZ = 6, 2.2
    ppm_b = float(rig.ppm_at(BZ))
    ring = 16
    th_ = np.linspace(0, 2 * math.pi, ring, endpoint=False)
    body_xy = np.c_[0.022 * np.cos(th_), 0.05 * np.sin(th_)]
    body_xy[:, 1] *= np.where(body_xy[:, 1] > 0, 1.12, 1.0)
    tail_xy = np.array([(-0.007, -0.047), (0.007, -0.047), (0.015, -0.08), (-0.015, -0.08)])
    faces = [(0, 1 + i, 1 + (i + 1) % ring) for i in range(ring)] + [(20, 19, 18, 17)]
    for w0, flip in ((21, False), (28, True)):                   # all faces wound so the normals point up
        fw = [(w0, w0 + 1, w0 + 5, w0 + 4), (w0 + 1, w0 + 2, w0 + 6, w0 + 5), (w0 + 2, w0 + 3, w0 + 6)]
        faces += [tuple(reversed(q)) for q in fw] if flip else fw
    WL = (0.05, 0.045, 0.032)
    CH = (0.034, 0.03, 0.02)

    def bird_local(phi, g):
        """local vertices (35 x 3) for wing phase phi and glide blend g (0 flapping .. 1 gliding)"""
        th = np.array([0.75 * math.sin(phi), 0.45 * math.sin(phi - 0.7), 0.35 * math.sin(phi - 1.2)])
        sw = 0.35 * max(0.0, math.cos(phi)) * np.array([0.0, 0.6, 1.0])     # upstroke: outer wing swept back, folded
        th = th * (1 - g) + np.array([0.1, 0.04, -0.03]) * g
        sw = sw * (1 - g) + np.array([0.0, 0.03, 0.06]) * g
        V = np.zeros((35, 3))
        V[0] = (0, 0, 0.012)
        V[1:17, :2] = body_xy
        V[1:17, 2] = 0.01
        V[17:21, :2] = tail_xy
        V[17:21, 2] = 0.008
        for side, w0 in ((-1, 21), (1, 28)):
            J = np.array([side * 0.018, 0.012, 0.008])
            cum = 0.0
            pts = [J.copy()]
            for i in range(3):
                cum += th[i]
                d = np.array([side * math.cos(cum) * math.cos(sw[i]), -math.sin(sw[i]) * math.cos(cum), math.sin(cum)])
                J = J + d * WL[i]
                pts.append(J.copy())
            for i in range(4):
                V[w0 + i] = pts[i]
            for i in range(3):
                V[w0 + 4 + i] = pts[i] + np.array([0.0, -CH[i], 0.0])
        return V
    def poly_mesh(name, V, F, coll, mat):                  # mixed triangles and quads
        me = bpy.data.meshes.new(name)
        me.from_pydata(V.tolist(), [], [list(q) for q in F])
        me.update()
        ob_ = bpy.data.objects.new(name, me)
        me.materials.append(mat)
        coll.objects.link(ob_)
        return ob_
    birds = []
    for i in range(NB):
        ob = poly_mesh(f"bird{i}", bird_local(0.0, 0.0), faces, ink, gw)
        ob.data.materials.append(gt)
        mi = np.zeros(len(faces), np.int32)
        mi[[ring + 1 + 2, ring + 1 + 5]] = 1                               # the tip feathers are dark
        ob.data.polygons.foreach_set("material_index", mi)
        ob.visible_shadow = False
        sh = poly_mesh(f"bird{i}_shadow", bird_local(0.0, 0.0), faces, env, gshadow)
        sh.visible_shadow = False
        birds.append((ob, sh))
    # flight simulation (world metres at the bird height; screen px via the rig)
    brng = np.random.default_rng(1207)
    START_PX = [(185, 205), (295, 150), (255, 305), (385, 245), (150, 370), (335, 400)]
    v_px = brng.uniform(66, 78, NB)                        # mean ground speed px/s
    hd_off = np.radians(brng.uniform(-12, 12, NB))
    f_hz = 1.5 * brng.uniform(0.94, 1.06, NB)
    ph0 = brng.uniform(0, 2 * math.pi, NB)
    wander_ph = brng.uniform(0, 2 * math.pi, (NB, 2))
    BASE_HD = math.radians(15.0)                           # up the frame and a little left
    LIGHT = np.array([-0.552, 0.834])                      # screen direction of the shadows (down-left)
    sim_frames = list(range(start - 72, end + 2))
    # obstacles in screen space
    shrub_xyz = shrub_pos.copy()
    shrub_r_px = np.full(len(shrub_pos), 1.0 * PPM)

    def scr(f, p):
        return np.array(rig.world_to_screen(max(f, start), p))
    pos = np.array([rig.screen_to_world(start, x, y, BZ)[:2] for x, y in START_PX])
    hd = BASE_HD + hd_off
    vel_m = v_px / 24.0 / PPM
    pos = pos - 72 * np.c_[-np.sin(hd), np.cos(hd)] * vel_m[:, None]   # fly in from where they were 3 s earlier
    phi = ph0.copy()
    # flap-and-glide schedule per bird
    state = ["flap"] * NB
    beats_left = brng.integers(4, 7, NB).astype(float)
    glide_left = np.zeros(NB)
    gblend = np.zeros(NB)
    btrack = {}
    for f in sim_frames:
        P_scr = np.array([scr(f, np.array([pos[i][0], pos[i][1], BZ])) for i in range(NB)])
        obs = []
        if f >= start:
            obs.append((scr(f, np.array(list(pa_pos(f)) + [1.0])), 70.0))
            if f >= B_START:
                obs.append((scr(f, np.array(list(pb_pos(f)) + [1.0])), 70.0))
            for q, rr in zip(shrub_xyz, shrub_r_px):
                obs.append((scr(f, q + np.array([0, 0, 1.0])), rr + 30.0))
            for rope_ in (rope_a, rope_b):
                fk = f - (f - start) % 2
                if fk in rope_.sim:
                    for q in rope_.sim[fk][::8]:
                        obs.append((scr(f, q), 28.0))
        for i in range(NB):
            t = f / 24.0
            want = BASE_HD + hd_off[i] + math.radians(8.0) * (math.sin(2 * math.pi * t / 7.3 + wander_ph[i, 0]) +
                                                               0.5 * math.sin(2 * math.pi * t / 11.0 + wander_ph[i, 1]))
            steer = np.zeros(2)
            for j in range(NB):
                if j != i:
                    dv = P_scr[i] - P_scr[j]
                    dd = np.linalg.norm(dv) + 1e-6
                    if dd < 60:
                        steer += dv / dd * (60 - dd) / 60 * 2.0
            cen = P_scr.mean(0)
            dc = np.linalg.norm(P_scr[i] - cen)
            if dc > 140:
                steer += (cen - P_scr[i]) / dc * min((dc - 140) / 110, 1.0)
            for q, rr in obs:
                dv = P_scr[i] - q
                dd = np.linalg.norm(dv) + 1e-6
                if dd < rr + 40:
                    steer += dv / dd * (rr + 40 - dd) / 40 * 3.0
            if np.linalg.norm(steer) > 1e-6:
                # screen -> world direction (screen y is down), then fold into the wanted heading
                sw_ = np.array([steer[0], -steer[1]])
                cur = np.array([-math.sin(hd[i]), math.cos(hd[i])])
                side = cur[0] * sw_[1] - cur[1] * sw_[0]
                want += math.radians(25.0) * math.tanh(side)
            dh_ = (want - hd[i] + math.pi) % (2 * math.pi) - math.pi
            hd[i] += max(-math.radians(0.5), min(math.radians(0.5), dh_))       # <= 12 deg/s
            # flap-and-glide
            if state[i] == "flap":
                before = phi[i]
                phi[i] += 2 * math.pi * f_hz[i] / 24.0
                if math.floor(phi[i] / (2 * math.pi)) > math.floor(before / (2 * math.pi)):
                    beats_left[i] -= 1
                    if beats_left[i] <= 0:
                        state[i] = "glide"
                        glide_left[i] = brng.uniform(0.8, 1.4) * 24
                gblend[i] = max(0.0, gblend[i] - 1 / 4.0)
            else:
                glide_left[i] -= 1
                gblend[i] = min(1.0, gblend[i] + 1 / 4.0)
                if glide_left[i] <= 0:
                    state[i] = "flap"
                    beats_left[i] = brng.integers(4, 7)
            pulse = 1.0 + 0.08 * math.sin(phi[i] - math.pi) * (1 - gblend[i])
            pos[i] = pos[i] + np.array([-math.sin(hd[i]), math.cos(hd[i])]) * vel_m[i] * pulse
        btrack[f] = (pos.copy(), hd.copy(), phi.copy(), gblend.copy())
    bird_log = []

    def pose_birds(f):
        P, H, PH, G = btrack[f]
        rec = []
        for i, (ob, sh) in enumerate(birds):
            V = bird_local(PH[i], G[i])
            bobs = 1.0 + 0.03 * math.cos(PH[i] - 1.5 * math.pi - 0.3) * (1 - G[i])
            c, s_ = math.cos(H[i]), math.sin(H[i])
            R2 = np.array([[c, -s_], [s_, c]])
            W = np.zeros_like(V)
            W[:, :2] = (V[:, :2] * bobs) @ R2.T + P[i]
            W[:, 2] = BZ + V[:, 2] * bobs + 0.02 * (bobs - 1.0) / 0.03
            ob.data.vertices.foreach_set("co", W.astype(np.float32).ravel())
            ob.data.update()
            # shadow: the same pose, 17 px down-left along the light on screen, draped on the dune
            Sx = np.array([scr(f, w) for w in W])
            Sx = Sx + LIGHT * (17.0 + 1.5 * (bobs - 1.0) / 0.03)
            SW = np.array([rig.screen_to_world(f, x, y, 0.0)[:2] for x, y in Sx])
            Z = dh(SW[:, 0], SW[:, 1]) + 0.006
            sh.data.vertices.foreach_set("co", np.c_[SW, Z].astype(np.float32).ravel())
            sh.data.update()
            tips = Sx - LIGHT * (17.0 + 1.5 * (bobs - 1.0) / 0.03)
            span = float(np.linalg.norm(tips[24] - tips[31]))
            ctr = scr(f, np.array([P[i][0], P[i][1], BZ]))
            rec.append([round(float(ctr[0]), 2), round(float(ctr[1]), 2), round(math.degrees(H[i]), 3), round(span, 2), round(float(G[i]), 2)])
        bird_log.append(dict(f=int(f), birds=rec))

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.45, bloom_threshold=0.92, streak=0.08, streak_threshold=1.25,
                         lift=(0.99, 0.985, 1.03), gain=(1.03, 1.0, 0.975), vignette=0.22, ink=0.3,
                         ink_normal=(0.7, 1.6), ink_depth=(0.06, 0.3), saturation=1.1), res_scale=opt.scale)

    run_log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        for Hm, wk in ((A, wa), (B, wb)):
            Jw, hd, ph_ = wk.pose(d)
            Hm.set_world(Jw, hd)
            if wk is wa:
                sc_ = lambda q: np.array(rig.world_to_screen(d, q))
                fw_ = np.array([-math.sin(hd), -math.cos(hd)])
                c_ = sc_(Jw["pelvis"])
                fwd_w = np.array([-math.sin(hd), math.cos(hd)])       # lateral offsets measured on the ground (world, px)
                lat_ = lambda q: float((fwd_w[0] * (q[1] - Jw["pelvis"][1]) - fwd_w[1] * (q[0] - Jw["pelvis"][0])) * PPM)
                run_log.append(dict(f=int(d), pelvis=c_.round(2).tolist(), yaw=round(math.degrees(hd), 3), ph=round(ph_, 4),
                                    run=round(wa.run(d), 3), flight=round(wa.flight(d), 3),
                                    toe=[np.round(Jw["toe_l"], 4).tolist(), np.round(Jw["toe_r"], 4).tolist()],
                                    foot_lat=[round(lat_(Jw["toe_l"]), 2), round(lat_(Jw["toe_r"]), 2)],
                                    hand_lat=[round(lat_(Jw["hnd_l"]), 2), round(lat_(Jw["hnd_r"]), 2)],
                                    hand_fwd=[round(float(-(fw_ @ (sc_(Jw["hnd_l"]) - c_))), 2), round(float(-(fw_ @ (sc_(Jw["hnd_r"]) - c_))), 2)]))
        vis_b = d >= B_START
        for o in B.all_objects():
            o.hide_render = not vis_b
        # footprints that have landed by now (B's only once B is in)
        pos = np.tile(far, (nfp, 1))
        on = prints[:, 0] <= d
        pos[on] = prints[on, 1:4] + np.array([0, 0, 0.004])
        geo.update_points(fp_obj, pos)
        # A's prints: appear at the landing, 25 % opacity, fade out over 1 s after 6 s
        age = (d - a_prints[:, 0]) / 24.0
        on = age >= 0
        pa_ = np.tile(far, (nfa, 1))
        pa_[on] = a_prints[on, 1:4] + np.array([0, 0, 0.004])
        ta_ = np.where(on, 0.25 * np.clip(7.0 - age, 0.0, 1.0), 0.0)
        me_ = fpa_obj.data
        me_.vertices.foreach_set("co", pa_.astype(np.float32).ravel())
        me_.attributes["tint"].data.foreach_set("value", ta_.astype(np.float32))
        me_.update()
        # dust
        ag = np.repeat(age, ND)
        live = (ag >= 0) & (ag < 0.4)
        u_ = np.clip(ag / 0.4, 0, 1)
        r_px = (4.0 + 6.0 * u_) * d_rad
        P_ = np.tile(far, (nd, 1))
        base_ = np.repeat(a_prints[:, 1:4], ND, axis=0)
        P_[live] = base_[live] + np.c_[np.cos(d_ang[live]) * r_px[live] / PPM, np.sin(d_ang[live]) * r_px[live] / PPM,
                                       0.02 + 0.03 * u_[live]]
        T_ = np.where(live, 0.4 * (1 - u_), 0.0)
        me_ = dust_obj.data
        me_.vertices.foreach_set("co", P_.astype(np.float32).ravel())
        me_.attributes["tint"].data.foreach_set("value", T_.astype(np.float32))
        me_.update()
        pose_birds(d)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig

    def finish(out):
        rope_io.export(out, [rope_a, rope_b])
        json.dump(dict(log=run_log, plants=[[round(float(x), 4) for x in p_] for p_ in a_prints], ppm=PPM),
                  open(os.path.join(out, "runner_log.json"), "w"))
        json.dump(bird_log, open(os.path.join(out, "bird_log.json"), "w"))
    r.finish = finish
    return r
