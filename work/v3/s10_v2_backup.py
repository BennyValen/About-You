"""Scene 10 (frames 2982-3315): late afternoon; a walker strolls up a dirt path between sunflower fields
and a harvested field with round bales and a lone tree. Low sun from the upper-right: every shadow is
long and falls lower-left. Sunflowers face the sun and sway; the red cord lies on the path behind."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, thread
from kit.look import _n, _l, _math, _mixrgb
from kit.paths import KeyPath

SCENE = 10
PPM = 120.0
SUN_DIR = (0.35, 0.94, 0.24)          # low sun: shadows ~4x body length
WALKER_SCREEN = (560, 1200)
PATH_X = 0.15                          # world x of the path centre
ROAD_K, ROAD_Y0 = 0.2125, 3.5          # diagonal road  y = ROAD_Y0 + ROAD_K * x  (world metres)
PAINT_BOIL = 0.45


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
        road = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#8a6f53"), core.hexc("#a0846a"), (-1200, -250))
        c = _mixrgb(nt, "MIX", sep.outputs["Green"], soil, stub, (-900, 300))
        c = _mixrgb(nt, "MIX", sep.outputs["Red"], c, dirt, (-750, 200))
        c = _mixrgb(nt, "MIX", sep.outputs["Blue"], c, road, (-600, 100))
        return c
    return look.cel("ground", core.hexc("#c9a865"), shadow=(0.55, 0.45, 0.6, 1), high=(1.08, 1.05, 1.0, 1), t1=0.42, t2=0.97,
                    paint=0.18, paint_scale=2.2, base_node=base, rough=0.9)


def sunflower_proto(name, coll, mats, seed, tilt=0.55):
    """stem, leaves, a seeded disc and a ring of cupped petals; head turned toward +X+Y (the sun)"""
    rng = np.random.default_rng(seed)
    parts = []
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.022, radius2=0.016, depth=1.5)
    bmesh.ops.translate(bm, vec=(0, 0, 0.75), verts=bm.verts)
    parts.append(geo.bm_to_object(bm, name + "_stem", mats["stem"], coll))
    for i in range(4):
        bm = bmesh.new()
        a = rng.uniform(0, 6.28)
        L = rng.uniform(0.28, 0.42)
        pts = [(0, 0, 0), (0.35 * L, 0.38 * L, 0.03), (0.9 * L, 0.32 * L, 0.0), (1.2 * L, 0, -0.03), (0.9 * L, -0.32 * L, 0.0), (0.35 * L, -0.38 * L, 0.03)]
        vs = [bm.verts.new(p) for p in pts]
        bm.faces.new(vs)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(a, 3, "Z"))
        bmesh.ops.translate(bm, vec=(0, 0, 0.6 + i * 0.2), verts=bm.verts)
        parts.append(geo.bm_to_object(bm, f"{name}_leaf{i}", mats["leaf"], coll, smooth=False))
    head = Matrix.Translation((0, 0, 1.52)) @ Matrix.Rotation(-tilt, 4, Vector((-0.94, 0.35, 0))).normalized() if False else None
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=0.1, radius2=0.085, depth=0.05)
    disc = geo.bm_to_object(bm, name + "_disc", mats["disc"], coll)
    bm = bmesh.new()
    for k in range(22):
        a = 2 * math.pi * k / 22 + rng.uniform(-0.05, 0.05)
        L = rng.uniform(0.09, 0.12)
        c, s = math.cos(a), math.sin(a)
        r0 = 0.085
        pts = [(r0 * c - 0.02 * s, r0 * s + 0.02 * c, 0.0), ((r0 + L) * c - 0.022 * s, (r0 + L) * s + 0.022 * c, 0.02),
               ((r0 + L * 1.12) * c, (r0 + L * 1.12) * s, 0.03), ((r0 + L) * c + 0.022 * s, (r0 + L) * s - 0.022 * c, 0.02),
               (r0 * c + 0.02 * s, r0 * s - 0.02 * c, 0.0)]
        vs = [bm.verts.new(p) for p in pts]
        bm.faces.new(vs)
    petals = geo.bm_to_object(bm, name + "_petals", mats["petal"], coll, smooth=False)
    hroot = bpy.data.objects.new(name + "_head", None)
    coll.objects.link(hroot)
    hroot.location = (0, 0, 1.52)
    axis = Vector((-0.94, 0.35, 0)).normalized()          # tilt the face toward the sun (+X, +Y)
    hroot.rotation_euler = Matrix.Rotation(tilt, 3, axis).to_euler()
    disc.parent = hroot
    petals.parent = hroot
    # merge everything into one prototype mesh for instancing
    Mh = Matrix.Translation(hroot.location) @ hroot.rotation_euler.to_matrix().to_4x4()
    for o in (disc, petals):
        o.parent = None
        o.matrix_world = Mh @ o.matrix_basis
    objs = parts + [disc, petals]
    ob = geo.merge_objects(objs, name, coll)
    bpy.data.objects.remove(hroot)
    return ob


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
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
    mats = dict(stem=look.cel("sf_stem", core.hexc("#6b7440"), paint=0.0),
                leaf=look.cel("sf_leaf", core.hexc("#7e7d4f"), shadow=(0.6, 0.6, 0.62, 1), high=(1.15, 1.13, 1.05, 1), paint=0.08, backface=True),
                disc=look.cel("sf_disc", core.hexc("#4c311b"), paint=0.15, paint_scale=30.0),
                petal=look.cel("sf_petal", core.hexc("#e7b52f"), shadow=(0.75, 0.62, 0.55, 1), high=(1.1, 1.08, 0.98, 1), paint=0.05, backface=True))
    for i in range(4):
        sunflower_proto(f"sf_{i}", protos, mats, seed=100 + i, tilt=0.45 + 0.08 * i)
    rng = np.random.default_rng(1010)
    pts = []
    for xr in np.arange(x0, x1, 0.62):
        for yr in np.arange(y0, y1, 0.46):
            x = xr + rng.normal(0, 0.05)
            y = yr + rng.normal(0, 0.05) + (0.23 if int((xr - x0) / 0.62) % 2 else 0)
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
                       scl=np.c_[sf_scale, sf_scale, sf_scale], variant=rng.integers(0, 4, n), coll=env)
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
    tree_mat = look.cel("tree", core.hexc("#7f9748"), shadow=(0.55, 0.6, 0.55, 1), high=(1.15, 1.15, 1.02, 1), paint=0.12, paint_scale=6)
    trunk_mat = look.cel("trunk", core.hexc("#4a3524"), paint=0.0)
    tproto = geo.proto_collection("TREE_PROTOS")
    for i in range(3):
        geo.knobbly(f"tree_clump_{i}", tree_mat, tproto, seed=200 + i, subdiv=3, knob=0.6, flat=0.85, lumps=8)
    tx, ty = -2.4, 12.3
    cl = []
    for i in range(10):
        a = rng.uniform(0, 6.28)
        r = 0 if i == 0 else rng.uniform(0.3, 1.0)
        s = rng.uniform(0.6, 0.85)
        cl.append((tx + r * math.cos(a), ty + r * math.sin(a), 3.0 + rng.uniform(-0.3, 0.4), s))
    cl = np.array(cl)
    geo.instances("tree", tproto, cl[:, :3], rot=np.c_[np.zeros(10), np.zeros(10), rng.uniform(0, 6.28, 10)],
                  scl=np.c_[cl[:, 3], cl[:, 3], cl[:, 3]], variant=rng.integers(0, 3, 10), coll=env)
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
    walker = human.Human("walker", hm, hair="long", coll=ink)
    keys = [(f, *rig.screen_to_world(f, *WALKER_SCREEN, 0.0)[:2]) for f in range(start, end + 1, 8)]
    path = KeyPath(keys, start - 140, end + 30, sigma=2.0)
    gfun = lambda x, y: 0.0
    wk = human.Walker(path.pos, path.heading, start - 120, end + 20, height=1.72, ground=gfun, arm_swing=0.38)

    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    def attach(t):
        Jw, hd, _ = wk.pose(t)
        return wk.waist_back(Jw, hd)
    def breeze(x, y, t):
        return 0.9 * np.sin(y * 1.3 + t * 0.02) + 0.5 * np.sin(y * 3.1 - t * 0.035), np.zeros_like(y)
    cord = thread.Cord(n_seg=200, length=12.0, mode="ground", ground=lambda x, y: np.zeros_like(x) + 0.01, friction=0.55,
                       substeps=6, iters=22, push=breeze, bend=0.1)
    sim = cord.run(list(range(start, end)), attach, (0.0, -1.0), warm=110)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.6)

    st = look.freestyle(ink, thickness=1.7, res_scale=opt.scale)
    look.compositor(dict(kuwahara=10, bloom=0.45, bloom_threshold=0.92, streak=0.12, lift=(0.99, 0.99, 1.02), gain=(1.05, 1.01, 0.94),
                         vignette=0.3, grain=0.03, ink=0.5, ink_normal=(0.5, 1.4), saturation=1.05), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        Jw, hd, _ = wk.pose(d)
        walker.set_world(Jw, hd)
        t = d - start
        # wind sway: a gust field travelling across the field
        sw = 0.06 * np.sin(pts[:, 0] * 0.7 + pts[:, 1] * 0.4 - t * 0.06 + sway_ph * 0.3)
        geo.update_points(sf, np.c_[pts, np.zeros(n)], rot=np.c_[sw, sw * 0.6, sf_rot0])
        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})
        look.boil(st, d // 2)
        look.grain_seed(d // 2)
        look.set_drawing(d // 2, PAINT_BOIL)

    class Run:
        pass
    r = Run()
    r.update = update
    r.finish = lambda out: json.dump(log, open(os.path.join(out, "thread_log.json"), "w"))
    return r
