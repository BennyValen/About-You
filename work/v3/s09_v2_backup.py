"""Scene 9 (frames 2646-2981): a cyclist rides up a beige path beside a dark lake under big fluffy trees.
Wheels spin from the ground speed (omega = v / R), cranks geared to the wheels, feet on the pedals.
Sun from the upper-right: long dappled tree shadows fall lower-left across path and lawn."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, thread, vehicles
from kit.look import _n, _l, _math, _mixrgb

SCENE = 9
PPM = 75.0
SUN_DIR = (0.62, 0.62, 0.48)
BIKE_SCREEN = (540, 1180)
PATH_X = 0.0
PAINT_BOIL = 0.95


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
        # path
        px = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", sx.outputs[0], PATH_X, (-1400, -100)), None, (-1250, -100))
        pm = _n(nt, "ShaderNodeMapRange", (-1100, -100), clamp=True)
        _l(nt, px, pm.inputs["Value"])
        pm.inputs["From Min"].default_value, pm.inputs["From Max"].default_value = 0.8, 0.76
        pn = _n(nt, "ShaderNodeTexNoise", (-1250, -250))
        _l(nt, geo_n.outputs["Position"], pn.inputs["Vector"])
        pn.inputs["Scale"].default_value = 3.0
        path = _mixrgb(nt, "MIX", pn.outputs["Fac"], core.hexc("#d4c296"), core.hexc("#e6d8b0"), (-950, -250))
        c = _mixrgb(nt, "MIX", pm.outputs["Result"], g.outputs[0], path, (-800, 0))
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
    return look.cel("ground", core.hexc("#4a8a3c"), shadow=(0.45, 0.55, 0.5, 1), high=(1.1, 1.1, 1.02, 1), t1=0.42, t2=0.97,
                    paint=0.2, paint_scale=2.0, base_node=base, rough=0.9)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#a9c4a4"), 0.34)
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
        return _mixrgb(nt, "MIX", mr.outputs["Result"], core.hexc("#10221f"), core.hexc("#3f5545"), (-200, 0))
    def lake_h(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1000, -300))
        wn = _n(nt, "ShaderNodeTexNoise", (-800, -300), noise_dimensions="4D")
        _l(nt, geo_n.outputs["Position"], wn.inputs["Vector"])
        wn.inputs["Scale"].default_value = 3.0
        d = wn.inputs["W"].driver_add("default_value").driver
        d.type = "SCRIPTED"
        d.expression = "frame / 20.0"
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
    leaf = [core.hexc(h) for h in ("#6aa83a", "#86c046", "#a2d052", "#5d9636")]
    tm = look.cel("foliage", leaf[0], shadow=(0.42, 0.55, 0.42, 1), high=(1.18, 1.16, 1.0, 1), t1=0.4, t2=0.9, paint=0.12, paint_scale=7.0,
                  base_node=look.instancer_palette(leaf))
    for i in range(4):
        geo.spiky(f"clump_{i}", tm, tproto, seed=900 + i, subdiv=4, spikes=260, sharp=24, amp=0.6, flat=0.8)
    trees = []
    y = y0 - 2
    while y < y1 + 2:
        trees.append((rng.uniform(-4.8, -3.2), y, rng.uniform(2.2, 3.0)))
        y += rng.uniform(5.5, 7.5)
    y = y0
    while y < y1 + 2:
        trees.append((rng.uniform(2.4, 5.6), y, rng.uniform(1.0, 1.7)))
        y += rng.uniform(3.8, 5.2)
    cl = []
    for tx, ty, r in trees:
        for i in range(int(5 + r * 3)):
            a = rng.uniform(0, 6.28)
            rr = 0 if i == 0 else rng.uniform(0.25, 0.62) * r
            s = r * (0.55 if i == 0 else rng.uniform(0.32, 0.45))
            cl.append((tx + rr * math.cos(a), ty + rr * math.sin(a), r * 2.2 + rng.uniform(-0.2, 0.5) - rr * 0.3, s))
    cl = np.array(cl)
    k = len(cl)
    geo.instances("trees", tproto, cl[:, :3], rot=np.c_[np.zeros(k), np.zeros(k), rng.uniform(0, 6.28, k)], scl=np.c_[cl[:, 3], cl[:, 3], cl[:, 3]],
                  variant=rng.integers(0, 4, k), tint=rng.random(k), coll=env)
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
    rider = human.Human("rider", hm, hair="long", coll=ink)
    def bike_pos(t):
        return rig.screen_to_world(t, *BIKE_SCREEN, 0.0)
    def dist(t):
        return float(rig.ys[rig.local(t)] - rig.ys[0]) if t >= start else (t - start) * 4.17 / PPM

    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    def attach(t):
        p = bike_pos(min(max(t, start), end - 1)) if t >= start else bike_pos(start) + Vector((0, (t - start) * 4.17 / PPM, 0))
        return np.array([p[0] - 0.05, p[1] - 0.55, 0.85])
    def breeze(x, y, t):
        return 0.6 * np.sin(y * 1.1 + t * 0.02), np.zeros_like(y)
    cord = thread.Cord(n_seg=200, length=22.0, mode="ground", ground=lambda x, y: ground_h(x, y) + 0.01, friction=0.55,
                       substeps=6, iters=22, push=breeze, bend=0.1)
    sim = cord.run(list(range(start, end)), attach, (0.0, -1.0), warm=110)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.4)

    st = look.freestyle(ink, thickness=1.7, res_scale=opt.scale)
    look.compositor(dict(kuwahara=7, bloom=0.4, bloom_threshold=0.94, streak=0.1, lift=(0.98, 1.0, 1.02), gain=(1.04, 1.03, 0.95),
                         vignette=0.32, grain=0.03, ink=0.55, ink_normal=(0.45, 1.3), saturation=1.05), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        p = bike_pos(d)
        bike["root"].location = (p[0], p[1], 0.0)
        J, wheel, crank = vehicles.ride_pose(dist(d), bike)
        for w in bike["wheels"]:
            w.rotation_euler = (-wheel, 0, 0)
        bike["crank"].rotation_euler = (-crank, 0, 0)
        M = np.array(bike["root"].matrix_world)
        Jw = {k_: (M @ np.r_[v, 1.0])[:3] for k_, v in J.items()}
        rider.set_world(Jw, 0.0)
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
