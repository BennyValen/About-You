"""Scene 6 (frames 1674-2077): a heeled sailing dinghy crosses a clear turquoise lagoon. Sandy shallows,
winding deep channels, crusty coral heads, starfish, turtles; a manta glides up-left of the boat. The boat
and sail shadows fall on the seabed; a foam wake trails the stern and the red cord floats in it."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, thread, boats, creatures
from kit.look import _n, _l, _math, _mixrgb

SCENE = 6
PPM = 90.0
SUN_DIR = (-0.42, 0.42, 0.8)
BOAT_SCREEN = (555, 1180)
PAINT_BOIL = 0.45

# channels and large coral clusters, from the reference mosaic (world metres)
CHANNELS = [([(-9.0, 17.5), (-6.0, 18.6), (-3.33, 19.7), (-1.11, 21.7), (1.55, 23.3), (6.0, 24.8), (9.0, 25.4)], 0.95),
            ([(-9.0, 6.6), (-6.0, 6.17), (-2.89, 5.86), (0.22, 4.17), (2.89, 1.51), (6.0, -1.6), (9.0, -4.2)], 1.15)]
CORALS = [(-4.2, 11.7, 2.0), (4.66, 6.84, 1.55), (-4.2, 4.6, 1.8), (4.2, 3.3, 1.8), (2.44, -1.15, 1.8), (-2.9, -4.3, 2.2),
          (2.44, -5.6, 2.0), (-4.6, 19.0, 1.4), (4.5, 16.5, 1.2), (-5.0, -9.0, 1.6), (3.6, -11.0, 1.7), (-1.2, 26.5, 1.2)]


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def _seg_dist(px, py, pts):
    d = np.full_like(px, 1e9)
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        vx, vy = bx - ax, by - ay
        t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy), 0, 1)
        d = np.minimum(d, np.hypot(px - ax - t * vx, py - ay - t * vy))
    return d


def depth(x, y):
    """seabed depth below the surface (m, positive down)"""
    x, y = np.asarray(x, float), np.asarray(y, float)
    d = 0.35 + 0.12 * geo.fbm2(x * 0.3, y * 0.3, 3, 61)
    for pts, w in CHANNELS:
        dist = _seg_dist(x + 0.5 * geo.fbm2(x * 0.4, y * 0.4, 2, 5), y, pts)
        wide = w * (1 + 0.25 * geo.fbm2(x * 0.2, y * 0.2, 2, 9))
        t = np.clip(1 - dist / (wide * 2.3), 0, 1)
        d = d + 2.6 * (t * t * (3 - 2 * t))
    return d


def seabed_material():
    def base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1800, 200))
        sz = _n(nt, "ShaderNodeSeparateXYZ", (-1600, 200))
        _l(nt, geo_n.outputs["Position"], sz.inputs[0])
        dep = _math(nt, "MULTIPLY", sz.outputs[2], -1.0, (-1450, 200))
        ramp = _n(nt, "ShaderNodeValToRGB", (-1300, 200))
        cr = ramp.color_ramp
        cr.interpolation = "EASE"
        for pos, col in ((0.0, "#e2f7f1"), (0.1, "#c4eee8"), (0.22, "#7fd0d2"), (0.4, "#3aa8be"), (0.65, "#2595ae"), (1.0, "#1d7f9e")):
            e = cr.elements.new(pos) if pos not in (0.0, 1.0) else cr.elements[0 if pos == 0.0 else -1]
            e.position = pos
            e.color = core.hexc(col)
        mr = _n(nt, "ShaderNodeMapRange", (-1450, 50), clamp=True)
        _l(nt, dep, mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.3, 2.9
        _l(nt, mr.outputs["Result"], ramp.inputs[0])
        c = ramp.outputs[0]
        # painterly white strokes on the sand (stronger in the shallows)
        mp = _n(nt, "ShaderNodeMapping", (-1450, -150))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, 0.7)
        mp.inputs["Scale"].default_value = (0.5, 3.0, 1)
        sn = _n(nt, "ShaderNodeTexNoise", (-1250, -150))
        _l(nt, mp.outputs[0], sn.inputs["Vector"])
        sn.inputs["Scale"].default_value = 1.4
        sn.inputs["Detail"].default_value = 6
        sn.inputs["Distortion"].default_value = 1.2
        sm = _n(nt, "ShaderNodeMapRange", (-1050, -150), clamp=True)
        _l(nt, sn.outputs["Fac"], sm.inputs["Value"])
        sm.inputs["From Min"].default_value, sm.inputs["From Max"].default_value = 0.56, 0.7
        shallow = _math(nt, "SUBTRACT", 1.0, mr.outputs["Result"], (-1050, 0))
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", sm.outputs["Result"], _math(nt, "MULTIPLY", shallow, 0.7, (-900, 0)), (-800, -100)),
                    c, core.hexc("#f6fdfb"), (-700, 100))
        # animated caustics: warped voronoi edges
        vo = _n(nt, "ShaderNodeTexVoronoi", (-1250, -400), voronoi_dimensions="4D", feature="DISTANCE_TO_EDGE")
        _l(nt, geo_n.outputs["Position"], vo.inputs["Vector"])
        vo.inputs["Scale"].default_value = 1.7
        d = vo.inputs["W"].driver_add("default_value").driver
        d.type = "SCRIPTED"
        d.expression = "frame / 70.0"
        cm = _n(nt, "ShaderNodeMapRange", (-1050, -400), clamp=True)
        _l(nt, vo.outputs["Distance"], cm.inputs["Value"])
        cm.inputs["From Min"].default_value, cm.inputs["From Max"].default_value = 0.06, 0.0
        c = _mixrgb(nt, "ADD", _math(nt, "MULTIPLY", cm.outputs["Result"], 0.07, (-900, -400)), c, (1, 1, 1, 1), (-550, 50))
        return c
    return look.cel("seabed", core.hexc("#cdf1ea"), shadow=(0.55, 0.72, 0.82, 1), high=(1.06, 1.06, 1.04, 1), t1=0.45, t2=0.985,
                    paint=0.16, paint_scale=2.2, base_node=base, rough=0.7)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#bfe6ea"), 0.38)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.86, SUN_DIR, 0.28), core.hexc("#fffaee"), angle_deg=2.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    protos = geo.proto_collection("CORAL_PROTOS")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.3)
    nx, ny = int((x1 - x0) / 0.12), int((y1 - y0) / 0.12)
    bed = geo.grid("seabed", x0, y0, x1, y1, nx, ny, lambda X, Y: -depth(X, Y), env, seabed_material())

    # water surface: clear, slight tint, glints (does not cast shadows)
    def wh(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1000, -300))
        wn = _n(nt, "ShaderNodeTexNoise", (-800, -300), noise_dimensions="4D")
        _l(nt, geo_n.outputs["Position"], wn.inputs["Vector"])
        wn.inputs["Scale"].default_value = 1.6
        wn.inputs["Detail"].default_value = 3
        d = wn.inputs["W"].driver_add("default_value").driver
        d.type = "SCRIPTED"
        d.expression = "frame / 36.0"
        return wn.outputs["Fac"]
    wmat = look.cel("lagoon_surface", core.hexc("#bfeeee"), shadow=(0.8, 0.9, 0.95, 1), high=(1.25, 1.25, 1.25, 1), t1=0.15, t2=1.02,
                    paint=0.05, height_node=wh, bump=0.25, bump_dist=0.03, alpha=0.16, rough=0.05)
    surf = geo.grid("lagoon_surface", x0, y0, x1, y1, 4, 4, None, env, wmat)
    surf.visible_shadow = False

    # coral heads: knobbly prototypes, clustered, palette tinted per instance
    coral_cols = [core.hexc(h) for h in ("#7a6aa2", "#6e8a52", "#b8955e", "#4a7466", "#b98257", "#8a7aa8", "#7d8f5a")]
    def coral_base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-900, 200), attribute_type="INSTANCER", attribute_name="tint")
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, -50))
        nz = _n(nt, "ShaderNodeTexNoise", (-700, -50))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 3.5
        nz.inputs["Detail"].default_value = 3
        f = _math(nt, "FRACT", _math(nt, "ADD", at.outputs["Fac"], _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.5, (-550, -50)), (-450, 100)), None, (-350, 100))
        ramp = _n(nt, "ShaderNodeValToRGB", (-200, 100))
        cr = ramp.color_ramp
        cr.interpolation = "CONSTANT"
        while len(cr.elements) < len(coral_cols):
            cr.elements.new(0.5)
        for i, c in enumerate(coral_cols):
            cr.elements[i].position = i / len(coral_cols)
            cr.elements[i].color = c
        _l(nt, f, ramp.inputs[0])
        # polyp mottling
        vo = _n(nt, "ShaderNodeTexVoronoi", (-700, -250))
        _l(nt, geo_n.outputs["Position"], vo.inputs["Vector"])
        vo.inputs["Scale"].default_value = 22.0
        mott = _math(nt, "ADD", _math(nt, "MULTIPLY", vo.outputs["Distance"], 0.5, (-500, -250)), 0.78, (-400, -250))
        comb = _n(nt, "ShaderNodeCombineColor", (-250, -250))
        for i in range(3):
            _l(nt, mott, comb.inputs[i])
        return _mixrgb(nt, "MULTIPLY", 1.0, ramp.outputs[0], comb.outputs[0], (0, 0))
    cmat = look.cel("coral", coral_cols[0], shadow=(0.55, 0.62, 0.78, 1), high=(1.15, 1.13, 1.05, 1), paint=0.08, paint_scale=5.0,
                    base_node=coral_base, rough=0.9)
    for i in range(6):
        geo.knobbly(f"coral_{i}", cmat, protos, seed=40 + i, subdiv=3, knob=0.5, flat=0.5, lumps=7)
    rng = np.random.default_rng(606)
    pts, scl, var, tint = [], [], [], []
    for cx, cy, r in CORALS:
        for _ in range(int(9 + r * 9)):
            a = rng.uniform(0, 6.28)
            rr = r * math.sqrt(rng.random())
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            s = rng.uniform(0.28, 0.6) * (1.2 - 0.5 * rr / r) * min(1.3, r)
            pts.append((x, y, -float(depth(x, y)) + s * 0.1))
            scl.append((s, s * rng.uniform(0.8, 1.2), s * rng.uniform(0.6, 1.0)))
            var.append(rng.integers(0, 6))
            tint.append(rng.random())
    small = geo.poisson(rng, 220, x0, y0, x1, y1, 1.1, accept=lambda x, y: depth(x, y) < 0.9)
    for x, y in small:
        s = rng.uniform(0.18, 0.42)
        pts.append((x, y, -float(depth(x, y)) + s * 0.1))
        scl.append((s, s * rng.uniform(0.7, 1.3), s * 0.7))
        var.append(rng.integers(0, 6))
        tint.append(rng.random())
    pts = np.array(pts)
    n = len(pts)
    geo.instances("corals", protos, pts, rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)], scl=np.array(scl),
                  variant=np.array(var), tint=np.array(tint), coll=env)
    # starfish (blue and orange), lying on the sand
    sfm = look.cel("starfish", core.hexc("#4c5fae"), paint=0.0)
    sfo = look.cel("starfish_o", core.hexc("#d29a48"), paint=0.0)
    for i, (x, y) in enumerate(geo.poisson(rng, 26, x0, y0, x1, y1, 2.0, accept=lambda x, y: depth(x, y) < 0.7)):
        bm = bmesh.new()
        c = bm.verts.new((0, 0, 0.03))
        ring = []
        for k in range(10):
            a = 2 * math.pi * k / 10
            r = 0.22 if k % 2 == 0 else 0.08
            ring.append(bm.verts.new((r * math.cos(a), r * math.sin(a), 0.0)))
        for k in range(10):
            bm.faces.new((c, ring[k], ring[(k + 1) % 10]))
        o = geo.bm_to_object(bm, f"star{i}", sfm if i % 3 else sfo, env, smooth=False)
        o.location = (x, y, -float(depth(x, y)) + 0.01)
        o.rotation_euler = (0, 0, rng.uniform(0, 6.28))

    # creatures
    manta = creatures.Manta("manta", look.cel("manta", core.hexc("#45586a"), shadow=(0.55, 0.6, 0.75, 1), paint=0.05), span=4.0, coll=ink)
    def manta_path(t):
        keys = [(1674, 315, 400), (1714, 315, 450), (1876, 330, 720), (2037, 330, 990), (2077, 332, 1060)]
        fs = [k[0] for k in keys]
        sx = np.interp(t, fs, [k[1] for k in keys])
        sy = np.interp(t, fs, [k[2] for k in keys])
        return rig.screen_to_world(t, sx, sy, -0.7)
    tm_shell = look.cel("turtle_shell", core.hexc("#7d8a68"), shadow=(0.6, 0.65, 0.72, 1), paint=0.06, paint_scale=9)
    tm_skin = look.cel("turtle_skin", core.hexc("#9fa98a"), paint=0.03)
    turtles = []
    for i, (tx, ty, vx, vy) in enumerate(((3.6, 14.0, -0.004, 0.012), (-3.4, 3.0, 0.005, 0.016), (4.2, 26.0, -0.006, 0.01))):
        tt = creatures.Turtle(f"turtle{i}", tm_shell, tm_skin, length=0.95, coll=ink)
        turtles.append((tt, tx, ty, vx, vy))

    # sailing dinghy, heeled to starboard, sail out to the right; sailor hiking out to port
    bm_ = dict(hull=look.cel("hull", core.hexc("#c38f58"), shadow=(0.6, 0.55, 0.62, 1), paint=0.08, paint_scale=6.0),
               inner=look.cel("hull_in", core.hexc("#cb9862"), shadow=(0.6, 0.55, 0.62, 1), paint=0.1, paint_scale=7.0),
               trim=look.cel("trim", core.hexc("#a8773f"), paint=0.05), seat=look.cel("seat", core.hexc("#d6a46c"), paint=0.08, paint_scale=8.0),
               metal=look.cel("metal", core.hexc("#5a5753"), paint=0.0))
    boat, parts = boats.rowboat("boat", bm_, L=3.4, B=1.3, D=0.42, coll=ink, transom=0.45)
    spar = look.cel("spar", core.hexc("#b98f5e"), paint=0.03)
    def cyl(name, length, r, mat):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=r, radius2=r * 0.8, depth=length)
        bmesh.ops.translate(bm, vec=(0, 0, length / 2), verts=bm.verts)
        return geo.bm_to_object(bm, name, mat, ink)
    mast_root = bpy.data.objects.new("mast_root", None)
    ink.objects.link(mast_root)
    mast_root.parent = boat
    mast_root.location = (0, 0.75, 0.3)
    mast = cyl("mast", 4.2, 0.045, spar)
    mast.parent = mast_root
    boom = cyl("boom", 2.3, 0.035, spar)
    boom.parent = mast_root
    boom.location = (0, 0, 0.55)
    boom.rotation_euler = (math.radians(90), 0, math.radians(-150))
    sail_mat = look.cel("sail", core.hexc("#f4f2ea"), shadow=(0.7, 0.72, 0.82, 1), high=(1.05, 1.05, 1.05, 1), paint=0.06, paint_scale=6.0,
                        backface=True)
    # billowed triangular sail between mast foot, masthead and boom end (in mast_root space)
    A = Vector((0, 0, 0.6))
    B = Vector((0, 0, 4.1))
    C = Matrix.Rotation(math.radians(-150), 3, "Z") @ Vector((0, 2.25, 0.62))
    N = 14
    verts, faces = [], []
    idx = {}
    nrm = (B - A).cross(C - A).normalized()
    for i in range(N + 1):
        for j in range(N + 1 - i):
            u, v = i / N, j / N
            w = 1 - u - v
            p = A * w + B * u + C * v + nrm * (0.32 * 27 * u * v * w * 0.3)
            idx[(i, j)] = len(verts)
            verts.append(tuple(p))
    for i in range(N):
        for j in range(N - i):
            faces.append((idx[(i, j)], idx[(i + 1, j)], idx[(i, j + 1)]))
            if j < N - i - 1:
                faces.append((idx[(i + 1, j)], idx[(i + 1, j + 1)], idx[(i, j + 1)]))
    sail = geo.mesh_from_arrays("sail", verts, faces, ink, True, sail_mat)
    sail.parent = mast_root
    HEEL = math.radians(-42)               # mast leans to starboard (+X) -> seen from above, the sail shows area
    mast_root.rotation_euler = (0, -HEEL, 0)
    hm = dict(top=look.cel("sailor_top", core.hexc("#2f3672"), shadow=(0.55, 0.55, 0.78, 1), paint=0.04),
              legs=look.cel("sailor_legs", core.hexc("#2a2e52"), paint=0.03), shoes=look.cel("sailor_shoes", core.hexc("#252225"), paint=0.0),
              hands=look.cel("sailor_hands", core.hexc("#d3a58a"), paint=0.0), skin=look.cel("sailor_skin", core.hexc("#d3a58a"), paint=0.0),
              hair=look.cel("sailor_hair", core.hexc("#231c20"), paint=0.03))
    sailor = human.Human("sailor", hm, hair="short", coll=ink)

    def boat_frame(t):
        p = rig.screen_to_world(t, *BOAT_SCREEN, 0.0)
        return p
    def boat_matrix(t):
        p = boat_frame(t)
        pitch = math.radians(0.8) * math.sin(2 * math.pi * t / 53.0)
        roll = math.radians(4.0) + math.radians(1.2) * math.sin(2 * math.pi * t / 71.0)
        return Matrix.Translation((p[0], p[1], 0.02 * math.sin(t / 9.0))) @ Euler((pitch, roll, 0.0)).to_matrix().to_4x4()

    def sailor_pose(t):
        """hiking out over the port (left) gunwale, feet under the toe strap, holding the mainsheet"""
        J = {}
        k = 1.0
        hk = 0.75 + 0.05 * math.sin(t / 15.0)
        pel = np.array([-0.55, -0.55, 0.42])
        J["pelvis"] = pel
        lean = np.array([-math.sin(hk), 0.0, math.cos(hk)])
        for nm, l in (("spine", 0.18), ("chest", 0.38), ("neck", 0.54), ("head", 0.65)):
            J[nm] = pel + lean * l
        side = np.array([0, 1.0, 0])
        for s, sx in (("l", -1), ("r", 1)):
            J[f"sho_{s}"] = J["chest"] + side * 0.19 * sx * -1 + lean * 0.06
            J[f"hip_{s}"] = pel + side * 0.1 * sx * -1
            foot = pel + np.array([0.55, -0.1 * sx, -0.3])
            kn, an = human.ik2(J[f"hip_{s}"], foot, human.L_THIGH, human.L_SHIN, np.array([0.3, 0, 1.0]))
            J[f"kne_{s}"], J[f"ank_{s}"], J[f"toe_{s}"] = kn, an, an + np.array([0.15, 0, -0.03])
        hand_r = np.array([0.0, -0.9, 0.55])
        hand_l = np.array([-0.2, -0.4, 0.75])
        for s, h in (("r", hand_r), ("l", hand_l)):
            el, wr = human.ik2(J[f"sho_{s}"], h, human.L_UPPER, human.L_FORE, np.array([0, 0, -1.0]))
            J[f"elb_{s}"], J[f"wri_{s}"] = el, wr
            J[f"hnd_{s}"] = wr + (wr - el) / (np.linalg.norm(wr - el) + 1e-9) * 0.08
        J["hem_l"], J["hem_r"], J["hem_b"] = pel, pel, pel
        return J

    # wake foam (stateless particles) as flattened white blobs
    foam_mat = look.cel("foam", core.hexc("#f3fbfa"), shadow=(0.85, 0.9, 0.95, 1), paint=0.0, t1=0.1)
    fproto = geo.proto_collection("FOAM_PROTOS")
    bmf = bmesh.new()
    bmesh.ops.create_uvsphere(bmf, u_segments=8, v_segments=4, radius=0.06)
    bmesh.ops.scale(bmf, vec=(1, 1, 0.2), verts=bmf.verts)
    geo.bm_to_object(bmf, "foam_blob", foam_mat, fproto)
    def hull_frame(t):
        p = boat_frame(t)
        q = boat_frame(t + 1)
        sp = math.hypot(q[0] - p[0], q[1] - p[1])
        return (p[0], p[1]), (0.0, 1.0), (1.0, 0.0), sp
    wake = geo.Wake(hull_frame, start, end, rate=10, life=70.0, spread=0.55, decay=0.05, seed=6,
                    emit_points=((0.0, -1.7, 0.0), (0.55, -1.2, 1.0), (-0.55, -1.2, -1.0), (0.3, 0.9, 1.0), (-0.3, 0.9, -1.0)), jitter=0.1)
    MAXF = 900
    foam = geo.instances("foam", fproto, np.zeros((MAXF, 3)), scl=np.zeros((MAXF, 3)), coll=env)

    # cord floating in the wake
    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    frames = list(range(start, end))
    def stern(t):
        return np.array(boat_matrix(t) @ Vector((0, -1.69, 0.06)))
    def flow(x, y, t):
        return 0.04 * np.sin(y * 0.7 + t * 0.025), 0.02 * np.sin(x * 1.3 + t * 0.03)
    cord = thread.Cord(n_seg=200, length=13.0, mode="water", water_level=0.0, water_drag=5.0, flow=flow, substeps=6, iters=22, bend=0.12)
    sim = cord.run(frames, stern, (0.0, -1.0), warm=96)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.6)

    st = look.freestyle(ink, thickness=1.8, res_scale=opt.scale)
    look.compositor(dict(kuwahara=10, bloom=0.4, bloom_threshold=0.95, streak=0.1, lift=(0.99, 1.0, 1.01), gain=(1.02, 1.01, 0.99),
                         vignette=0.24, grain=0.03, ink=0.55), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        boat.matrix_world = boat_matrix(d)
        Mb = np.array(boat.matrix_world)
        Jw = {k: (Mb @ np.r_[v, 1.0])[:3] for k, v in sailor_pose(d).items()}
        sailor.set_world(Jw, math.pi / 2)
        mp = manta_path(d)
        manta.obj.location = (mp[0], mp[1], -min(float(depth(mp[0], mp[1])) - 0.18, 0.7))
        manta.obj.rotation_euler = (0, 0, 0.25 + 0.08 * math.sin(d / 40.0))
        manta.pose(d)
        for tt, tx, ty, vx, vy in turtles:
            t = d - start
            tt.shell.location = (tx + vx * t * 24 / 24, ty + vy * t, -float(depth(tx + vx * t, ty + vy * t)) + 0.35)
            tt.shell.rotation_euler = (0, 0, math.atan2(-vx, vy))
            tt.pose(t)
        W = wake.at(d, MAXF)
        z = np.full(MAXF, 0.012)
        s = W[:, 2] * 1.6
        geo.update_points(foam, np.c_[W[:, 0], W[:, 1], z], rot=np.c_[np.zeros(MAXF), np.zeros(MAXF), W[:, 3]],
                          scl=np.c_[s, s * 0.8, s])
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
