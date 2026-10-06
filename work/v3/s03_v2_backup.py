"""Scene 3 (frames 608-953): a rowboat moves up a channel between lily pads. The rower faces the stern;
stroke period 60 frames (2.5 s), measured from the camera surge. Koi glide under the pads; the red cord
floats from the stern and follows the water."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, thread, boats, creatures
from kit.look import _n, _l, _math, _mixrgb

SCENE = 3
PPM = 92.0
SUN_DIR = (-0.45, 0.5, 0.74)
BOAT_SCREEN = (540, 1180)
STROKE = 60.0
CATCH_OFFSET = 12.0          # stroke phase 0 (catch) at local frame -12 (mod 60): boat speed peaks ~frame 10
PAINT_BOIL = 0.06


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
        fr = _math(nt, "FRACT", _math(nt, "MULTIPLY", ang, 22 / (2 * math.pi), (-650, 40)), None, (-520, 40))
        dv = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", fr, 0.5, (-400, 40)), None, (-300, 40))
        width = _math(nt, "MULTIPLY", r, 0.07, (-400, -90))
        vein = _math(nt, "LESS_THAN", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 0.5, dv, (-200, 40)), r, (-100, 40)), width, (0, 40))
        vein = _math(nt, "MULTIPLY", vein, _math(nt, "LESS_THAN", r, 0.8, (-100, -150)), (100, 0))
        hub = _math(nt, "LESS_THAN", r, 0.06, (100, -150))
        lit = _mixrgb(nt, "MULTIPLY", 1.0, ramp.outputs[0], (1.32, 1.34, 1.18, 1), (150, 300))
        c = _mixrgb(nt, "MIX", _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", vein, 0.75, (200, 0)), hub, (300, 0)), ramp.outputs[0], lit, (400, 200))
        return c
    return look.cel(name, colors[0], shadow=(0.6, 0.66, 0.66, 1), high=(1.12, 1.12, 1.02, 1), t1=0.42, t2=0.96,
                    paint=0.07 if not dark else 0.12, paint_scale=2.4, base_node=base, rough=0.5)


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
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
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
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", mr.outputs["Result"], 0.5, (-450, -50)), c, core.hexc("#3f6450"), (-300, 100))
    def water_h(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1200, -400))
        wn = _n(nt, "ShaderNodeTexNoise", (-1000, -400), noise_dimensions="4D")
        _l(nt, geo_n.outputs["Position"], wn.inputs["Vector"])
        wn.inputs["Scale"].default_value = 2.2
        wn.inputs["Detail"].default_value = 2
        d = wn.inputs["W"].driver_add("default_value").driver
        d.type = "SCRIPTED"
        d.expression = "frame / 48.0"
        return wn.outputs["Fac"]
    wmat = look.cel("pond_water", core.hexc("#264537"), shadow=(0.62, 0.7, 0.7, 1), t1=0.4, t2=0.985, paint=0.1, paint_scale=1.6,
                    base_node=water_base, height_node=water_h, bump=0.1, bump_dist=0.02, alpha=0.82, rough=0.1)
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
                if (px - x) ** 2 + (py - y) ** 2 < (0.78 * (pr + r)) ** 2:
                    ok = False
                    break
            if ok:
                pts.append((x, y, r, zbase + rng.uniform(0, 0.03)))
        return np.array(pts)
    P = place(900, 0.42, 1.75, 0.15, 0.01)
    n = len(P)
    geo.instances("pads", protos, np.c_[P[:, 0], P[:, 1], P[:, 3]], rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)],
                  scl=np.c_[P[:, 2], P[:, 2], P[:, 2] * 0.6], variant=rng.integers(0, 5, n), tint=rng.random(n), coll=env)
    D = place(900, 0.35, 1.4, -0.35, -0.05)
    m = len(D)
    geo.instances("pads_dark", dprotos, np.c_[D[:, 0], D[:, 1], np.full(m, -0.08)], rot=np.c_[np.zeros(m), np.zeros(m), rng.uniform(0, 6.28, m)],
                  scl=np.c_[D[:, 2], D[:, 2], D[:, 2] * 0.3], variant=rng.integers(0, 3, m), tint=rng.random(m), coll=env)

    # koi under the water
    kmat = look.cel("koi", core.hexc("#e6d8b2"), shadow=(0.72, 0.7, 0.62, 1), paint=0.05)
    kfin = look.cel("koi_fin", core.hexc("#efe4c6"), shadow=(0.8, 0.78, 0.7, 1), paint=0.0, alpha=0.85)
    fish = []
    for i in range(8):
        k = creatures.Koi(f"koi{i}", kmat, kfin, length=rng.uniform(1.05, 1.55), coll=ink, seed=i * 1.7)
        fish.append(dict(k=k, x0=rng.uniform(-3.5, 3.5), y0=rng.uniform(-6, 14), vy=rng.uniform(0.012, 0.04) * (1 if rng.random() < 0.7 else -1),
                         vx=rng.uniform(-0.006, 0.006), wob=rng.uniform(0.3, 1.0), ph=rng.uniform(0, 6.28), z=rng.uniform(-0.32, -0.18)))

    # boat, rower, oars
    bm_ = dict(hull=look.cel("hull", core.hexc("#b98a58"), shadow=(0.6, 0.55, 0.6, 1), paint=0.08, paint_scale=6.0),
               inner=look.cel("hull_in", core.hexc("#c49460"), shadow=(0.6, 0.55, 0.6, 1), paint=0.1, paint_scale=7.0),
               trim=look.cel("trim", core.hexc("#a0723f"), shadow=(0.58, 0.52, 0.58, 1), paint=0.05),
               seat=look.cel("seat", core.hexc("#cfa06b"), shadow=(0.6, 0.55, 0.6, 1), paint=0.08, paint_scale=8.0),
               metal=look.cel("metal", core.hexc("#55524f"), paint=0.0))
    boat, parts = boats.rowboat("boat", bm_, L=3.6, B=1.25, D=0.42, coll=ink)
    om = dict(shaft=look.cel("oar", core.hexc("#c49a63"), paint=0.04), blade=look.cel("blade", core.hexc("#b98c58"), paint=0.04),
              grip=look.cel("grip", core.hexc("#6b4a2e"), paint=0.0))
    oars = {s: boats.oar(f"oar_{s}", om, coll=ink) for s in ("l", "r")}
    for s in oars:
        oars[s][0].parent = boat
    hm = dict(top=look.cel("rower_top", core.hexc("#40418f"), shadow=(0.55, 0.55, 0.78, 1), paint=0.04),
              legs=look.cel("rower_legs", core.hexc("#2f3047"), paint=0.03), shoes=look.cel("rower_shoes", core.hexc("#2a2524"), paint=0.0),
              hands=look.cel("rower_hands", core.hexc("#d6a98f"), paint=0.0), skin=look.cel("rower_skin", core.hexc("#d6a98f"), paint=0.0),
              hair=look.cel("rower_hair", core.hexc("#2b2124"), paint=0.03))
    rower = human.Human("rower", hm, hair="short", coll=ink)
    seat_pos = np.array([0.0, 0.05, 0.36 - 0.1 + 0.02])
    lock_l = np.array(parts["oarlock_pos"][0])
    lock_r = np.array(parts["oarlock_pos"][1])

    # ripple rings at every catch
    rmat = ring_material()
    rings = [ring_mesh(f"ring{i}", rmat, env) for i in range(8)]
    def psi_of(f):
        return ((f - start + CATCH_OFFSET) / STROKE) % 1.0

    def boat_matrix(t):
        p = rig.screen_to_world(t, *BOAT_SCREEN, 0.0)
        ps = psi_of(t)
        pitch = math.radians(0.9) * math.sin(2 * math.pi * ps - 0.6)
        roll = math.radians(0.6) * math.sin(2 * math.pi * t / 97.0)
        heave = 0.012 * math.sin(2 * math.pi * ps)
        return Matrix.Translation((p[0], p[1], heave)) @ Euler((pitch, roll, 0.0)).to_matrix().to_4x4()

    # cord floating from the stern
    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    frames = list(range(start, end))
    def stern(t):
        M = boat_matrix(t)
        return np.array(M @ Vector((0, -1.79, 0.08)))
    def flow(x, y, t):
        fx = 0.05 * np.sin(y * 0.8 + t * 0.03) + 0.03 * np.sin(y * 2.1 - t * 0.05)
        fy = np.zeros_like(x)
        return fx, fy
    cord = thread.Cord(n_seg=200, length=11.0, mode="water", water_level=0.0, water_drag=5.0, flow=flow, substeps=6, iters=22, bend=0.12)
    sim = cord.run(frames, stern, (0.0, -1.0), warm=96)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.6)

    st = look.freestyle(ink, thickness=1.8, res_scale=opt.scale)
    look.compositor(dict(kuwahara=10, bloom=0.35, bloom_threshold=0.95, streak=0.08, lift=(0.98, 1.0, 1.01), gain=(1.03, 1.02, 0.97),
                         vignette=0.28, grain=0.03, ink=0.6), res_scale=opt.scale)
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
        for fi in fish:
            t = d - start
            x = fi["x0"] + fi["vx"] * t + fi["wob"] * math.sin(t * 0.012 + fi["ph"])
            y = fi["y0"] + fi["vy"] * t
            dx = fi["vx"] + fi["wob"] * 0.012 * math.cos(t * 0.012 + fi["ph"])
            hd = math.atan2(-dx, fi["vy"])
            fi["k"].body.location = (x, y, fi["z"])
            fi["k"].body.rotation_euler = (0, 0, hd)
            fi["k"].pose(t)
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
