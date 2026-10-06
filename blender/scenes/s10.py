"""Scene 10 (frames 2982-3315): late afternoon; a walker strolls up a dirt path between sunflower fields
and a harvested field with round bales and a lone tree. Low sun from the upper-right: every shadow is
long and falls lower-left. Sunflowers face the sun and sway; the red cord lies on the path behind."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, rope_io
from kit.look import _n, _l, _math, _mixrgb
from kit.paths import KeyPath

SCENE = 10
PPM = 120.0
SUN_DIR = (0.1, 0.95, 0.33)          # low sun from the top: long shadows fall down the frame, along the path
WALKER_SCREEN = (560, 1200)
PATH_X = 0.15                          # world x of the path centre
ROAD_K, ROAD_Y0 = 0.2125, 3.5          # diagonal road  y = ROAD_Y0 + ROAD_K * x  (world metres)
POST = dict(light_deg=80.0, flow_deg=90.0, stroke_px=11.0, boil_mean=2.1, thread_shadow_px=2.4, thread_shadow_per_m=6.0, repaint=0.5)
CANOPY = 1.05                          # flower-head height (the rope rides over it when the wind pushes it off the path)


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def road_d(x, y):
    return (y - (ROAD_Y0 + ROAD_K * x)) * 0.978


def region(x, y):
    """0 = sunflowers, 1 = stubble field (top-left), 2 = path/road verge"""
    px = np.abs(x - PATH_X - 0.06 * np.sin(y * 0.3))
    on_path = px < 0.48
    stubble = (x < PATH_X - 0.48) & (road_d(x, y) > 0.35) & (y < 15.5)
    return on_path, stubble


def ground_material():
    def base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1800, 300))
        attr = _n(nt, "ShaderNodeAttribute", (-1800, 0), attribute_type="GEOMETRY", attribute_name="zone")
        sep = _n(nt, "ShaderNodeSeparateColor", (-1600, 0))
        _l(nt, attr.outputs["Color"], sep.inputs[0])
        nz = _n(nt, "ShaderNodeTexNoise", (-1600, 300))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 0.6
        nz.inputs["Detail"].default_value = 4
        soil = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#4a3420"), core.hexc("#64482b"), (-1400, 400))
        soil = look.mul_color(nt, soil, look.tex_value_detail(nt, "forest_ground_04", size_m=1.5, amount=0.3, loc=(-1800, 700)), (-1300, 450))
        # stubble: golden, fine diagonal rows
        mp = _n(nt, "ShaderNodeMapping", (-1600, 150))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, 0.36)
        wv = _n(nt, "ShaderNodeTexWave", (-1400, 150), wave_type="BANDS", bands_direction="X")
        _l(nt, mp.outputs[0], wv.inputs["Vector"])
        wv.inputs["Scale"].default_value = 1.6
        wv.inputs["Distortion"].default_value = 2.0
        stub = _mixrgb(nt, "MIX", wv.outputs["Fac"], core.hexc("#c7a660"), core.hexc("#dcc07c"), (-1200, 200))
        stub = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.35, (-1200, 300)), stub, core.hexc("#a8874e"), (-1050, 200))
        dirt = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#c9b07a"), core.hexc("#d8c18c"), (-1200, -100))
        dirt = look.mul_color(nt, dirt, look.tex_value_detail(nt, "brown_mud_02", size_m=1.4, amount=0.25, loc=(-1800, -500)), (-1100, -150))
        road = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#8a6f53"), core.hexc("#a0846a"), (-1200, -250))
        c = _mixrgb(nt, "MIX", sep.outputs["Green"], soil, stub, (-900, 300))
        c = _mixrgb(nt, "MIX", sep.outputs["Red"], c, dirt, (-750, 200))
        c = _mixrgb(nt, "MIX", sep.outputs["Blue"], c, road, (-600, 100))
        return c
    return look.cel("ground", core.hexc("#c9a865"), shadow=(0.55, 0.45, 0.6, 1), high=(1.08, 1.05, 1.0, 1), t1=0.42, t2=0.97,
                    paint=0.06, paint_scale=2.2, base_node=base, rough=0.9, soft=0.16, ao=0.5, ao_dist=0.4)


def seedhead_image(name="seedhead", size=512, n=900):
    """phyllotaxis seed disc painted procedurally (Vogel spiral, golden angle): dark seeds, lighter florets at the rim"""
    img = bpy.data.images.get(name)
    if img:
        return img
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5
    rr = np.sqrt(xx * xx + yy * yy)
    base = np.zeros((size, size, 3), np.float32)
    base[:] = np.array([0.16, 0.09, 0.04])
    acc = np.zeros((size, size), np.float32)
    ga = math.pi * (3 - math.sqrt(5))
    for k in range(n):
        r = 0.47 * math.sqrt((k + 0.5) / n)
        a = k * ga
        cx, cy = 0.5 + r * math.cos(a), 0.5 + r * math.sin(a)
        rad = 0.0105 * (0.7 + 0.6 * r / 0.47)
        x0, x1 = int((cx - rad * 2) * size), int((cx + rad * 2) * size) + 1
        y0, y1 = int((cy - rad * 2) * size), int((cy + rad * 2) * size) + 1
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size), min(y1, size)
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32) / size
        d2 = (gx - cx) ** 2 + (gy - cy) ** 2
        acc[y0:y1, x0:x1] = np.maximum(acc[y0:y1, x0:x1], np.exp(-d2 / (2 * (rad * 0.55) ** 2)))
    seed = np.array([0.33, 0.2, 0.09])
    col = base * (1 - acc[..., None]) + seed * acc[..., None]
    # greenish centre, golden florets ring at the rim
    centre = np.exp(-(rr / 0.09) ** 2)[..., None]
    col = col * (1 - centre * 0.6) + np.array([0.32, 0.3, 0.1]) * centre * 0.6
    rim = np.clip((rr - 0.38) / 0.1, 0, 1)[..., None]
    col = col * (1 - rim * 0.55) + np.array([0.62, 0.42, 0.1]) * rim * 0.55
    rgba = np.concatenate([col, np.ones((size, size, 1), np.float32)], 2)
    img = bpy.data.images.new(name, size, size)
    img.colorspace_settings.name = "sRGB"
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.pack()
    return img


def disc_material(name):
    def base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-800, 0), attribute_type="GEOMETRY", attribute_name="uvd")
        tx = _n(nt, "ShaderNodeTexImage", (-550, 0))
        tx.image = seedhead_image()
        _l(nt, at.outputs["Vector"], tx.inputs["Vector"])
        return tx.outputs["Color"]
    return look.cel(name, core.hexc("#4c311b"), shadow=(0.62, 0.55, 0.62, 1), high=(1.1, 1.08, 1.0, 1), paint=0.0, base_node=base, soft=0.22,
                    ao=0.4, ao_dist=0.05)


def sunflower_proto(name, coll, mats, seed, tilt=0.55, n_petals=24):
    """one mesh: stem, 5-6 heart-shaped drooping leaves, green sepals, 21-28 cupped petals with value variation
    ('pv' attribute), and the seed disc ('uvd' attribute -> painted phyllotaxis texture). Head faces the sun."""
    rng = np.random.default_rng(seed)
    V, F, M, UV, PV = [], [], [], [], []

    def add(verts, faces, mat, uv=None, pv=0.5):
        i0 = len(V)
        V.extend(verts)
        for f in faces:
            F.append(tuple(i0 + k for k in f))
            M.append(mat)
        UV.extend(uv if uv is not None else [(0.5, 0.5)] * len(verts))
        PV.extend([pv] * len(verts))
    # stem
    sides = 6
    for k in range(2):
        z0, z1 = k * 0.75, (k + 1) * 0.75
        ring0 = [(0.022 * math.cos(2 * math.pi * i / sides), 0.022 * math.sin(2 * math.pi * i / sides), z0) for i in range(sides)]
        ring1 = [(0.017 * math.cos(2 * math.pi * i / sides), 0.017 * math.sin(2 * math.pi * i / sides), z1) for i in range(sides)]
        add(ring0 + ring1, [(i, (i + 1) % sides, sides + (i + 1) % sides, sides + i) for i in range(sides)], 0)
    # leaves: heart shape, midrib fold, drooping tip
    for i in range(int(rng.integers(5, 7))):
        a = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(0.3, 0.46)
        z = 0.45 + i * 0.16 + rng.uniform(-0.03, 0.03)
        pts = []
        prof = [(0.0, 0.0), (0.18, 0.2), (0.4, 0.3), (0.62, 0.27), (0.82, 0.16), (1.0, 0.0)]
        for u, w in prof:
            pts.append((u, w))
        for u, w in reversed(prof[1:-1]):
            pts.append((u, -w))
        ca, sa = math.cos(a), math.sin(a)
        verts = [(0.0, 0.0, z)]
        for u, w in pts:
            droop = -0.18 * u * u * L
            fold = 0.04 * L * (1 - abs(w) / 0.3)
            x, y = u * L, w * L
            verts.append((x * ca - y * sa, x * sa + y * ca, z + droop + fold))
        nring = len(pts)
        add(verts, [(0, 1 + k, 1 + (k + 1) % nring) for k in range(nring)], 1, pv=rng.uniform(0.2, 0.8))
    # head frame: centre at the stem top, face normal toward the sun
    hz = 1.52
    axis = np.array([-0.94, 0.35, 0.0])
    axis /= np.linalg.norm(axis)
    c, s_ = math.cos(tilt), math.sin(tilt)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + s_ * K + (1 - c) * K @ K
    H = lambda p: tuple(R @ np.asarray(p, float) + np.array([0, 0, hz]))
    # sepals: ring of pointed green bracts behind the petals
    for k in range(14):
        a = 2 * math.pi * k / 14 + rng.uniform(-0.1, 0.1)
        ca, sa = math.cos(a), math.sin(a)
        r0, L = 0.09, rng.uniform(0.06, 0.09)
        add([H((r0 * ca - 0.02 * sa, r0 * sa + 0.02 * ca, -0.02)), H(((r0 + L) * ca, (r0 + L) * sa, -0.035)),
             H((r0 * ca + 0.02 * sa, r0 * sa - 0.02 * ca, -0.02))], [(0, 1, 2)], 1, pv=0.3)
    # petals: two layers, cupped, value variation
    npet = int(n_petals)
    for layer in range(2):
        for k in range(npet):
            a = 2 * math.pi * (k + 0.5 * layer) / npet + rng.uniform(-0.04, 0.04)
            ca, sa = math.cos(a), math.sin(a)
            L = rng.uniform(0.09, 0.13) * (0.92 if layer else 1.0)
            r0 = 0.083
            w = 0.022
            lift = 0.012 + 0.012 * layer
            pts = [(r0 * ca - w * sa, r0 * sa + w * ca, 0.0), ((r0 + L * 0.6) * ca - w * 1.15 * sa, (r0 + L * 0.6) * sa + w * 1.15 * ca, lift),
                   ((r0 + L) * ca, (r0 + L) * sa, lift * 0.6), ((r0 + L * 0.6) * ca + w * 1.15 * sa, (r0 + L * 0.6) * sa - w * 1.15 * ca, lift),
                   (r0 * ca + w * sa, r0 * sa - w * ca, 0.0)]
            add([H(q) for q in pts], [(0, 1, 2, 3, 4)], 2, pv=rng.uniform(0, 1))
    # seed disc: fan with uv
    nseg = 28
    verts = [H((0, 0, 0.012))]
    uv = [(0.5, 0.5)]
    for k in range(nseg):
        a = 2 * math.pi * k / nseg
        verts.append(H((0.088 * math.cos(a), 0.088 * math.sin(a), 0.0)))
        uv.append((0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)))
    add(verts, [(0, 1 + k, 1 + (k + 1) % nseg) for k in range(nseg)], 3, uv=uv)
    ob = geo.mesh_from_faces(name, np.array(V), F, coll, smooth=True)
    me = ob.data
    for m in (mats["stem"], mats["leaf"], mats["petal"], mats["disc"]):
        me.materials.append(m)
    me.polygons.foreach_set("material_index", np.array(M, np.int32))
    a = me.attributes.new("uvd", "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", np.c_[np.array(UV, np.float32), np.zeros(len(UV), np.float32)].ravel())
    b = me.attributes.new("pv", "FLOAT", "POINT")
    b.data.foreach_set("value", np.array(PV, np.float32))
    me.update()
    return ob


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0, drift_x=lambda i: -0.06)
    core.world_ambient(core.hexc("#cdb994"), 0.34)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.86, SUN_DIR, 0.26), core.hexc("#ffe9c4"), angle_deg=2.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.3)
    nx, ny = int((x1 - x0) / 0.06), int((y1 - y0) / 0.06)
    ground = geo.grid("ground", x0, y0, x1, y1, nx, ny, lambda X, Y: 0.03 * geo.fbm2(X * 0.8, Y * 0.8, 3, 2), env, ground_material())
    # per-vertex zone colours: R = path dirt, G = stubble, B = road
    me = ground.data
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    on_path, stubble = region(co[:, 0], co[:, 1])
    rd = np.abs(road_d(co[:, 0], co[:, 1]))
    road = rd < 0.32
    verge = (np.abs(co[:, 0] - PATH_X - 0.06 * np.sin(co[:, 1] * 0.3)) < 0.75) & ~on_path
    col = np.zeros((len(co), 4), np.float32)
    col[:, 0] = np.maximum(on_path.astype(np.float32), (verge & ~stubble).astype(np.float32) * 0.6)
    col[:, 1] = np.maximum(stubble.astype(np.float32), verge.astype(np.float32) * 0.5)
    col[:, 2] = (road & ~on_path).astype(np.float32)
    col[:, 3] = 1
    ca = me.color_attributes.new("zone", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", col.ravel())

    # sunflowers in rows (right field, lower-left field), heads toward the sun, swaying
    protos = geo.proto_collection("SUNFLOWER_PROTOS")
    def pv_ramp(c0, c1):
        def build_(nt):
            at = _n(nt, "ShaderNodeAttribute", (-700, 100), attribute_type="GEOMETRY", attribute_name="pv")
            it = _n(nt, "ShaderNodeAttribute", (-700, -100), attribute_type="INSTANCER", attribute_name="tint")
            v = _math(nt, "ADD", _math(nt, "MULTIPLY", at.outputs["Fac"], 0.7, (-550, 100)), _math(nt, "MULTIPLY", it.outputs["Fac"], 0.3, (-550, -100)), (-450, 0))
            return _mixrgb(nt, "MIX", v, core.hexc(c0), core.hexc(c1), (-300, 0))
        return build_
    mats = dict(stem=look.cel("sf_stem", core.hexc("#6b6c3c"), paint=0.0, soft=0.2),
                leaf=look.cel("sf_leaf", core.hexc("#6f6d3e"), shadow=(0.55, 0.55, 0.6, 1), high=(1.15, 1.12, 1.02, 1), paint=0.04, backface=True,
                              base_node=pv_ramp("#575a30", "#8a8550"), soft=0.2, ao=0.55, ao_dist=0.3),
                disc=disc_material("sf_disc"),
                petal=look.cel("sf_petal", core.hexc("#e7b52f"), shadow=(0.75, 0.6, 0.55, 1), high=(1.1, 1.07, 0.97, 1), paint=0.03, backface=True,
                               base_node=pv_ramp("#d99a22", "#f4cc48"), soft=0.22, ao=0.35, ao_dist=0.05))
    for i in range(5):
        sunflower_proto(f"sf_{i}", protos, mats, seed=100 + i, tilt=0.42 + 0.07 * i, n_petals=21 + i * 2)
    rng = np.random.default_rng(1010)
    pts = []
    for xr in np.arange(x0, x1, 0.55):
        for yr in np.arange(y0, y1, 0.42):
            x = xr + rng.normal(0, 0.07)
            y = yr + rng.normal(0, 0.08) + (0.21 if int((xr - x0) / 0.55) % 2 else 0)
            op, stb = region(np.array([x]), np.array([y]))
            if op[0] or stb[0] or abs(road_d(x, y)) < 0.55 or abs(x - PATH_X) < 0.75:
                continue
            if rng.random() < 0.04:
                continue
            pts.append((x, y))
    pts = np.array(pts)
    n = len(pts)
    sf_scale = rng.uniform(0.85, 1.12, n)
    sf_rot0 = rng.uniform(-0.25, 0.25, n)
    sf = geo.instances("sunflowers", protos, np.c_[pts, np.zeros(n)], rot=np.c_[np.zeros(n), np.zeros(n), sf_rot0],
                       scl=np.c_[sf_scale, sf_scale, sf_scale], variant=rng.integers(0, 5, n), tint=rng.random(n), coll=env)
    sway_ph = rng.uniform(0, 6.28, n)

    # hay bales standing on end (spiral tops) in a diagonal row, a lone tree
    def spiral_base(nt):
        tc = _n(nt, "ShaderNodeTexCoord", (-900, 0))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-750, 0))
        _l(nt, tc.outputs["Object"], sx.inputs[0])
        r = _math(nt, "SQRT", _math(nt, "ADD", _math(nt, "MULTIPLY", sx.outputs[0], sx.outputs[0], (-600, 50)),
                                    _math(nt, "MULTIPLY", sx.outputs[1], sx.outputs[1], (-600, -50)), (-480, 0)), None, (-380, 0))
        a = _math(nt, "ARCTAN2", sx.outputs[1], sx.outputs[0], (-600, -150))
        sp = _math(nt, "FRACT", _math(nt, "SUBTRACT", _math(nt, "MULTIPLY", r, 7.0, (-280, 0)), _math(nt, "DIVIDE", a, 6.2832, (-380, -150)), (-180, -50)), None, (-80, -50))
        line = _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", sp, 0.5, (20, -50)), None, (120, -50)), 0.16, (220, -50))
        top = _math(nt, "GREATER_THAN", sx.outputs[2], 0.49, (220, -200))
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", line, top, (330, -100)), core.hexc("#e7cc80"), core.hexc("#a8894c"), (450, 0))
    bale_mat = look.cel("bale", core.hexc("#e2c47a"), shadow=(0.6, 0.5, 0.55, 1), paint=0.08, paint_scale=12.0, base_node=spiral_base)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=1.0, radius2=1.0, depth=1.0)
    bale = geo.bm_to_object(bm, "bale_proto", bale_mat, env)
    bale.hide_render = True
    bales = []
    for i, (bx, by) in enumerate(((-0.95, 7.05), (-1.4, 6.2), (-1.95, 5.35), (-2.6, 4.6), (-3.35, 3.95))):
        o = bale.copy()
        o.data = bale.data
        env.objects.link(o)
        o.hide_render = False
        o.location = (bx, by, 0.6)
        o.scale = (0.42, 0.42, 1.2)
        bales.append(o)
    def tree_base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-700, 200), attribute_type="GEOMETRY", attribute_name="lv")
        return _mixrgb(nt, "MIX", at.outputs["Fac"], core.hexc("#2f4a22"), core.hexc("#a9bb5c"), (-400, 100))
    tree_mat = look.cel("tree", core.hexc("#7f9748"), shadow=(0.55, 0.6, 0.55, 1), high=(1.15, 1.15, 1.02, 1), paint=0.03, base_node=tree_base,
                        soft=0.2, ao=0.6, ao_dist=0.6)
    trunk_mat = look.cel("trunk", core.hexc("#4a3524"), paint=0.0)
    tproto = geo.proto_collection("TREE_PROTOS")
    from kit import plants
    tx, ty = -2.4, 12.3
    crown_ob = plants.crown("tree_crown", tree_mat, env, seed=200, radius=1.6, height=2.0, n_clumps=60, leaves=120, leaf=0.09, core=True)
    crown_ob.location = (tx, ty, 1.7)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.16, radius2=0.1, depth=3.0)
    bmesh.ops.translate(bm, vec=(tx, ty, 1.5), verts=bm.verts)
    geo.bm_to_object(bm, "trunk", trunk_mat, env)
    # pale stones by the road
    stone_mat = look.cel("stone", core.hexc("#cdc8c0"), paint=0.05)
    sproto = geo.proto_collection("STONE_PROTOS")
    geo.knobbly("stone", stone_mat, sproto, seed=9, subdiv=2, knob=0.3, flat=0.6, lumps=3)
    sp = []
    for _ in range(60):
        x = rng.uniform(x0, x1)
        y = ROAD_Y0 + ROAD_K * x + rng.choice([-0.38, 0.38]) + rng.normal(0, 0.06)
        if x > PATH_X + 0.6:
            sp.append((x, y, 0.02))
    sp = np.array(sp)
    m = len(sp)
    ss = rng.uniform(0.05, 0.11, m)
    geo.instances("stones", sproto, sp, scl=np.c_[ss, ss, ss], rot=np.c_[np.zeros(m), np.zeros(m), rng.uniform(0, 6.28, m)], coll=env)

    # walker (white shirt, dark hair), planted feet
    hm = dict(top=look.cel("w_top", core.hexc("#eeece7"), shadow=(0.62, 0.58, 0.7, 1), paint=0.03),
              legs=look.cel("w_legs", core.hexc("#3d3a45"), paint=0.0), shoes=look.cel("w_shoes", core.hexc("#2a2628"), paint=0.0),
              hands=look.cel("w_hands", core.hexc("#d6a98f"), paint=0.0), skin=look.cel("w_skin", core.hexc("#d6a98f"), paint=0.0),
              hair=look.cel("w_hair", core.hexc("#2a1e1a"), paint=0.03))
    for m_ in hm.values():
        g_ = [x for x in m_.node_tree.nodes if x.type == "GROUP"][0]
        g_.inputs["Hero"].default_value = 1.0
        g_.inputs["Soft"].default_value = 0.22
    walker = human.Human("walker", hm, hair="long", height=1.8, coll=ink, bulk={"top": 1.2, "shoes": 0.8})
    hat_m = look.cel("w_hat", core.hexc("#e6cf93"), shadow=(0.62, 0.55, 0.6, 1), high=(1.1, 1.08, 1.0, 1), paint=0.06, paint_scale=60, soft=0.2,
                     rim=0.3, hero=True)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.23, radius2=0.2, depth=0.02)
    hat_brim = geo.bm_to_object(bm, "w_hat_brim", hat_m, ink)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=8, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.11, 0.12, 0.08), verts=bm.verts)
    hat_crown = geo.bm_to_object(bm, "w_hat_crown", hat_m, ink)
    keys = [(f, *rig.screen_to_world(f, *WALKER_SCREEN, 0.0)[:2]) for f in range(start, end + 1, 8)]
    path = KeyPath(keys, start - 140, end + 30, sigma=2.0)
    gfun = lambda x, y: 0.0
    mot = rope_io.C.owner_motion(SCENE)
    # v5: a straight walk with one slow bow (no side-to-side sway), short steps along the path (0.29 m = 35 px at
    # 2.1 steps/s, matching the ground speed so stance feet stay planted), feet 10 px off the centre line, small
    # shoes, arms hanging close and swinging along the path only, shoulders counter-rotating 3 degrees
    bow = lambda t: 0.05 * math.sin(math.pi * min(max((t - start) / (end - start), 0.0), 1.0))
    wk = human.Walker(lambda t: (path.pos(t)[0] + mot(t)[0] + bow(t), path.pos(t)[1]), path.heading, start - 120, end + 20, height=1.8,
                      ground=gfun, arm_swing=0.14, step_len=0.29, foot_lat=0.081, toe_len=0.045, arm_in=0.13,
                      shoulder_yaw=math.radians(3.0), swing_pitch=0.6, arm_bend=0.12)

    # rope: lies on the path; where the wind pushes it over the field it rides on the flower heads
    def canopy(x, y):
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        on_path = np.abs(x - PATH_X - 0.06 * np.sin(y * 0.3)) < 0.62
        field = (~on_path) & ~((x < PATH_X - 0.48) & ((y - (ROAD_Y0 + ROAD_K * x)) * 0.978 > 0.35) & (y < 15.5))
        return np.where(field, CANOPY, 0.01)
    def calm_near_owner(wind):
        # v5: halve the sideways wind on the first ~40 px of thread so no body sway comes back through the cord
        def w(P, t):
            out = wind(P, t)
            out[:2, 0] *= 0.5
            out[2, 0] *= 0.75
            return out
        return w
    rope = rope_io.Owner("A", SCENE, rig, wk.attach, list(range(start, end, 2)), trail=(0.0, -1.0),
                         ground_fn=lambda x, y: np.full_like(np.asarray(x, float), 0.01), warm=150, cfg_motion=False,
                         wind_wrap=calm_near_owner)

    st = look.freestyle(ink, thickness=1.7, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.4, bloom_threshold=0.92, streak=0.08, lift=(1.0, 0.99, 1.0), gain=(1.05, 1.01, 0.93),
                         vignette=0.3, ink=0.35, ink_normal=(0.5, 1.4), saturation=0.95), res_scale=opt.scale)
    log = []
    walk_log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        Jw, hd, ph = wk.pose(d)
        walker.set_world(Jw, hd)
        hp = Jw["head"] + np.array([0, 0, 0.1])
        hat_brim.location = Vector(hp.tolist())
        hat_crown.location = Vector((hp + np.array([0, 0, 0.04])).tolist())
        hs = 1.0 + 0.015 * math.cos(4 * math.pi * ph)          # hat bob: a scale change at the step rate, no x motion
        hat_brim.scale = hat_crown.scale = (hs, hs, hs)
        scr = lambda p: np.array(rig.world_to_screen(d, p))
        fwd = np.array([-math.sin(hd), -math.cos(hd)])            # screen-space forward (y down)
        c = scr(Jw["pelvis"])
        lat = lambda p: float(abs(fwd[0] * (scr(p) - c)[1] - fwd[1] * (scr(p) - c)[0]))
        walk_log.append(dict(f=int(d), hat=scr(hp).round(2).tolist(), yaw=round(math.degrees(hd), 3), ph=round(ph, 4),
                             foot=[round(lat(Jw["toe_l"]), 2), round(lat(Jw["toe_r"]), 2), round(lat(Jw["ank_l"]), 2), round(lat(Jw["ank_r"]), 2)],
                             hand=[round(lat(Jw["hnd_l"]), 2), round(lat(Jw["hnd_r"]), 2)],
                             toe=[scr(Jw["toe_l"]).round(2).tolist(), scr(Jw["toe_r"]).round(2).tolist()],
                             toe_z=[round(float(Jw["toe_l"][2]), 3), round(float(Jw["toe_r"][2]), 3)]))
        t = d - start
        # wind sway: gust waves travelling across the field; plants near the walker part and sway more
        sw = 0.07 * np.sin(pts[:, 0] * 0.7 + pts[:, 1] * 0.4 - t * 0.06 + sway_ph * 0.3) + 0.025 * np.sin(pts[:, 0] * 2.1 - t * 0.17 + sway_ph)
        bx, by = Jw["pelvis"][0], Jw["pelvis"][1]
        dxw, dyw = pts[:, 0] - bx, pts[:, 1] - by
        near = np.exp(-(dxw * dxw + dyw * dyw) / 0.5)
        part_x = -np.sign(dxw) * 0.25 * near
        geo.update_points(sf, np.c_[pts, np.zeros(n)], rot=np.c_[sw + 0.08 * near * np.sin(t * 0.5 + sway_ph), sw * 0.6 + part_x, sf_rot0])
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    def finish(out):
        rope_io.export(out, [rope])
        json.dump(walk_log, open(os.path.join(out, "walk_log.json"), "w"))
    r.finish = finish
    return r
