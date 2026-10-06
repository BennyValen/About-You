"""Scene 5 (frames 1314-1673): a rider on a horse walks up a valley between meandering dunes. Low sun from the
left: the steep lee faces of the ridges fall into purple shadow, and horse and rider throw a long side-profile
shadow to the right (cast by the real silhouette: legs, neck, head, tail, rider and hat, moving with the gait).

v3: a real horse (barrel, neck, head with ears, mane, swishing tail, four legs in a four-beat walk with planted
hooves), a seated rider with a wide hat and hands to the reins, dotted hoofprint pairs at the gait spacing that
persist, fine dust at the hooves, contour-following ripple lines with irregular spacing and painted variation,
CC0 sand grain, and the world-space rope dragging on the sand (high friction)."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector
from kit import core, look, geo, human, animals, rope_io
from kit.look import _n, _l, _math, _mixrgb

SCENE = 5
PPM = 95.0
SUN_DIR = (-0.8, -0.22, 0.62)
HORSE_SCREEN = (560, 1150)
RIDGES = [(-2.85, 0.0, 1.0), (3.0, 1.9, 1.0), (-6.7, 4.1, 1.2), (6.8, 2.7, 1.2)]   # base x, phase, height scale
POST = dict(light_deg=195.0, flow_deg=90.0, stroke_px=11.0, boil_mean=2.2, thread_shadow_px=2.0, repaint=0.5)


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def ridge_x(k, y):
    bx, ph, _ = RIDGES[k]
    return bx + 0.74 * np.sin(y * 0.44 + ph) + 0.36 * np.sin(y * 1.16 + ph * 2) + 0.42 * geo.fbm2(y * 0.21, ph * 3 + 0 * y, 2, k)


def dune_h(X, Y):
    """asymmetric dunes: gentle windward (west) slope up to a crest, steep lee (east) face"""
    h = np.zeros_like(X)
    for k in range(len(RIDGES)):
        u = X - ridge_x(k, Y)
        hs = RIDGES[k][2]
        wind = np.exp(-np.maximum(-u, 0) / 1.6)
        lee = np.exp(-np.maximum(u, 0) / 0.95)
        h = np.maximum(h, hs * np.where(u < 0, wind, lee) * 0.75)
    return h + 0.05 * geo.fbm2(X * 0.6, Y * 0.6, 3, 5)


def ripple_coord(nt, pos, loc=(-2400, 0)):
    """coordinate whose X runs across the ridges: lines follow the meandering dunes; spacing varies with noise"""
    sx = _n(nt, "ShaderNodeSeparateXYZ", (loc[0] + 150, loc[1]))
    _l(nt, pos, sx.inputs[0])
    s1 = _math(nt, "SINE", _math(nt, "MULTIPLY", sx.outputs[1], 0.44, (loc[0] + 300, loc[1] - 100)), None, (loc[0] + 400, loc[1] - 100))
    s2 = _math(nt, "SINE", _math(nt, "MULTIPLY", sx.outputs[1], 1.16, (loc[0] + 300, loc[1] - 180)), None, (loc[0] + 400, loc[1] - 180))
    meander = _math(nt, "ADD", _math(nt, "MULTIPLY", s1, 0.74, (loc[0] + 500, loc[1] - 100)), _math(nt, "MULTIPLY", s2, 0.36, (loc[0] + 500, loc[1] - 180)), (loc[0] + 600, loc[1] - 140))
    nz = _n(nt, "ShaderNodeTexNoise", (loc[0] + 300, loc[1] + 150))
    _l(nt, pos, nz.inputs["Vector"])
    nz.inputs["Scale"].default_value = 0.35
    nz.inputs["Detail"].default_value = 3
    irr = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", nz.outputs["Fac"], 0.5, (loc[0] + 450, loc[1] + 150)), 0.35, (loc[0] + 550, loc[1] + 150))
    xw = _math(nt, "SUBTRACT", sx.outputs[0], _math(nt, "MULTIPLY", meander, 0.85, (loc[0] + 700, loc[1] - 140)), (loc[0] + 800, loc[1] - 50))
    xw = _math(nt, "ADD", xw, irr, (loc[0] + 880, loc[1]))
    comb = _n(nt, "ShaderNodeCombineXYZ", (loc[0] + 950, loc[1] - 50))
    _l(nt, xw, comb.inputs[0])
    _l(nt, sx.outputs[1], comb.inputs[1])
    return comb.outputs[0], nz.outputs["Fac"]


def ripple_lines(nt, pos, loc=(-2400, 0)):
    co, nz = ripple_coord(nt, pos, loc)
    wv = _n(nt, "ShaderNodeTexWave", (loc[0] + 1100, loc[1] - 50), wave_type="BANDS", bands_direction="X", wave_profile="SIN")
    _l(nt, co, wv.inputs["Vector"])
    wv.inputs["Scale"].default_value = 2.6
    wv.inputs["Distortion"].default_value = 0.9
    wv.inputs["Detail"].default_value = 1.0
    wv.inputs["Detail Scale"].default_value = 0.4
    return wv.outputs["Fac"], nz


def sand_material():
    def height(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-2600, -300))
        rl, nz = ripple_lines(nt, g.outputs["Position"], (-2400, -300))
        grain = look.tex_height(nt, "aerial_sand", size_m=1.4, loc=(-1200, -700))
        return _math(nt, "ADD", rl, _math(nt, "MULTIPLY", grain, 0.35, (-900, -600)), (-700, -400))

    def base(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-2600, 300))
        pos = g.outputs["Position"]
        n1 = _n(nt, "ShaderNodeTexNoise", (-1000, 400))
        _l(nt, pos, n1.inputs["Vector"])
        n1.inputs["Scale"].default_value = 0.22
        n1.inputs["Detail"].default_value = 3
        c = _mixrgb(nt, "MIX", n1.outputs["Fac"], core.hexc("#e0946c"), core.hexc("#f0b47e"), (-800, 300))
        n2 = _n(nt, "ShaderNodeTexNoise", (-1000, 600))
        _l(nt, pos, n2.inputs["Vector"])
        n2.inputs["Scale"].default_value = 0.08
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", n2.outputs["Fac"], 0.4, (-850, 600)), c, core.hexc("#e7a08c"), (-650, 400))
        rl, nz = ripple_lines(nt, pos, (-2400, 0))
        # light ripple crests with varying contrast (painted, not machine-regular)
        lines = _n(nt, "ShaderNodeMapRange", (-700, 0), clamp=True)
        _l(nt, rl, lines.inputs["Value"])
        lines.inputs["From Min"].default_value, lines.inputs["From Max"].default_value = 0.7, 0.95
        amt = _math(nt, "MULTIPLY", lines.outputs["Result"], _math(nt, "ADD", 0.45, _math(nt, "MULTIPLY", nz, 0.7, (-700, -150)), (-600, -150)), (-500, -50))
        c = _mixrgb(nt, "MIX", amt, c, core.hexc("#ffe7c4"), (-400, 200))
        dk = _n(nt, "ShaderNodeMapRange", (-700, -250), clamp=True)
        _l(nt, rl, dk.inputs["Value"])
        dk.inputs["From Min"].default_value, dk.inputs["From Max"].default_value = 0.25, 0.05
        c = _mixrgb(nt, "MULTIPLY", _math(nt, "MULTIPLY", dk.outputs["Result"], 0.35, (-550, -250)), c, core.hexc("#d58a78"), (-300, 100))
        det = look.tex_value_detail(nt, "aerial_sand", size_m=1.4, amount=0.18, loc=(-1000, 900))
        return look.mul_color(nt, c, det, (-150, 200))

    return look.cel("sand", core.hexc("#eaa775"), shadow=(0.24, 0.24, 1.12, 1), high=(1.07, 1.08, 1.1, 1), t1=0.55, t2=0.95,
                    paint=0.06, paint_scale=2.4, base_node=base, height_node=height, bump=0.6, bump_dist=0.018, rough=0.95,
                    soft=0.12, ao=0.35, ao_dist=0.5)


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#c7a3c4"), 0.3)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.9, SUN_DIR, 0.18), core.hexc("#ffe2c2"), angle_deg=2.2)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.3)
    hg = geo.HeightGrid(dune_h, x0 - 3, y0 - 3, x1 + 3, y1 + 3, 0.05)
    nx, ny = int((x1 - x0) / 0.05), int((y1 - y0) / 0.05)
    geo.grid("dunes", x0, y0, x1, y1, nx, ny, hg, env, sand_material())
    rng = np.random.default_rng(505)

    coat = look.cel("horse", core.hexc("#ece6e0"), shadow=(0.6, 0.55, 0.8, 1), high=(1.08, 1.06, 1.03, 1), paint=0.05, paint_scale=6,
                    soft=0.24, rim=0.3, ao=0.5, ao_dist=0.25, hero=True)
    mane = look.cel("mane", core.hexc("#9c918f"), shadow=(0.55, 0.5, 0.72, 1), paint=0.08, paint_scale=14, soft=0.2, hero=True)
    hoofm = look.cel("hoof", core.hexc("#4a4048"), paint=0.0, soft=0.2, hero=True)
    horse = animals.Horse("horse", dict(coat=coat, mane=mane, hoof=hoofm), ink, scale=1.0)
    hm = dict(top=look.cel("rider_top", core.hexc("#6a5f78"), shadow=(0.55, 0.52, 0.78, 1), paint=0.04, soft=0.22, rim=0.25, hero=True),
              legs=look.cel("rider_legs", core.hexc("#4e4658"), paint=0.02, soft=0.2, hero=True),
              shoes=look.cel("rider_shoes", core.hexc("#2a2628"), paint=0.0, hero=True),
              hands=look.cel("rider_hands", core.hexc("#c9997c"), paint=0.0, hero=True),
              skin=look.cel("rider_skin", core.hexc("#c9997c"), paint=0.0, hero=True),
              hair=look.cel("rider_hair", core.hexc("#2a2124"), paint=0.0, hero=True))
    rider = human.Human("rider", hm, hair="short", coll=ink, bulk={"top": 1.2})
    hatm = look.cel("hat", core.hexc("#3b3442"), shadow=(0.6, 0.55, 0.8, 1), high=(1.3, 1.25, 1.2, 1), paint=0.0, soft=0.2, rim=0.3, hero=True)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.24, radius2=0.22, depth=0.025)
    brim = geo.bm_to_object(bm, "hat_brim", hatm, ink)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.12, 0.13, 0.09), verts=bm.verts)
    crown = geo.bm_to_object(bm, "hat_crown", hatm, ink)

    mot = rope_io.C.owner_motion(SCENE)
    def base_path(t):
        p = rig.screen_to_world(min(max(t, start), end), *HORSE_SCREEN, 0.0)
        y = p[1] + (min(t - start, 0) + max(t - end, 0)) * 2.88 / PPM
        return (p[0] + mot(t)[0], y)
    heading = lambda t: 0.0
    walk = animals.HorseWalk(horse, base_path, heading, start - 200, end + 20, stride=1.3,
                             ground=lambda x, y: hg(float(x), float(y)))

    # hoofprints: every plant of every hoof, appearing on contact, persistent (dotted pairs at the gait spacing)
    pm = look.cel("hoofprint", core.hexc("#b46c55"), shadow=(0.3, 0.28, 1.0, 1), paint=0.0, soft=0.25, ao=0.0)
    pproto = geo.proto_collection("P_print")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=6, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.06, 0.07, 0.01), verts=bm.verts)
    geo.bm_to_object(bm, "hp", pm, pproto)
    prints = []
    c0, c1 = int(walk.cycles(start - 200)) - 1, int(walk.cycles(end)) + 2
    for leg in animals.LEGS:
        off = animals.LEGS[leg][6]
        for ci in range(c0, c1):
            P, hdp = walk.plant(leg, ci)
            prints.append((walk.time_at_phase(ci + off), P[0], P[1], P[2], hdp))
    prints = np.array(prints)
    npr = len(prints)
    far = np.array([0.0, -1e4, -50.0])
    pr_obj = geo.instances("hoofprints", pproto, np.tile(far, (npr, 1)), rot=np.c_[np.zeros(npr), np.zeros(npr), prints[:, 4]], coll=env)

    # dust: small soft puffs kicked up when a hoof lifts, drifting with the wind and fading
    dm = look.cel("dust", core.hexc("#f3c9a0"), paint=0.0, soft=0.4, alpha=0.4, ao=0.0)
    dgrp = [n for n in dm.node_tree.nodes if n.type == "GROUP"][0]
    at = _n(dm.node_tree, "ShaderNodeAttribute", (-300, -300), attribute_type="INSTANCER", attribute_name="tint")
    _l(dm.node_tree, at.outputs["Fac"], dgrp.inputs["Alpha"])
    dproto = geo.proto_collection("P_dust")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.06)
    geo.bm_to_object(bm, "puff", dm, dproto)
    lifts = prints.copy()
    lifts[:, 0] = [walk.time_at_phase(walk.cycles(t) + walk.duty) for t in prints[:, 0]]
    ND = 6
    dust_obj = geo.instances("dust", dproto, np.tile(far, (npr * ND, 1)), scl=np.ones((npr * ND, 3)), tint=np.zeros(npr * ND), coll=env)
    drng = rng.normal(0, 1, (npr * ND, 3))

    # thread: rope from the saddle cantle, dragging on the sand
    frames = list(range(start, end, 2))
    rope = rope_io.Owner("A", SCENE, rig, walk.cantle, frames, trail=(0.0, -1.0), ground_fn=hg, warm=150, cfg_motion=False,
                         heading_fn=heading)

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.99, 0.98, 1.03), gain=(1.03, 1.0, 0.97),
                         vignette=0.24, ink=0.35, ink_normal=(0.55, 1.4), saturation=1.06), res_scale=opt.scale)

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        J, R, hd, ev = walk.pose(d)
        seat, Rs, _ = walk.saddle(d)
        RJ = animals.rider_joints(seat, Rs, d, 1.0, walk.cycles(d))
        rider.set_world(RJ, hd)
        hp = RJ["head"] + Rs @ np.array([0, 0.0, 0.11])
        brim.location = Vector(hp.tolist())
        brim.rotation_euler = (0, 0, hd)
        crown.location = Vector((hp + np.array([0, 0, 0.05])).tolist())
        pos = np.tile(far, (npr, 1))
        on = prints[:, 0] <= d
        pos[on] = prints[on, 1:4] + np.array([0, 0, 0.004])
        geo.update_points(pr_obj, pos)
        # dust puffs alive for 0.8 s after each lift-off
        age = (d - lifts[:, 0]) / 19.0
        alive = (age >= 0) & (age < 1)
        dp = np.tile(far, (npr * ND, 1))
        sc_ = np.full((npr * ND, 3), 0.01)
        tint = np.zeros(npr * ND)
        a = np.repeat(age, ND)
        al = np.repeat(alive, ND)
        base = np.repeat(lifts[:, 1:4], ND, axis=0)
        drift = np.c_[0.25 + 0.15 * drng[:, 0], 0.1 * drng[:, 1], 0.05 + 0.04 * np.abs(drng[:, 2])]
        dp[al] = base[al] + drift[al] * a[al, None] * 1.6 + np.c_[drng[al, 0] * 0.05, drng[al, 1] * 0.05, np.zeros(al.sum())]
        sc_[al] = (0.6 + 1.6 * a[al])[:, None] * np.array([1.0, 1.0, 0.6])
        tint[al] = 0.45 * (1 - a[al]) ** 1.5
        me = dust_obj.data
        me.vertices.foreach_set("co", dp.astype(np.float32).ravel())
        me.attributes["scl"].data.foreach_set("vector", sc_.astype(np.float32).ravel())
        me.attributes["tint"].data.foreach_set("value", tint.astype(np.float32))
        me.update()
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    if os.environ.get("S5_SHADOW_GATE"):
        # gate mode: the horse and rider cast their shadow on a plain white ground but are invisible to the camera
        white = bpy.data.materials.new("gate_white")
        white.use_nodes = True
        white.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1, 1, 1, 1)
        dunes = bpy.data.objects["dunes"]
        co_ = np.zeros(len(dunes.data.vertices) * 3, np.float32)
        dunes.data.vertices.foreach_get("co", co_)
        co_ = co_.reshape(-1, 3)
        co_[:, 2] = hg(co_[:, 0], co_[:, 1]) * 0.0 + 0.0      # flat ground: only the hero shadow remains
        dunes.data.vertices.foreach_set("co", co_.ravel())
        dunes.data.update()
        dunes.data.materials.clear()
        dunes.data.materials.append(white)
        for o in horse.all_objects() + rider.all_objects() + [brim, crown]:
            o.visible_camera = False
        for nm in ("hoofprints", "dust"):
            bpy.data.objects[nm].hide_render = True
        bpy.context.scene.render.use_freestyle = False

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])
    return r
