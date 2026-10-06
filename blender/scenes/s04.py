"""Scene 4 (frames 954-1313): an ice skater in a white coat glides over a frozen lake at night under the aurora.

v3: a skater with a clear body (long dark hair, white coat, dark tights, white skates) in a push-glide stroke
along a gentle S-curve, arms swinging against the legs. Each blade cuts thin white scratches into the ice (a pair of
close parallel curves per blade, brighter and deeper where the skater pushes) that persist in world space and fade
over ~6 s; fine ice shavings spray at each push-off. Translucent navy ice with trapped bubbles graded by depth,
long crooked fractures with a light and a dark edge (not wire-straight), streaky frost and snow drifts (CC0 snow
texture), and the pink-gold aurora reflected in the ice (screen-fixed). The rope slides and whips on the ice."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector
from kit import core, look, geo, human, rope_io
from kit.look import _n, _l, _math, _mixrgb
from kit.human import ik2, standing, rot_z, L_UPPER, L_FORE, L_HAND, L_THIGH, L_SHIN

SCENE = 4
PPM = 100.0
SUN_DIR = (0.5, 0.62, 0.46)             # moon / aurora light from the upper-right -> long shadows lower-left
SKATER_SCREEN = (520, 1180)
STRIDE = 30.0                           # frames per push (one side)
POST = dict(light_deg=51.0, flow_deg=25.0, stroke_px=12.0, boil_mean=1.8, thread_shadow_px=1.6, thread_glow=0.18, repaint=0.5,
            grain=1.2)


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def ice_material():
    def base(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-1800, 300))
        pos = g.outputs["Position"]
        mp = _n(nt, "ShaderNodeMapping", (-1600, 300))
        _l(nt, pos, mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, 0.35)
        mp.inputs["Scale"].default_value = (0.12, 1.4, 1)
        nz = _n(nt, "ShaderNodeTexNoise", (-1400, 300))
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 0.8
        nz.inputs["Detail"].default_value = 5
        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#0d1c47"), core.hexc("#233b74"), (-1200, 300))
        dk = _n(nt, "ShaderNodeTexNoise", (-1400, 100))
        _l(nt, pos, dk.inputs["Vector"])
        dk.inputs["Scale"].default_value = 0.12
        dm = _n(nt, "ShaderNodeMapRange", (-1200, 100), clamp=True)
        _l(nt, dk.outputs["Fac"], dm.inputs["Value"])
        dm.inputs["From Min"].default_value, dm.inputs["From Max"].default_value = 0.45, 0.65
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", dm.outputs["Result"], 0.65, (-1050, 100)), c, core.hexc("#081331"), (-950, 250))
        # milky depth clouds inside the ice
        mk = _n(nt, "ShaderNodeTexNoise", (-1400, -100))
        _l(nt, pos, mk.inputs["Vector"])
        mk.inputs["Scale"].default_value = 0.5
        mk.inputs["Detail"].default_value = 6
        mm = _n(nt, "ShaderNodeMapRange", (-1200, -100), clamp=True)
        _l(nt, mk.outputs["Fac"], mm.inputs["Value"])
        mm.inputs["From Min"].default_value, mm.inputs["From Max"].default_value = 0.55, 0.75
        c = _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", mm.outputs["Result"], 0.22, (-1050, -100)), c, core.hexc("#3d5f9e"), (-850, 150))
        # wind-blown frost and snow drifts (mostly on the right), streaked diagonally, CC0 snow detail
        m3 = _n(nt, "ShaderNodeMapping", (-1400, -950))
        _l(nt, pos, m3.inputs[0])
        m3.inputs["Rotation"].default_value = (0, 0, 0.55)
        m3.inputs["Scale"].default_value = (0.35, 1.2, 1)
        sn = _n(nt, "ShaderNodeTexNoise", (-1200, -950))
        _l(nt, m3.outputs[0], sn.inputs["Vector"])
        sn.inputs["Scale"].default_value = 0.45
        sn.inputs["Detail"].default_value = 6
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-1400, -1100))
        _l(nt, pos, sx.inputs[0])
        bias = _n(nt, "ShaderNodeMapRange", (-1200, -1100), clamp=True)
        _l(nt, sx.outputs[0], bias.inputs["Value"])
        bias.inputs["From Min"].default_value, bias.inputs["From Max"].default_value = -1.0, 4.0
        bias.inputs["To Min"].default_value, bias.inputs["To Max"].default_value = 0.0, 0.24
        sv = _math(nt, "ADD", sn.outputs["Fac"], bias.outputs["Result"], (-1050, -1000))
        sm = _n(nt, "ShaderNodeMapRange", (-900, -1000), clamp=True)
        _l(nt, sv, sm.inputs["Value"])
        sm.inputs["From Min"].default_value, sm.inputs["From Max"].default_value = 0.69, 0.8
        m4 = _n(nt, "ShaderNodeMapping", (-1200, -1250))
        _l(nt, pos, m4.inputs[0])
        m4.inputs["Rotation"].default_value = (0, 0, -1.0)
        m4.inputs["Scale"].default_value = (0.3, 8.0, 1)
        st_ = _n(nt, "ShaderNodeTexNoise", (-1000, -1250))
        _l(nt, m4.outputs[0], st_.inputs["Vector"])
        st_.inputs["Scale"].default_value = 2.0
        snow = _mixrgb(nt, "MIX", st_.outputs["Fac"], core.hexc("#7884b2"), core.hexc("#d3d8ee"), (-750, -1100))
        snow = look.mul_color(nt, snow, look.tex_value_detail(nt, "snow_02", size_m=1.2, amount=0.3, loc=(-1000, -1450)), (-600, -1100))
        # frost speckle field
        fr = _n(nt, "ShaderNodeTexNoise", (-1200, -1550))
        _l(nt, pos, fr.inputs["Vector"])
        fr.inputs["Scale"].default_value = 9.0
        fm = _n(nt, "ShaderNodeMapRange", (-1000, -1550), clamp=True)
        _l(nt, fr.outputs["Fac"], fm.inputs["Value"])
        fm.inputs["From Min"].default_value, fm.inputs["From Max"].default_value = 0.66, 0.74
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", fm.outputs["Result"], 0.25, (-850, -1550)), c, core.hexc("#8fa4d2"), (-600, 0))
        c = _mixrgb(nt, "MIX", sm.outputs["Result"], c, snow, (-450, 100))
        return c
    return look.cel("ice", core.hexc("#1a3266"), shadow=(0.55, 0.55, 0.8, 1), high=(1.18, 1.2, 1.25, 1), t1=0.4, t2=0.97,
                    paint=0.06, paint_scale=1.8, base_node=base, rough=0.1, soft=0.2, ao=0.3)


def aurora_material():
    m = bpy.data.materials.new("aurora")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial", (700, 0))
    tc = _n(nt, "ShaderNodeTexCoord", (-900, 0))
    sx = _n(nt, "ShaderNodeSeparateXYZ", (-700, 0))
    _l(nt, tc.outputs["UV"], sx.inputs[0])
    yv = _math(nt, "SUBTRACT", sx.outputs[1], _math(nt, "ADD", _math(nt, "MULTIPLY", sx.outputs[0], -0.12, (-550, 100)), 0.78, (-450, 100)), (-350, 0))
    nz = _n(nt, "ShaderNodeTexNoise", (-550, -200))
    _l(nt, tc.outputs["UV"], nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 3.0
    yv = _math(nt, "ADD", yv, _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", nz.outputs["Fac"], 0.5, (-350, -200)), 0.06, (-250, -200)), (-200, 0))
    g = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", yv, yv, (-100, 0)), -95.0, (0, 0)), None, (100, 0))
    ramp = _n(nt, "ShaderNodeValToRGB", (100, 250))
    cr = ramp.color_ramp
    cr.elements[0].color = core.hexc("#5a4c9a")
    cr.elements[1].color = core.hexc("#e8c9a4")
    e = cr.elements.new(0.6)
    e.color = core.hexc("#c98ab8")
    _l(nt, g, ramp.inputs[0])
    em = _n(nt, "ShaderNodeEmission", (300, 100))
    _l(nt, ramp.outputs[0], em.inputs[0])
    em.inputs[1].default_value = 0.95
    tr = _n(nt, "ShaderNodeBsdfTransparent", (300, -100))
    mx = _n(nt, "ShaderNodeMixShader", (450, -150))
    _l(nt, _math(nt, "MULTIPLY", g, 0.62, (250, -250)), mx.inputs[0])
    _l(nt, tr.outputs[0], mx.inputs[1])
    _l(nt, em.outputs[0], mx.inputs[2])
    _l(nt, mx.outputs[0], out.inputs[0])
    m.surface_render_method = "BLENDED"
    return m


def line_material(name, color, strength=1.0):
    """emissive line material whose alpha comes from a per-vertex attribute 'a' (fading scratches, fractures)"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial", (500, 0))
    at = _n(nt, "ShaderNodeAttribute", (-400, -100), attribute_type="GEOMETRY", attribute_name="a")
    em = _n(nt, "ShaderNodeEmission", (0, 50))
    em.inputs[0].default_value = color
    em.inputs[1].default_value = strength
    tr = _n(nt, "ShaderNodeBsdfTransparent", (0, -100))
    mx = _n(nt, "ShaderNodeMixShader", (250, 0))
    _l(nt, at.outputs["Fac"], mx.inputs[0])
    _l(nt, tr.outputs[0], mx.inputs[1])
    _l(nt, em.outputs[0], mx.inputs[2])
    _l(nt, mx.outputs[0], out.inputs[0])
    m.surface_render_method = "BLENDED"
    return m


def ribbons(lines, width, z=0.003):
    """lines: list of (pts (n,2), alpha (n,), width scale (n,)) -> verts, faces, per-vertex alpha"""
    V, F, A = [], [], []
    for P, a, ws in lines:
        n = len(P)
        if n < 2:
            continue
        d = np.gradient(P, axis=0)
        d /= np.linalg.norm(d, axis=1)[:, None] + 1e-9
        nrm = np.c_[-d[:, 1], d[:, 0]]
        i0 = len(V)
        for i in range(n):
            w = width * ws[i] * 0.5
            V.append((P[i, 0] - nrm[i, 0] * w, P[i, 1] - nrm[i, 1] * w, z))
            V.append((P[i, 0] + nrm[i, 0] * w, P[i, 1] + nrm[i, 1] * w, z))
            A += [a[i], a[i]]
        for i in range(n - 1):
            F.append((i0 + 2 * i, i0 + 2 * i + 1, i0 + 2 * i + 3, i0 + 2 * i + 2))
    return V, F, A


def set_mesh(ob, V, F, A):
    me = ob.data
    me.clear_geometry()
    if not V:
        return
    me.from_pydata(V, [], F)
    a = me.attributes.get("a") or me.attributes.new("a", "FLOAT", "POINT")
    a.data.foreach_set("value", np.asarray(A, np.float32))
    me.update()


def skate_local(t, height=1.72):
    """skating stride in body space: one blade glides under the body while the other pushes out-back.
    Returns joints and per-foot (blade position, on_ice, pushing, push strength)."""
    k = height / 1.72
    J = standing(height)
    ph = (t / STRIDE) % 2.0          # 0..1 left pushes, 1..2 right pushes
    side = -1 if ph < 1 else 1
    u = ph % 1.0
    push = math.sin(math.pi * min(u / 0.75, 1.0))
    lean = 0.34
    crouch = 0.12 * k
    for n in ("pelvis", "spine", "chest", "neck", "head", "sho_l", "sho_r", "hip_l", "hip_r", "hem_l", "hem_r", "hem_b"):
        J[n] = J[n] + np.array([-side * 0.07 * push, 0, -crouch])
        z = J[n][2] - J["pelvis"][2]
        if z > 0:
            J[n][1] += z * math.sin(lean)
            J[n][2] = J["pelvis"][2] + z * math.cos(lean)
    feet = {}
    for s, sx in (("l", -1), ("r", 1)):
        pushing = (s == "l") == (side == -1)
        if pushing:
            ang = math.radians(40)
            reach = 0.6 * push + 0.12
            foot = J[f"hip_{s}"] + np.array([sx * math.sin(ang) * reach, -math.cos(ang) * reach * 0.8 - 0.1, 0]) * k
            lift = 0.09 * k * max(0.0, (u - 0.75) / 0.25)
            foot[2] = 0.06 * k + lift
            on_ice = u < 0.78
            strength = push
        else:
            foot = np.array([J[f"hip_{s}"][0] * 0.55, 0.14 * k, 0.06 * k])
            on_ice = True
            strength = 0.25
        kne, ank = ik2(J[f"hip_{s}"], foot, L_THIGH * k, L_SHIN * k, np.array([sx * 0.2, 1.0, 0.3]))
        J[f"kne_{s}"], J[f"ank_{s}"] = kne, ank
        J[f"toe_{s}"] = ank + np.array([0, 0.22 * k, -0.05 * k])
        blade = (ank + J[f"toe_{s}"]) * 0.5
        blade[2] = 0.0
        feet[s] = (blade, on_ice, pushing, strength)
        # arms swing against the legs: the arm opposite the pushing leg reaches forward
        fwd = 1.0 if not pushing else -1.0
        a = 0.45 * push * fwd
        sh = J[f"sho_{s}"]
        el = sh + np.array([sx * 0.05, 0.26 * math.sin(a) + 0.04, -0.24]) * k
        wr = el + np.array([-sx * 0.02, 0.26 * math.sin(a + 0.5) + 0.08, -0.1]) * k
        J[f"elb_{s}"], J[f"wri_{s}"], J[f"hnd_{s}"] = el, wr, wr + np.array([sx * 0.03, 0.06, -0.03]) * k
    fl = 0.03 * math.sin(t * 0.7)
    J["hem_l"] = J["pelvis"] + np.array([-0.21, 0.0 + fl, -0.3]) * k
    J["hem_r"] = J["pelvis"] + np.array([0.21, 0.0 - fl, -0.3]) * k
    J["hem_b"] = J["pelvis"] + np.array([0.0, -0.2 + fl, -0.32]) * k
    return J, feet


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#4f5c9a"), 0.26)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.7, SUN_DIR, 0.16), core.hexc("#e9e6ff"), angle_deg=3.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.3)
    geo.grid("ice", x0, y0, x1, y1, 4, 4, None, env, ice_material())
    rng = np.random.default_rng(404)

    # trapped bubbles: clusters and vertical strings, graded by depth (deeper = smaller, dimmer, bluer)
    bproto = geo.proto_collection("P_bubble")
    bmat = look.cel("bubble", core.hexc("#a9bde0"), shadow=(0.7, 0.8, 0.95, 1), high=(1.15, 1.15, 1.15, 1), paint=0.0, t1=0.25, soft=0.25, ao=0.0,
                    base_node=look.instancer_palette([core.hexc("#33507f"), core.hexc("#4d6a9c"), core.hexc("#7d97c6"), core.hexc("#b9cbea"),
                                                      core.hexc("#e3ecfa")]))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
    bmesh.ops.scale(bm, vec=(1, 1, 0.35), verts=bm.verts)
    geo.bm_to_object(bm, "bubble", bmat, bproto)
    pts = []
    for sxs in (-3.6, -0.2, 3.4):
        y = y0
        while y < y1:
            if rng.random() < 0.65:
                depth = rng.uniform(0, 1)
                for _ in range(rng.integers(3, 9)):
                    pts.append((sxs + 0.6 * math.sin(y * 0.2) + rng.normal(0, 0.12), y + rng.normal(0, 0.1), rng.uniform(0.02, 0.05) * (1.1 - 0.5 * depth), depth))
            y += rng.uniform(0.3, 0.6)
    for cx, cy in geo.poisson(rng, 80, x0, y0, x1, y1, 1.5):
        depth = rng.uniform(0, 1)
        for _ in range(rng.integers(6, 24)):
            pts.append((cx + rng.normal(0, 0.35), cy + rng.normal(0, 0.35), rng.uniform(0.012, 0.045) * (1.1 - 0.5 * depth), depth))
    pts = np.array(pts)
    n = len(pts)
    geo.instances("bubbles", bproto, np.c_[pts[:, 0], pts[:, 1], np.full(n, 0.002)], scl=np.c_[pts[:, 2], pts[:, 2], pts[:, 2]],
                  tint=np.clip(1.0 - pts[:, 3] + rng.normal(0, 0.08, n), 0, 0.999), coll=env)

    # fractures: crooked branching polylines with a light edge and a darker partner line (a crack plane with depth)
    frac_light = bpy.data.objects.new("fractures", bpy.data.meshes.new("fractures"))
    frac_dark = bpy.data.objects.new("fractures_dk", bpy.data.meshes.new("fractures_dk"))
    for o, mname, col in ((frac_light, "frac_l", core.hexc("#7fb2d6")), (frac_dark, "frac_d", core.hexc("#06102a"))):
        env.objects.link(o)
        o.data.materials.append(line_material(mname, col, 0.9 if o is frac_light else 0.0))
    lines_l, lines_d = [], []

    def crack(p, ang, length, lvl):
        npts = max(4, int(length / 0.08))
        P = [np.array(p, float)]
        a = ang
        for i in range(npts):
            a += rng.normal(0, 0.07)
            P.append(P[-1] + 0.08 * np.array([math.cos(a), math.sin(a)]))
        P = np.array(P)
        t = np.linspace(0, 1, len(P))
        taper = np.minimum(1, np.minimum(t, 1 - t) * 6) * (0.9 if lvl == 0 else 0.6)
        lines_l.append((P, 0.55 * taper, 0.6 + 0.6 * taper))
        off = 0.012 * np.c_[-np.sin(ang), np.cos(ang)]
        lines_d.append((P + off, 0.45 * taper, 0.5 + 0.5 * taper))
        if lvl < 2:
            for _ in range(rng.integers(1, 4)):
                k = rng.integers(len(P) // 5, len(P) - 2)
                crack(P[k], a + rng.choice([-1, 1]) * rng.uniform(0.4, 1.1), length * rng.uniform(0.25, 0.5), lvl + 1)
    for i in range(14):
        crack((rng.uniform(x0, x1), rng.uniform(y0, y1)), rng.uniform(0, math.pi * 2), rng.uniform(3, 8), 0)
    set_mesh(frac_light, *ribbons(lines_l, 0.018, 0.0025))
    set_mesh(frac_dark, *ribbons(lines_d, 0.014, 0.0022))

    # old scratches from earlier skaters: faint curling arcs
    old = bpy.data.objects.new("old_scratches", bpy.data.meshes.new("old_scratches"))
    env.objects.link(old)
    scr_mat = line_material("scratch", core.hexc("#dfe8f8"), 1.0)
    old.data.materials.append(scr_mat)
    olds = []
    for i in range(55):
        cx, cy = rng.uniform(x0, x1), rng.uniform(y0, y1)
        a0, r0 = rng.uniform(0, 6.28), rng.uniform(1.0, 4.0)
        m = int(rng.integers(12, 40))
        aa = a0 + np.cumsum(rng.normal(0.05, 0.03, m)) * rng.choice([-1, 1])
        rr = r0 * (1 + np.cumsum(rng.normal(0, 0.02, m)))
        P = np.c_[cx + rr * np.cos(aa), cy + rr * np.sin(aa)]
        t = np.linspace(0, 1, m)
        olds.append((P, 0.28 * np.minimum(1, np.minimum(t, 1 - t) * 5), np.ones(m)))
        olds.append((P + 0.015, 0.2 * np.minimum(1, np.minimum(t, 1 - t) * 5), np.ones(m)))
    set_mesh(old, *ribbons(olds, 0.009, 0.0028))

    # aurora reflection: a camera-locked plane just above the ice
    au = geo.grid("aurora", -1, -1, 1, 1, 2, 2, None, env, aurora_material())
    au.visible_shadow = False

    # skater
    hm = dict(top=look.cel("sk_coat", core.hexc("#efecf2"), shadow=(0.58, 0.6, 0.84, 1), high=(1.06, 1.06, 1.08, 1), paint=0.04, soft=0.24, rim=0.3, hero=True),
              coat=look.cel("sk_coat2", core.hexc("#e9e6ee"), shadow=(0.58, 0.6, 0.84, 1), paint=0.04, soft=0.24, hero=True),
              legs=look.cel("sk_legs", core.hexc("#2b2c3c"), paint=0.0, soft=0.2, hero=True),
              shoes=look.cel("sk_boots", core.hexc("#f0eef0"), paint=0.0, soft=0.2, hero=True),
              hands=look.cel("sk_hands", core.hexc("#2a2830"), paint=0.0, hero=True),
              skin=look.cel("sk_skin", core.hexc("#d6a98f"), paint=0.0, hero=True),
              hair=look.cel("sk_hair", core.hexc("#231b20"), high=(1.4, 1.35, 1.4, 1), paint=0.03, soft=0.2, rim=0.35, hero=True))
    skater = human.Human("skater", hm, hair="long", height=1.95, coll=ink, bulk={"top": 1.25, "coat": 1.2})
    skater.hair_scale = 1.1
    blade_mat = look.cel("blade", core.hexc("#cfd6e2"), paint=0.0, hero=True)
    blades = {}
    for s in ("l", "r"):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.012, 0.3, 0.02), verts=bm.verts)
        blades[s] = geo.bm_to_object(bm, f"blade_{s}", blade_mat, ink, smooth=False)

    mot = rope_io.C.owner_motion(SCENE)

    def base(t):
        tt = min(max(t, start), end)
        p = rig.screen_to_world(tt, *SKATER_SCREEN, 0.0)
        y = p[1] + (min(t - start, 0) + max(t - end, 0)) * 4.87 / PPM
        return np.array([p[0] + mot(t)[0], y])

    def heading(t):
        a, b = base(t - 1), base(t + 1)
        return math.atan2(-(b[0] - a[0]), b[1] - a[1])

    def world_pose(t):
        b = base(t)
        hd = heading(t)
        R = rot_z(hd)
        J, feet = skate_local(t, 1.95)
        b3 = np.array([b[0], b[1], 0.0])
        Jw = {k_: b3 + R @ v for k_, v in J.items()}
        fw = {s: (b3 + R @ f[0], f[1], f[2], f[3]) for s, f in feet.items()}
        return Jw, fw, hd

    # skate scratches: sample every blade every frame from well before the scene; each blade leaves two edges
    trail = {s: [] for s in ("l", "r")}
    shav = []
    prev_on = {"l": True, "r": True}
    for t in range(start - 160, end + 1):
        Jw, fw, hd = world_pose(float(t))
        for s, (bp, on, pushing, strength) in fw.items():
            if on:
                trail[s].append((t, bp[0], bp[1], hd, strength))
            elif prev_on[s]:
                shav.append((t, bp[0], bp[1], hd))
            prev_on[s] = on
    trail = {s: np.array(v) for s, v in trail.items()}
    scratch_obj = bpy.data.objects.new("scratches", bpy.data.meshes.new("scratches"))
    env.objects.link(scratch_obj)
    scratch_obj.data.materials.append(scr_mat)

    def scratch_lines(d):
        out = []
        for s, T in trail.items():
            T = T[T[:, 0] <= d]
            if len(T) < 2:
                continue
            # split into contiguous runs (the pushing blade lifts between pushes)
            br = np.nonzero(np.diff(T[:, 0]) > 1.5)[0] + 1
            for run in np.split(T, br):
                if len(run) < 2:
                    continue
                age = (d - run[:, 0]) / 24.0
                a = np.clip(0.35 + 0.6 * run[:, 4], 0, 1) * np.exp(-age / 6.0)
                keep = a > 0.02
                run, a = run[keep], a[keep]
                if len(run) < 2:
                    continue
                P = run[:, 1:3]
                hd = run[:, 3]
                perp = np.c_[np.cos(hd), np.sin(hd)]
                ws = 0.7 + 0.8 * run[:, 4]
                out.append((P - perp * 0.008, a, ws))
                out.append((P + perp * 0.008, a * 0.8, ws * 0.8))
        return out

    # ice shavings: a spray of fine specks at each push-off, settling and fading over ~3 s
    shav = np.array(shav)
    NS = 14
    sproto = geo.proto_collection("P_shav")
    smat = look.cel("shaving", core.hexc("#eef3ff"), paint=0.0, soft=0.3, ao=0.0, alpha=0.9)
    sgrp = [x for x in smat.node_tree.nodes if x.type == "GROUP"][0]
    sat = _n(smat.node_tree, "ShaderNodeAttribute", (-300, -300), attribute_type="INSTANCER", attribute_name="tint")
    _l(smat.node_tree, sat.outputs["Fac"], sgrp.inputs["Alpha"])
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.012)
    geo.bm_to_object(bm, "speck", smat, sproto)
    ns = len(shav) * NS
    far = np.array([0.0, -1e4, -50.0])
    shav_obj = geo.instances("shavings", sproto, np.tile(far, (max(ns, 1), 1)), tint=np.zeros(max(ns, 1)), coll=env)
    srng = rng.normal(0, 1, (max(ns, 1), 3))

    # thread
    frames = list(range(start, end, 2))
    rope = rope_io.Owner("A", SCENE, rig, lambda t: (lambda J: J["pelvis"] + rot_z(heading(t)) @ np.array([0, -0.16, 0.0]))(world_pose(t)[0]),
                         frames, trail=(0.0, -1.0), warm=150, cfg_motion=False)

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.6, bloom_threshold=0.78, streak=0.14, streak_threshold=1.05, lift=(0.98, 0.99, 1.05),
                         gain=(1.02, 0.99, 1.0), vignette=0.3, ink=0.3, ink_normal=(0.45, 1.3)), res_scale=opt.scale)

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        Jw, fw, hd = world_pose(d)
        skater.set_world(Jw, hd)
        for s, (bp, on, pushing, strength) in fw.items():
            blades[s].location = (bp[0], bp[1], 0.012 + (0.0 if on else 0.06))
            blades[s].rotation_euler = (0, 0, hd + (0.0 if not pushing else (-0.6 if s == "l" else 0.6)))
        set_mesh(scratch_obj, *ribbons(scratch_lines(d), 0.01, 0.003))
        if ns:
            age = (d - np.repeat(shav[:, 0], NS)) / 24.0
            alive = (age >= 0) & (age < 3.0)
            bx = np.repeat(shav[:, 1:3], NS, axis=0)
            hdv = np.repeat(shav[:, 3], NS)
            out_dir = np.c_[np.cos(hdv), np.sin(hdv)] * np.sign(srng[:, 0])[:, None]
            travel = np.minimum(age, 0.4) / 0.4
            p = np.tile(far, (ns, 1))
            p[alive, :2] = bx[alive] + (out_dir[alive] * (0.15 + 0.12 * np.abs(srng[alive, 1]))[:, None] + srng[alive, :2] * 0.05) * travel[alive, None]
            p[alive, 2] = 0.004 + 0.05 * np.sin(np.pi * np.clip(age[alive] / 0.4, 0, 1))
            tint = np.where(alive, 0.9 * np.exp(-age / 1.2), 0.0)
            me = shav_obj.data
            me.vertices.foreach_set("co", p.astype(np.float32).ravel())
            me.attributes["tint"].data.foreach_set("value", tint.astype(np.float32))
            me.update()
        cx, cy = rig.pos(f)
        au.location = (cx, cy, 0.01)
        au.scale = (1080 / 2 / PPM, 1920 / 2 / PPM, 1)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])
    return r
