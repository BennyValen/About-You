"""Scene 2 (frames 294-607): a bright forest drawn as raised contour hedges (fingerprint-like rings of
clipped hedge with dark gaps), lime to deep green with teal patches. A white modern train runs straight up
the central track. The hedge pattern is real displaced geometry that re-draws on twos: fast until ~17.2 s,
then slowly. Round bushes and pale rocks are scattered; mist drifts over in the second half."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, thread, vehicles
from kit.look import _n, _l, _math, _mixrgb

SCENE = 2
PPM = 30.0
SUN_DIR = (-0.5, 0.55, 0.72)
FRONT_SCREEN_Y = 980
CAR_LEN, GAP = 7.8, 0.35
SPACING = 0.5
MORPH_END = 119
PAINT_BOIL = 0.2


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def morph_clock(local_frame):
    t = local_frame / 24.0
    te = MORPH_END / 24.0
    return 1.6 * t if t < te else 1.6 * te + (t - te) * 0.12


def _hash2(ix, iy, seed):
    v = np.sin(ix * 127.1 + iy * 311.7 + seed * 74.7) * 43758.5453
    return v - np.floor(v)


def ring_height(X, Y, m):
    """smooth-min distance to jittered moving centres -> evenly spaced rings meeting in deltas"""
    wx = geo.fbm2(X * 0.042 + 1.3, Y * 0.042 + m * 0.35, 3, 1)
    wy = geo.fbm2(X * 0.042 - 4.1, Y * 0.042 + 2.0 - m * 0.3, 3, 2)
    qx, qy = X + wx * 4.2, Y + wy * 4.2
    cell = 17.0
    gx, gy = np.floor(qx / cell), np.floor(qy / cell)
    k = 0.87
    acc = np.zeros_like(X)
    for j in (-1, 0, 1):
        for i in (-1, 0, 1):
            cx_, cy_ = gx + i, gy + j
            hx, hy, hz = _hash2(cx_, cy_, 1), _hash2(cx_, cy_, 2), _hash2(cx_, cy_, 3)
            cx = (cx_ + 0.5 + (hx - 0.5) * 0.7) * cell + np.sin(m * 0.9 + hz * 6) * 1.3
            cy = (cy_ + 0.5 + (hy - 0.5) * 0.7) * cell + np.cos(m * 0.7 + hx * 6) * 1.3
            dx, dy = qx - cx, qy - cy
            ang = hz * math.pi
            c, s = np.cos(ang), np.sin(ang)
            rx = (c * dx - s * dy) * (0.75 + 0.5 * hy)
            ry = s * dx + c * dy
            acc += np.exp(-np.sqrt(rx * rx + ry * ry) / k)
    d = -k * np.log(np.maximum(acc, 1e-9))
    ph = d / SPACING - m * 0.9
    fr = ph - np.floor(ph)
    brk = geo.value_noise2(X * 0.36 + m * 0.4, Y * 0.36, 5) * 0.6 + geo.value_noise2(X * 1.0 - m * 0.2, Y * 1.0, 6) * 0.4
    half = np.clip(0.36 - 0.25 * np.clip((brk - 0.55) * 3, 0, 1), 0.08, 0.36)
    u = (fr - 0.5) / half
    clear = np.clip((np.abs(X) - 2.35) / 0.3, 0, 1)        # keep the track corridor clear of hedges
    return 0.3 * np.sqrt(np.clip(1 - u * u, 0, 1)) * clear


def hedge_material():
    def base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1400, 200))
        sz = _n(nt, "ShaderNodeSeparateXYZ", (-1200, 200))
        _l(nt, geo_n.outputs["Position"], sz.inputs[0])
        nz = _n(nt, "ShaderNodeTexNoise", (-1200, 0))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 0.035
        nz.inputs["Detail"].default_value = 3
        ramp = _n(nt, "ShaderNodeValToRGB", (-1000, 0))
        cr = ramp.color_ramp
        cr.elements[0].color = core.hexc("#3a8a4e")
        cr.elements[1].color = core.hexc("#c2e86a")
        e = cr.elements.new(0.45)
        e.color = core.hexc("#5aae50")
        e = cr.elements.new(0.68)
        e.color = core.hexc("#96d250")
        _l(nt, nz.outputs["Fac"], ramp.inputs[0])
        tn = _n(nt, "ShaderNodeTexNoise", (-1200, -200))
        _l(nt, geo_n.outputs["Position"], tn.inputs["Vector"])
        tn.inputs["Scale"].default_value = 0.028
        tval = _n(nt, "ShaderNodeValue", (-1200, -380), name="TEAL")
        d = tval.outputs[0].driver_add("default_value").driver
        d.type = "SCRIPTED"
        d.expression = "0.35 + 0.65 * min(1, max(0, (frame - 354) / 140.0))"
        tm = _n(nt, "ShaderNodeMapRange", (-1000, -200), clamp=True)
        _l(nt, tn.outputs["Fac"], tm.inputs["Value"])
        tm.inputs["From Min"].default_value, tm.inputs["From Max"].default_value = 0.48, 0.58
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", tm.outputs["Result"], _math(nt, "MULTIPLY", tval.outputs[0], 0.85, (-900, -380)), (-800, -250)),
                    ramp.outputs[0], core.hexc("#4aa58e"), (-700, 0))
        gap = _n(nt, "ShaderNodeMapRange", (-1000, 300), clamp=True)
        _l(nt, sz.outputs[2], gap.inputs["Value"])
        gap.inputs["From Min"].default_value, gap.inputs["From Max"].default_value = 0.03, 0.09
        return _mixrgb(nt, "MIX", gap.outputs["Result"], core.hexc("#224b2b"), c, (-500, 100))
    return look.cel("hedge", core.hexc("#5aae50"), shadow=(0.66, 0.75, 0.71, 1), high=(1.11, 1.08, 1.0, 1), t1=0.45, t2=0.95,
                    paint=0.14, paint_scale=1.6, base_node=base, rough=0.9)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#cfe8d4"), 0.36)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.86, SUN_DIR, 0.28), core.hexc("#fff6e0"), angle_deg=2.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    hw, hh = 1080 / 2 / PPM * 1.15, 1920 / 2 / PPM * 1.15
    step = 0.11
    nx, ny = int(2 * hw / step), int(2 * hh / step)
    hedge = geo.grid("hedges", -hw, -hh, hw, hh, nx, ny, None, env, hedge_material())
    me = hedge.data
    base_co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", base_co)
    base_co = base_co.reshape(-1, 3)
    # track bed (ballast, ties, rails, rust strip left, grass strip right), slightly raised
    def bed_base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1200, 0))
        sz = _n(nt, "ShaderNodeSeparateXYZ", (-1000, 0))
        _l(nt, geo_n.outputs["Position"], sz.inputs[0])
        vo = _n(nt, "ShaderNodeTexVoronoi", (-1000, 200))
        _l(nt, geo_n.outputs["Position"], vo.inputs["Vector"])
        vo.inputs["Scale"].default_value = 9.0
        c = _mixrgb(nt, "MIX", vo.outputs["Distance"], core.hexc("#d9d5c8"), core.hexc("#b3ad9f"), (-800, 200))
        tie = _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "FRACT", _math(nt, "MULTIPLY", sz.outputs[1], 1.36, (-900, -100)), None, (-800, -100)), 0.5, (-700, -100)), None, (-600, -100)), 0.16, (-500, -100))
        ax = _math(nt, "ABSOLUTE", sz.outputs[0], None, (-900, -250))
        tie = _math(nt, "MULTIPLY", tie, _math(nt, "LESS_THAN", ax, 1.4, (-700, -250)), (-400, -150))
        c = _mixrgb(nt, "MIX", tie, c, core.hexc("#8d877c"), (-300, 100))
        rail = _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", ax, 0.9, (-700, -350)), None, (-600, -350)), 0.07, (-500, -350))
        c = _mixrgb(nt, "MIX", rail, c, core.hexc("#6f6d6b"), (-200, 100))
        rust = _math(nt, "MULTIPLY", _math(nt, "LESS_THAN", sz.outputs[0], -1.95, (-700, -500)), 1.0, (-500, -500))
        grass = _math(nt, "GREATER_THAN", sz.outputs[0], 1.9, (-700, -600))
        c = _mixrgb(nt, "MIX", rust, c, core.hexc("#a2532c"), (-100, 100))
        return _mixrgb(nt, "MIX", grass, c, core.hexc("#79c04a"), (0, 100))
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.25)
    bed = geo.grid("trackbed", -2.25, y0, 2.25, y1, 20, 400, None, env, look.cel("bed", core.hexc("#cfcabc"), shadow=(0.62, 0.62, 0.72, 1), paint=0.08, base_node=bed_base))
    bed.location.z = 0.18
    rng = np.random.default_rng(202)
    bproto = geo.proto_collection("BUSH_PROTOS")
    bush_m = look.cel("bush", core.hexc("#2f6b3e"), shadow=(0.5, 0.6, 0.55, 1), high=(1.2, 1.2, 1.05, 1), paint=0.08, paint_scale=5,
                      base_node=look.instancer_palette([core.hexc(h) for h in ("#2f6b3e", "#3a7a44", "#2a5e3a")]))
    for i in range(3):
        geo.spiky(f"bush_{i}", bush_m, bproto, seed=20 + i, subdiv=3, spikes=120, sharp=14, amp=0.3, flat=0.85)
    bp = geo.poisson(rng, 600, x0, y0, x1, y1, 3.8, accept=lambda x, y: abs(x) > 3.0)
    nb = len(bp)
    bs = rng.uniform(0.5, 0.9, nb)
    geo.instances("bushes", bproto, np.c_[bp, np.full(nb, 0.25)], scl=np.c_[bs, bs, bs * 0.8], rot=np.c_[np.zeros(nb), np.zeros(nb), rng.uniform(0, 6.28, nb)],
                  variant=rng.integers(0, 3, nb), tint=rng.random(nb), coll=env)
    rproto = geo.proto_collection("ROCK_PROTOS")
    geo.knobbly("rock", look.cel("rock", core.hexc("#e2ded2"), paint=0.04), rproto, seed=7, subdiv=1, knob=0.4, flat=0.6, lumps=3)
    rp = geo.poisson(rng, 150, x0, y0, x1, y1, 7.0, accept=lambda x, y: abs(x) > 3.0)
    nr = len(rp)
    rs = rng.uniform(0.2, 0.32, nr)
    geo.instances("rocks", rproto, np.c_[rp, np.full(nr, 0.3)], scl=np.c_[rs, rs * 1.2, rs * 0.7], rot=np.c_[np.zeros(nr), np.zeros(nr), rng.uniform(0, 6.28, nr)], coll=env)
    # white train
    tmats = dict(body=look.cel("wcar", core.hexc("#efede6"), shadow=(0.66, 0.68, 0.74, 1), high=(1.04, 1.04, 1.04, 1), paint=0.04),
                 window=look.cel("wwin", core.hexc("#2b2e38"), paint=0.0), roof=look.cel("wroof", core.hexc("#cfccc4"), paint=0.0),
                 under=look.cel("wunder", core.hexc("#55565c"), paint=0.0))
    cars = []
    for i in range(3):
        root, parts = vehicles.train_car(f"wcar{i}", tmats, ink, length=CAR_LEN, width=2.0, height=2.4, nose=(i == 0), fans=2, modern=True, windows=True)
        cars.append(root)
    def mist_mat(name, seed, dens):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = _n(nt, "ShaderNodeOutputMaterial", (500, 0))
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, 0))
        mp = _n(nt, "ShaderNodeMapping", (-700, 0))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Scale"].default_value = (0.03, 0.03, 0)
        dr = mp.inputs["Location"].driver_add("default_value", 0).driver
        dr.type = "SCRIPTED"
        dr.expression = f"frame * {0.0008 + seed * 0.0003:.5f}"
        nz = _n(nt, "ShaderNodeTexNoise", (-500, 0), noise_dimensions="4D")
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["W"].default_value = seed * 9
        nz.inputs["Detail"].default_value = 5
        mr = _n(nt, "ShaderNodeMapRange", (-300, 0), clamp=True)
        _l(nt, nz.outputs["Fac"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.52, 0.78
        th = _n(nt, "ShaderNodeValue", (-300, -200))
        dd = th.outputs[0].driver_add("default_value").driver
        dd.type = "SCRIPTED"
        dd.expression = f"{dens} * min(1, max(0, (frame - 394) / 130.0))"
        a = _math(nt, "MULTIPLY", mr.outputs["Result"], th.outputs[0], (-100, 0))
        em = _n(nt, "ShaderNodeEmission", (100, 50))
        em.inputs[0].default_value = core.hexc("#e4f4ec")
        em.inputs[1].default_value = 1.0
        tr = _n(nt, "ShaderNodeBsdfTransparent", (100, -100))
        mx = _n(nt, "ShaderNodeMixShader", (300, 0))
        _l(nt, a, mx.inputs[0])
        _l(nt, tr.outputs[0], mx.inputs[1])
        _l(nt, em.outputs[0], mx.inputs[2])
        _l(nt, mx.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
        return m
    for i, (z, dens) in enumerate(((10.0, 0.5), (22.0, 0.35))):
        mp_ = geo.grid(f"mist{i}", x0 - 30, y0 - 30, x1 + 30, y1 + 30, 4, 4, None, env, mist_mat(f"mist{i}", i * 0.5, dens))
        mp_.location.z = z
        mp_.visible_shadow = False

    def front_y(t):
        return rig.screen_to_world(max(t, start), 540, FRONT_SCREEN_Y, 0.0)[1] + (min(t - start, 0)) * 7.08 / PPM
    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99, paint=0.0, glow=0.35, rough=0.5)
    def coupler(t):
        return np.array([0.0, front_y(t) - 3 * CAR_LEN - 2 * GAP - 0.1, 0.6])
    cord = thread.Cord(n_seg=200, length=16.0, mode="ground", ground=lambda x, y: np.where(np.abs(x) < 2.25, 0.2, 0.1), friction=0.7, substeps=6, iters=22)
    sim = cord.run(list(range(start, end)), coupler, (0.0, -1.0), warm=100)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.4)

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=6, bloom=0.4, bloom_threshold=0.95, streak=0.1, lift=(0.99, 1.0, 1.01), gain=(1.03, 1.02, 0.97),
                         vignette=0.28, grain=0.03, ink=0.5, ink_normal=(0.45, 1.3), saturation=1.08), res_scale=opt.scale)
    log = []
    cache = {}

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        cx, cy = rig.pos(f)
        hedge.location = (cx, cy, 0.0)
        X = base_co[:, 0] + cx
        Y = base_co[:, 1] + cy
        Z = ring_height(X, Y, morph_clock(d - start))
        co = base_co.copy()
        co[:, 2] = Z
        me.vertices.foreach_set("co", co.ravel())
        me.update()
        fy = front_y(d)
        for i, c in enumerate(cars):
            c.location = (0.02 * math.sin(d * 0.06 + i), fy - (i + 1) * CAR_LEN - i * GAP, 0.18)
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
