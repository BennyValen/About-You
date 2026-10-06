"""Scene 11 (frames 3316-3647): a V of white cranes flies over peach-lavender cumulus; the camera keeps a
constant 4.97 px/frame right up to the cut. Bird shadows fall on the cloud tops; gaps (widening along the
route) open onto the deep blue world far below. The red cord streams behind the lead crane."""
import json, math, os
import numpy as np
import bpy
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, thread, creatures
from kit.look import _n, _l, _math, _mixrgb

SCENE = 11
PPM = 92.0
BIRD_Z = 2.4
SUN_DIR = (0.5, 0.42, 0.76)
PAINT_BOIL = 0.45
# formation: screen positions measured from the source (lead first)
V = [(540, 1190), (370, 1320), (690, 1350), (230, 1450), (840, 1484), (110, 1616), (980, 1650), (700, 1800)]


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def cloud_height(X, Y, rng):
    """cauliflower cumulus: max of sphere caps at three scales inside a cover mask that thins along +Y"""
    Z = np.full_like(X, -1.6)
    x0, x1, y0, y1 = X.min(), X.max(), Y.min(), Y.max()
    dx = X[0, 1] - X[0, 0]
    cover = geo.fbm2(X * 0.07, Y * 0.07, 4, 31) + 0.5 - 0.010 * (Y - y0) + 0.12 * geo.fbm2(X * 0.3, Y * 0.3, 2, 3)
    inside = cover > 0.0
    for scale, n, rr, hh in ((1.0, 260, (2.6, 4.8), 0.55), (0.5, 900, (1.0, 2.0), 0.6), (0.25, 2600, (0.35, 0.8), 0.65)):
        cx = rng.uniform(x0, x1, n)
        cy = rng.uniform(y0, y1, n)
        r = rng.uniform(*rr, n)
        for i in range(n):
            i0, i1 = int((cx[i] - r[i] - x0) / dx), int((cx[i] + r[i] - x0) / dx) + 1
            j0, j1 = int((cy[i] - r[i] - y0) / dx), int((cy[i] + r[i] - y0) / dx) + 1
            i0, j0 = max(i0, 0), max(j0, 0)
            sx, sy = X[j0:j1, i0:i1], Y[j0:j1, i0:i1]
            if sx.size == 0:
                continue
            m = inside[j0:j1, i0:i1]
            if not m.any():
                continue
            c = cover[j0:j1, i0:i1]
            d2 = (sx - cx[i]) ** 2 + (sy - cy[i]) ** 2
            cap = np.sqrt(np.maximum(r[i] ** 2 - d2, 0)) * hh + np.minimum(c, 0.6) * 1.6 - 1.2 * (1 - scale)
            cap = np.where((d2 < r[i] ** 2) & m, cap, -1.6)
            Z[j0:j1, i0:i1] = np.maximum(Z[j0:j1, i0:i1], cap)
    return Z - 0.95


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#b9a9d6"), 0.42)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.84, SUN_DIR, 0.3), core.hexc("#fff0e2"), angle_deg=3.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.35)
    rng = np.random.default_rng(1111)
    step = 0.09
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    xs, ys = np.linspace(x0, x1, nx), np.linspace(y0, y1, ny)
    X, Y = np.meshgrid(xs, ys)
    Z = cloud_height(X, Y, rng)
    cloud = geo.grid("clouds", x0, y0, x1, y1, nx, ny, None, env)
    co = np.zeros(nx * ny * 3, np.float32)
    cloud.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    co[:, 2] = Z.ravel()
    cloud.data.vertices.foreach_set("co", co.ravel())
    cloud.data.update()
    def cloud_base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, 200))
        nz = _n(nt, "ShaderNodeTexNoise", (-700, 200))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 0.35
        nz.inputs["Detail"].default_value = 3
        return _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#f3dccd"), core.hexc("#e6cbd0"), (-500, 200))
    def cloud_h(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, -200))
        out = None
        for i, sc_ in enumerate((1.1, 2.6)):
            vo = _n(nt, "ShaderNodeTexVoronoi", (-700, -200 - i * 200), feature="F1")
            _l(nt, geo_n.outputs["Position"], vo.inputs["Vector"])
            vo.inputs["Scale"].default_value = sc_
            dome = _math(nt, "SQRT", _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", vo.outputs["Distance"], vo.outputs["Distance"], (-500, -200 - i * 200)), (-400, -200 - i * 200), clamp=True), None, (-300, -200 - i * 200))
            dome = _math(nt, "MULTIPLY", dome, 1.0 / (i + 1.6), (-200, -200 - i * 200))
            out = dome if out is None else _math(nt, "ADD", out, dome, (-100, -300))
        nz = _n(nt, "ShaderNodeTexNoise", (-700, -600))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 3.0
        nz.inputs["Detail"].default_value = 5
        return _math(nt, "ADD", out, _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.3, (-500, -600)), (0, -400))
    cmat = look.cel("cloud", core.hexc("#ead4cc"), shadow=(0.5, 0.42, 0.82, 1), high=(1.08, 1.03, 0.96, 1), t1=0.66, t2=0.9,
                    paint=0.26, paint_scale=1.6, base_node=cloud_base, height_node=cloud_h, bump=0.9, bump_dist=0.12, rough=0.9)
    cloud.data.materials.append(cmat)
    # the world far below, seen through the gaps
    def below_base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, 200))
        mp = _n(nt, "ShaderNodeMapping", (-700, 200))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, 0.35)
        mp.inputs["Scale"].default_value = (0.15, 2.0, 1)
        nz = _n(nt, "ShaderNodeTexNoise", (-500, 200))
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 0.8
        nz.inputs["Detail"].default_value = 5
        return _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#2f3a6c"), core.hexc("#55598f"), (-300, 200))
    below = geo.grid("below", x0 - 10, y0 - 10, x1 + 10, y1 + 10, 4, 4, None, env,
                     look.cel("below", core.hexc("#3a4576"), paint=0.2, paint_scale=0.6, base_node=below_base))
    below.location.z = -1.95
    below.visible_shadow = False

    # cranes
    mw = look.cel("crane_white", core.hexc("#f6f4f1"), shadow=(0.72, 0.7, 0.86, 1), high=(1.04, 1.04, 1.04, 1), paint=0.05, paint_scale=8)
    mb = look.cel("crane_black", core.hexc("#2a2730"), paint=0.0)
    ml = look.cel("crane_leg", core.hexc("#3b3640"), paint=0.0)
    birds = [creatures.Crane(f"crane{i}", mw, mb, ml, span=2.25 if i == 0 else 2.05, coll=ink) for i in range(len(V))]
    # simple boids: slot seeking + separation + alignment, deterministic integration over the scene
    n = len(V)
    frames = np.arange(start - 48, end + 2)
    slots = lambda f: np.array([rig.screen_to_world(f, sx, sy, BIRD_Z)[:2] for sx, sy in V])
    pos = slots(frames[0]) + rng.normal(0, 0.15, (n, 2))
    vel = np.tile(slots(frames[0] + 1)[0] - slots(frames[0])[0], (n, 1))
    track = {}
    for f in frames:
        tgt = slots(f)
        acc = (tgt - pos) * 0.02 - (vel - (slots(f + 1) - tgt)) * 0.08
        for i in range(n):
            dv = pos[i] - pos
            dist = np.linalg.norm(dv, axis=1) + 1e-6
            near = (dist < 1.6) & (dist > 1e-5)
            acc[i] += (dv[near] / dist[near][:, None] ** 2).sum(0) * 0.004
        acc[1:] += (vel.mean(0) - vel[1:]) * 0.02
        acc += 0.0015 * np.c_[np.sin(f * 0.031 + np.arange(n) * 1.7), np.cos(f * 0.023 + np.arange(n) * 2.3)]
        vel = vel + acc
        pos = pos + vel
        track[int(f)] = pos.copy()
    track_lead_z = lambda f: BIRD_Z + 0.08 * math.sin(f * 0.05)

    # cord streaming behind the lead crane (light thread: drag dominates gravity)
    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    def lead_attach(t):
        f0 = int(math.floor(t))
        a = track.get(f0, track[min(track)])
        b = track.get(f0 + 1, a)
        u = t - f0
        p = a[0] * (1 - u) + b[0] * u
        return np.array([p[0], p[1] - 0.25, track_lead_z(t) - 0.12])
    # the flock flies fast through the air (clouds far below drift slowly), so the cord streams back in the
    # relative wind with a gentle sag and sway, staying clear of the cloud tops
    def wind(x, y, z, t):
        return 0.5 * np.sin(y * 0.5 + t * 0.04), np.full_like(x, -14.0), np.zeros_like(x)
    cord = thread.Cord(n_seg=200, length=11.0, mode="air", ground=lambda x, y: np.full_like(x, -30.0), air_drag=3.0, wind=wind,
                       substeps=14, iters=60, bend=0.15)
    sim = cord.run(list(range(start, end)), lead_attach, (0.0, -1.0), warm=96)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.8)

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=11, bloom=0.45, bloom_threshold=0.92, streak=0.12, lift=(0.99, 0.98, 1.03), gain=(1.03, 1.0, 0.98),
                         vignette=0.24, grain=0.03, ink=0.45, ink_normal=(0.4, 1.2)), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        P = track[d]
        for i, b in enumerate(birds):
            v = track[d + 2][i] - track[d][i] if d + 2 in track else track[d][i] - track[d - 2][i]
            hd = math.atan2(-v[0], v[1])
            b.body.location = (P[i][0], P[i][1], BIRD_Z + 0.1 * math.sin(d * 0.05 + i))
            b.body.rotation_euler = (0.04, 0.05 * math.sin(d * 0.04 + i), hd)
            b.pose(d, phase=i * 0.9)
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
