"""Scene 2 (frames 294-607): a tea garden seen from above: curving terraces of clipped tea hedges (rounded rows made of
leaf dabs, lighter tops, shadowed sides, dark gaps and narrow paths), teal to yellow-green, a few round shade trees.
A white modern train runs straight up the central track.

v3: the ground does NOT morph: it is a static world-space field sampled on a fixed world lattice, so it scrolls rigidly
with the camera (~14 px per distinct drawing, on twos). 22 tea pickers at fixed places along the rows: conical pale
straw hats (bright), coloured clothes, baskets on their backs, walking slowly and bending to pick, arms reaching into
the bushes, small cast shadows. Roof units and a pantograph on the train, light mist drifting above."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, vehicles, plants, rope_io
from kit.look import _n, _l, _math, _mixrgb

SCENE = 2
PPM = 30.0
SUN_DIR = (-0.5, 0.55, 0.72)
FRONT_SCREEN_Y = 980
CAR_LEN, GAP = 7.8, 0.35
SPACING = 0.5
MORPH_END = 119
M_FIXED = 1.6 * MORPH_END / 24.0       # the frozen state of the contour field (no morphing in v3)
POST = dict(light_deg=132.0, flow_deg=90.0, stroke_px=11.0, boil_mean=2.0, thread_shadow_px=1.6, repaint=0.5)


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
        d.expression = "0.75"
        tm = _n(nt, "ShaderNodeMapRange", (-1000, -200), clamp=True)
        _l(nt, tn.outputs["Fac"], tm.inputs["Value"])
        tm.inputs["From Min"].default_value, tm.inputs["From Max"].default_value = 0.48, 0.58
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", tm.outputs["Result"], _math(nt, "MULTIPLY", tval.outputs[0], 0.85, (-900, -380)), (-800, -250)),
                    ramp.outputs[0], core.hexc("#4aa58e"), (-700, 0))
        # clipped tea leaves: small dabs with random value (voronoi cells), lighter on the tops
        vo = _n(nt, "ShaderNodeTexVoronoi", (-1200, -600))
        _l(nt, geo_n.outputs["Position"], vo.inputs["Vector"])
        vo.inputs["Scale"].default_value = 7.0
        dab = _n(nt, "ShaderNodeMapRange", (-1000, -600), clamp=True)
        _l(nt, _n(nt, "ShaderNodeRGBToBW", (-1100, -650)).outputs[0] if False else vo.outputs["Color"], dab.inputs["Value"])
        dab.inputs["To Min"].default_value, dab.inputs["To Max"].default_value = 0.86, 1.14
        top = _n(nt, "ShaderNodeMapRange", (-1000, -800), clamp=True)
        _l(nt, sz.outputs[2], top.inputs["Value"])
        top.inputs["From Min"].default_value, top.inputs["From Max"].default_value = 0.18, 0.3
        top.inputs["To Min"].default_value, top.inputs["To Max"].default_value = 0.92, 1.1
        c = look.mul_color(nt, look.mul_color(nt, c, dab.outputs["Result"], (-800, -600)), top.outputs["Result"], (-650, -600))
        gap = _n(nt, "ShaderNodeMapRange", (-1000, 300), clamp=True)
        _l(nt, sz.outputs[2], gap.inputs["Value"])
        gap.inputs["From Min"].default_value, gap.inputs["From Max"].default_value = 0.03, 0.1
        return _mixrgb(nt, "MIX", gap.outputs["Result"], core.hexc("#1f4328"), c, (-500, 100))
    return look.cel("hedge", core.hexc("#5aae50"), shadow=(0.6, 0.72, 0.7, 1), high=(1.12, 1.09, 1.0, 1), t1=0.45, t2=0.95,
                    paint=0.04, paint_scale=1.6, base_node=base, rough=0.9, soft=0.2, ao=0.6, ao_dist=0.25)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
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
    def tree_base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-700, 200), attribute_type="GEOMETRY", attribute_name="lv")
        return _mixrgb(nt, "MIX", at.outputs["Fac"], core.hexc("#1d4a2a"), core.hexc("#6fa851"), (-400, 100))
    bush_m = look.cel("bush", core.hexc("#2f6b3e"), shadow=(0.5, 0.6, 0.55, 1), high=(1.15, 1.15, 1.05, 1), paint=0.03, base_node=tree_base,
                      soft=0.2, ao=0.6, ao_dist=0.5)
    for i in range(3):
        plants.crown(f"bush_{i}", bush_m, bproto, seed=20 + i, radius=1.0, height=1.0, n_clumps=30, leaves=60, leaf=0.12, core=True)
    bp = geo.poisson(rng, 120, x0, y0, x1, y1, 9.0, accept=lambda x, y: abs(x) > 3.5)
    nb = len(bp)
    bs = rng.uniform(1.2, 2.0, nb)
    geo.instances("bushes", bproto, np.c_[bp, np.full(nb, 0.6)], scl=np.c_[bs, bs, bs * 0.9], rot=np.c_[np.zeros(nb), np.zeros(nb), rng.uniform(0, 6.28, nb)],
                  variant=rng.integers(0, 3, nb), tint=rng.random(nb), coll=env)
    # tea pickers: conical straw hat, coloured clothes, basket on the back; slow walk + bending + reaching arms
    hat_m = look.cel("picker_hat", core.hexc("#f6ecc8"), shadow=(0.7, 0.68, 0.7, 1), high=(1.06, 1.05, 1.02, 1), paint=0.03, soft=0.22, rim=0.3, hero=True)
    basket_m = look.cel("picker_basket", core.hexc("#a8763f"), shadow=(0.6, 0.55, 0.6, 1), paint=0.08, paint_scale=60, soft=0.2, hero=True)
    skin_m = look.cel("picker_skin", core.hexc("#c99a76"), paint=0.0, soft=0.25, hero=True)
    clothes = [look.cel(f"picker_cloth{i}", core.hexc(h), shadow=(0.58, 0.55, 0.7, 1), paint=0.03, soft=0.22, hero=True)
               for i, h in enumerate(("#d23b3b", "#e8892e", "#3b6fc4", "#c43b9a", "#e3c23a", "#2e9a8a"))]
    def prim(name, mat, kind, scale):
        bm = bmesh.new()
        if kind == "cone":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=1.0, radius2=0.02, depth=1.0)
        elif kind == "cyl":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=1.0, radius2=0.85, depth=1.0)
        else:
            bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
        bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
        return geo.bm_to_object(bm, name, mat, ink)
    pickers = []
    pk = geo.poisson(rng, 22, -16, y0 + 8, 16, y1 - 8, 6.0, accept=lambda x, y: 3.6 < abs(x) < 16)
    for i, (px_, py_) in enumerate(pk):
        cm = clothes[i % len(clothes)]
        parts = dict(body=prim(f"pk{i}_body", cm, "sph", (1, 1, 1)), hat=prim(f"pk{i}_hat", hat_m, "cone", (1, 1, 1)),
                     basket=prim(f"pk{i}_basket", basket_m, "cyl", (1, 1, 1)),
                     arm_l=prim(f"pk{i}_arml", cm, "sph", (1, 1, 1)), arm_r=prim(f"pk{i}_armr", cm, "sph", (1, 1, 1)),
                     hand_l=prim(f"pk{i}_hl", skin_m, "sph", (0.04, 0.04, 0.04)), hand_r=prim(f"pk{i}_hr", skin_m, "sph", (0.04, 0.04, 0.04)))
        pickers.append(dict(parts=parts, x=px_, y=py_, hd=rng.uniform(0, 6.28), ph=rng.uniform(0, 6.28), v=rng.uniform(0.004, 0.009),
                            span=rng.uniform(1.0, 2.5)))

    def pose_picker(pkr, t):
        hd = pkr["hd"]
        f_ = np.array([-math.sin(hd), math.cos(hd), 0.0])
        r_ = np.array([math.cos(hd), math.sin(hd), 0.0])
        walk = pkr["span"] * math.sin(t * pkr["v"] + pkr["ph"])
        base = np.array([pkr["x"], pkr["y"], 0.0]) + f_ * walk
        bend = 0.55 + 0.35 * max(0.0, math.sin(t * 0.045 + pkr["ph"] * 1.7))
        pel = base + np.array([0, 0, 0.85])
        chest = pel + np.array([0, 0, 0.45 * math.cos(bend)]) + f_ * 0.45 * math.sin(bend)
        head = chest + np.array([0, 0, 0.2 * math.cos(bend)]) + f_ * 0.22 * math.sin(bend)
        P = pkr["parts"]
        M = Matrix.Translation(Vector(((pel + chest) / 2).tolist())) @ Matrix.Rotation(hd, 4, "Z") @ Matrix.Rotation(-bend, 4, "X")
        P["body"].matrix_world = M @ Matrix.Diagonal((0.2, 0.15, 0.3, 1))
        P["hat"].matrix_world = Matrix.Translation(Vector((head + np.array([0, 0, 0.08])).tolist())) @ Matrix.Rotation(hd, 4, "Z") @ \
            Matrix.Rotation(-bend * 0.6, 4, "X") @ Matrix.Diagonal((0.42, 0.42, 0.22, 1))
        back = (pel + chest) / 2 - f_ * 0.2 + np.array([0, 0, 0.12])
        P["basket"].matrix_world = Matrix.Translation(Vector(back.tolist())) @ Matrix.Rotation(hd, 4, "Z") @ Matrix.Rotation(-bend * 0.5, 4, "X") @ \
            Matrix.Diagonal((0.14, 0.14, 0.18, 1))
        for side, arm, hand in ((-1, "arm_l", "hand_l"), (1, "arm_r", "hand_r")):
            reach = 0.35 + 0.18 * math.sin(t * 0.22 + pkr["ph"] + side)
            sh = chest + r_ * side * 0.17
            hnd = sh + f_ * reach + np.array([0, 0, -0.38]) + r_ * side * 0.05
            mid = (sh + hnd) / 2
            dv = hnd - sh
            ang = math.atan2(-dv[0], dv[1])
            tilt = math.atan2(-dv[2], math.hypot(dv[0], dv[1]))
            P[arm].matrix_world = Matrix.Translation(Vector(mid.tolist())) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(tilt, 4, "X") @ \
                Matrix.Diagonal((0.05, max(0.1, np.linalg.norm(dv) / 2), 0.05, 1))
            P[hand].location = Vector(hnd.tolist())
    # white train
    tmats = dict(body=look.cel("wcar", core.hexc("#efede6"), shadow=(0.66, 0.68, 0.74, 1), high=(1.04, 1.04, 1.04, 1), paint=0.04),
                 window=look.cel("wwin", core.hexc("#2b2e38"), paint=0.0), roof=look.cel("wroof", core.hexc("#cfccc4"), paint=0.0),
                 under=look.cel("wunder", core.hexc("#55565c"), paint=0.0))
    cars = []
    for m_ in tmats.values():
        g_ = [x for x in m_.node_tree.nodes if x.type == "GROUP"][0]
        g_.inputs["Hero"].default_value = 1.0
        g_.inputs["Soft"].default_value = 0.2
    for i in range(3):
        root, parts = vehicles.train_car(f"wcar{i}", tmats, ink, length=CAR_LEN, width=2.0, height=2.4, nose=(i == 0), fans=2, modern=True, windows=True)
        cars.append(root)
    panto_m = look.cel("panto", core.hexc("#55575e"), paint=0.0, soft=0.2, hero=True)
    pv, pf = [], []
    for k_, (a_, b_) in enumerate((((-0.5, -0.6, 2.45), (0.5, 0.0, 2.95)), ((0.5, -0.6, 2.45), (-0.5, 0.0, 2.95)), ((-0.7, 0.0, 2.95), (0.7, 0.0, 2.95)))):
        a_, b_ = np.array(a_), np.array(b_)
        sd = np.array([0, 0.03, 0])
        i0 = len(pv)
        pv += [a_ - sd, a_ + sd, b_ + sd, b_ - sd]
        pf.append((i0, i0 + 1, i0 + 2, i0 + 3))
    panto = geo.mesh_from_arrays("pantograph", np.array(pv), pf, ink, False, panto_m)
    panto.parent = cars[1]
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
    def coupler(t):
        return np.array([0.0, front_y(t) - 3 * CAR_LEN - 2 * GAP - 0.1, 0.6])
    rope = rope_io.Owner("A", SCENE, rig, coupler, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150,
                         ground_fn=lambda x, y: np.where(np.abs(np.asarray(x, float)) < 2.25, 0.2, 0.1))

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.99, 1.0, 1.01), gain=(1.03, 1.02, 0.97),
                         vignette=0.26, ink=0.4, ink_normal=(0.45, 1.3), saturation=1.05), res_scale=opt.scale)
    log = []
    cache = {}

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        cx, cy = rig.pos(f)
        sx_, sy_ = round(cx / step) * step, round(cy / step) * step
        hedge.location = (sx_, sy_, 0.0)
        key = (round(sx_ / step), round(sy_ / step))
        X = base_co[:, 0] + sx_
        Y = base_co[:, 1] + sy_
        Z = ring_height(X, Y, M_FIXED)
        co = base_co.copy()
        co[:, 2] = Z
        me.vertices.foreach_set("co", co.ravel())
        me.update()
        fy = front_y(d)
        for i, c in enumerate(cars):
            c.location = (0.02 * math.sin(d * 0.06 + i), fy - (i + 1) * CAR_LEN - i * GAP, 0.18)
        for pkr in pickers:
            pose_picker(pkr, d)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])
    return r
