"""Scene 1 (frames 0-293): night, snowy pine forest from straight above. A dark three-car train runs up a
cleared corridor; its windows throw warm light onto the snow (real area lights, shadowed by the trees) and
its headlight scatters in the night mist (volumetric spot). Fog banks drift; a frozen pond enters top-left.
The red cord trails from the last car's coupler along the track bed."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, thread, vehicles
from kit.look import _n, _l, _math, _mixrgb

SCENE = 1
PPM = 30.0
MOON_DIR = (-0.55, 0.45, 0.7)
FRONT_SCREEN_Y = 990
CAR_LEN, GAP = 7.6, 0.45
PAINT_BOIL = 0.3


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def pond_sdf(x, y):
    return np.hypot((x + 15.0) * 0.82, y - 88.0) - 7.5 + 1.2 * geo.fbm2(x * 0.1, y * 0.1, 3, 3)


def snow_h(X, Y):
    h = 0.25 * geo.fbm2(X * 0.08, Y * 0.08, 4, 1)
    bank = np.clip(1 - np.abs(np.abs(X) - 2.3) / 0.8, 0, 1)
    corridor = np.abs(X) < 2.0
    h = np.where(corridor, 0.0, h) + 0.35 * bank ** 2
    pond = pond_sdf(X, Y) < 0
    return np.where(pond, -0.15, h)


def conifer(name, mats, coll, seed):
    """spruce from above: tiers of drooping branch blades in a star, snow caught on upper surfaces"""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    tiers = 7
    H = rng.uniform(9, 13)
    along_vals = []
    for t in range(tiers):
        u = t / (tiers - 1)
        R = 3.6 * (1 - u) ** 0.9 + 0.35
        z = 1.5 + u * H * 0.85
        nb = int(rng.integers(13, 19))
        rot = rng.uniform(0, 6.28)
        for b in range(nb):
            a = rot + 2 * math.pi * b / nb
            L = R * rng.uniform(0.7, 1.15)
            w = R * 0.15 / max(nb / 12, 1)
            c, s = math.cos(a), math.sin(a)
            tip = (c * L, s * L, z - L * 0.35)
            base_l = (-s * w * 0.5, c * w * 0.5, z + 0.1)
            base_r = (s * w * 0.5, -c * w * 0.5, z + 0.1)
            mid_l = (c * L * 0.55 - s * w, s * L * 0.55 + c * w, z - L * 0.12)
            mid_r = (c * L * 0.55 + s * w, s * L * 0.55 - c * w, z - L * 0.12)
            vs = [bm.verts.new(p) for p in (base_l, mid_l, tip, mid_r, base_r)]
            bm.faces.new(vs)
            along_vals.extend([0.0, 0.55, 1.0, 0.55, 0.0])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    ob = geo.bm_to_object(bm, name, mats, coll, smooth=False)
    me = ob.data
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    tip = np.array(along_vals, np.float32)
    col = np.c_[tip, tip, tip, np.ones_like(tip)].astype(np.float32)
    ca = me.color_attributes.new("tip", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", col.ravel())
    return ob


def tree_material():
    def base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1000, 200))
        sz = _n(nt, "ShaderNodeSeparateXYZ", (-800, 200))
        _l(nt, geo_n.outputs["Normal"], sz.inputs[0])
        nz = _n(nt, "ShaderNodeTexNoise", (-800, 0))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 3.0
        nz.inputs["Detail"].default_value = 3
        at = _n(nt, "ShaderNodeAttribute", (-1000, 400), attribute_type="GEOMETRY", attribute_name="tip")
        tipv = _math(nt, "ADD", at.outputs["Fac"], _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.6, (-450, 300)), (-250, 350))
        mr = _n(nt, "ShaderNodeMapRange", (-150, 350), clamp=True)
        _l(nt, tipv, mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.1, 1.16
        snow = mr.outputs["Result"]
        needles = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#1d2440"), core.hexc("#2b3456"), (-500, 0))
        return _mixrgb(nt, "MIX", snow, needles, core.hexc("#c8d0ee"), (-300, 100))
    return look.cel("spruce", core.hexc("#262e4c"), shadow=(0.55, 0.55, 0.75, 1), high=(1.25, 1.25, 1.3, 1), t1=0.35, t2=0.9,
                    paint=0.12, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#c9cff0"), 0.15)
    core.sun(MOON_DIR, core.sun_irradiance_for(0.5, MOON_DIR, 0.15), core.hexc("#d4daf6"), angle_deg=1.5)
    # thin volumetric slab near the ground for the headlight beam and lit mist
    beam_m = bpy.data.materials.new("beam")
    beam_m.use_nodes = True
    bnt = beam_m.node_tree
    bnt.nodes.clear()
    bout = _n(bnt, "ShaderNodeOutputMaterial", (600, 0))
    btc = _n(bnt, "ShaderNodeTexCoord", (-900, 0))
    bsx = _n(bnt, "ShaderNodeSeparateXYZ", (-700, 0))
    _l(bnt, btc.outputs["UV"], bsx.inputs[0])
    lat = _math(bnt, "ABSOLUTE", _math(bnt, "SUBTRACT", bsx.outputs[0], 0.5, (-550, 100)), None, (-450, 100))
    halfw = _math(bnt, "ADD", _math(bnt, "MULTIPLY", bsx.outputs[1], 0.42, (-550, 200)), 0.06, (-450, 200))
    side = _math(bnt, "SUBTRACT", 1.0, _math(bnt, "DIVIDE", lat, halfw, (-350, 150)), (-250, 150), clamp=True)
    along = _math(bnt, "POWER", _math(bnt, "SUBTRACT", 1.0, bsx.outputs[1], (-350, 0)), 1.8, (-250, 0))
    bnz = _n(bnt, "ShaderNodeTexNoise", (-550, -200), noise_dimensions="4D")
    _l(bnt, btc.outputs["Generated"], bnz.inputs["Vector"])
    bnz.inputs["Scale"].default_value = 5.0
    bdr = bnz.inputs["W"].driver_add("default_value").driver
    bdr.type = "SCRIPTED"
    bdr.expression = "floor(frame / 2) * 0.04"
    ba = _math(bnt, "MULTIPLY", _math(bnt, "MULTIPLY", _math(bnt, "POWER", side, 0.8, (-150, 150)), along, (0, 100)),
               _math(bnt, "ADD", _math(bnt, "MULTIPLY", bnz.outputs["Fac"], 0.6, (-350, -200)), 0.55, (-200, -200)), (100, 50), clamp=True)
    bem = _n(bnt, "ShaderNodeEmission", (300, 100))
    bem.inputs[0].default_value = (0.86, 0.9, 1.0, 1)
    bem.inputs[1].default_value = 1.15
    btr = _n(bnt, "ShaderNodeBsdfTransparent", (300, -100))
    bmx = _n(bnt, "ShaderNodeMixShader", (450, 0))
    _l(bnt, _math(bnt, "MULTIPLY", ba, 0.75, (250, -250)), bmx.inputs[0])
    _l(bnt, btr.outputs[0], bmx.inputs[1])
    _l(bnt, bem.outputs[0], bmx.inputs[2])
    _l(bnt, bmx.outputs[0], bout.inputs[0])
    beam_m.surface_render_method = "BLENDED"
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.25)
    nx, ny = int((x1 - x0) / 0.25), int((y1 - y0) / 0.25)
    def snow_base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1200, 200))
        mp = _n(nt, "ShaderNodeMapping", (-1000, 200))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, -0.35)
        mp.inputs["Scale"].default_value = (0.08, 0.5, 1)
        nz = _n(nt, "ShaderNodeTexNoise", (-800, 200))
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 1.2
        nz.inputs["Detail"].default_value = 5
        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#3d4882"), core.hexc("#56629f"), (-600, 200))
        sz = _n(nt, "ShaderNodeSeparateXYZ", (-1000, -100))
        _l(nt, geo_n.outputs["Position"], sz.inputs[0])
        pondm = _n(nt, "ShaderNodeMapRange", (-800, -100), clamp=True)
        _l(nt, sz.outputs[2], pondm.inputs["Value"])
        pondm.inputs["From Min"].default_value, pondm.inputs["From Max"].default_value = -0.05, -0.12
        ice = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#3a4170"), core.hexc("#545d96"), (-600, -100))
        c = _mixrgb(nt, "MIX", pondm.outputs["Result"], c, ice, (-400, 100))
        # rails and ties in the corridor
        rx = _math(nt, "ABSOLUTE", sz.outputs[0], None, (-1000, -300))
        rail = _n(nt, "ShaderNodeMapRange", (-800, -300), clamp=True)
        _l(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", rx, 0.72, (-900, -350)), None, (-850, -350)), rail.inputs["Value"])
        rail.inputs["From Min"].default_value, rail.inputs["From Max"].default_value = 0.06, 0.03
        ties = _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "FRACT", _math(nt, "MULTIPLY", sz.outputs[1], 1.6, (-900, -500)), None, (-800, -500)), 0.5, (-700, -500)), None, (-600, -500)), 0.13, (-500, -500))
        ties = _math(nt, "MULTIPLY", ties, _math(nt, "LESS_THAN", rx, 1.15, (-600, -600)), (-400, -550))
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", ties, 0.8, (-300, -500)), c, core.hexc("#232335"), (-200, 0))
        c = _mixrgb(nt, "MIX", rail.outputs["Result"], c, core.hexc("#1b1c2a"), (-100, 0))
        return c
    geo.grid("snow", x0, y0, x1, y1, nx, ny, snow_h, env,
             look.cel("snow", core.hexc("#4b579c"), shadow=(0.5, 0.52, 0.75, 1), high=(1.15, 1.15, 1.2, 1), t1=0.36, t2=0.92,
                      paint=0.2, paint_scale=0.6, base_node=snow_base, rough=0.9, light_tint=1.0))
    tproto = geo.proto_collection("TREE_PROTOS")
    tm = tree_material()
    for i in range(5):
        conifer(f"spruce_{i}", tm, tproto, seed=10 + i)
    rng = np.random.default_rng(101)
    pts = geo.poisson(rng, 4000, x0, y0, x1, y1, 3.6, accept=lambda x, y: abs(x) > 4.2 and pond_sdf(x, y) > 1.5)
    n = len(pts)
    s = rng.uniform(0.62, 0.95, n)
    geo.instances("forest", tproto, np.c_[pts, np.zeros(n)], rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)],
                  scl=np.c_[s, s, s], variant=rng.integers(0, 5, n), coll=env)
    # train
    tmats = dict(body=look.cel("car", core.hexc("#2a2c3c"), shadow=(0.6, 0.6, 0.75, 1), high=(1.5, 1.5, 1.6, 1), paint=0.05),
                 window=look.emissive("window", (1.0, 0.62, 0.22, 1), 5.0), roof=look.cel("fan", core.hexc("#3c3f58"), paint=0.0),
                 under=look.cel("bogie", core.hexc("#15161f"), paint=0.0))
    cars = []
    for i in range(3):
        root, parts = vehicles.train_car(f"car{i}", tmats, ink, length=CAR_LEN, width=1.9, height=2.3, nose=(i == 0), fans=3)
        cars.append(root)
        # warm window light spilling sideways onto the snow
        for side in (-1, 1):
            li = bpy.data.lights.new(f"win{i}{side}", "AREA")
            li.shape = "RECTANGLE"
            li.size, li.size_y = CAR_LEN * 0.9, 0.4
            li.energy = 700.0
            li.color = (1.0, 0.5, 0.14)
            lo = bpy.data.objects.new(f"winlight{i}{side}", li)
            env.objects.link(lo)
            lo.parent = root
            lo.location = (side * 1.15, CAR_LEN / 2, 1.6)
            zl = -Vector((side, 0.0, -0.55)).normalized()
            xl = Vector((0.0, 1.0, 0.0))
            yl = zl.cross(xl)
            lo.matrix_basis = Matrix.Translation(lo.location) @ Matrix((xl, yl, zl)).transposed().to_4x4()
    head = bpy.data.lights.new("headlight", "SPOT")
    head.energy = 9000.0
    head.spot_size = math.radians(16)
    head.spot_blend = 0.6
    head.color = (0.9, 0.93, 1.0)
    head.volume_factor = 0.0
    ho = bpy.data.objects.new("headlight", head)
    env.objects.link(ho)
    ho.parent = cars[0]
    ho.location = (0, CAR_LEN + 0.1, 1.2)
    ho.rotation_euler = (math.radians(-78), 0, 0)
    # fog banks
    fog = look.emissive("fog", core.hexc("#aeb8e6"), 0.55)
    def fog_mat(name, seed, dens):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = _n(nt, "ShaderNodeOutputMaterial", (500, 0))
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, 0))
        mp = _n(nt, "ShaderNodeMapping", (-700, 0))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Scale"].default_value = (0.025, 0.03, 0)
        dr = mp.inputs["Location"].driver_add("default_value", 0).driver
        dr.type = "SCRIPTED"
        dr.expression = f"frame * {0.0012 + seed * 0.0004:.5f}"
        nz = _n(nt, "ShaderNodeTexNoise", (-500, 0), noise_dimensions="4D")
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["W"].default_value = seed * 7
        nz.inputs["Detail"].default_value = 5
        mr = _n(nt, "ShaderNodeMapRange", (-300, 0), clamp=True)
        _l(nt, nz.outputs["Fac"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.5, 0.75
        # fog thickens through the middle of the shot (driven by frame)
        thick = _n(nt, "ShaderNodeValue", (-300, -200))
        dd = thick.outputs[0].driver_add("default_value").driver
        dd.type = "SCRIPTED"
        dd.expression = f"{dens} * (0.45 + 0.55 * sin(min(1.0, max(frame, 0) / 260.0) * 3.1416))"
        a = _math(nt, "MULTIPLY", mr.outputs["Result"], thick.outputs[0], (-100, 0))
        em = _n(nt, "ShaderNodeEmission", (100, 50))
        em.inputs[0].default_value = core.hexc("#b6bfe8")
        em.inputs[1].default_value = 0.55
        tr = _n(nt, "ShaderNodeBsdfTransparent", (100, -100))
        mx = _n(nt, "ShaderNodeMixShader", (300, 0))
        _l(nt, a, mx.inputs[0])
        _l(nt, tr.outputs[0], mx.inputs[1])
        _l(nt, em.outputs[0], mx.inputs[2])
        _l(nt, mx.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
        return m
    beam = geo.grid("beam", -1, 0, 1, 1, 2, 2, None, env, beam_m)
    beam.visible_shadow = False
    for i, (z, dens) in enumerate(((8.0, 0.3), (16.0, 0.24))):
        fp = geo.grid(f"fog{i}", x0 - 30, y0 - 30, x1 + 30, y1 + 30, 4, 4, None, env, fog_mat(f"fog{i}", i * 0.6, dens))
        fp.location.z = z
        fp.visible_shadow = False

    def front_y(t):
        return rig.screen_to_world(max(t, start), 540, FRONT_SCREEN_Y, 0.0)[1] + (min(t - start, 0)) * 6.26 / PPM
    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.85, 0.75, 0.85, 1), t1=0.1, t2=1.5, paint=0.0, glow=0.5, rough=0.5)
    def coupler(t):
        return np.array([0.0, front_y(t) - 3 * CAR_LEN - 2 * GAP - 0.1, 0.5])
    cord = thread.Cord(n_seg=200, length=16.0, mode="ground", ground=lambda x, y: np.zeros_like(x) + 0.08, friction=0.7, substeps=6, iters=22)
    sim = cord.run(list(range(start, end)), coupler, (0.0, -1.0), warm=100)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.4)

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=10, bloom=1.0, bloom_threshold=0.62, bloom_size=0.72, streak=0.32, streak_threshold=1.05,
                         lift=(0.98, 0.99, 1.06), gain=(1.03, 0.99, 0.96), vignette=0.36, grain=0.02, ink=0.45, ink_normal=(0.45, 1.3)),
                    res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        fy = front_y(d)
        for i, c in enumerate(cars):
            sway = 0.03 * math.sin(d * 0.07 + i)
            c.location = (sway, fy - (i + 1) * CAR_LEN - i * GAP, 0.0)
            c.rotation_euler = (0, 0, 0.002 * math.sin(d * 0.05 + i * 1.3))
        beam.location = (0.0, fy + 0.2, 1.6)
        beam.scale = (7.0, 30.0, 1.0)
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
