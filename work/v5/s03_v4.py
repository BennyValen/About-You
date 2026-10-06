"""Scene 3 (frames 608-953): a rowboat moves up a channel between lily pads. The rower faces the stern;
stroke period 60 frames (2.5 s), measured from the camera surge. Koi glide under the pads; the red cord
floats from the stern and follows the water."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, boats, creatures, plants, rope_io
from kit.look import _n, _l, _math, _mixrgb

SCENE = 3
PPM = 92.0
SUN_DIR = (-0.45, 0.5, 0.74)
BOAT_SCREEN = (540, 1180)
STROKE = 60.0
CATCH_OFFSET = 12.0          # stroke phase 0 (catch) at local frame -12 (mod 60): boat speed peaks ~frame 10
POST = dict(light_deg=132.0, flow_deg=90.0, stroke_px=12.0, boil_mean=1.7, thread_shadow_px=1.5, repaint=0.5)


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def channel(y):
    xc = 0.15 * np.sin(y * 0.12) + 0.1 * np.sin(y * 0.37 + 1.0)
    hw = 2.05 + 0.35 * np.sin(y * 0.21 + 1.0) + 0.22 * np.sin(y * 0.53 + 2.0)
    return xc, hw


def pad_proto(name, mat, coll, notch_w=0.22, wobble=0.03, seed=0, n=64):
    """lily pad: a slightly cupped disc with a V notch and a rolled rim (radius 1, centred)"""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    c = bm.verts.new((0, 0, 0.0))
    ring_o, ring_i = [], []
    na = 0.0
    for i in range(n + 1):
        a = notch_w / 2 + (2 * math.pi - notch_w) * i / n
        r = 1.0 + wobble * math.sin(a * 5 + seed) + wobble * 0.5 * math.sin(a * 11 + seed * 2)
        ring_i.append(bm.verts.new((0.82 * r * math.cos(a), 0.82 * r * math.sin(a), 0.035)))
        ring_o.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0.07)))
    for i in range(n):
        bm.faces.new((c, ring_i[i], ring_i[i + 1]))
        bm.faces.new((ring_i[i], ring_o[i], ring_o[i + 1], ring_i[i + 1]))
    bm.faces.new((c, ring_i[-1], ring_i[0]))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z"))
    ob = geo.bm_to_object(bm, name, mat, coll)
    me = ob.data
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    col = np.c_[co[:, 0] * 0.5 + 0.5, co[:, 1] * 0.5 + 0.5, np.zeros(len(co)), np.ones(len(co))].astype(np.float32)
    ca = me.color_attributes.new("padxy", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", col.ravel())
    return ob


def pad_material(name, colors, dark=False):
    def base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-900, 300), attribute_type="INSTANCER", attribute_name="tint")
        ramp = _n(nt, "ShaderNodeValToRGB", (-700, 300))
        cr = ramp.color_ramp
        cr.interpolation = "CONSTANT"
        while len(cr.elements) < len(colors):
            cr.elements.new(0.5)
        for i, c in enumerate(colors):
            cr.elements[i].position = i / len(colors)
            cr.elements[i].color = c
        _l(nt, at.outputs["Fac"], ramp.inputs[0])
        if dark:
            return ramp.outputs[0]
        # radial veins from the pad centre (object coordinates of each instance)
        tc = _n(nt, "ShaderNodeAttribute", (-1100, 0), attribute_type="GEOMETRY", attribute_name="padxy")
        uvc = _n(nt, "ShaderNodeVectorMath", (-1000, 0), operation="MULTIPLY_ADD")
        _l(nt, tc.outputs["Vector"], uvc.inputs[0])
        uvc.inputs[1].default_value = (2.0, 2.0, 0.0)
        uvc.inputs[2].default_value = (-1.0, -1.0, 0.0)
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-950, 0))
        _l(nt, uvc.outputs[0], sx.inputs[0])
        ang = _math(nt, "ARCTAN2", sx.outputs[1], sx.outputs[0], (-800, 40))
        r = _math(nt, "SQRT", _math(nt, "ADD", _math(nt, "MULTIPLY", sx.outputs[0], sx.outputs[0], (-800, -60)),
                                    _math(nt, "MULTIPLY", sx.outputs[1], sx.outputs[1], (-800, -120)), (-650, -90)), None, (-520, -90))
        def veins(count, w, y):
            fr = _math(nt, "FRACT", _math(nt, "MULTIPLY", ang, count / (2 * math.pi), (-650, y)), None, (-520, y))
            dv = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", fr, 0.5, (-400, y)), None, (-300, y))
            d = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 0.5, dv, (-200, y)), r, (-100, y))
            mr = _n(nt, "ShaderNodeMapRange", (0, y), clamp=True)
            _l(nt, d, mr.inputs["Value"])
            mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = w * 1.6, w * 0.4
            return mr.outputs["Result"]
        v1 = veins(26, 0.034, 40)
        v2 = _math(nt, "MULTIPLY", veins(52, 0.018, -40), _math(nt, "GREATER_THAN", r, 0.45, (-100, -60)), (100, -40))
        vein = _math(nt, "MAXIMUM", v1, _math(nt, "MULTIPLY", v2, 0.6, (150, -40)), (200, 0))
        vein = _math(nt, "MULTIPLY", vein, _math(nt, "LESS_THAN", r, 0.86, (-100, -150)), (250, 0))
        hub = _math(nt, "LESS_THAN", r, 0.07, (100, -150))
        lit = _mixrgb(nt, "MIX", 0.6, ramp.outputs[0], (0.86, 0.95, 0.52, 1), (150, 300))
        c = _mixrgb(nt, "MIX", _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", vein, 0.9, (300, 0)), hub, (350, 0)), ramp.outputs[0], lit, (400, 200))
        # centre lighter, rim band lighter still with a darker inner edge (rolled rim), wet sheen near the centre
        shade = _n(nt, "ShaderNodeMapRange", (300, -250), clamp=True)
        _l(nt, r, shade.inputs["Value"])
        shade.inputs["From Min"].default_value, shade.inputs["From Max"].default_value = 0.1, 0.84
        shade.inputs["To Min"].default_value, shade.inputs["To Max"].default_value = 1.06, 0.88
        c = look.mul_color(nt, c, shade.outputs["Result"], (500, 150))
        rim = _n(nt, "ShaderNodeMapRange", (300, -400), clamp=True, interpolation_type="SMOOTHSTEP")
        _l(nt, r, rim.inputs["Value"])
        rim.inputs["From Min"].default_value, rim.inputs["From Max"].default_value = 0.86, 0.93
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", rim.outputs["Result"], 0.55, (450, -400)), c, (0.62, 0.78, 0.32, 1), (600, 100))
        wet = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", r, r, (300, -550)), -18.0, (400, -550)), None, (500, -550))
        c = _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", wet, 0.18, (600, -550)), c, (0.9, 0.95, 0.85, 1), (700, 50))
        return c
    return look.cel(name, colors[0], shadow=(0.6, 0.66, 0.66, 1), high=(1.12, 1.12, 1.02, 1), t1=0.42, t2=0.96,
                    paint=0.04 if not dark else 0.08, paint_scale=2.4, base_node=base, rough=0.5, soft=0.2, ao=0.55, ao_dist=0.3)


def ring_material():
    m = bpy.data.materials.new("ripple")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial", (400, 0))
    oi = _n(nt, "ShaderNodeObjectInfo", (-200, 0))
    em = _n(nt, "ShaderNodeEmission", (0, 50))
    em.inputs[0].default_value = core.hexc("#5f8670")
    tr = _n(nt, "ShaderNodeBsdfTransparent", (0, -100))
    mx = _n(nt, "ShaderNodeMixShader", (200, 0))
    _l(nt, oi.outputs["Alpha"], mx.inputs[0])
    _l(nt, tr.outputs[0], mx.inputs[1])
    _l(nt, em.outputs[0], mx.inputs[2])
    _l(nt, mx.outputs[0], out.inputs[0])
    m.surface_render_method = "BLENDED"
    return m


def ring_mesh(name, mat, coll):
    bm = bmesh.new()
    n = 48
    vi = [bm.verts.new((0.92 * math.cos(2 * math.pi * i / n), 0.92 * math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
    vo = [bm.verts.new((math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n), 0)) for i in range(n)]
    for i in range(n):
        bm.faces.new((vi[i], vo[i], vo[(i + 1) % n], vi[(i + 1) % n]))
    return geo.bm_to_object(bm, name, mat, coll, smooth=False)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#a8c4b0"), 0.34)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.82, SUN_DIR, 0.25), core.hexc("#fff6e2"), angle_deg=3.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    protos = geo.proto_collection("PAD_PROTOS")
    dprotos = geo.proto_collection("DARK_PROTOS")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.3)

    # pond: bottom, koi layer, semi-transparent surface
    bottom = geo.grid("pond_bottom", x0, y0, x1, y1, 4, 4, None, env,
                      look.cel("pond_bottom", core.hexc("#1b3328"), paint=0.18, paint_scale=0.8))
    bottom.location.z = -0.9
    def water_base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1200, 200))
        n1 = _n(nt, "ShaderNodeTexNoise", (-1000, 200))
        _l(nt, geo_n.outputs["Position"], n1.inputs["Vector"])
        n1.inputs["Scale"].default_value = 0.25
        n1.inputs["Detail"].default_value = 4
        c = _mixrgb(nt, "MIX", n1.outputs["Fac"], core.hexc("#2a4a3b"), core.hexc("#203a2f"), (-800, 200))
        mp = _n(nt, "ShaderNodeMapping", (-1000, -50))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Scale"].default_value = (0.4, 2.2, 1)
        n2 = _n(nt, "ShaderNodeTexNoise", (-800, -50))
        _l(nt, mp.outputs[0], n2.inputs["Vector"])
        n2.inputs["Scale"].default_value = 1.2
        n2.inputs["Detail"].default_value = 5
        mr = _n(nt, "ShaderNodeMapRange", (-600, -50), clamp=True)
        _l(nt, n2.outputs["Fac"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.55, 0.72
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", mr.outputs["Result"], 0.5, (-450, -50)), c, core.hexc("#3f6450"), (-300, 100))
        # soft sky reflections: large pale sheen patches drifting slowly
        sk = _n(nt, "ShaderNodeTexNoise", (-800, -300))
        _l(nt, geo_n.outputs["Position"], sk.inputs["Vector"])
        sk.inputs["Scale"].default_value = 0.09
        sk.inputs["Detail"].default_value = 2
        skm = _n(nt, "ShaderNodeMapRange", (-600, -300), clamp=True)
        _l(nt, sk.outputs["Fac"], skm.inputs["Value"])
        skm.inputs["From Min"].default_value, skm.inputs["From Max"].default_value = 0.5, 0.75
        c = _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", skm.outputs["Result"], 0.16, (-450, -300)), c, core.hexc("#a9c7c2"), (-200, 50))
        # glints: tiny bright specks where ripples catch the sun (move with the current)
        mpg = _n(nt, "ShaderNodeMapping", (-1000, -500))
        _l(nt, geo_n.outputs["Position"], mpg.inputs[0])
        dr = mpg.inputs["Location"].driver_add("default_value", 1).driver
        dr.type = "SCRIPTED"
        dr.expression = "frame * 0.004"
        gl = _n(nt, "ShaderNodeTexNoise", (-800, -500), noise_dimensions="4D")
        _l(nt, mpg.outputs[0], gl.inputs["Vector"])
        gl.inputs["Scale"].default_value = 7.0
        dg = gl.inputs["W"].driver_add("default_value").driver
        dg.type = "SCRIPTED"
        dg.expression = "floor(frame / 2) * 0.08"
        glm = _n(nt, "ShaderNodeMapRange", (-600, -500), clamp=True)
        _l(nt, gl.outputs["Fac"], glm.inputs["Value"])
        glm.inputs["From Min"].default_value, glm.inputs["From Max"].default_value = 0.74, 0.8
        c = _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", glm.outputs["Result"], 0.5, (-450, -500)), c, core.hexc("#e8f2df"), (-100, 0))
        return c
    def water_h(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1200, -400))
        mpw = _n(nt, "ShaderNodeMapping", (-1100, -400))
        _l(nt, geo_n.outputs["Position"], mpw.inputs[0])
        dw = mpw.inputs["Location"].driver_add("default_value", 1).driver
        dw.type = "SCRIPTED"
        dw.expression = "frame * 0.004"
        wn = _n(nt, "ShaderNodeTexNoise", (-1000, -400), noise_dimensions="4D")
        _l(nt, mpw.outputs[0], wn.inputs["Vector"])
        wn.inputs["Scale"].default_value = 2.2
        wn.inputs["Detail"].default_value = 2
        d = wn.inputs["W"].driver_add("default_value").driver
        d.type = "SCRIPTED"
        d.expression = "floor(frame / 2) / 24.0"
        return wn.outputs["Fac"]
    wmat = look.cel("pond_water", core.hexc("#264537"), shadow=(0.62, 0.7, 0.7, 1), t1=0.4, t2=0.985, paint=0.1, paint_scale=1.6,
                    base_node=water_base, height_node=water_h, bump=0.1, bump_dist=0.02, alpha=0.8, rough=0.1, soft=0.2, ao=0.0)
    water = geo.grid("pond_water", x0, y0, x1, y1, 4, 4, None, env, wmat)

    # lily pads (instanced): floating layer and darker submerged layer
    greens = [core.hexc(h) for h in ("#5f8f47", "#8db55e", "#a3c766", "#b8da6e", "#729b54", "#93b85f", "#6a874c")]
    pmat = pad_material("pad", greens)
    for i in range(5):
        pad_proto(f"pad_{i}", pmat, protos, notch_w=0.18 + 0.06 * i, wobble=0.02 + 0.01 * i, seed=i)
    dmat = pad_material("pad_dark", [core.hexc(h) for h in ("#22402f", "#2b4a37", "#1f3a2c")], dark=True)
    for i in range(3):
        pad_proto(f"dpad_{i}", dmat, dprotos, notch_w=0.25, wobble=0.03, seed=10 + i)
    rng = np.random.default_rng(303)
    def place(n_target, rmin, rmax, inner_margin, zbase, tries=20000):
        pts = []
        for _ in range(tries):
            if len(pts) >= n_target:
                break
            r = rmin + (rmax - rmin) * rng.random() ** 0.85
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            xc, hw = channel(y)
            if abs(x - xc) < hw + r * inner_margin:
                continue
            ok = True
            for (px, py, pr, _) in pts[-400:]:
                if (px - x) ** 2 + (py - y) ** 2 < (0.58 * (pr + r)) ** 2:
                    ok = False
                    break
            if ok:
                pts.append((x, y, r, zbase + rng.uniform(0, 0.07)))
        return np.array(pts)
    P = place(900, 0.42, 1.75, 0.15, 0.01)
    n = len(P)
    pad_rot = np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)]
    pads_obj = geo.instances("pads", protos, np.c_[P[:, 0], P[:, 1], P[:, 3]], rot=pad_rot,
                             scl=np.c_[P[:, 2], P[:, 2], np.full(n, 0.04)], variant=rng.integers(0, 5, n), tint=rng.random(n), coll=env)
    pad_ph = rng.uniform(0, 6.28, n)
    # water lilies (pink flowers with a yellow centre) and closed buds, sitting on some pads
    fprotos = geo.proto_collection("FLOWER_PROTOS")
    petal = look.cel("lily_petal", core.hexc("#f2b6c8"), shadow=(0.75, 0.62, 0.78, 1), high=(1.06, 1.04, 1.04, 1), paint=0.03, soft=0.25, ao=0.4,
                     base_node=look.instancer_palette([core.hexc("#f4bfd0"), core.hexc("#eaa2ba"), core.hexc("#f7d3de"), core.hexc("#e48fae")]))
    centre = look.cel("lily_centre", core.hexc("#f2c84b"), paint=0.0, soft=0.2)
    def lily(name, seed, rings=((10, 0.2, 0.55), (8, 0.14, 0.9)), closed=False):
        lr = np.random.default_rng(seed)
        V, F = [], []
        for nring, (np_, ln, lift) in enumerate(rings):
            for i in range(np_):
                a = 2 * math.pi * (i + 0.5 * nring) / np_ + lr.normal(0, 0.05)
                d = np.array([math.cos(a), math.sin(a), 0.0])
                sd = np.array([-math.sin(a), math.cos(a), 0.0])
                L = ln * lr.uniform(0.85, 1.1) * (0.5 if closed else 1.0)
                up = lift * (2.2 if closed else 1.0)
                base = d * 0.02
                tip = d * L + np.array([0, 0, L * up])
                mid = d * L * 0.5 + np.array([0, 0, L * up * 0.35])
                i0 = len(V)
                V += [base, mid + sd * L * 0.22, tip, mid - sd * L * 0.22]
                F.append((i0, i0 + 1, i0 + 2, i0 + 3))
        ob = geo.mesh_from_faces(name, np.array(V), F, fprotos, smooth=True, mat=petal)
        return ob
    for i in range(3):
        lily(f"lily_{i}", 30 + i)
    lily("lily_bud", 40, rings=((6, 0.12, 1.0),), closed=True)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.045)
    cen = geo.bm_to_object(bm, "lily_zc", centre, fprotos)
    cen.location.z = 0.03
    picks = rng.choice(n, 34, replace=False)
    fl_pos = np.c_[P[picks, 0] + rng.normal(0, 0.15, 34) * P[picks, 2], P[picks, 1] + rng.normal(0, 0.15, 34) * P[picks, 2], np.full(34, 0.1)]
    fl_var = np.where(np.arange(34) < 24, rng.integers(0, 3, 34), 3)
    geo.instances("lilies", fprotos, fl_pos, rot=np.c_[np.zeros(34), np.zeros(34), rng.uniform(0, 6.28, 34)],
                  scl=np.repeat(rng.uniform(0.8, 1.3, 34)[:, None], 3, 1), variant=fl_var, tint=rng.random(34), coll=env)
    geo.instances("lily_centres", fprotos, fl_pos[:24] + np.array([0, 0, 0.0]), variant=np.full(24, 4), coll=env)
    # reeds at the outer edges of the pond
    rprotos = geo.proto_collection("REED_PROTOS")
    reedm = look.cel("reed", core.hexc("#6e8c45"), shadow=(0.55, 0.62, 0.6, 1), high=(1.12, 1.1, 1.0, 1), paint=0.04, soft=0.22, ao=0.4,
                     base_node=look.instancer_palette([core.hexc("#6e8c45"), core.hexc("#86a253"), core.hexc("#5b7a3c"), core.hexc("#9bb064")]))
    for i in range(4):
        plants.grass_tuft(f"reed_{i}", reedm, rprotos, seed=60 + i, n=(10, 22), height=rng.uniform(0.8, 1.3), lean=0.25)
    rp = []
    for side in (-1, 1):
        for y in np.arange(y0, y1, 0.55):
            if rng.random() < 0.7:
                rp.append((side * rng.uniform(4.6, 5.8), y + rng.normal(0, 0.2)))
    rp = np.array(rp)
    nr = len(rp)
    geo.instances("reeds", rprotos, np.c_[rp, np.full(nr, 0.0)], rot=np.c_[np.zeros(nr), np.zeros(nr), rng.uniform(0, 6.28, nr)],
                  scl=np.repeat(rng.uniform(0.8, 1.3, nr)[:, None], 3, 1), variant=rng.integers(0, 4, nr), tint=rng.random(nr), coll=env)
    D = place(900, 0.35, 1.4, -0.35, -0.05)
    m = len(D)
    geo.instances("pads_dark", dprotos, np.c_[D[:, 0], D[:, 1], np.full(m, -0.08)], rot=np.c_[np.zeros(m), np.zeros(m), rng.uniform(0, 6.28, m)],
                  scl=np.c_[D[:, 2], D[:, 2], D[:, 2] * 0.3], variant=rng.integers(0, 3, m), tint=rng.random(m), coll=env)

    # koi under the water
    kmat = look.cel("koi", core.hexc("#e2d8b8"), shadow=(0.72, 0.7, 0.62, 1), paint=0.03, soft=0.3, alpha=0.92, ao=0.0)
    kfin = look.cel("koi_fin", core.hexc("#efe4c6"), shadow=(0.8, 0.78, 0.7, 1), paint=0.0, alpha=0.85)
    fish = []
    for i in range(8):
        k = creatures.Koi(f"koi{i}", kmat, kfin, length=rng.uniform(1.05, 1.55), coll=env, seed=i * 1.7)
        fish.append(dict(k=k, x0=rng.uniform(-3.5, 3.5), y0=rng.uniform(-6, 14), vy=rng.uniform(0.012, 0.04) * (1 if rng.random() < 0.7 else -1),
                         vx=rng.uniform(-0.006, 0.006), wob=rng.uniform(0.3, 1.0), ph=rng.uniform(0, 6.28), z=rng.uniform(-0.16, -0.08)))

    # boat, rower, oars
    bm_ = dict(hull=look.cel("hull", core.hexc("#b98a58"), shadow=(0.6, 0.55, 0.6, 1), paint=0.08, paint_scale=6.0, soft=0.22, hero=True),
               inner=look.cel("hull_in", core.hexc("#c49460"), shadow=(0.6, 0.55, 0.6, 1), paint=0.1, paint_scale=7.0, soft=0.22, hero=True),
               trim=look.cel("trim", core.hexc("#a0723f"), shadow=(0.58, 0.52, 0.58, 1), paint=0.05, soft=0.22, hero=True),
               seat=look.cel("seat", core.hexc("#cfa06b"), shadow=(0.6, 0.55, 0.6, 1), paint=0.08, paint_scale=8.0, soft=0.22, hero=True),
               metal=look.cel("metal", core.hexc("#55524f"), paint=0.0, soft=0.22, hero=True))
    boat, parts = boats.rowboat("boat", bm_, L=3.6, B=1.25, D=0.42, coll=ink)
    om = dict(shaft=look.cel("oar", core.hexc("#c49a63"), paint=0.04, soft=0.22, hero=True), blade=look.cel("blade", core.hexc("#b98c58"), paint=0.04, soft=0.22, hero=True),
              grip=look.cel("grip", core.hexc("#6b4a2e"), paint=0.0, soft=0.22, hero=True))
    oars = {s: boats.oar(f"oar_{s}", om, coll=ink) for s in ("l", "r")}
    for s in oars:
        oars[s][0].parent = boat
    hm = dict(top=look.cel("rower_top", core.hexc("#40418f"), shadow=(0.55, 0.55, 0.78, 1), paint=0.04, soft=0.22, hero=True),
              legs=look.cel("rower_legs", core.hexc("#2f3047"), paint=0.03, soft=0.22, hero=True), shoes=look.cel("rower_shoes", core.hexc("#2a2524"), paint=0.0, soft=0.22, hero=True),
              hands=look.cel("rower_hands", core.hexc("#d6a98f"), paint=0.0, soft=0.22, hero=True), skin=look.cel("rower_skin", core.hexc("#d6a98f"), paint=0.0, soft=0.22, hero=True),
              hair=look.cel("rower_hair", core.hexc("#2b2124"), paint=0.03, soft=0.22, hero=True))
    rower = human.Human("rower", hm, hair="short", coll=ink)
    seat_pos = np.array([0.0, 0.05, 0.36 - 0.1 + 0.02])
    lock_l = np.array(parts["oarlock_pos"][0])
    lock_r = np.array(parts["oarlock_pos"][1])

    # ripple rings at every catch
    rmat = ring_material()
    rings = [ring_mesh(f"ring{i}", rmat, env) for i in range(8)]
    # swirl puddles left by each blade at the release: a darker eddy with a light rim, drifting back, fading
    pmat_ = look.cel("puddle", core.hexc("#1c3529"), paint=0.0, soft=0.3, alpha=0.6, ao=0.0)
    pgrp = [x for x in pmat_.node_tree.nodes if x.type == "GROUP"][0]
    oi_ = _n(pmat_.node_tree, "ShaderNodeObjectInfo", (-300, -300))
    _l(pmat_.node_tree, oi_.outputs["Alpha"], pgrp.inputs["Alpha"])
    puddles = []
    for i in range(6):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=1.0)
        puddles.append(geo.bm_to_object(bm, f"puddle{i}", pmat_, env))
        rim_ = ring_mesh(f"puddle_rim{i}", rmat, env)
        rim_.parent = puddles[-1]
    def psi_of(f):
        return ((f - start + CATCH_OFFSET) / STROKE) % 1.0

    mot = rope_io.C.owner_motion(SCENE)
    def boat_matrix(t):
        tt = min(max(t, start), end)
        p = rig.screen_to_world(tt, *BOAT_SCREEN, 0.0)
        p = Vector((p[0] + mot(t)[0], p[1] + (min(t - start, 0) + max(t - end, 0)) * 2.3 / PPM, 0.0))
        ps = psi_of(t)
        pitch = math.radians(0.9) * math.sin(2 * math.pi * ps - 0.6)
        roll = math.radians(0.6) * math.sin(2 * math.pi * t / 97.0)
        heave = 0.012 * math.sin(2 * math.pi * ps)
        yaw = -0.3 * (mot(t + 1)[0] - mot(t - 1)[0]) * PPM / 2.3
        return Matrix.Translation((p[0], p[1], heave)) @ Euler((pitch, roll, yaw)).to_matrix().to_4x4()

    # cord floating from the stern
    # V-wake: closed-form foam particles from the bow shoulders and the stern
    def hull_frame(t):
        M = boat_matrix(t)
        o = M @ Vector((0, 0, 0))
        sp = speed_profile()(int(min(max(t - start, 0), end - start))) / PPM
        return (o.x, o.y), (0.0, 1.0), (1.0, 0.0), sp
    wake = geo.Wake(hull_frame, start - 60, end + 2, rate=4, life=80.0, spread=0.5, decay=0.04, seed=33,
                    emit_points=((-0.42, 0.9, -1), (0.42, 0.9, 1), (-0.35, -1.65, -1), (0.35, -1.65, 1)), jitter=0.03)
    foam = look.cel("foam", core.hexc("#e5efe2"), paint=0.0, soft=0.3, alpha=0.75, ao=0.0)
    fgrp = [x for x in foam.node_tree.nodes if x.type == "GROUP"][0]
    fat = _n(foam.node_tree, "ShaderNodeAttribute", (-300, -300), attribute_type="INSTANCER", attribute_name="tint")
    _l(foam.node_tree, fat.outputs["Fac"], fgrp.inputs["Alpha"])
    wproto = geo.proto_collection("P_foam")
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=10, radius=0.03)
    geo.bm_to_object(bm, "foam_dot", foam, wproto)
    NW = 700
    foam_obj = geo.instances("foam", wproto, np.tile([0.0, -1e4, -50.0], (NW, 1)), tint=np.zeros(NW), coll=env)
    frames = list(range(start, end, 2))
    def stern(t):
        M = boat_matrix(t)
        return np.array(M @ Vector((0, -1.79, 0.08)))
    rope = rope_io.Owner("A", SCENE, rig, stern, frames, trail=(0.0, -1.0), warm=150, cfg_motion=False,
                         heading_fn=lambda t: boat_matrix(t).to_euler().z)

    st = look.freestyle(ink, thickness=1.8, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.98, 1.0, 1.01), gain=(1.03, 1.02, 0.97),
                         vignette=0.26, ink=0.4), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        boat.matrix_world = boat_matrix(d)
        ps = psi_of(d)
        Jb, info = boats.row_pose(ps, seat_pos, lock_l, lock_r)
        Mb = np.array(boat.matrix_world)
        Jw = {k: (Mb @ np.r_[v, 1.0])[:3] for k, v in Jb.items()}
        rower.set_world(Jw, math.pi + math.atan2(Mb[1, 0], Mb[0, 0]) * 0)
        for s in ("l", "r"):
            boats.place_oar(oars[s][0], lock_l if s == "l" else lock_r, info[s], s)
        # ripples: rings spawned at the blades at each catch (and release)
        k = 0
        for back in range(3):
            cf = math.floor((d - start + CATCH_OFFSET) / STROKE) - back
            tc = start - CATCH_OFFSET + cf * STROKE
            age = d - tc
            if age < 0 or age > 70:
                continue
            Mc = boat_matrix(tc)
            _, inf_c = boats.row_pose(0.02, seat_pos, lock_l, lock_r)
            for s in ("l", "r"):
                if k >= len(rings):
                    break
                bp = Mc @ Vector(inf_c[s]["blade"].tolist())
                rr = 0.12 + age * 0.011
                rings[k].location = (bp.x, bp.y, 0.012)
                rings[k].scale = (rr, rr, 1)
                rings[k].color = (1, 1, 1, max(0.0, 0.32 * (1 - age / 70.0)))
                rings[k].hide_render = False
                k += 1
        for j in range(k, len(rings)):
            rings[j].hide_render = True
        # pads near the boat are pushed aside by the bow wave and bob in the wake, then drift back
        bo = boat.matrix_world.translation
        dy = P[:, 1] - bo.y
        dx = P[:, 0] - bo.x
        env_ = np.exp(-np.maximum(dy - 1.2, 0) ** 2 / 0.6) * np.exp(-np.maximum(-dy - 1.0, 0) / 3.5) * (dy > -12)
        prox = np.exp(-np.maximum(np.abs(dx) - 0.9 - P[:, 2], 0) / 0.5)
        push = 0.28 * env_ * prox
        pos = np.c_[P[:, 0] + np.sign(dx) * push, P[:, 1] - 0.05 * push, P[:, 3] + 0.012 * env_ * prox * np.sin(d * 0.35 + pad_ph)]
        rot = pad_rot.copy()
        rot[:, 0] = 0.03 * env_ * prox * np.sin(d * 0.3 + pad_ph)
        rot[:, 1] = 0.03 * env_ * prox * np.cos(d * 0.27 + pad_ph)
        geo.update_points(pads_obj, pos, rot=rot)
        # swirl puddles at the last releases
        k2 = 0
        for back in range(3):
            cf = math.floor((d - start + CATCH_OFFSET - 0.42 * STROKE) / STROKE) - back
            tr_ = start - CATCH_OFFSET + 0.42 * STROKE + cf * STROKE
            age = d - tr_
            if age < 0 or age > 72:
                continue
            Mr = boat_matrix(tr_)
            _, inf_r = boats.row_pose(0.42, seat_pos, lock_l, lock_r)
            for s_ in ("l", "r"):
                if k2 >= len(puddles):
                    break
                bp = Mr @ Vector(inf_r[s_]["blade"].tolist())
                pr_ = 0.14 + age * 0.004
                puddles[k2].location = (bp.x, bp.y - age * 0.004, 0.011)
                puddles[k2].scale = (pr_, pr_ * 0.85, 1)
                puddles[k2].rotation_euler = (0, 0, age * 0.04 * (1 if s_ == "r" else -1))
                puddles[k2].color = (1, 1, 1, max(0.0, 0.45 * (1 - age / 72.0)))
                for ch in puddles[k2].children:
                    ch.color = (1, 1, 1, max(0.0, 0.5 * (1 - age / 72.0)))
                puddles[k2].hide_render = False
                k2 += 1
        for j in range(k2, len(puddles)):
            puddles[j].hide_render = True
        W_ = wake.at(d, NW)
        alive = W_[:, 2] > 0
        fp = np.c_[W_[:, 0], W_[:, 1], np.full(NW, 0.012)]
        fp[~alive] = (0.0, -1e4, -50.0)
        fs = np.repeat(np.maximum(W_[:, 2], 0.01)[:, None], 3, 1) * np.array([1.6, 1.0, 1.0])
        me = foam_obj.data
        me.vertices.foreach_set("co", fp.astype(np.float32).ravel())
        me.attributes["scl"].data.foreach_set("vector", fs.astype(np.float32).ravel())
        me.attributes["rot"].data.foreach_set("vector", np.c_[np.zeros(NW), np.zeros(NW), W_[:, 3]].astype(np.float32).ravel())
        me.attributes["tint"].data.foreach_set("value", (0.38 * (1 - W_[:, 4]) ** 1.5 * alive).astype(np.float32))
        me.update()
        for fi in fish:
            t = d - start
            x = fi["x0"] + fi["vx"] * t + fi["wob"] * math.sin(t * 0.012 + fi["ph"])
            y = fi["y0"] + fi["vy"] * t
            dx = fi["vx"] + fi["wob"] * 0.012 * math.cos(t * 0.012 + fi["ph"])
            hd = math.atan2(-dx, fi["vy"])
            fi["k"].body.location = (x, y, fi["z"])
            fi["k"].body.rotation_euler = (0, 0, hd)
            fi["k"].pose(t)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])
    return r
