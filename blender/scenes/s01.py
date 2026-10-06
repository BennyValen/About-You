"""Scene 1 (frames 0-293): night, snowy pine forest from straight above. A dark three-car train runs up a
cleared corridor; its windows throw warm light onto the snow (real area lights, shadowed by the trees) and
its headlight scatters in the night mist (volumetric spot). Fog banks drift; a frozen pond enters top-left.
The red cord trails from the last car's coupler along the track bed."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, vehicles, rope_io
from kit.look import _n, _l, _math, _mixrgb

SCENE = 1
PPM = 30.0
MOON_DIR = (-0.55, 0.45, 0.7)
FRONT_SCREEN_Y = 990
PLUME_SX, PLUME_LEN = 2.6, 700.0 / 30.0        # plume plane half-width and length (m)
CAR_LEN, GAP = 3.0, 0.3            # v4: seven short carriages (~690 px train, as in the source)
N_CARS = 7
POST = dict(light_deg=140.0, flow_deg=90.0, stroke_px=12.0, boil_mean=1.8, thread_shadow_px=1.4, thread_glow=0.25, repaint=0.5, grain=1.2)
WIN_X = 0.95                         # window strips (m from the track axis)
CORRIDOR_PX = 101.0                  # no crown within 100 px of the window strips
CROWN_R = 3.95 * 1.15                # crown radius of a scale-1 spruce (longest blade), m


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
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.24, 1.3
        snow = mr.outputs["Result"]
        needles = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#1E253E"), core.hexc("#3B4160"), (-500, 0))
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", snow, 0.7, (-350, 300)), needles, core.hexc("#8F96BA"), (-300, 100))
        # frost speckles: small bright flecks along the blades (fine noise, thresholded), more towards the tips
        fz = _n(nt, "ShaderNodeTexNoise", (-800, -250))
        _l(nt, geo_n.outputs["Position"], fz.inputs["Vector"])
        fz.inputs["Scale"].default_value = 9.0
        fz.inputs["Detail"].default_value = 2
        fr = _n(nt, "ShaderNodeMapRange", (-600, -250), clamp=True)
        _l(nt, fz.outputs["Fac"], fr.inputs["Value"])
        fr.inputs["From Min"].default_value, fr.inputs["From Max"].default_value = 0.61, 0.65
        fk = _math(nt, "MULTIPLY", fr.outputs["Result"], _math(nt, "POWER", at.outputs["Fac"], 1.5, (-500, -350)), (-400, -300), clamp=True)
        return _mixrgb(nt, "MIX", fk, c, core.hexc("#D4D8EC"), (-200, 0))
    return look.cel("spruce", core.hexc("#2B324F"), shadow=(0.6, 0.62, 0.78, 1), high=(1.3, 1.3, 1.36, 1), t1=0.35, t2=0.9,
                    paint=0.04, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0, soft=0.35, ao=0.45, ao_dist=1.5,
                    rim=0.45)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#c4c8dc"), 0.21)
    core.sun(MOON_DIR, core.sun_irradiance_for(0.66, MOON_DIR, 0.28), core.hexc("#d8dcf0"), angle_deg=1.5)       # moon, upper left
    # thin volumetric slab near the ground for the headlight beam and lit mist
    beam_m = bpy.data.materials.new("beam")
    beam_m.use_nodes = True
    bnt = beam_m.node_tree
    bnt.nodes.clear()
    bout = _n(bnt, "ShaderNodeOutputMaterial", (600, 0))
    btc = _n(bnt, "ShaderNodeTexCoord", (-900, 0))
    bsx = _n(bnt, "ShaderNodeSeparateXYZ", (-700, 0))
    _l(bnt, btc.outputs["UV"], bsx.inputs[0])
    # plane: x in [-1, 1] * PLUME_SX m, y in [0, 1] * PLUME_LEN m; UV x 0..1 across, y 0..1 along (from the chimney)
    lat = _math(bnt, "ABSOLUTE", _math(bnt, "SUBTRACT", bsx.outputs[0], 0.5, (-550, 100)), None, (-450, 100))
    halfw = _math(bnt, "ADD", _math(bnt, "MULTIPLY", bsx.outputs[1], 52.5 / PPM / (2 * PLUME_SX), (-550, 200)),
                  17.5 / PPM / (2 * PLUME_SX), (-450, 200))
    q = _math(bnt, "DIVIDE", lat, halfw, (-350, 150))                     # 0 on the axis, 1 at the plume edge
    prof = _math(bnt, "ADD", 0.15, _math(bnt, "MULTIPLY", 0.35, _math(bnt, "SUBTRACT", 1.0, _math(bnt, "POWER", q, 2.0, (-250, 250)),
                                                                     (-150, 250)), (-50, 250)), (50, 250))
    edge = _math(bnt, "SUBTRACT", 1.0, _math(bnt, "MULTIPLY", _math(bnt, "SUBTRACT", q, 0.85, (-250, 120)), 1.0 / 0.25, (-150, 120)),
                 (-50, 120), clamp=True)                                   # soft fade just past the edge
    fin = _math(bnt, "MULTIPLY", _math(bnt, "MINIMUM", _math(bnt, "MULTIPLY", bsx.outputs[1], 20.0, (-350, 0)), 1.0, (-250, 0)),
                _math(bnt, "MINIMUM", _math(bnt, "MULTIPLY", _math(bnt, "SUBTRACT", 1.0, bsx.outputs[1], (-450, -50)), 5.0, (-350, -50)),
                      1.0, (-250, -50)), (-150, 0))
    # streaks along the track, drifting backwards (the train runs into still air)
    bgeo = _n(bnt, "ShaderNodeNewGeometry", (-900, -250))
    bmp = _n(bnt, "ShaderNodeMapping", (-700, -250))
    _l(bnt, bgeo.outputs["Position"], bmp.inputs[0])
    bmp.inputs["Scale"].default_value = (2.6, 0.12, 1.0)
    bnz = _n(bnt, "ShaderNodeTexNoise", (-550, -200), noise_dimensions="4D")
    _l(bnt, bmp.outputs[0], bnz.inputs["Vector"])
    bnz.inputs["Scale"].default_value = 2.0
    bnz.inputs["Detail"].default_value = 6
    bdr = bnz.inputs["W"].driver_add("default_value").driver
    bdr.type = "SCRIPTED"
    bdr.expression = "floor(frame / 2) * 0.03"
    streak = _math(bnt, "ADD", 0.55, _math(bnt, "MULTIPLY", bnz.outputs["Fac"], 0.75, (-350, -200)), (-200, -200))
    ba = _math(bnt, "MINIMUM", _math(bnt, "MULTIPLY", _math(bnt, "MULTIPLY", _math(bnt, "MULTIPLY", prof, edge, (150, 200)), fin, (200, 100)),
                                     streak, (250, 50)), 0.48, (300, 0), clamp=True)
    bem = _n(bnt, "ShaderNodeEmission", (300, 100))
    bem.inputs[0].default_value = core.hexc("#C9CFE6")
    bem.inputs[1].default_value = 0.78
    btr = _n(bnt, "ShaderNodeBsdfTransparent", (300, -100))
    bmx = _n(bnt, "ShaderNodeMixShader", (450, 0))
    _l(bnt, ba, bmx.inputs[0])
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
        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#495175"), core.hexc("#656C90"), (-600, 200))
        sz = _n(nt, "ShaderNodeSeparateXYZ", (-1000, -100))
        _l(nt, geo_n.outputs["Position"], sz.inputs[0])
        pondm = _n(nt, "ShaderNodeMapRange", (-800, -100), clamp=True)
        _l(nt, sz.outputs[2], pondm.inputs["Value"])
        pondm.inputs["From Min"].default_value, pondm.inputs["From Max"].default_value = -0.05, -0.12
        ice = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#3B4160"), core.hexc("#565E84"), (-600, -100))
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
             look.cel("snow", core.hexc("#565E84"), shadow=(0.55, 0.57, 0.76, 1), high=(1.2, 1.2, 1.24, 1), t1=0.36, t2=0.92,
                      paint=0.2, paint_scale=0.6, base_node=snow_base, rough=0.9, light_tint=1.0))
    tproto = geo.proto_collection("TREE_PROTOS")
    tm = tree_material()
    for i in range(5):
        conifer(f"spruce_{i}", tm, tproto, seed=10 + i)
    rng = np.random.default_rng(101)
    CORRIDOR_LOG = {}
    clear_m = WIN_X + CORRIDOR_PX / PPM            # crowns must stay outside |x| >= clear_m
    pts = geo.poisson(rng, 6000, x0, y0, x1, y1, 2.7 / math.sqrt(0.7),
                      accept=lambda x, y: abs(x) - 0.42 * CROWN_R >= clear_m and pond_sdf(x, y) > 1.5)
    n = len(pts)
    # two canopy layers: tall spruces and a lower understorey between them; near the corridor only trees small
    # enough to keep the clearance grow (the edge of a cut line)
    s = np.where(rng.random(n) < 0.6, rng.uniform(0.75, 1.0, n), rng.uniform(0.42, 0.6, n))
    s = np.minimum(s, (np.abs(pts[:, 0]) - clear_m) / CROWN_R)
    CORRIDOR_LOG.update(trees=int(n), min_clear_px=float(((np.abs(pts[:, 0]) - s * CROWN_R) - WIN_X).min() * PPM),
                        density_per_100m2=float(n / ((x1 - x0) * (y1 - y0)) * 100))
    geo.instances("forest", tproto, np.c_[pts, np.zeros(n)], rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)],
                  scl=np.c_[s, s, s], variant=rng.integers(0, 5, n), coll=env)
    # train
    tmats = dict(body=look.cel("car", core.hexc("#2a2c3c"), shadow=(0.6, 0.6, 0.75, 1), high=(1.5, 1.5, 1.6, 1), paint=0.03, soft=0.22,
                               rim=0.45, hero=True),
                 window=look.emissive("window", core.hexc("#E8A24A"), 0.85, hero=True),
                 roof=look.cel("fan", core.hexc("#3c3f58"), paint=0.0, soft=0.2, rim=0.4, hero=True),
                 under=look.cel("bogie", core.hexc("#15161f"), paint=0.0, hero=True))
    cars = []
    for i in range(N_CARS):
        root, parts = vehicles.train_car(f"car{i}", tmats, ink, length=CAR_LEN, width=1.9, height=2.3, nose=(i == 0), fans=2, windows=True)
        cars.append(root)
        # warm window light spilling sideways onto the snow and the crowns (soft falloff, shadowed by the trees)
        for side in (-1, 1):
            li = bpy.data.lights.new(f"win{i}{side}", "AREA")
            li.shape = "RECTANGLE"
            li.size, li.size_y = CAR_LEN * 1.05, 1.2
            li.energy = 55.0
            li.color = (1.0, 0.55, 0.2)
            li.use_shadow = False
            lo = bpy.data.objects.new(f"winlight{i}{side}", li)
            env.objects.link(lo)
            lo.parent = root
            lo.location = (side * 1.45, CAR_LEN / 2, 2.1)
            zl = -Vector((side * 0.6, 0.0, -1.0)).normalized()        # down and outwards: a broad pool, smooth falloff
            xl = Vector((0.0, 1.0, 0.0))
            yl = zl.cross(xl)
            lo.matrix_basis = Matrix.Translation(lo.location) @ Matrix((xl, yl, zl)).transposed().to_4x4()
    # warm window light on the snow: a soft pool beside the train, bright at the window strips (#E8A24A) and fading
    # smoothly to the dusk tan (#A57861) and out over ~200 px; never clipped. (The area lights above add the faint warm
    # gradient on the nearest crowns; no tree shadows, so no spikes.)
    glow_m = bpy.data.materials.new("window_glow")
    glow_m.use_nodes = True
    gnt = glow_m.node_tree
    gnt.nodes.clear()
    gout = _n(gnt, "ShaderNodeOutputMaterial", (700, 0))
    gtc = _n(gnt, "ShaderNodeTexCoord", (-900, 0))
    gsx = _n(gnt, "ShaderNodeSeparateXYZ", (-700, 0))
    _l(gnt, gtc.outputs["Object"], gsx.inputs[0])
    dpx = _math(gnt, "MAXIMUM", _math(gnt, "MULTIPLY", _math(gnt, "SUBTRACT", _math(gnt, "ABSOLUTE", gsx.outputs[0], None, (-550, 100)),
                                                              WIN_X + 0.02, (-450, 100)), PPM, (-350, 100)), 0.0, (-250, 100))
    u = _math(gnt, "MINIMUM", _math(gnt, "DIVIDE", dpx, 200.0, (-150, 100)), 1.0, (-50, 100))
    fall = _math(gnt, "POWER", _math(gnt, "SUBTRACT", 1.0, u, (50, 100)), 2.2, (150, 100))
    # along the train: full over the cars, soft 50 px ends; slightly darker between cars
    tl = N_CARS * CAR_LEN + (N_CARS - 1) * GAP
    yin = _math(gnt, "MINIMUM", _math(gnt, "MULTIPLY", _math(gnt, "ADD", gsx.outputs[1], tl, (-550, -100)), PPM / 50.0, (-450, -100)), 1.0, (-350, -100), clamp=True)
    yout = _math(gnt, "MINIMUM", _math(gnt, "MULTIPLY", _math(gnt, "SUBTRACT", 0.0, gsx.outputs[1], (-550, -200)), PPM / 50.0, (-450, -200)), 1.0, (-350, -200), clamp=True)
    cyc = _math(gnt, "ADD", 0.86, _math(gnt, "MULTIPLY", 0.14, _math(gnt, "COSINE", _math(gnt, "MULTIPLY", gsx.outputs[1], 2 * math.pi / (CAR_LEN + GAP),
                                                                                         (-550, -300)), None, (-450, -300)), (-350, -300)), (-250, -300))
    ga = _math(gnt, "MULTIPLY", _math(gnt, "MULTIPLY", _math(gnt, "MULTIPLY", fall, yin, (250, 0)), yout, (350, 0)), cyc, (450, 0))
    ga = _math(gnt, "MULTIPLY", ga, 0.62, (520, 0))
    ga = _math(gnt, "MULTIPLY", ga, _math(gnt, "GREATER_THAN", _math(gnt, "ABSOLUTE", gsx.outputs[0], None, (400, -200)), WIN_X + 0.02,
                                          (500, -200)), (600, -100))       # nothing between the cars
    gem = _n(gnt, "ShaderNodeEmission", (450, 200))
    _l(gnt, _mixrgb(gnt, "MIX", _math(gnt, "POWER", u, 0.6, (150, 300)), core.hexc("#E8A24A"), core.hexc("#A57861"), (300, 300)), gem.inputs[0])
    gem.inputs[1].default_value = 1.0
    gtr = _n(gnt, "ShaderNodeBsdfTransparent", (450, -150))
    gmx = _n(gnt, "ShaderNodeMixShader", (600, 0))
    _l(gnt, ga, gmx.inputs[0])
    _l(gnt, gtr.outputs[0], gmx.inputs[1])
    _l(gnt, gem.outputs[0], gmx.inputs[2])
    _l(gnt, gmx.outputs[0], gout.inputs[0])
    glow_m.surface_render_method = "BLENDED"
    glow = geo.grid("window_glow", -9.0, -tl - 3.0, 9.0, 3.0, 2, 2, None, env, glow_m)
    glow.visible_shadow = False
    head = bpy.data.lights.new("headlight", "SPOT")
    head.energy = 2600.0
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
    for i, (z, dens) in enumerate(((8.0, 0.26), (16.0, 0.2))):
        fp = geo.grid(f"fog{i}", x0 - 30, y0 - 30, x1 + 30, y1 + 30, 4, 4, None, env, fog_mat(f"fog{i}", i * 0.6, dens))
        fp.location.z = z
        fp.visible_shadow = False

    def front_y(t):
        return rig.screen_to_world(max(t, start), 540, FRONT_SCREEN_Y, 0.0)[1] + (min(t - start, 0)) * 6.26 / PPM
    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.85, 0.75, 0.85, 1), t1=0.1, t2=1.5, paint=0.0, glow=0.5, rough=0.5)
    def coupler(t):
        return np.array([0.0, front_y(t) - N_CARS * CAR_LEN - (N_CARS - 1) * GAP - 0.1, 0.5])
    rope = rope_io.Owner("A", SCENE, rig, coupler, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150,
                         heading_fn=lambda t: 0.002 * math.sin((t - t % 2) * 0.05 + (N_CARS - 1) * 1.3),     # last car's yaw
                         ground_fn=lambda x, y: np.full_like(np.asarray(x, float), 0.12))
    # steam plume: puffs leave the locomotive, rise, billow and drift with the wind over the forest; lit by the train
    puff_m = look.cel("steam", core.hexc("#dfe3f4"), shadow=(0.55, 0.58, 0.8, 1), high=(1.05, 1.05, 1.05, 1), paint=0.03, soft=0.4, alpha=0.6,
                      ao=0.0, light_tint=1.0)
    pg = [x for x in puff_m.node_tree.nodes if x.type == "GROUP"][0]
    pat = _n(puff_m.node_tree, "ShaderNodeAttribute", (-400, -300), attribute_type="INSTANCER", attribute_name="tint")
    plw = _n(puff_m.node_tree, "ShaderNodeLayerWeight", (-400, -450))
    plw.inputs["Blend"].default_value = 0.5
    soft_edge = _math(puff_m.node_tree, "POWER", _math(puff_m.node_tree, "SUBTRACT", 1.0, plw.outputs["Facing"], (-250, -450)), 1.6, (-150, -450))
    _l(puff_m.node_tree, _math(puff_m.node_tree, "MULTIPLY", pat.outputs["Fac"], soft_edge, (-50, -350)), pg.inputs["Alpha"])
    pprot = geo.proto_collection("P_steam")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for v in bm.verts:
        v.co *= 1.0 + 0.12 * math.sin(v.co.x * 5 + v.co.y * 3)
    geo.bm_to_object(bm, "puff", puff_m, pprot, smooth=True)
    NP = 1
    puff_t = np.linspace(start - 140, end, NP)
    prng = np.random.default_rng(111)
    puff_j = prng.normal(0, 1, (NP, 3))
    puff_obj = geo.instances("steam", pprot, np.tile([0.0, -1e4, -50.0], (NP, 1)), tint=np.zeros(NP), coll=env)

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=1.0, bloom_size=0.7, streak=0.0, streak_threshold=1.5,
                         lift=(0.98, 0.99, 1.06), gain=(1.03, 0.99, 0.96), vignette=0.34, ink=0.35, ink_normal=(0.45, 1.3)),
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
        beam.location = (0.0, fy + 0.1, 2.6)
        glow.location = (0.0, fy, 0.42)
        beam.scale = (PLUME_SX, PLUME_LEN, 1.0)
        # steam: emitted at the chimney position of the locomotive at time te, then left behind in world space,
        # rising and drifting with a crosswind, growing and fading
        age = (d - puff_t) / 24.0
        alive = (age >= 0) & (age < 5.0) & False
        P = np.tile([0.0, -1e4, -50.0], (NP, 1))
        S = np.full((NP, 3), 0.01)
        T = np.zeros(NP)
        for k in np.nonzero(alive)[0]:
            a_ = age[k]
            ey = front_y(puff_t[k]) - 1.2
            P[k] = (1.6 * a_ + 0.5 * puff_j[k, 0] * a_, ey + 0.8 * a_ + 0.4 * puff_j[k, 1] * a_, 12.5 + 1.2 * a_ + 0.3 * puff_j[k, 2])
            r_ = 0.6 + 0.8 * a_ ** 0.8
            S[k] = (r_, r_ * 0.9, r_ * 0.5)
            T[k] = 0.3 * min(1.0, a_ / 0.3) * (1 - a_ / 5.0) ** 1.5
        me = puff_obj.data
        me.vertices.foreach_set("co", P.astype(np.float32).ravel())
        me.attributes["scl"].data.foreach_set("vector", S.astype(np.float32).ravel())
        me.attributes["tint"].data.foreach_set("value", T.astype(np.float32))
        me.update()
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    def finish(out):
        rope_io.export(out, [rope])
        CORRIDOR_LOG.update(window_x_px=WIN_X * PPM, required_px=100.0, pass_=CORRIDOR_LOG["min_clear_px"] >= 100.0)
        json.dump(CORRIDOR_LOG, open(os.path.join(out, "corridor.json"), "w"), indent=1)
    r.finish = finish
    return r
