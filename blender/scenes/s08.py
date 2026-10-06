"""Scene 8 (frames 2492-2645), replaced in v3: a moonlit ski glide.

A skier glides down a snow slope at night through scattered pines, seen from above, in gentle carving S-turns.
Cold blue moonlight from the left throws long blue shadows from every pine; a warm headlamp pool lights the snow
ahead of the skier; powder sprays from the skis at each turn and sparkles in the moonlight; two parallel ski tracks
with soft edges stay cut into the snow behind; the snow has wind ripples, small drifts and CC0 snow texture.
The skier has a clear body (red jacket, dark trousers, helmet, gloves), skis and poles with pole plants at the turn
changes. The red thread streams behind in the wind with glints of ice crystals. Camera at a moderate constant speed
(like scene 4), on twos, dark palette so it still sits between the canyon and the lake."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector
from kit import core, look, geo, human, rope_io
from kit.look import _n, _l, _math, _mixrgb
from kit.human import ik2, standing, rot_z, L_UPPER, L_FORE, L_HAND, L_THIGH, L_SHIN
from scenes.s01 import conifer, tree_material

SCENE = 8
PPM = 80.0
SPEED = 4.0                          # px per frame (moderate, like scene 4)
MOON_DIR = (-0.85, 0.22, 0.42)       # low moon from the left: long blue shadows to the right
SKIER_SCREEN = (540, 1180)
TURN_A, TURN_HZ = 0.022, 0.22        # v4: a straight run with only tiny corrections (half-width m, rate)
POST = dict(light_deg=165.0, flow_deg=100.0, stroke_px=12.0, boil_mean=1.6, thread_shadow_px=1.6, thread_glow=0.22, thread_glints=6,
            repaint=0.5, grain=1.3)


def speed_profile():
    return lambda i: SPEED


def snow_h(X, Y):
    """gentle undulations and wind-built drifts (elongated along the wind)"""
    h = 0.6 * geo.fbm2(X * 0.07, Y * 0.07, 3, 81)
    h += 0.12 * geo.fbm2(X * 0.35 + Y * 0.12, Y * 0.08, 3, 82)
    return h


def snow_material():
    def base(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-1600, 200))
        pos = g.outputs["Position"]
        nz = _n(nt, "ShaderNodeTexNoise", (-1400, 300))
        _l(nt, pos, nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 0.12
        nz.inputs["Detail"].default_value = 3
        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#CBD6EA"), core.hexc("#D8E2F0"), (-1200, 300))
        # wind ripples: fine bands across the slope, broken up
        mp = _n(nt, "ShaderNodeMapping", (-1400, 0))
        _l(nt, pos, mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, 0.5)
        wv = _n(nt, "ShaderNodeTexWave", (-1200, 0), wave_type="BANDS", bands_direction="X", wave_profile="SIN")
        _l(nt, mp.outputs[0], wv.inputs["Vector"])
        wv.inputs["Scale"].default_value = 2.4
        wv.inputs["Distortion"].default_value = 2.5
        wv.inputs["Detail"].default_value = 2.0
        rp = _n(nt, "ShaderNodeMapRange", (-1000, 0), clamp=True)
        _l(nt, wv.outputs["Fac"], rp.inputs["Value"])
        rp.inputs["To Min"].default_value, rp.inputs["To Max"].default_value = 0.93, 1.05
        c = look.mul_color(nt, c, rp.outputs["Result"], (-850, 150))
        c = look.mul_color(nt, c, look.tex_value_detail(nt, "snow_field_aerial", size_m=3.0, amount=0.25, loc=(-1400, -300)), (-700, 150))
        return c

    def height(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-1600, -600))
        mp = _n(nt, "ShaderNodeMapping", (-1400, -600))
        _l(nt, g.outputs["Position"], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, 0.5)
        wv = _n(nt, "ShaderNodeTexWave", (-1200, -600), wave_type="BANDS", bands_direction="X", wave_profile="SIN")
        _l(nt, mp.outputs[0], wv.inputs["Vector"])
        wv.inputs["Scale"].default_value = 2.4
        wv.inputs["Distortion"].default_value = 2.5
        wv.inputs["Detail"].default_value = 2.0
        sn = look.tex_height(nt, "snow_field_aerial", size_m=3.0, loc=(-1200, -900), m="nor_gl")
        bw = _n(nt, "ShaderNodeRGBToBW", (-1000, -900))
        _l(nt, sn, bw.inputs[0])
        return _math(nt, "ADD", _math(nt, "MULTIPLY", wv.outputs["Fac"], 0.5, (-900, -600)), _math(nt, "MULTIPLY", bw.outputs[0], 0.4, (-850, -900)), (-700, -700))

    return look.cel("snow", core.hexc("#D8E2F0"), shadow=(0.136, 0.167, 0.316, 1), high=(1.0, 1.0, 1.0, 1), t1=0.45, t2=0.99, paint=0.04,
                    base_node=base, height_node=height, bump=0.3, bump_dist=0.02, rough=0.9, soft=0.2, ao=0.5, ao_dist=0.6, light_tint=1.0)


def line_material(name, color, strength=1.0, emissive=True):
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


def ribbons(lines, width, zfun):
    V, F, A = [], [], []
    for P, a, ws in lines:
        n = len(P)
        if n < 2:
            continue
        d = np.gradient(P, axis=0)
        d /= np.linalg.norm(d, axis=1)[:, None] + 1e-9
        nrm = np.c_[-d[:, 1], d[:, 0]]
        z = zfun(P[:, 0], P[:, 1])
        i0 = len(V)
        for i in range(n):
            w = width * ws[i] * 0.5
            V.append((P[i, 0] - nrm[i, 0] * w, P[i, 1] - nrm[i, 1] * w, z[i]))
            V.append((P[i, 0] + nrm[i, 0] * w, P[i, 1] + nrm[i, 1] * w, z[i]))
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


def snow_pine_material():
    def base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1000, 200))
        nz = _n(nt, "ShaderNodeTexNoise", (-800, 0))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 3.0
        nz.inputs["Detail"].default_value = 3
        at = _n(nt, "ShaderNodeAttribute", (-1000, 400), attribute_type="GEOMETRY", attribute_name="tip")
        tipv = _math(nt, "ADD", at.outputs["Fac"], _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.7, (-450, 300)), (-250, 350))
        mr = _n(nt, "ShaderNodeMapRange", (-150, 350), clamp=True)
        _l(nt, tipv, mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.08, 1.28
        needles = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#2C3764"), core.hexc("#454F78"), (-500, 0))
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", mr.outputs["Result"], 0.8, (-350, 300)), needles, core.hexc("#C9D3E8"), (-300, 100))
    return look.cel("snowpine", core.hexc("#3E4A7A"), shadow=(0.5, 0.54, 0.7, 1), high=(1.1, 1.1, 1.12, 1), t1=0.38, t2=0.92,
                    paint=0.04, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0, soft=0.3, ao=0.4, ao_dist=1.0, rim=0.5)


def ski_local(t, edge, height=1.8):
    """skier body pose (local frame, +Y forward): knees flexed, torso forward, hands forward with poles; the body
    angulates into the turn (edge > 0: turning right). Returns joints, ski centres (l, r), pole tips."""
    k = height / 1.72
    J = standing(height)
    crouch = 0.17 * k
    lean_f = 0.32
    for n in ("pelvis", "spine", "chest", "neck", "head", "sho_l", "sho_r", "hip_l", "hip_r", "hem_l", "hem_r", "hem_b"):
        J[n] = J[n] + np.array([0, -0.06 * k, -crouch])
        z = J[n][2] - J["pelvis"][2]
        if z > 0:
            J[n][1] += z * math.sin(lean_f)
            J[n][2] = J["pelvis"][2] + z * math.cos(lean_f)
    # angulation: hips/knees inside, upper body over the outside ski
    shift = 0.12 * edge * k
    for n in ("pelvis", "hip_l", "hip_r", "hem_l", "hem_r", "hem_b"):
        J[n] = J[n] + np.array([shift, 0, 0])
    skis = {}
    for s, sx in (("l", -1), ("r", 1)):
        foot = np.array([sx * 0.13 * k + shift * 1.4, 0.05, 0.1 * k])
        kne, ank = ik2(J[f"hip_{s}"], foot, L_THIGH * k, L_SHIN * k, np.array([0, 1.0, 0.2]))
        J[f"kne_{s}"], J[f"ank_{s}"] = kne, ank
        J[f"toe_{s}"] = ank + np.array([0, 0.18 * k, -0.06 * k])
        skis[s] = np.array([ank[0], ank[1] + 0.05, 0.0])
    poles = {}
    for s, sx in (("l", -1), ("r", 1)):
        sh = J[f"sho_{s}"]
        hand = sh + np.array([sx * 0.16, 0.34, -0.38]) * k
        el, wr = ik2(sh, hand, L_UPPER * k, L_FORE * k, np.array([sx * 0.6, -0.3, -1.0]))
        J[f"elb_{s}"], J[f"wri_{s}"] = el, wr
        J[f"hnd_{s}"] = wr + (wr - el) / (np.linalg.norm(wr - el) + 1e-9) * 0.08 * k
        poles[s] = (J[f"hnd_{s}"], np.array([sx * 0.34 * k, -0.95 * k, 0.05]))
    return J, skis, poles


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#a4a8b6"), 0.1)       # near-neutral fill: shadows keep the palette blue, not more
    core.sun(MOON_DIR, core.sun_irradiance_for(0.75, MOON_DIR, 0.08), core.hexc("#eceef4"), angle_deg=1.2, name="moon")
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.35)
    step = 0.1
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    hg = geo.HeightGrid(snow_h, x0 - 3, y0 - 3, x1 + 3, y1 + 3, step)
    geo.grid("snow", x0, y0, x1, y1, nx, ny, hg, env, snow_material())
    rng = np.random.default_rng(808)

    # scattered pines (two sizes), long blue moon shadows
    tproto = geo.proto_collection("P_pine")
    tm = snow_pine_material()
    for i in range(4):
        conifer(f"pine_{i}", tm, tproto, seed=80 + i)
    mot_x = lambda t: TURN_A * math.sin(2 * math.pi * TURN_HZ * t / 24.0)
    pts = geo.poisson(rng, 360, x0, y0, x1, y1, 2.4, accept=lambda x, y: abs(x - 0.0) > 2.2)
    n = len(pts)
    s = np.where(rng.random(n) < 0.6, rng.uniform(0.45, 0.62, n), rng.uniform(0.25, 0.36, n))
    geo.instances("pines", tproto, np.c_[pts, hg(pts[:, 0], pts[:, 1]) - 0.1], rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)],
                  scl=np.c_[s, s, s], variant=rng.integers(0, 4, n), coll=env)

    # skier
    hm = dict(top=look.cel("sk_jacket", core.hexc("#c9372f"), shadow=(0.45, 0.4, 0.75, 1), high=(1.2, 1.1, 1.05, 1), paint=0.04, soft=0.22, rim=0.4, hero=True),
              legs=look.cel("sk_pants", core.hexc("#2a2d3e"), paint=0.0, soft=0.2, rim=0.3, hero=True),
              shoes=look.cel("sk_boots", core.hexc("#d8d6dc"), paint=0.0, soft=0.2, hero=True),
              hands=look.cel("sk_gloves", core.hexc("#1d1e26"), paint=0.0, hero=True),
              skin=look.cel("sk_skin", core.hexc("#d0a48a"), paint=0.0, hero=True),
              hair=look.cel("sk_helmet", core.hexc("#e6e4ea"), high=(1.3, 1.3, 1.3, 1), paint=0.0, soft=0.18, rim=0.5, hero=True))
    skier = human.Human("skier", hm, hair="short", height=1.8, coll=ink, bulk={"top": 1.3, "legs": 1.15})
    skier.hair_scale = 1.15
    ski_m = look.cel("skis", core.hexc("#2d3c6a"), high=(1.6, 1.6, 1.6, 1), paint=0.0, soft=0.2, rim=0.4, hero=True)
    pole_m = look.cel("poles", core.hexc("#c8ccd8"), paint=0.0, hero=True)
    gog_m = look.cel("goggles", core.hexc("#F2C98A"), shadow=(0.4, 0.35, 0.5, 1), high=(1.5, 1.4, 1.2, 1), paint=0.0, soft=0.15, rim=0.6, hero=True)
    strap_m = look.cel("gog_strap", core.hexc("#232838"), paint=0.0, hero=True)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.19, 0.05, 0.07), verts=bm.verts)
    goggles = geo.bm_to_object(bm, "goggles", gog_m, ink, smooth=False)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, cap_tris=False, segments=20, radius1=0.125, radius2=0.125, depth=0.035)
    strap = geo.bm_to_object(bm, "gog_strap", strap_m, ink, smooth=True)
    skis, poles = {}, {}
    for sd in ("l", "r"):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(0.085, 1.7, 0.02), verts=bm.verts)
        skis[sd] = geo.bm_to_object(bm, f"ski_{sd}", ski_m, ink, smooth=False)
        pv = np.array([(-0.012, 0, 0), (0.012, 0, 0), (0.012, 0, 1), (-0.012, 0, 1)])
        poles[sd] = geo.mesh_from_arrays(f"pole_{sd}", pv, [(0, 1, 2, 3)], ink, False, pole_m)

    def base(t):
        tt = min(max(t, start), end)
        p = rig.screen_to_world(tt, *SKIER_SCREEN, 0.0)
        y = p[1] + (min(t - start, 0) + max(t - end, 0)) * SPEED / PPM
        return np.array([p[0] + mot_x(t), y])

    def heading(t):
        a, b = base(t - 1), base(t + 1)
        return math.atan2(-(b[0] - a[0]), b[1] - a[1])

    def world_pose(t):
        b = base(t)
        hd = heading(t)
        turn = heading(t + 2) - heading(t - 2)
        edge = max(-1.0, min(1.0, -turn * 18.0))
        R = rot_z(hd)
        gz = hg(float(b[0]), float(b[1]))
        b3 = np.array([b[0], b[1], gz])
        J, sk, pl = ski_local(t, edge)
        Jw = {k_: b3 + R @ v for k_, v in J.items()}
        skw = {k_: b3 + R @ v for k_, v in sk.items()}
        plw = {k_: (b3 + R @ h, b3 + R @ tp) for k_, (h, tp) in pl.items()}
        return Jw, skw, plw, hd, edge

    # headlamp: warm spot from the helmet, aimed ahead and down
    hl = bpy.data.lights.new("headlamp", "SPOT")
    hl.energy = 90.0
    hl.color = core.hexc("#F2C98A")[:3]
    hl.spot_size = math.radians(40)
    hl.spot_blend = 1.0
    hl.shadow_soft_size = 0.05
    hl.use_shadow = False
    hlo = bpy.data.objects.new("headlamp", hl)
    env.objects.link(hlo)
    cone_m = bpy.data.materials.new("lamp_cone")
    cone_m.use_nodes = True
    cnt = cone_m.node_tree
    cnt.nodes.clear()
    cout = _n(cnt, "ShaderNodeOutputMaterial", (600, 0))
    ctc = _n(cnt, "ShaderNodeTexCoord", (-900, 0))
    csx = _n(cnt, "ShaderNodeSeparateXYZ", (-700, 0))
    _l(cnt, ctc.outputs["Object"], csx.inputs[0])
    along = _math(cnt, "DIVIDE", csx.outputs[1], 6.0, (-550, 0), clamp=True)                 # 0 at the head, 1 at 6 m
    halfw = _math(cnt, "ADD", 0.08, _math(cnt, "MULTIPLY", along, 1.5, (-450, 100)), (-350, 100))
    q = _math(cnt, "DIVIDE", _math(cnt, "ABSOLUTE", csx.outputs[0], None, (-450, 200)), halfw, (-250, 150))
    side = _math(cnt, "POWER", _math(cnt, "SUBTRACT", 1.0, q, (-150, 150), clamp=True), 1.5, (-50, 150))
    fade = _math(cnt, "MULTIPLY", _math(cnt, "POWER", _math(cnt, "SUBTRACT", 1.0, along, (-350, -100)), 1.6, (-250, -100)),
                 _math(cnt, "GREATER_THAN", csx.outputs[1], 0.25, (-250, -200)), (-150, -100))
    ca = _math(cnt, "MULTIPLY", _math(cnt, "MULTIPLY", side, fade, (50, 50)), 0.28, (150, 50))
    # the pool on the snow: a soft elongated ellipse ahead (1.1 m x 2.4 m half-axes, centred 3.4 m ahead)
    ex = _math(cnt, "DIVIDE", csx.outputs[0], 1.1, (-450, -400))
    ey = _math(cnt, "DIVIDE", _math(cnt, "SUBTRACT", csx.outputs[1], 3.4, (-550, -500)), 2.4, (-450, -500))
    q2 = _math(cnt, "ADD", _math(cnt, "MULTIPLY", ex, ex, (-350, -400)), _math(cnt, "MULTIPLY", ey, ey, (-350, -500)), (-250, -450))
    pool = _math(cnt, "POWER", _math(cnt, "SUBTRACT", 1.0, q2, (-150, -450), clamp=True), 1.6, (-50, -450))
    ca = _math(cnt, "ADD", ca, _math(cnt, "MULTIPLY", pool, 0.55, (50, -450)), (200, -100))
    cem = _n(cnt, "ShaderNodeEmission", (300, 100))
    cem.inputs[0].default_value = core.hexc("#F2C98A")
    _l(cnt, ca, cem.inputs[1])                      # additive glow: the beam brightens the air, never greys it
    ctr = _n(cnt, "ShaderNodeBsdfTransparent", (300, -100))
    cmx = _n(cnt, "ShaderNodeAddShader", (450, 0))
    _l(cnt, ctr.outputs[0], cmx.inputs[0])
    _l(cnt, cem.outputs[0], cmx.inputs[1])
    _l(cnt, cmx.outputs[0], cout.inputs[0])
    cone_m.surface_render_method = "BLENDED"
    cone = geo.grid("lamp_cone", -2.0, 0.0, 2.0, 6.5, 2, 2, None, env, cone_m)
    cone.visible_shadow = False

    # ski tracks: sample each ski every frame from before the scene; grooves (dark) + moonlit rims
    tr = {"l": [], "r": []}
    spray = []
    for t in range(start - 200, end + 1):
        Jw, skw, plw, hd, edge = world_pose(float(t))
        for sd, p in skw.items():
            tr[sd].append((t, p[0], p[1], hd))
        if t % 2 == 0:
            for sd_, sg_ in (("l", 1.0), ("r", -1.0)):
                tail = skw[sd_] - np.array([-math.sin(hd), math.cos(hd), 0.0]) * 0.7
                spray.append((t, tail[0], tail[1], hd, sg_))
    tr = {k_: np.array(v) for k_, v in tr.items()}
    groove_m = line_material("groove", core.hexc("#56648F"), 0.9)
    rim_m = line_material("track_rim", core.hexc("#E4EAF6"), 0.95)
    grooves = bpy.data.objects.new("grooves", bpy.data.meshes.new("grooves"))
    rims = bpy.data.objects.new("rims", bpy.data.meshes.new("rims"))
    for o, m_ in ((grooves, groove_m), (rims, rim_m)):
        env.objects.link(o)
        o.data.materials.append(m_)
    moon_side = np.array([-MOON_DIR[0], -MOON_DIR[1]])
    moon_side /= np.linalg.norm(moon_side)

    def track_lines(d, rim=False):
        out = []
        for sd, T in tr.items():
            T = T[T[:, 0] <= d - 6]                   # the tracks start a little behind the ski tail
            if len(T) < 2:
                continue
            P = T[:, 1:3] - np.c_[-np.sin(T[:, 3]), np.cos(T[:, 3])] * 0.75
            a = np.full(len(P), 0.55 if not rim else 0.35)
            if rim:
                perp = np.c_[np.cos(T[:, 3]), np.sin(T[:, 3])]
                for sg in (-1.0, 1.0):
                    out.append(((P + perp * 0.06 * sg)[::2], a[::2], np.ones(len(P[::2]))))
                continue
            out.append((P[::2], a[::2], np.ones(len(P[::2]))))
        return out

    # powder spray: soft puffs flung outward from the outside ski at the turns, plus sparkling crystals
    spray = np.array(spray) if spray else np.zeros((0, 5))
    NS = 5
    sp_m = look.cel("powder", core.hexc("#E4EAF6"), paint=0.0, soft=0.4, alpha=0.6, ao=0.0, light_tint=1.0)
    sg = [x for x in sp_m.node_tree.nodes if x.type == "GROUP"][0]
    sat = _n(sp_m.node_tree, "ShaderNodeAttribute", (-300, -300), attribute_type="INSTANCER", attribute_name="tint")
    _l(sp_m.node_tree, sat.outputs["Fac"], sg.inputs["Alpha"])
    spp = geo.proto_collection("P_powder")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.06)
    geo.bm_to_object(bm, "puff", sp_m, spp, smooth=True)
    nsp = max(1, len(spray) * NS)
    far = np.array([0.0, -1e4, -50.0])
    spray_obj = geo.instances("spray", spp, np.tile(far, (nsp, 1)), tint=np.zeros(nsp), coll=env)
    srng = rng.normal(0, 1, (nsp, 3))
    sparkle_m = look.emissive("sparkle", (0.95, 0.97, 1.0, 1), 3.0)
    skp = geo.proto_collection("P_sparkle")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.012)
    geo.bm_to_object(bm, "sparkle", sparkle_m, skp)
    NK = 120
    spark_obj = geo.instances("sparkles", skp, np.tile(far, (NK, 1)), coll=env)

    # rope from the skier's lower back
    def attach(t):
        Jw, skw, plw, hd, edge = world_pose(t)
        return Jw["pelvis"] + rot_z(hd) @ np.array([0, -0.16, 0.02])
    rope = rope_io.Owner("A", SCENE, rig, attach, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,
                         heading_fn=heading,
                         ground_fn=lambda x, y: hg(x, y) + 0.01)

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.3, bloom_threshold=0.95, streak=0.05, streak_threshold=1.1, lift=(0.99, 0.99, 1.02),
                         gain=(1.02, 0.99, 1.0), vignette=0.32, ink=0.3, ink_normal=(0.45, 1.3)), res_scale=opt.scale)

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        Jw, skw, plw, hd, edge = world_pose(d)
        skier.set_world(Jw, hd)
        for sd in ("l", "r"):
            p = skw[sd]
            skis[sd].location = (p[0], p[1], p[2] + 0.02)
            skis[sd].rotation_euler = (0, 0.15 * edge, hd)       # both skis share the heading: always parallel
            h, tip = plw[sd]
            # pole plant: at the turn changes the inside pole touches down ahead
            plant = 0.0                   # v4: straight run, no pole plants
            tip = tip + (h - tip) * 0.0 + rot_z(hd) @ np.array([0, 0.9 * plant, 0])
            dv = h - tip
            L = np.linalg.norm(dv) + 1e-9
            ax = Vector((0, 0, 1)).rotation_difference(Vector((dv / L).tolist()))
            poles[sd].matrix_world = Matrix.Translation(Vector(tip.tolist())) @ ax.to_matrix().to_4x4() @ Matrix.Diagonal((1, 1, L, 1))
        head = Jw["head"]
        hc = head + rot_z(hd) @ np.array([0, 0.0, 0.1])
        goggles.location = Vector((hc + rot_z(hd) @ np.array([0, 0.12, 0.0])).tolist())
        goggles.rotation_euler = (0, 0, hd)
        strap.location = Vector(hc.tolist())
        strap.rotation_euler = (0, 0, hd)
        hlo.location = Vector((head + rot_z(hd) @ np.array([0, 0.3, 0.35])).tolist())
        aim = Vector((-math.sin(hd), math.cos(hd), -0.45)).normalized()      # low: a long soft pool ahead
        cone.location = (float(head[0]), float(head[1]), float(hg(float(head[0]), float(head[1]))) + 0.9)
        cone.rotation_euler = (0, 0, hd)
        hlo.rotation_euler = aim.to_track_quat("-Z", "Y").to_euler()
        set_mesh(grooves, *ribbons(track_lines(d), 0.07, lambda x, y: hg(x, y) + 0.004))
        set_mesh(rims, *ribbons(track_lines(d, True), 0.025, lambda x, y: hg(x, y) + 0.005))
        if len(spray):
            age = (d - np.repeat(spray[:, 0], NS)) / 24.0
            alive = (age >= 0) & (age < 1.4)
            bx = np.repeat(spray[:, 1:3], NS, axis=0)
            hdv = np.repeat(spray[:, 3], NS)
            sgn = np.repeat(spray[:, 4], NS)
            outv = np.c_[np.cos(hdv), np.sin(hdv)] * (-sgn)[:, None]
            back = -np.c_[-np.sin(hdv), np.cos(hdv)]
            u = np.minimum(age / 0.5, 1.0)
            P = np.tile(far, (nsp, 1))
            P[alive, :2] = bx[alive] + (outv[alive] * (0.12 + 0.12 * np.abs(srng[alive, 0]))[:, None] + back[alive] * 0.25 +
                                        srng[alive, :2] * 0.06) * u[alive, None]
            P[alive, 2] = hg(P[alive, 0], P[alive, 1]) + 0.12 * np.sin(np.pi * np.clip(age[alive] / 0.9, 0, 1)) + 0.02
            S = np.repeat((0.5 + 1.4 * np.clip(age, 0, 1.4))[:, None], 3, 1)
            T = np.where(alive, 0.32 * (1 - age / 1.4) ** 1.4, 0.0)
            me = spray_obj.data
            me.vertices.foreach_set("co", P.astype(np.float32).ravel())
            me.attributes["scl"].data.foreach_set("vector", S.astype(np.float32).ravel())
            me.attributes["tint"].data.foreach_set("value", T.astype(np.float32))
            me.update()
            # sparkles: a fresh random subset of the live spray particles each drawing (they twinkle on twos)
            live = np.nonzero(alive)[0]
            kr = np.random.default_rng(d)
            pick = kr.choice(live, min(NK, len(live)), replace=False) if len(live) else np.array([], int)
            SP = np.tile(far, (NK, 1))
            SP[:len(pick)] = P[pick] + kr.normal(0, 0.05, (len(pick), 3))
            spark_obj.data.vertices.foreach_set("co", SP.astype(np.float32).ravel())
            spark_obj.data.update()
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])
    return r
