"""Scene 7 (frames 2078-2491): a teal paraglider high above grey canyon country with lichen plateaus,
rust patches, winding tracks and cloud wisps. The glider flies into a headwind (ground speed 1.9 px/frame,
airspeed far higher), so the red cord streams behind and below the pilot to the bottom edge."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, thread, human
from kit.look import _n, _l, _math, _mixrgb

SCENE = 7
PPM = 30.0                         # ground scale (px per metre)
GLIDER_Z = 58.0                    # canopy height above the ground (ppm at canopy ~47)
SUN_DIR = (0.86, 0.38, 3.6)        # high sun from the right: glider shadow lands lower-left within frame
GLIDER_SCREEN = (540, 1180)
PAINT_BOIL = 2.4


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def terrain(X, Y):
    h = 15.0 * geo.fbm2(X * 0.022, Y * 0.022, 4, 71) + 4.0 * geo.fbm2(X * 0.075, Y * 0.075, 4, 5)
    r = np.abs(geo.fbm2(X * 0.05 + 3, Y * 0.05, 4, 13))
    h += 4.0 * (0.5 - r)
    plateau = np.clip((h - 0.5) * 0.8, 0, 1)
    return h + plateau * 1.2


def terrain_material():
    def base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1900, 300))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-1700, 300))
        _l(nt, geo_n.outputs["Position"], sx.inputs[0])
        nz = _n(nt, "ShaderNodeSeparateXYZ", (-1700, 100))
        _l(nt, geo_n.outputs["Normal"], nz.inputs[0])
        # rock: blue-grey with darker valleys
        hval = _n(nt, "ShaderNodeMapRange", (-1500, 300), clamp=True)
        _l(nt, sx.outputs[2], hval.inputs["Value"])
        hval.inputs["From Min"].default_value, hval.inputs["From Max"].default_value = -4.0, 13.0
        rock = _n(nt, "ShaderNodeValToRGB", (-1300, 300))
        cr = rock.color_ramp
        cr.elements[0].color = core.hexc("#343b4f")
        cr.elements[1].color = core.hexc("#a3a7b0")
        e = cr.elements.new(0.5)
        e.color = core.hexc("#6c7284")
        _l(nt, hval.outputs["Result"], rock.inputs[0])
        # lichen on flat high ground: mottled ochre/yellow/orange
        flat = _n(nt, "ShaderNodeMapRange", (-1500, 100), clamp=True)
        _l(nt, nz.outputs[2], flat.inputs["Value"])
        flat.inputs["From Min"].default_value, flat.inputs["From Max"].default_value = 0.8, 0.94
        high = _n(nt, "ShaderNodeMapRange", (-1500, -50), clamp=True)
        _l(nt, sx.outputs[2], high.inputs["Value"])
        high.inputs["From Min"].default_value, high.inputs["From Max"].default_value = -1.0, 2.0
        ln = _n(nt, "ShaderNodeTexNoise", (-1500, -200))
        _l(nt, geo_n.outputs["Position"], ln.inputs["Vector"])
        ln.inputs["Scale"].default_value = 0.03
        ln.inputs["Detail"].default_value = 3
        lm = _n(nt, "ShaderNodeMapRange", (-1300, -200), clamp=True)
        _l(nt, ln.outputs["Fac"], lm.inputs["Value"])
        lm.inputs["From Min"].default_value, lm.inputs["From Max"].default_value = 0.5, 0.57
        lich_mask = _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", flat.outputs["Result"], high.outputs["Result"], (-1150, 0)), lm.outputs["Result"], (-1000, 0))
        mot = _n(nt, "ShaderNodeTexNoise", (-1300, -400))
        _l(nt, geo_n.outputs["Position"], mot.inputs["Vector"])
        mot.inputs["Scale"].default_value = 1.3
        mot.inputs["Detail"].default_value = 5
        mot.inputs["Distortion"].default_value = 1.4
        lich = _n(nt, "ShaderNodeValToRGB", (-1100, -400))
        cl = lich.color_ramp
        cl.interpolation = "CONSTANT"
        cl.elements[0].color = core.hexc("#a48544")
        cl.elements[1].position = 0.42
        cl.elements[1].color = core.hexc("#dfc04c")
        e = cl.elements.new(0.62)
        e.color = core.hexc("#e39b35")
        e = cl.elements.new(0.8)
        e.color = core.hexc("#c9cbcc")
        _l(nt, mot.outputs["Fac"], lich.inputs[0])
        # painterly rock mottling: fine strokes of lighter/darker grey
        rk = _n(nt, "ShaderNodeTexNoise", (-1300, 600))
        _l(nt, geo_n.outputs["Position"], rk.inputs["Vector"])
        rk.inputs["Scale"].default_value = 1.4
        rk.inputs["Detail"].default_value = 8
        rk.inputs["Distortion"].default_value = 2.5
        rkm = _n(nt, "ShaderNodeMapRange", (-1100, 600), clamp=True)
        _l(nt, rk.outputs["Fac"], rkm.inputs["Value"])
        rkm.inputs["From Min"].default_value, rkm.inputs["From Max"].default_value = 0.35, 0.65
        rkm.inputs["To Min"].default_value, rkm.inputs["To Max"].default_value = 0.42, 1.55
        rkc = _n(nt, "ShaderNodeCombineColor", (-950, 600))
        for i in range(3):
            _l(nt, rkm.outputs["Result"], rkc.inputs[i])
        rockc = _mixrgb(nt, "MULTIPLY", 1.0, rock.outputs[0], rkc.outputs[0], (-900, 450))
        c = _mixrgb(nt, "MIX", lich_mask, rockc, lich.outputs[0], (-850, 200))
        # rust patches
        rn = _n(nt, "ShaderNodeTexNoise", (-1100, -650))
        _l(nt, geo_n.outputs["Position"], rn.inputs["Vector"])
        rn.inputs["Scale"].default_value = 0.045
        rn.inputs["Detail"].default_value = 4
        rm = _n(nt, "ShaderNodeMapRange", (-900, -650), clamp=True)
        _l(nt, rn.outputs["Fac"], rm.inputs["Value"])
        rm.inputs["From Min"].default_value, rm.inputs["From Max"].default_value = 0.62, 0.68
        rust = _mixrgb(nt, "MIX", mot.outputs["Fac"], core.hexc("#8e4a36"), core.hexc("#d0662f"), (-750, -500))
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", rm.outputs["Result"], 0.9, (-750, -650)), c, rust, (-600, 100))
        # winding double tracks: zero set of a smooth field, drawn as two thin pale lines
        tn = _n(nt, "ShaderNodeTexNoise", (-1100, -900))
        _l(nt, geo_n.outputs["Position"], tn.inputs["Vector"])
        tn.inputs["Scale"].default_value = 0.012
        tn.inputs["Detail"].default_value = 1.5
        dd = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", tn.outputs["Fac"], 0.5, (-900, -900)), None, (-780, -900))
        l1 = _n(nt, "ShaderNodeMapRange", (-650, -900), clamp=True)
        _l(nt, dd, l1.inputs["Value"])
        l1.inputs["From Min"].default_value, l1.inputs["From Max"].default_value = 0.0016, 0.0008
        l2 = _n(nt, "ShaderNodeMapRange", (-650, -1050), clamp=True)
        _l(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", dd, 0.0032, (-780, -1050)), None, (-700, -1050)), l2.inputs["Value"])
        l2.inputs["From Min"].default_value, l2.inputs["From Max"].default_value = 0.0008, 0.0003
        trk = _math(nt, "MAXIMUM", l1.outputs["Result"], l2.outputs["Result"], (-500, -950))
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", trk, 0.85, (-400, -950)), c, core.hexc("#c5c9cf"), (-300, 50))
        return c
    return look.cel("terrain", core.hexc("#8c909c"), shadow=(0.5, 0.54, 0.72, 1), high=(1.12, 1.1, 1.05, 1), t1=0.7, t2=0.95,
                    paint=0.32, paint_scale=1.6, base_node=base, rough=0.9)


def canopy_mesh(name, mats, coll):
    """paraglider: arc of airfoil cells, crescent planform; per-cell colour via material slots"""
    cells, R, th = 30, 6.0, math.radians(62)
    chord = 2.6
    verts, faces, mat_idx = [], [], []
    NT = 8
    def pt(s, t, up):
        a = s * th
        prof_up = 0.32 * math.sin(math.pi * (1 - t) ** 0.6) * (1 - 0.3 * t)
        prof_lo = -0.06 * math.sin(math.pi * t)
        r = R + (prof_up if up else prof_lo) * chord * 0.3 * (1 - 0.4 * s * s)
        ch = chord * (1 - 0.45 * s * s)
        y = ch * (0.5 - t) - 1.6 * s * s + 0.5
        return (math.sin(a) * r * 1.1, y, math.cos(a) * r - R)
    for i in range(cells):
        s0, s1 = -1 + 2 * i / cells, -1 + 2 * (i + 1) / cells
        for k in range(NT):
            t0, t1 = k / NT, (k + 1) / NT
            for up in (True, False):
                b = len(verts)
                quad = [pt(s0, t0, up), pt(s0, t1, up), pt(s1, t1, up), pt(s1, t0, up)]
                # cell bulge: the top skin balloons between ribs
                if up:
                    mid = 0.5 * (s0 + s1)
                    quad = [(x, y, z + 0.0) for (x, y, z) in quad]
                verts += quad
                faces.append((b, b + 1, b + 2, b + 3) if up else (b, b + 3, b + 2, b + 1))
                mat_idx.append((0 if k > 0 else 2) if up else 3)
                if up and i % 2 == 1 and k > 0:
                    mat_idx[-1] = 1
    ob = geo.mesh_from_arrays(name, verts, faces, coll, True, None)
    for m in mats:
        ob.data.materials.append(m)
    ob.data.polygons.foreach_set("material_index", np.array(mat_idx, np.int32))
    ob.data.update()
    return ob


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 8))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#c3c8d6"), 0.4)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.86, SUN_DIR, 0.3), core.hexc("#fff4e2"), angle_deg=2.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.3)
    step = 0.3
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    ground = geo.grid("terrain", x0, y0, x1, y1, nx, ny, terrain, env, terrain_material())

    # cloud wisps at two heights (they drift), soft painted alpha
    def wisp_mat(name, seed, dens):
        def base(nt):
            return (0.96, 0.96, 0.97, 1)
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = _n(nt, "ShaderNodeOutputMaterial", (500, 0))
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, 0))
        mp = _n(nt, "ShaderNodeMapping", (-700, 0))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Scale"].default_value = (0.04, 0.02, 0.0)
        mp.inputs["Rotation"].default_value = (0, 0, 0.5 + seed)
        drv = mp.inputs["Location"].driver_add("default_value", 0).driver
        drv.type = "SCRIPTED"
        drv.expression = f"frame * {0.0055 + seed * 0.002:.5f}"
        nz = _n(nt, "ShaderNodeTexNoise", (-500, 0), noise_dimensions="4D")
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 1.0
        nz.inputs["W"].default_value = seed * 10
        nz.inputs["Detail"].default_value = 6
        nz.inputs["Distortion"].default_value = 0.8
        mr = _n(nt, "ShaderNodeMapRange", (-300, 0), clamp=True)
        _l(nt, nz.outputs["Fac"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.6, 0.8
        a = _math(nt, "MULTIPLY", mr.outputs["Result"], dens, (-150, 0))
        em = _n(nt, "ShaderNodeEmission", (0, 50))
        em.inputs[0].default_value = core.hexc("#eef0f3")
        em.inputs[1].default_value = 0.95
        tr = _n(nt, "ShaderNodeBsdfTransparent", (0, -100))
        mx = _n(nt, "ShaderNodeMixShader", (250, 0))
        _l(nt, a, mx.inputs[0])
        _l(nt, tr.outputs[0], mx.inputs[1])
        _l(nt, em.outputs[0], mx.inputs[2])
        _l(nt, mx.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
        return m
    for i, (z, dens) in enumerate(((18.0, 1.0), (34.0, 0.85))):
        w = geo.grid(f"wisps{i}", x0 - 20, y0 - 20, x1 + 20, y1 + 20, 4, 4, None, env, wisp_mat(f"wisp{i}", i * 0.37, dens))
        w.location.z = z
        w.visible_shadow = i == 0

    # paraglider canopy + pilot
    teal = look.cel("canopy", core.hexc("#2f9692"), shadow=(0.55, 0.65, 0.78, 1), high=(1.2, 1.18, 1.12, 1), t1=0.4, t2=0.9, paint=0.04)
    teal2 = look.cel("canopy_b", core.hexc("#287f80"), shadow=(0.55, 0.65, 0.78, 1), high=(1.2, 1.18, 1.12, 1), t1=0.4, t2=0.9, paint=0.04)
    lead = look.cel("canopy_le", core.hexc("#1b4c57"), paint=0.0)
    under = look.cel("canopy_under", core.hexc("#d8e0dd"), shadow=(0.7, 0.75, 0.85, 1), paint=0.0)
    canopy = canopy_mesh("canopy", [teal, teal2, lead, under], ink)
    hm = dict(top=look.cel("pilot_top", core.hexc("#ece8e2"), paint=0.03), legs=look.cel("pilot_legs", core.hexc("#3a3a48"), paint=0.0),
              shoes=look.cel("pilot_shoes", core.hexc("#2a2628"), paint=0.0), hands=look.cel("pilot_hands", core.hexc("#d6a98f"), paint=0.0),
              skin=look.cel("pilot_skin", core.hexc("#d6a98f"), paint=0.0), hair=look.cel("pilot_hair", core.hexc("#2b2124"), paint=0.0))
    pilot = human.Human("pilot", hm, hair="long", coll=ink)
    harness = geo.knobbly("harness", look.cel("harness", core.hexc("#40465a"), paint=0.0), ink, seed=3, subdiv=2, knob=0.1, flat=0.7, lumps=2)
    harness.scale = (0.32, 0.55, 0.3)

    def glider_world(t):
        p = rig.screen_to_world(t, *GLIDER_SCREEN, GLIDER_Z)
        swing = math.radians(2.5) * math.sin(2 * math.pi * t / 110.0)
        yaw = math.radians(1.5) * math.sin(2 * math.pi * t / 170.0)
        return p, swing, yaw
    def pilot_pose():
        J = {}
        pel = np.array([0, 0.0, 0.0])
        J["pelvis"] = pel
        for nm, l in (("spine", 0.18), ("chest", 0.38), ("neck", 0.54), ("head", 0.65)):
            J[nm] = pel + np.array([0, -0.12 * l, l])
        for s, sx in (("l", -1), ("r", 1)):
            J[f"sho_{s}"] = J["chest"] + np.array([sx * 0.19, 0, 0.06])
            J[f"hip_{s}"] = pel + np.array([sx * 0.1, 0, 0])
            J[f"kne_{s}"] = J[f"hip_{s}"] + np.array([0, 0.42, -0.08])
            J[f"ank_{s}"] = J[f"kne_{s}"] + np.array([0, 0.25, -0.35])
            J[f"toe_{s}"] = J[f"ank_{s}"] + np.array([0, 0.14, -0.02])
            J[f"elb_{s}"] = J[f"sho_{s}"] + np.array([sx * 0.12, 0.05, 0.22])
            J[f"wri_{s}"] = J[f"elb_{s}"] + np.array([sx * 0.02, 0.02, 0.24])
            J[f"hnd_{s}"] = J[f"wri_{s}"] + np.array([0, 0, 0.08])
        J["hem_l"] = J["hem_r"] = J["hem_b"] = pel
        return J

    # hawks
    hawk_b = look.cel("hawk", core.hexc("#7a5a3e"), paint=0.0)
    hawk_d = look.cel("hawk_d", core.hexc("#4e3a2a"), paint=0.0)
    hawks = []
    for i in range(2):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
        bmesh.ops.scale(bm, vec=(0.08, 0.26, 0.07), verts=bm.verts)
        body = geo.bm_to_object(bm, f"hawk{i}", hawk_b, ink)
        wings = []
        for s in (-1, 1):
            bm = bmesh.new()
            pts = [(0, 0.08, 0), (0.35 * s, 0.12, 0.0), (0.62 * s, 0.02, 0.0), (0.66 * s, -0.1, 0), (0.3 * s, -0.12, 0), (0, -0.1, 0)]
            vs = [bm.verts.new(p) for p in pts]
            bm.faces.new(vs if s > 0 else vs[::-1])
            bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.02)
            w = geo.bm_to_object(bm, f"hawk{i}_w{s}", hawk_d, ink, smooth=False)
            w.parent = body
            wings.append((w, s))
        hawks.append((body, wings))

    # cord streaming from the harness into the headwind
    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    def harness_pt(t):
        p, swing, yaw = glider_world(t)
        return np.array([p[0] + math.sin(swing) * 6.0, p[1] - 0.4, GLIDER_Z - 6.5])
    def wind(x, y, z, t):
        return 0.4 * np.sin(y * 0.05 + t * 0.02), np.full_like(x, -7.5), np.zeros_like(x)
    cord = thread.Cord(n_seg=200, length=34.0, mode="air", ground=lambda x, y: terrain(x, y) + 0.3, air_drag=6.0, wind=wind,
                       substeps=8, iters=24, bend=0.15, friction=0.7)
    sim = cord.run(list(range(start, end)), harness_pt, (0.0, -1.0), warm=120)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.2)

    st = look.freestyle(ink, thickness=1.7, res_scale=opt.scale)
    look.compositor(dict(kuwahara=5, bloom=0.4, bloom_threshold=0.95, streak=0.1, lift=(0.985, 0.995, 1.03), gain=(1.04, 1.01, 0.97),
                         vignette=0.26, grain=0.03, ink=0.5, ink_normal=(0.45, 1.3)), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        p, swing, yaw = glider_world(d)
        breathe = 1.0 + 0.012 * math.sin(2 * math.pi * d / 40.0)
        canopy.matrix_world = Matrix.Translation((p[0], p[1], GLIDER_Z)) @ Euler((0, swing, yaw)).to_matrix().to_4x4() @ Matrix.Diagonal((breathe, 1, 1 / breathe, 1))
        hp = harness_pt(d)
        M = Matrix.Translation(Vector(hp.tolist())) @ Euler((0, swing, yaw)).to_matrix().to_4x4()
        harness.matrix_world = M @ Matrix.Diagonal((0.32, 0.55, 0.3, 1))
        Jw = {k: np.array(M @ Vector(v.tolist())) for k, v in pilot_pose().items()}
        pilot.set_world(Jw, yaw)
        for i, (body, wings) in enumerate(hawks):
            t = d - start
            sx = 760 + i * 70 + 60 * math.sin(t * 0.012 + i)
            sy = 330 - i * 90 + 40 * math.cos(t * 0.01 + i) + t * 0.35
            q = rig.screen_to_world(f, sx, sy, 30.0 + i * 3)
            body.location = q
            body.rotation_euler = (0, 0, -0.6 + 0.3 * math.sin(t * 0.015 + i))
            glide = (t // 60 + i) % 2 == 0
            flap = 0.0 if glide else 0.5 * math.sin(d * 0.6 + i)
            for w, s in wings:
                w.rotation_euler = (0, -s * flap, 0)
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
