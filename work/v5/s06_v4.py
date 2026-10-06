"""Scene 6 (frames 1674-2077): a heeled sailing dinghy crosses a clear turquoise lagoon. Sandy shallows,
winding deep channels, crusty coral heads, starfish, turtles; a manta glides up-left of the boat. The boat
and sail shadows fall on the seabed; a foam wake trails the stern and the red cord floats in it."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, boats, creatures, plants, rope_io
from kit.look import _n, _l, _math, _mixrgb

SCENE = 6
PPM = 90.0
SUN_DIR = (-0.42, 0.42, 0.8)
BOAT_SCREEN = (555, 1180)
POST = dict(light_deg=135.0, flow_deg=60.0, stroke_px=12.0, boil_mean=2.0, thread_shadow_px=1.8, thread_shadow_per_m=0.0, repaint=0.5)

# channels and large coral clusters, from the reference mosaic (world metres)
CHANNELS = [([(-9.0, 17.5), (-6.0, 18.6), (-3.33, 19.7), (-1.11, 21.7), (1.55, 23.3), (6.0, 24.8), (9.0, 25.4)], 0.95),
            ([(-9.0, 6.6), (-6.0, 6.17), (-2.89, 5.86), (0.22, 4.17), (2.89, 1.51), (6.0, -1.6), (9.0, -4.2)], 1.15),
            # v4: the deep turquoise channel the boat sails along (straight course)
            ([(0.15, -14.0), (0.25, 0.0), (0.1, 12.0), (0.2, 24.0), (0.15, 36.0)], 0.9)]
BOAT_X = (555 - 540) / 90.0
LAYER = dict(floor=0, coral=1, creature=2, surface=3, boat=4, land=5)
CORALS = [(-4.2, 11.7, 2.0), (4.66, 6.84, 1.55), (-4.2, 4.6, 1.8), (4.2, 3.3, 1.8), (2.44, -1.15, 1.8), (-2.9, -4.3, 2.2),
          (2.44, -5.6, 2.0), (-4.6, 19.0, 1.4), (4.5, 16.5, 1.2), (-5.0, -9.0, 1.6), (3.6, -11.0, 1.7), (-1.2, 26.5, 1.2)]


def islands_v4(ylo=-8.0, yhi=26.0):
    out = []
    for cx, cy, r in CORALS:
        R = r * 1.45
        if ylo - R < cy < yhi + R:
            left = BOAT_X - (R + 0.7 + 0.56 + 0.15)
            right = BOAT_X + (R + 2.6 + 0.56 + 0.15)
            if left < cx < right:
                cx = left if cx < BOAT_X + 0.5 else right
        out.append([cx, cy, r])
    for _ in range(30):                                   # resolve island-island overlaps (rims at 1.45 r)
        moved = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                (xi, yi, ri), (xj, yj, rj) = out[i], out[j]
                dd = math.hypot(xi - xj, yi - yj)
                need = 1.45 * (ri + rj) + 0.1
                if dd < need:
                    k = max(0.6, dd / need)
                    out[i][2] *= k
                    out[j][2] *= k
                    moved = True
        if not moved:
            break
    return [tuple(v) for v in out]


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
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
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
    def coral_leaf_base(nt):
        cl = _n(nt, "ShaderNodeAttribute", (-900, 300), attribute_type="GEOMETRY", attribute_name="cl")
        lv = _n(nt, "ShaderNodeAttribute", (-900, 100), attribute_type="GEOMETRY", attribute_name="lv")
        at = _n(nt, "ShaderNodeAttribute", (-900, -100), attribute_type="INSTANCER", attribute_name="tint")
        f = _math(nt, "FRACT", _math(nt, "ADD", cl.outputs["Fac"], _math(nt, "MULTIPLY", at.outputs["Fac"], 0.37, (-700, -100)), (-600, 200)), None, (-500, 200))
        ramp = _n(nt, "ShaderNodeValToRGB", (-350, 200))
        cr = ramp.color_ramp
        cr.interpolation = "CONSTANT"
        while len(cr.elements) < len(coral_cols):
            cr.elements.new(0.5)
        for i, c in enumerate(coral_cols):
            cr.elements[i].position = i / len(coral_cols)
            cr.elements[i].color = c
        _l(nt, f, ramp.inputs[0])
        val = _n(nt, "ShaderNodeMapRange", (-350, 0), clamp=True)
        _l(nt, lv.outputs["Fac"], val.inputs["Value"])
        val.inputs["To Min"].default_value, val.inputs["To Max"].default_value = 0.55, 1.25
        return look.mul_color(nt, ramp.outputs[0], val.outputs["Result"], (-100, 100))
    cmat = look.cel("coral", coral_cols[0], shadow=(0.55, 0.62, 0.8, 1), high=(1.15, 1.13, 1.05, 1), paint=0.04, base_node=coral_leaf_base,
                    rough=0.9, soft=0.2, ao=0.6, ao_dist=0.25, backface=True)
    for i in range(6):
        plants.crown(f"coral_{i}", cmat, protos, seed=40 + i, radius=1.0, height=0.9, n_clumps=26, leaves=55, leaf=0.12, flat=0.5,
                     core=True, clump_attr=True)
    palm_m = look.cel("palm", core.hexc("#5f8a45"), shadow=(0.5, 0.6, 0.6, 1), high=(1.15, 1.12, 1.0, 1), paint=0.04, soft=0.2, ao=0.4,
                      base_node=look.instancer_palette([core.hexc("#5f8a45"), core.hexc("#7aa054"), core.hexc("#4b7440")]))
    palms = geo.proto_collection("P_palm")
    for i in range(3):
        plants.grass_tuft(f"palm_{i}", palm_m, palms, seed=70 + i, n=(8, 13), height=0.55, lean=1.6)
    halo_m = look.cel("halo", core.hexc("#f2f4ea"), paint=0.0, soft=0.35, alpha=0.5, ao=0.0)
    hgrp = [x for x in halo_m.node_tree.nodes if x.type == "GROUP"][0]
    hat_ = _n(halo_m.node_tree, "ShaderNodeAttribute", (-400, -300), attribute_type="GEOMETRY", attribute_name="r")
    _l(halo_m.node_tree, _math(halo_m.node_tree, "MULTIPLY", _math(halo_m.node_tree, "SUBTRACT", 1.0, hat_.outputs["Fac"], (-250, -300)), 0.45, (-100, -300)),
       hgrp.inputs["Alpha"])
    hprot = geo.proto_collection("P_halo")
    nh = 32
    hv = [(0.0, 0.0, 0.0)] + [(math.cos(2 * math.pi * k / nh), math.sin(2 * math.pi * k / nh), 0.0) for k in range(nh)]
    hob = geo.mesh_from_arrays("halo", np.array(hv), [(0, 1 + k, 1 + (k + 1) % nh) for k in range(nh)], hprot, True, halo_m)
    ra = hob.data.attributes.new("r", "FLOAT", "POINT")
    ra.data.foreach_set("value", np.array([0.0] + [1.0] * nh, np.float32))
    rng = np.random.default_rng(606)
    ISL = islands_v4()
    pts, scl, var, tint = [], [], [], []
    for cx, cy, r in ISL:
        for _ in range(int(9 + r * 9)):
            a = rng.uniform(0, 6.28)
            rr = r * math.sqrt(rng.random())
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            s = rng.uniform(0.28, 0.6) * (1.2 - 0.5 * rr / r) * min(1.3, r)
            pts.append((x, y, -float(depth(x, y)) + s * 0.1))
            scl.append((s, s * rng.uniform(0.8, 1.2), s * rng.uniform(0.6, 1.0)))
            var.append(rng.integers(0, 6))
            tint.append(rng.random())
    def coral_ok(x, y):
        if depth(x, y) >= 0.9:
            return False
        if BOAT_X - (0.7 + 0.56 + 0.5) < x < BOAT_X + (2.6 + 0.56 + 0.5):     # clear of the course (hull + sail + 50 px)
            return False
        return all(math.hypot(x - cx, y - cy) > 1.45 * r + 0.6 for cx, cy, r in ISL)
    small = geo.poisson(rng, 60, x0, y0, x1, y1, 1.8, accept=coral_ok)
    CORAL_HEADS = []
    for x, y in small:
        s = rng.uniform(0.18, 0.42)
        CORAL_HEADS.append((x, y, s * 1.08))
        pts.append((x, y, -float(depth(x, y)) + s * 0.1))
        scl.append((s, s * rng.uniform(0.7, 1.3), s * 0.7))
        var.append(rng.integers(0, 6))
        tint.append(rng.random())
    pts = np.array(pts)
    n = len(pts)
    geo.instances("corals", protos, pts, rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)], scl=np.array(scl),
                  variant=np.array(var), tint=np.array(tint), coll=env)
    hp = np.array([(cx, cy, -float(depth(cx, cy)) + 0.015) for cx, cy, r in ISL])
    hr = np.array([r * 1.45 for cx, cy, r in ISL])
    geo.instances("halos", hprot, hp, scl=np.c_[hr, hr, np.ones(len(hr))], coll=env)
    pp = []
    for cx, cy, r in ISL:
        for _ in range(int(rng.integers(1, 4))):
            a = rng.uniform(0, 6.28)
            rr = r * 0.5 * math.sqrt(rng.random())
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            pp.append((x, y, -float(depth(x, y)) + 0.45))
    pp = np.array(pp)
    npp = len(pp)
    geo.instances("palms", palms, pp, rot=np.c_[np.zeros(npp), np.zeros(npp), rng.uniform(0, 6.28, npp)],
                  scl=np.repeat(rng.uniform(1.4, 2.2, npp)[:, None], 3, 1), variant=rng.integers(0, 3, npp), tint=rng.random(npp), coll=env)
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
    def manta_base(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-700, 0))
        tc = _n(nt, "ShaderNodeTexCoord", (-700, -200))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-550, -200))
        _l(nt, tc.outputs["Object"], sx.inputs[0])
        edge = _n(nt, "ShaderNodeMapRange", (-400, -200), clamp=True)
        _l(nt, _math(nt, "ABSOLUTE", sx.outputs[0], None, (-450, -250)), edge.inputs["Value"])
        edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 0.6, 2.0
        return _mixrgb(nt, "MIX", edge.outputs["Result"], core.hexc("#3c4f63"), core.hexc("#6e8494"), (-200, 0))
    manta_m = look.cel("manta", core.hexc("#45586a"), shadow=(0.55, 0.6, 0.78, 1), high=(1.15, 1.15, 1.15, 1), paint=0.03,
                       base_node=manta_base, soft=0.22, rim=0.3, hero=True)
    look.add_mask_aov(manta_m, "manta")
    manta = creatures.Manta("manta", manta_m, span=4.0, coll=ink)
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

    # fish schools: small silvery fish swirling around a drifting school centre
    fish_m = look.cel("fish", core.hexc("#c9d8dc"), shadow=(0.6, 0.7, 0.8, 1), paint=0.0, soft=0.25, ao=0.0)
    fprot = geo.proto_collection("P_fish")
    fv = np.array([(0, 0.11, 0), (0.025, 0.02, 0.01), (0.012, -0.06, 0), (0.035, -0.1, 0), (-0.035, -0.1, 0), (-0.012, -0.06, 0), (-0.025, 0.02, 0.01)])
    geo.mesh_from_faces("fishp", fv, [(0, 1, 2, 5, 6), (2, 3, 4, 5)], fprot, smooth=False, mat=fish_m)
    schools = []
    NF = 26
    for k, (sx_, sy_, vx_, vy_) in enumerate(((-2.5, 9.0, 0.012, 0.02), (3.0, 20.0, -0.01, 0.014), (-1.0, 27.0, 0.008, 0.024))):
        offs = np.clip(rng.normal(0, 1, (NF, 2)) * np.array([0.5, 0.32]), -1.0, 1.0)
        ph = rng.uniform(0, 6.28, NF)
        ob_ = geo.instances(f"school{k}", fprot, np.zeros((NF, 3)), coll=env)
        schools.append((ob_, sx_, sy_, vx_, vy_, offs, ph))

    # sailing dinghy, heeled to starboard, sail out to the right; sailor hiking out to port
    bm_ = dict(hull=look.cel("hull", core.hexc("#c38f58"), shadow=(0.6, 0.55, 0.62, 1), paint=0.08, paint_scale=6.0, soft=0.22, hero=True),
               inner=look.cel("hull_in", core.hexc("#cb9862"), shadow=(0.6, 0.55, 0.62, 1), paint=0.1, paint_scale=7.0, soft=0.22, hero=True),
               trim=look.cel("trim", core.hexc("#a8773f"), paint=0.05, soft=0.22, hero=True), seat=look.cel("seat", core.hexc("#d6a46c"), paint=0.08, paint_scale=8.0, soft=0.22, hero=True),
               metal=look.cel("metal", core.hexc("#5a5753"), paint=0.0, soft=0.22, hero=True))
    boat, parts = boats.rowboat("boat", bm_, L=3.4, B=1.3, D=0.42, coll=ink, transom=0.45)
    spar = look.cel("spar", core.hexc("#b98f5e"), paint=0.03, soft=0.22, hero=True)
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
    def sail_base(nt):
        tc = _n(nt, "ShaderNodeTexCoord", (-700, 0))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-550, 0))
        _l(nt, tc.outputs["Object"], sx.inputs[0])
        seam = _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "FRACT", _math(nt, "MULTIPLY", sx.outputs[2], 2.2, (-400, 0)), None,
                                                                                                   (-300, 0)), 0.5, (-200, 0)), None, (-100, 0)), 0.02, (0, 0))
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", seam, 0.5, (100, 0)), core.hexc("#f4f0e4"), core.hexc("#c9c2b0"), (200, 0))
    sail_mat = look.cel("sail", core.hexc("#f4f2ea"), shadow=(0.7, 0.72, 0.84, 1), high=(1.05, 1.05, 1.05, 1), paint=0.04, base_node=sail_base,
                        backface=True, soft=0.3, hero=True)
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
    hm = dict(top=look.cel("sailor_top", core.hexc("#2f3672"), shadow=(0.55, 0.55, 0.78, 1), paint=0.04, soft=0.22, hero=True),
              legs=look.cel("sailor_legs", core.hexc("#2a2e52"), paint=0.03, soft=0.22, hero=True), shoes=look.cel("sailor_shoes", core.hexc("#252225"), paint=0.0, soft=0.22, hero=True),
              hands=look.cel("sailor_hands", core.hexc("#d3a58a"), paint=0.0, soft=0.22, hero=True), skin=look.cel("sailor_skin", core.hexc("#d3a58a"), paint=0.0, soft=0.22, hero=True),
              hair=look.cel("sailor_hair", core.hexc("#231c20"), paint=0.03, soft=0.22, hero=True))
    sailor = human.Human("sailor", hm, hair="short", coll=ink)

    mot = rope_io.C.owner_motion(SCENE)
    def boat_frame(t):
        tt = min(max(t, start), end)
        p = rig.screen_to_world(tt, *BOAT_SCREEN, 0.0)
        return Vector((p[0] + mot(t)[0], p[1] + (min(t - start, 0) + max(t - end, 0)) * 3.51 / PPM, 0.0))
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
    wake = geo.Wake(hull_frame, start, end, rate=3, life=70.0, spread=0.55, decay=0.05, seed=6,
                    emit_points=((0.0, -1.7, 0.0), (0.55, -1.2, 1.0), (-0.55, -1.2, -1.0), (0.3, 0.9, 1.0), (-0.3, 0.9, -1.0)), jitter=0.1)
    MAXF = 900
    foam = geo.instances("foam", fproto, np.zeros((MAXF, 3)), scl=np.zeros((MAXF, 3)), coll=env)

    # cord floating in the wake
    def stern(t):
        return np.array(boat_matrix(t) @ Vector((0, -1.69, 0.06)))
    rope = rope_io.Owner("A", SCENE, rig, stern, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,
                         heading_fn=lambda t: boat_matrix(t).to_euler().z)

    st = look.freestyle(ink, thickness=1.8, res_scale=opt.scale)
    # ---------------------------------------------------------------- v4: creatures steer around everything
    # creatures (layer 2) as conservative circles: manta (wings incl.), 3 turtles, 3 fish schools
    obstacles = [(cx, cy, 1.45 * r) for cx, cy, r in ISL] + list(CORAL_HEADS)
    BOAT_R = 1.9                                           # hull circle (the sail is above the water: not an obstacle below)
    cre = []
    mp0 = manta_path(start)
    cre.append(dict(id="manta", R=2.05, p=np.array([mp0[0], mp0[1]]), v=np.zeros(2), vmax=0.03, goal=lambda t: np.array(manta_path(t)[:2])))
    for i, (tx, ty, vx, vy) in enumerate(((3.6, 14.0, -0.004, 0.012), (-3.4, 3.0, 0.005, 0.016), (4.2, 26.0, -0.006, 0.01))):
        cre.append(dict(id=f"turtle{i}", R=0.62, p=np.array([tx, ty]), v=np.array([vx, vy]), vmax=0.022, base=np.array([vx, vy])))
    for k, (sx_, sy_, vx_, vy_) in enumerate(((-2.5, 9.0, 0.012, 0.02), (3.0, 20.0, -0.01, 0.014), (-1.0, 27.0, 0.008, 0.024))):
        cre.append(dict(id=f"school{k}", R=1.35, p=np.array([sx_, sy_]), v=np.array([vx_, vy_]), vmax=0.03, base=np.array([vx_, vy_])))
    traj = {c["id"]: {} for c in cre}
    head = {c["id"]: {} for c in cre}
    hd_state = {c["id"]: math.atan2(-c["v"][0], c["v"][1] + 1e-9) for c in cre}
    for fr in range(start - 30, end + 3):
        bp = np.array(boat_frame(fr)[:2])
        movers = [(c["p"][0], c["p"][1], c["R"]) for c in cre]
        for ci, c in enumerate(cre):
            if "goal" in c:
                want = np.clip((c["goal"](fr) - c["p"]) * 0.05, -c["vmax"], c["vmax"])
            else:
                want = c["base"]
            v = 0.9 * c["v"] + 0.1 * want
            obs = obstacles + [(bp[0], bp[1], BOAT_R)] + [m for j, m in enumerate(movers) if j != ci]
            for ox, oy, orr in obs:
                dvec = c["p"] - np.array([ox, oy])
                dist = math.hypot(*dvec) + 1e-6
                need = 1.2 * (c["R"] + orr)
                if dist < need * 1.5:
                    v = v + dvec / dist * (need * 1.5 - dist) / need * 0.03
            sp = math.hypot(*v)
            if sp > c["vmax"]:
                v = v / sp * c["vmax"]
            c["v"] = v
            c["p"] = c["p"] + v
            # hard projection: never overlap anything (touching tolerance 2 cm)
            for _ in range(3):
                for ox, oy, orr in obs:
                    dvec = c["p"] - np.array([ox, oy])
                    dist = math.hypot(*dvec) + 1e-9
                    if dist < c["R"] + orr + 0.02:
                        c["p"] = np.array([ox, oy]) + dvec / dist * (c["R"] + orr + 0.02)
            want_h = math.atan2(-c["v"][0], c["v"][1] + 1e-9)
            dh = (want_h - hd_state[c["id"]] + math.pi) % (2 * math.pi) - math.pi
            hd_state[c["id"]] += max(-0.02, min(0.02, dh))
            traj[c["id"]][fr] = c["p"].copy()
            head[c["id"]][fr] = hd_state[c["id"]]
    col_rows = []

    def log_colliders(f):
        ppm_ = rig.ppm
        def add(id_, layer, x, y, rx, ry, deg):
            sx_, sy_ = rig.world_to_screen(f, (x, y, 0.0))
            if -300 < sx_ < 1380 and -300 < sy_ < 2220:
                col_rows.append(f"{f},{id_},{layer},{sx_:.1f},{sy_:.1f},{rx * ppm_:.1f},{ry * ppm_:.1f},{deg:.1f}")
        for i, (cx, cy, r) in enumerate(ISL):
            add(f"island{i}", LAYER["land"], cx, cy, 1.45 * r, 1.45 * r, 0.0)
        for i, (cx, cy, r) in enumerate(CORAL_HEADS):
            add(f"coral{i}", LAYER["coral"], cx, cy, r, r, 0.0)
        for c in cre:
            q = traj[c["id"]][f]
            add(c["id"], LAYER["creature"], q[0], q[1], c["R"], c["R"], 0.0)
        bp = boat_frame(f)
        add("boat", LAYER["boat"], bp[0], bp[1], 0.68, 1.72, 0.0)

    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.99, 1.0, 1.01), gain=(1.02, 1.01, 0.99),
                         vignette=0.22, ink=0.4), res_scale=opt.scale)
    look.register_mask_output("manta")
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        boat.matrix_world = boat_matrix(d)
        Mb = np.array(boat.matrix_world)
        Jw = {k: (Mb @ np.r_[v, 1.0])[:3] for k, v in sailor_pose(d).items()}
        sailor.set_world(Jw, math.pi / 2)
        mq = traj["manta"][d]
        manta.obj.location = (mq[0], mq[1], -0.12)
        manta.obj.rotation_euler = (0, 0, head["manta"][d])
        manta.pose(d, amp=0.08)
        for i, (tt, tx, ty, vx, vy) in enumerate(turtles):
            t = d - start
            q = traj[f"turtle{i}"][d]
            tt.shell.location = (q[0], q[1], -float(depth(q[0], q[1])) + 0.35)
            tt.shell.rotation_euler = (0, 0, head[f"turtle{i}"][d])
            tt.pose(t)
        log_colliders(f)
        W = wake.at(d, MAXF)
        z = np.full(MAXF, 0.012)
        s = W[:, 2] * 0.7
        geo.update_points(foam, np.c_[W[:, 0], W[:, 1], z], rot=np.c_[np.zeros(MAXF), np.zeros(MAXF), W[:, 3]],
                          scl=np.c_[s, s * 0.8, s])
        t_ = d - start
        for k_, (ob_, sx_, sy_, vx_, vy_, offs, ph) in enumerate(schools):
            cx, cy = traj[f"school{k_}"][d]
            heading = head[f"school{k_}"][d]
            R2 = np.array([[math.cos(heading), -math.sin(heading)], [math.sin(heading), math.cos(heading)]])
            o2 = offs @ R2.T * (1 + 0.15 * np.sin(t_ * 0.05 + ph))[:, None]
            px_ = cx + o2[:, 0] + 0.05 * np.sin(t_ * 0.3 + ph)
            py_ = cy + o2[:, 1]
            pz = np.array([-float(depth(a_, b_)) * 0.5 for a_, b_ in zip(px_, py_)])
            geo.update_points(ob_, np.c_[px_, py_, pz], rot=np.c_[np.zeros(len(px_)), np.zeros(len(px_)), heading + 0.25 * np.sin(t_ * 0.4 + ph)])
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    def finish(out):
        rope_io.export(out, [rope])
        with open(os.path.join(out, "colliders.csv"), "w") as fh:
            fh.write("frame,id,layer,cx,cy,rx,ry,deg\n")
            for row in col_rows:
                fh.write(row + "\n")
    r.finish = finish
    return r
