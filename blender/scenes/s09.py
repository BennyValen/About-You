"""Scene 9 (frames 2646-2981): a cyclist rides up a beige path beside a dark lake under big fluffy trees.
Wheels spin from the ground speed (omega = v / R), cranks geared to the wheels, feet on the pedals.
Sun from the upper-right: long dappled tree shadows fall lower-left across path and lawn."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, vehicles, plants, rope_io
from kit.look import _n, _l, _math, _mixrgb

SCENE = 9
PPM = 75.0
SUN_DIR = (0.62, 0.62, 0.48)
BIKE_SCREEN = (540, 1180)
PATH_X = 0.0
POST = dict(light_deg=45.0, flow_deg=90.0, stroke_px=12.0, boil_mean=2.0, thread_shadow_px=2.0, repaint=0.55)


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def shore_x(y):
    return -1.4 + 0.12 * np.sin(y * 0.35) + 0.08 * np.sin(y * 0.9 + 1)


def ground_h(X, Y):
    lake = X < shore_x(Y)
    h = 0.04 * geo.fbm2(X * 0.5, Y * 0.5, 3, 3)
    return np.where(lake, -0.25, h + 0.12 * np.clip((X - shore_x(Y)) / 0.4, 0, 1))


def ground_material():
    def base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1800, 300))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-1600, 300))
        _l(nt, geo_n.outputs["Position"], sx.inputs[0])
        # lawn: streaky grass strokes
        mp = _n(nt, "ShaderNodeMapping", (-1600, 100))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, 1.05)
        mp.inputs["Scale"].default_value = (0.25, 6.0, 1)
        gn = _n(nt, "ShaderNodeTexNoise", (-1400, 100))
        _l(nt, mp.outputs[0], gn.inputs["Vector"])
        gn.inputs["Scale"].default_value = 2.5
        gn.inputs["Detail"].default_value = 6
        g = _n(nt, "ShaderNodeValToRGB", (-1200, 100))
        g.color_ramp.elements[0].color = core.hexc("#2c6a30")
        g.color_ramp.elements[1].color = core.hexc("#5ea646")
        e = g.color_ramp.elements.new(0.5)
        e.color = core.hexc("#3f8a3a")
        _l(nt, gn.outputs["Fac"], g.inputs[0])
        # mowing stripes along the path (alternating light/dark bands ~1.1 m wide), softened by noise
        stw = _math(nt, "SINE", _math(nt, "MULTIPLY", sx.outputs[0], math.pi / 1.1, (-1500, 450)), None, (-1400, 450))
        stv = _n(nt, "ShaderNodeMapRange", (-1300, 450), clamp=True)
        _l(nt, stw, stv.inputs["Value"])
        stv.inputs["From Min"].default_value, stv.inputs["From Max"].default_value = -0.3, 0.3
        stv.inputs["To Min"].default_value, stv.inputs["To Max"].default_value = 0.86, 1.12
        gcol = look.mul_color(nt, g.outputs[0], stv.outputs["Result"], (-1100, 300))
        gcol = look.mul_color(nt, gcol, look.tex_value_detail(nt, "aerial_grass_rock", size_m=2.5, amount=0.25, loc=(-1500, 700)), (-1000, 300))
        # path
        px = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", sx.outputs[0], PATH_X, (-1400, -100)), None, (-1250, -100))
        pm = _n(nt, "ShaderNodeMapRange", (-1100, -100), clamp=True)
        _l(nt, px, pm.inputs["Value"])
        pm.inputs["From Min"].default_value, pm.inputs["From Max"].default_value = 0.8, 0.76
        pn = _n(nt, "ShaderNodeTexNoise", (-1250, -250))
        _l(nt, geo_n.outputs["Position"], pn.inputs["Vector"])
        pn.inputs["Scale"].default_value = 3.0
        path = _mixrgb(nt, "MIX", pn.outputs["Fac"], core.hexc("#d4c296"), core.hexc("#e6d8b0"), (-950, -250))
        path = look.mul_color(nt, path, look.tex_value_detail(nt, "gravel_road", size_m=1.2, amount=0.28, loc=(-1500, -600)), (-900, -350))
        # wheel marks: two darker stripes along the path
        for wx_ in (-0.28, 0.24):
            wm = _n(nt, "ShaderNodeMapRange", (-1100, -650), clamp=True, interpolation_type="SMOOTHSTEP")
            _l(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", sx.outputs[0], PATH_X + wx_, (-1300, -650)), None, (-1200, -650)), wm.inputs["Value"])
            wm.inputs["From Min"].default_value, wm.inputs["From Max"].default_value = 0.07, 0.02
            path = _mixrgb(nt, "MULTIPLY", _math(nt, "MULTIPLY", wm.outputs["Result"], 0.22, (-1000, -650)), path, core.hexc("#a8946c"), (-850, -500))
        c = _mixrgb(nt, "MIX", pm.outputs["Result"], gcol, path, (-800, 0))
        edge = _n(nt, "ShaderNodeMapRange", (-1100, -400), clamp=True)
        _l(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", px, 0.8, (-1250, -400)), None, (-1180, -400)), edge.inputs["Value"])
        edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 0.03, 0.0
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", edge.outputs["Result"], 0.6, (-950, -400)), c, core.hexc("#6d6248"), (-650, 0))
        # lake bed (seen as dark water) for x below the shore
        dep = _n(nt, "ShaderNodeMapRange", (-1100, 450), clamp=True)
        _l(nt, sx.outputs[2], dep.inputs["Value"])
        dep.inputs["From Min"].default_value, dep.inputs["From Max"].default_value = -0.05, -0.15
        c = _mixrgb(nt, "MIX", dep.outputs["Result"], c, core.hexc("#152a24"), (-500, 100))
        return c
    return look.cel("ground", core.hexc("#4a8a3c"), shadow=(0.42, 0.52, 0.5, 1), high=(1.1, 1.1, 1.02, 1), t1=0.42, t2=0.97,
                    paint=0.06, paint_scale=2.0, base_node=base, rough=0.9, soft=0.16, ao=0.5, ao_dist=0.5)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#a9c4a4"), 0.25)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.88, SUN_DIR, 0.26), core.hexc("#fff3d8"), angle_deg=2.5)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.3)
    nx, ny = int((x1 - x0) / 0.08), int((y1 - y0) / 0.08)
    geo.grid("ground", x0, y0, x1, y1, nx, ny, ground_h, env, ground_material())
    # lake surface: dark, reflection streaks, glints
    def lake_base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1000, 0))
        mp = _n(nt, "ShaderNodeMapping", (-800, 0))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Scale"].default_value = (0.1, 3.5, 1)
        nz = _n(nt, "ShaderNodeTexNoise", (-600, 0))
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 1.2
        nz.inputs["Detail"].default_value = 6
        mr = _n(nt, "ShaderNodeMapRange", (-400, 0), clamp=True)
        _l(nt, nz.outputs["Fac"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.52, 0.72
        c = _mixrgb(nt, "MIX", mr.outputs["Result"], core.hexc("#10221f"), core.hexc("#3f5545"), (-200, 0))
        sk = _n(nt, "ShaderNodeTexNoise", (-600, 200))
        _l(nt, geo_n.outputs["Position"], sk.inputs["Vector"])
        sk.inputs["Scale"].default_value = 0.1
        skm = _n(nt, "ShaderNodeMapRange", (-400, 200), clamp=True)
        _l(nt, sk.outputs["Fac"], skm.inputs["Value"])
        skm.inputs["From Min"].default_value, skm.inputs["From Max"].default_value = 0.5, 0.78
        return _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", skm.outputs["Result"], 0.14, (-250, 200)), c, core.hexc("#9db8b4"), (-100, 50))
    def lake_h(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1000, -300))
        wn = _n(nt, "ShaderNodeTexNoise", (-800, -300), noise_dimensions="4D")
        _l(nt, geo_n.outputs["Position"], wn.inputs["Vector"])
        wn.inputs["Scale"].default_value = 3.0
        d = wn.inputs["W"].driver_add("default_value").driver
        d.type = "SCRIPTED"
        d.expression = "floor(frame / 2) / 10.0"
        return wn.outputs["Fac"]
    lake = geo.grid("lake", x0, y0, -1.2, y1, 4, 4, None, env,
                    look.cel("lake", core.hexc("#14282a"), shadow=(0.6, 0.7, 0.75, 1), t1=0.3, t2=0.99, paint=0.15, paint_scale=1.5,
                             base_node=lake_base, height_node=lake_h, bump=0.15, rough=0.1))
    lake.location.z = -0.03
    rng = np.random.default_rng(909)
    # lily pads near the shore, reeds on the bank
    pproto = geo.proto_collection("PAD_PROTOS")
    padm = look.cel("pad", core.hexc("#5aa04a"), shadow=(0.55, 0.65, 0.6, 1), high=(1.15, 1.15, 1.02, 1), paint=0.05)
    bm = bmesh.new()
    c = bm.verts.new((0, 0, 0))
    ring = [bm.verts.new((math.cos(a), math.sin(a), 0.0)) for a in np.linspace(0.3, 2 * math.pi, 28)]
    for i in range(len(ring) - 1):
        bm.faces.new((c, ring[i], ring[i + 1]))
    geo.bm_to_object(bm, "lp", padm, pproto)
    lp = []
    for cx, cy in geo.poisson(rng, 40, x0, y0, -1.6, y1, 1.6):
        for _ in range(rng.integers(3, 8)):
            lp.append((cx + rng.normal(0, 0.35), cy + rng.normal(0, 0.35), -0.02))
    lp = np.array([p for p in lp if p[0] < shore_x(p[1]) - 0.1])
    m = len(lp)
    ls = rng.uniform(0.1, 0.22, m)
    geo.instances("lilypads", pproto, lp, rot=np.c_[np.zeros(m), np.zeros(m), rng.uniform(0, 6.28, m)], scl=np.c_[ls, ls, ls], coll=env)
    # trees: clumps of spiky foliage; big trees overhang the path from the lake side, smaller ones on the lawn
    tproto = geo.proto_collection("TREE_PROTOS")
    def foliage_base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-700, 200), attribute_type="GEOMETRY", attribute_name="lv")
        it = _n(nt, "ShaderNodeAttribute", (-700, 0), attribute_type="INSTANCER", attribute_name="tint")
        v = _math(nt, "ADD", at.outputs["Fac"], _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", it.outputs["Fac"], 0.5, (-550, 0)), 0.3, (-450, 0)), (-350, 100))
        ramp = _n(nt, "ShaderNodeValToRGB", (-250, 100))
        cr = ramp.color_ramp
        cr.elements[0].position, cr.elements[0].color = 0.05, core.hexc("#1f4a22")
        cr.elements[1].position, cr.elements[1].color = 0.95, core.hexc("#c8e070")
        for pos_, h_ in ((0.3, "#3d7a2e"), (0.55, "#6aa83a"), (0.75, "#93c64b")):
            e_ = cr.elements.new(pos_)
            e_.color = core.hexc(h_)
        _l(nt, v, ramp.inputs[0])
        return ramp.outputs[0]
    tm = look.cel("foliage", core.hexc("#6aa83a"), shadow=(0.4, 0.52, 0.42, 1), high=(1.16, 1.14, 1.0, 1), t1=0.4, t2=0.92, paint=0.04,
                  base_node=foliage_base, soft=0.2, ao=0.6, ao_dist=0.6, backface=True)
    for i in range(5):
        plants.crown(f"crown_{i}", tm, tproto, seed=900 + i, radius=1.0, n_clumps=55, leaves=110, leaf=0.055, core=True)
    trees = []
    y = y0 - 2
    while y < y1 + 2:
        trees.append((rng.uniform(-3.9, -2.4), y, rng.uniform(2.0, 3.1)))
        y += rng.uniform(4.8, 7.0)
    y = y0
    while y < y1 + 2:
        trees.append((rng.uniform(2.6, 5.6), y, rng.uniform(1.5, 2.3)))
        y += rng.uniform(3.8, 5.2)
    cl = np.array([(tx, ty, r * 1.2, r) for tx, ty, r in trees])
    k = len(cl)
    tree_rot = np.c_[np.zeros(k), np.zeros(k), rng.uniform(0, 6.28, k)]
    tree_obj = geo.instances("trees", tproto, cl[:, :3], rot=tree_rot, scl=np.c_[cl[:, 3], cl[:, 3], cl[:, 3]],
                             variant=rng.integers(0, 5, k), tint=rng.random(k), coll=env)
    tree_ph = rng.uniform(0, 6.28, k)
    # trunks hinted under the crowns
    bark = look.cel("bark", core.hexc("#5a4632"), paint=0.03, soft=0.2)
    for i, (tx, ty, z_, r) in enumerate(cl):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.12 * r, radius2=0.07 * r, depth=r * 1.4)
        bmesh.ops.translate(bm, vec=(tx, ty, r * 0.7), verts=bm.verts)
        geo.bm_to_object(bm, f"trunk{i}", bark, env)
    # lawn tufts and small flower dots, fallen leaves on the path and lawn, reeds along the shore
    vprot = geo.proto_collection("P_lawn")
    tuftm = look.cel("tuft", core.hexc("#3d7d33"), shadow=(0.45, 0.55, 0.5, 1), paint=0.03, soft=0.2, ao=0.4,
                     base_node=look.instancer_palette([core.hexc("#3d7d33"), core.hexc("#4f9238"), core.hexc("#2f6a2c"), core.hexc("#6aa846")]))
    for i in range(3):
        plants.grass_tuft(f"a_tuft_{i}", tuftm, vprot, seed=950 + i, n=(10, 18), height=0.14, lean=0.6)
    flm = look.cel("flower_dot", core.hexc("#f4f0d6"), paint=0.0, soft=0.3,
                   base_node=look.instancer_palette([core.hexc("#f4f0d6"), core.hexc("#f0d85a"), core.hexc("#e9e2f2")]))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=0.025)
    geo.bm_to_object(bm, "b_flower", flm, vprot)
    lfm = look.cel("fallen_leaf", core.hexc("#a8b84a"), paint=0.0, soft=0.25,
                   base_node=look.instancer_palette([core.hexc("#a8b84a"), core.hexc("#c9a64a"), core.hexc("#8c6e3a"), core.hexc("#7ea33e")]))
    plants.leaf_card("c_leaf", lfm, vprot, size=0.08)
    reedm = look.cel("reed9", core.hexc("#4e7a35"), shadow=(0.45, 0.55, 0.5, 1), paint=0.03, soft=0.2, ao=0.4,
                     base_node=look.instancer_palette([core.hexc("#4e7a35"), core.hexc("#5f8a3c"), core.hexc("#3d6a2e")]))
    plants.grass_tuft("d_reed", reedm, vprot, seed=990, n=(12, 24), height=0.9, lean=0.3)
    lawn = geo.poisson(rng, 1600, 0.95, y0, x1, y1, 0.32)
    nl = len(lawn)
    geo.instances("lawn_tufts", vprot, np.c_[lawn, np.full(nl, 0.0)], rot=np.c_[np.zeros(nl), np.zeros(nl), rng.uniform(0, 6.28, nl)],
                  scl=np.repeat(rng.uniform(0.7, 1.4, nl)[:, None], 3, 1), variant=rng.integers(0, 3, nl), tint=rng.random(nl), coll=env)
    fl = geo.poisson(rng, 700, 0.95, y0, x1, y1, 0.25)
    nf = len(fl)
    geo.instances("lawn_flowers", vprot, np.c_[fl, np.full(nf, 0.02)], variant=np.full(nf, 3), tint=rng.random(nf), coll=env)
    lv = np.c_[rng.uniform(-1.2, x1, 500), rng.uniform(y0, y1, 500)]
    nlv = len(lv)
    geo.instances("fallen_leaves", vprot, np.c_[lv, np.full(nlv, 0.13)], rot=np.c_[np.zeros(nlv), np.zeros(nlv), rng.uniform(0, 6.28, nlv)],
                  scl=np.repeat(rng.uniform(0.7, 1.3, nlv)[:, None], 3, 1), variant=np.full(nlv, 4), tint=rng.random(nlv), coll=env)
    rd = []
    for yv in np.arange(y0, y1, 0.32):
        if rng.random() < 0.75:
            rd.append((shore_x(yv) - rng.uniform(0.0, 0.35), yv + rng.normal(0, 0.1)))
    rd = np.array(rd)
    nrd = len(rd)
    geo.instances("reeds", vprot, np.c_[rd, np.full(nrd, -0.1)], rot=np.c_[np.zeros(nrd), np.zeros(nrd), rng.uniform(0, 6.28, nrd)],
                  scl=np.repeat(rng.uniform(0.7, 1.3, nrd)[:, None], 3, 1), variant=np.full(nrd, 5), tint=rng.random(nrd), coll=env)
    # benches and a small dock
    wood = look.cel("wood", core.hexc("#8a5a36"), paint=0.05)
    for by in np.arange(y0 + 3, y1, 11.0):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.35, 1.4, 0.45), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(1.15, by, 0.22), verts=bm.verts)
        geo.bm_to_object(bm, f"bench{by:.0f}", wood, env, smooth=False)
    bm = bmesh.new()
    for i in range(7):
        bmesh.ops.create_cube(bm, size=1.0)
    geo_v = []
    bm.free()
    bm = bmesh.new()
    for i in range(7):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(1.6, 0.16, 0.06), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(-2.4, 14.0 + i * 0.19, 0.05), verts=r["verts"])
    geo.bm_to_object(bm, "dock", wood, env, smooth=False)

    # bicycle + rider
    bmats = dict(tyre=look.cel("tyre", core.hexc("#1e1e22"), paint=0.0), metal=look.cel("bmetal", core.hexc("#55575c"), paint=0.0),
                 frame=look.cel("bframe", core.hexc("#2b2d36"), paint=0.0), saddle=look.cel("saddle", core.hexc("#2a2224"), paint=0.0),
                 basket=look.cel("basket", core.hexc("#d8b25a"), shadow=(0.6, 0.5, 0.45, 1), paint=0.12, paint_scale=40))
    bike = vehicles.bicycle("bike", bmats, ink)
    hm = dict(top=look.cel("c_top", core.hexc("#efede8"), shadow=(0.6, 0.6, 0.7, 1), paint=0.03), legs=look.cel("c_legs", core.hexc("#3a3a46"), paint=0.0),
              shoes=look.cel("c_shoes", core.hexc("#2a2628"), paint=0.0), hands=look.cel("c_hands", core.hexc("#d6a98f"), paint=0.0),
              skin=look.cel("c_skin", core.hexc("#d6a98f"), paint=0.0), hair=look.cel("c_hair", core.hexc("#231a18"), paint=0.03))
    for m_ in list(bmats.values()) + list(hm.values()):
        nt_ = m_.node_tree
        g_ = [x for x in nt_.nodes if x.type == "GROUP"][0]
        g_.inputs["Hero"].default_value = 1.0
        g_.inputs["Soft"].default_value = 0.22
    rider = human.Human("rider", hm, hair="long", coll=ink, bulk={"top": 1.15})
    helm_m = look.cel("helmet", core.hexc("#d8473b"), shadow=(0.6, 0.5, 0.6, 1), high=(1.3, 1.2, 1.15, 1), paint=0.0, soft=0.18, rim=0.35, hero=True)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.12, 0.15, 0.1), verts=bm.verts)
    helmet = geo.bm_to_object(bm, "helmet", helm_m, ink)
    mot = rope_io.C.owner_motion(SCENE)
    def bike_pos(t):
        tt = min(max(t, start), end)
        p = rig.screen_to_world(tt, *BIKE_SCREEN, 0.0)
        return Vector((p[0] + mot(t)[0], p[1] + (min(t - start, 0) + max(t - end, 0)) * 4.17 / PPM, 0.0))
    def dist(t):
        return float(rig.ys[rig.local(t)] - rig.ys[0]) if t >= start else (t - start) * 4.17 / PPM

    def attach(t):
        p = bike_pos(t)
        return np.array([p[0] - 0.05, p[1] - 0.55, 0.85])
    hg = geo.HeightGrid(ground_h, x0 - 2, y0 - 2, x1 + 2, y1 + 2, 0.08)
    rope = rope_io.Owner("A", SCENE, rig, attach, list(range(start, end, 2)), trail=(0.0, -1.0), ground_fn=lambda x, y: hg(x, y) + 0.01,
                         heading_fn=lambda t: 0.0,
                         warm=150, cfg_motion=False)

    st = look.freestyle(ink, thickness=1.7, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.94, streak=0.06, lift=(0.98, 1.0, 1.02), gain=(1.04, 1.03, 0.95),
                         vignette=0.3, ink=0.4, ink_normal=(0.45, 1.3), saturation=1.05), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        p = bike_pos(d)
        wob = 0.012 * math.sin(d * 0.21) + 0.006 * math.sin(d * 0.53)
        bike["root"].location = (p[0], p[1], 0.0)
        bike["root"].rotation_euler = (0, wob, 0.0)
        # wind sways the crowns (dappled shadows move on path and lawn)
        rr = tree_rot.copy()
        rr[:, 0] = 0.012 * np.sin(d * 0.09 + tree_ph)
        rr[:, 1] = 0.012 * np.cos(d * 0.07 + tree_ph * 1.3)
        geo.update_points(tree_obj, cl[:, :3], rot=rr)
        J, wheel, crank = vehicles.ride_pose(dist(d), bike)
        for w in bike["wheels"]:
            w.rotation_euler = (-wheel, 0, 0)
        bike["crank"].rotation_euler = (-crank, 0, 0)
        M = np.array(bike["root"].matrix_basis)
        Jw = {k_: (M @ np.r_[v, 1.0])[:3] for k_, v in J.items()}
        rider.set_world(Jw, 0.0)
        hd_ = Jw["head"]
        helmet.location = (hd_[0], hd_[1] - 0.01, hd_[2] + 0.05)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])
    return r
