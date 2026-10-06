"""Scene 7 (frames 2078-2491): a teal paraglider high above grey canyon country with lichen plateaus,
rust patches, winding tracks and cloud wisps. The glider flies into a headwind (ground speed 1.9 px/frame,
airspeed far higher), so the red cord streams behind and below the pilot to the bottom edge."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, human, plants, rope_io
from kit.look import _n, _l, _math, _mixrgb

SCENE = 7
PPM = 30.0                         # ground scale (px per metre)
GLIDER_Z = 58.0                    # canopy height above the ground (ppm at canopy ~47)
SUN_DIR = (0.86, 0.38, 0.75)        # sun from the right, ~45 deg: ridges throw long soft shadows; glider shadow lower-left
GLIDER_SCREEN = (540, 1180)
POST = dict(light_deg=24.0, flow_deg=70.0, stroke_px=12.0, boil_mean=1.6, thread_shadow_px=0.0, thread_shadow_alpha=0.0, repaint=0.55)
TRACKS = [[(-30, -40), (-14, -20), (-6, 0), (-12, 18), (-2, 36), (8, 52), (4, 75), (14, 100), (6, 130)],
          [(30, -30), (18, -6), (22, 14), (10, 30), (16, 50), (26, 70), (18, 95), (24, 125)]]


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def terrain_base(X, Y):
    """ridged canyon relief + plateaus (metres)"""
    r = 1.0 - np.abs(geo.fbm2(X * 0.018 + 3, Y * 0.018, 4, 13) * 2.0)
    h = 13.0 * r ** 2.2 + 6.0 * geo.fbm2(X * 0.03, Y * 0.03, 4, 71) + 2.0 * geo.fbm2(X * 0.12, Y * 0.12, 3, 5)
    plateau = np.clip((h - 8.0) * 0.6, 0, 1)
    return 1.5 * (h - plateau * (h - 8.0) * 0.55)


def erode(H, step, iters=50, talus=0.9, carve=0.9):
    """thermal erosion (material slides where the slope exceeds the talus angle) + flow-accumulation gully carving"""
    H = H.copy()
    lim = talus * step
    for _ in range(iters):
        for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nb = np.roll(np.roll(H, dy, 0), dx, 1)
            d = H - nb
            mv = np.where(d > lim, (d - lim) * 0.25, 0.0)
            H -= mv
            H += np.roll(np.roll(mv, -dy, 0), -dx, 1)
    # D8 flow accumulation
    ny, nx = H.shape
    flat = H.ravel()
    order = np.argsort(-flat)
    acc = np.ones_like(flat)
    nbrs = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                nbrs.append((dy, dx, math.hypot(dy, dx)))
    Hp = np.pad(H, 1, mode="edge")
    best = np.full(H.shape, -1, np.int64)
    bslope = np.zeros(H.shape)
    yy, xx = np.mgrid[0:ny, 0:nx]
    for dy, dx, dl in nbrs:
        sl = (H - Hp[1 + dy:1 + dy + ny, 1 + dx:1 + dx + nx]) / dl
        tgt = np.clip(yy + dy, 0, ny - 1) * nx + np.clip(xx + dx, 0, nx - 1)
        m = sl > bslope
        best[m] = tgt[m]
        bslope[m] = sl[m]
    bflat = best.ravel()
    for k in order:
        t = bflat[k]
        if t >= 0:
            acc[t] += acc[k]
    A = acc.reshape(H.shape)
    g = np.log1p(A) / math.log1p(A.max())
    H -= carve * 4.0 * np.clip(g - 0.35, 0, None)
    return H, g


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
        hval.inputs["From Min"].default_value, hval.inputs["From Max"].default_value = -2.0, 13.0
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
        flat.inputs["From Min"].default_value, flat.inputs["From Max"].default_value = 0.82, 0.95
        high = _n(nt, "ShaderNodeMapRange", (-1500, -50), clamp=True)
        _l(nt, sx.outputs[2], high.inputs["Value"])
        high.inputs["From Min"].default_value, high.inputs["From Max"].default_value = -50.0, -40.0
        ln = _n(nt, "ShaderNodeTexNoise", (-1500, -200))
        _l(nt, geo_n.outputs["Position"], ln.inputs["Vector"])
        ln.inputs["Scale"].default_value = 0.03
        ln.inputs["Detail"].default_value = 3
        lm = _n(nt, "ShaderNodeMapRange", (-1300, -200), clamp=True)
        _l(nt, ln.outputs["Fac"], lm.inputs["Value"])
        lm.inputs["From Min"].default_value, lm.inputs["From Max"].default_value = 0.44, 0.52
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
        # sedimentary strata: warped height bands of orange / ochre / grey / cream on the slopes
        sw = _n(nt, "ShaderNodeTexNoise", (-1700, 900))
        _l(nt, geo_n.outputs["Position"], sw.inputs["Vector"])
        sw.inputs["Scale"].default_value = 0.04
        sz = _math(nt, "ADD", sx.outputs[2], _math(nt, "MULTIPLY", sw.outputs["Fac"], 3.0, (-1550, 900)), (-1450, 850))
        sb = _n(nt, "ShaderNodeValToRGB", (-1300, 900))
        crs = sb.color_ramp
        crs.interpolation = "EASE"
        bands = ["#8f96aa", "#c98a52", "#d9b673", "#9aa0b0", "#e2d6bf", "#b8743f", "#a3a8b6"]
        crs.elements[0].position, crs.elements[0].color = 0.0, core.hexc(bands[0])
        crs.elements[1].position, crs.elements[1].color = 1.0, core.hexc(bands[-1])
        for k_, h_ in enumerate(bands[1:-1]):
            e_ = crs.elements.new((k_ + 1) / (len(bands) - 1))
            e_.color = core.hexc(h_)
        _l(nt, _math(nt, "FRACT", _math(nt, "DIVIDE", sz, 5.5, (-1350, 850)), None, (-1250, 850)), sb.inputs[0])
        slope = _n(nt, "ShaderNodeMapRange", (-1300, 750), clamp=True)
        _l(nt, nz.outputs[2], slope.inputs["Value"])
        slope.inputs["From Min"].default_value, slope.inputs["From Max"].default_value = 0.92, 0.7
        rockc = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", slope.outputs["Result"], 0.75, (-1100, 750)), rockc,
                        _mixrgb(nt, "MULTIPLY", 1.0, sb.outputs[0], rkc.outputs[0], (-1100, 850)), (-950, 600))
        # CC0 rock detail (Poly Haven aerial_rocks_02) in the scene palette
        rockc = look.mul_color(nt, rockc, look.tex_value_detail(nt, "aerial_rocks_02", size_m=6.0, amount=0.35, loc=(-1700, 1200)), (-850, 650))
        # scree / talus at the foot of slopes (baked attribute) with CC0 scree texture
        scr = _n(nt, "ShaderNodeAttribute", (-1300, 1100), attribute_type="GEOMETRY", attribute_name="scree")
        screec = look.mul_color(nt, core.hexc("#b9bcc4"), look.tex_value_detail(nt, "rocky_terrain_03", size_m=3.0, amount=0.5, loc=(-1700, 1400)),
                                (-1000, 1100))
        rockc = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", scr.outputs["Fac"], 0.8, (-900, 1100)), rockc, screec, (-800, 700))
        # gullies darker blue-grey
        gul = _n(nt, "ShaderNodeAttribute", (-1300, 1250), attribute_type="GEOMETRY", attribute_name="gully")
        gm = _n(nt, "ShaderNodeMapRange", (-1150, 1250), clamp=True)
        _l(nt, gul.outputs["Fac"], gm.inputs["Value"])
        gm.inputs["From Min"].default_value, gm.inputs["From Max"].default_value = 0.4, 0.75
        rockc = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", gm.outputs["Result"], 0.6, (-1000, 1250)), rockc, core.hexc("#3b4258"), (-750, 750))
        c = _mixrgb(nt, "MIX", lich_mask, rockc, lich.outputs[0], (-850, 200))
        # rust patches
        rn = _n(nt, "ShaderNodeTexNoise", (-1100, -650))
        _l(nt, geo_n.outputs["Position"], rn.inputs["Vector"])
        rn.inputs["Scale"].default_value = 0.045
        rn.inputs["Detail"].default_value = 4
        rm = _n(nt, "ShaderNodeMapRange", (-900, -650), clamp=True)
        _l(nt, rn.outputs["Fac"], rm.inputs["Value"])
        rm.inputs["From Min"].default_value, rm.inputs["From Max"].default_value = 0.58, 0.64
        rust = _mixrgb(nt, "MIX", mot.outputs["Fac"], core.hexc("#8e4a36"), core.hexc("#d0662f"), (-750, -500))
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", rm.outputs["Result"], 0.9, (-750, -650)), c, rust, (-600, 100))
        # dirt tracks from the baked signed distance across each track: a pale bed with two darker tyre ruts
        td = _n(nt, "ShaderNodeAttribute", (-1100, -900), attribute_type="GEOMETRY", attribute_name="track")
        ad = _math(nt, "ABSOLUTE", td.outputs["Fac"], None, (-950, -900))
        bed = _n(nt, "ShaderNodeMapRange", (-800, -900), clamp=True, interpolation_type="SMOOTHSTEP")
        _l(nt, ad, bed.inputs["Value"])
        bed.inputs["From Min"].default_value, bed.inputs["From Max"].default_value = 1.4, 0.9
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", bed.outputs["Result"], 0.85, (-650, -900)), c, core.hexc("#d8d2c4"), (-500, 50))
        rut = _n(nt, "ShaderNodeMapRange", (-800, -1050), clamp=True, interpolation_type="SMOOTHSTEP")
        _l(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", ad, 0.62, (-950, -1050)), None, (-880, -1050)), rut.inputs["Value"])
        rut.inputs["From Min"].default_value, rut.inputs["From Max"].default_value = 0.22, 0.06
        c = _mixrgb(nt, "MULTIPLY", _math(nt, "MULTIPLY", rut.outputs["Result"], 0.35, (-650, -1050)), c, core.hexc("#8b8478"), (-400, 0))
        # haze settles in the low valleys
        hz = _n(nt, "ShaderNodeMapRange", (-800, -1250), clamp=True, interpolation_type="SMOOTHSTEP")
        _l(nt, sx.outputs[2], hz.inputs["Value"])
        hz.inputs["From Min"].default_value, hz.inputs["From Max"].default_value = 1.0, 6.0
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", hz.outputs["Result"], 0.32, (-650, -1250)), c, core.hexc("#d7dbe4"), (-300, 0))
        return c
    return look.cel("terrain", core.hexc("#8c909c"), shadow=(0.48, 0.52, 0.72, 1), high=(1.12, 1.1, 1.05, 1), t1=0.55, t2=0.95,
                    paint=0.05, paint_scale=1.6, base_node=base, rough=0.9, soft=0.18, ao=0.6, ao_dist=2.0)


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
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#c3c8d6"), 0.4)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.86, SUN_DIR, 0.3), core.hexc("#fff4e2"), angle_deg=2.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.3)
    step = 0.2
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    Xg, Yg = np.meshgrid(x0 + np.arange(nx + 2) * step, y0 + np.arange(ny + 2) * step)
    Hg, Gg = erode(terrain_base(Xg, Yg), step)
    hgrid = geo.HeightGrid(lambda X, Y: np.zeros_like(X), x0, y0, x0 + (nx + 0.5) * step, y0 + (ny + 0.5) * step, step)
    hgrid.Z = Hg
    hgrid.ny, hgrid.nx = Hg.shape
    global terrain
    terrain = lambda X, Y: hgrid(X, Y)
    ground = geo.grid("terrain", x0, y0, x1, y1, nx, ny, lambda X, Y: hgrid(X, Y), env, terrain_material())
    # baked attributes: gully (flow accumulation), scree (foot of steep slopes), signed distance across the tracks
    me = ground.data
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    gy_ = np.clip(((co[:, 1] - y0) / step).round().astype(int), 0, Gg.shape[0] - 1)
    gx_ = np.clip(((co[:, 0] - x0) / step).round().astype(int), 0, Gg.shape[1] - 1)
    gully = Gg[gy_, gx_]
    gyH, gxH = np.gradient(Hg, step)
    slope = np.hypot(gxH, gyH)
    lap = (np.roll(Hg, 1, 0) + np.roll(Hg, -1, 0) + np.roll(Hg, 1, 1) + np.roll(Hg, -1, 1) - 4 * Hg)
    scree_g = np.clip((lap / step ** 2) * 0.6, 0, 1) * np.clip(slope * 1.2, 0, 1)
    def blur(a, r=2):
        out = a.copy()
        for _ in range(r):
            out = (out + np.roll(out, 1, 0) + np.roll(out, -1, 0) + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 5.0
        return out
    scree = np.clip(blur(scree_g, 3) * 3.0, 0, 1)[gy_, gx_]
    # signed distance across the nearest track (polyline, metres)
    tdist = np.full(len(co), 99.0)
    for poly in TRACKS:
        P = np.array(poly, float)
        # densify with a smooth Catmull-like resample
        tt = np.linspace(0, len(P) - 1, (len(P) - 1) * 20)
        Px = np.interp(tt, np.arange(len(P)), P[:, 0])
        Py = np.interp(tt, np.arange(len(P)), P[:, 1])
        Q = np.c_[Px, Py]
        for _ in range(6):
            Q[1:-1] = 0.5 * Q[1:-1] + 0.25 * (Q[:-2] + Q[2:])
        for k in range(len(Q) - 1):
            a, b = Q[k], Q[k + 1]
            ab = b - a
            L2 = ab @ ab + 1e-9
            sel = (np.abs(co[:, 0] - a[0]) < 6) & (np.abs(co[:, 1] - a[1]) < 6)
            if not sel.any():
                continue
            pa = co[sel, :2] - a
            t = np.clip(pa @ ab / L2, 0, 1)
            dvec = pa - t[:, None] * ab
            dd = np.hypot(dvec[:, 0], dvec[:, 1])
            sgn = np.sign(ab[0] * pa[:, 1] - ab[1] * pa[:, 0])
            cur = tdist[sel]
            better = dd < np.abs(cur)
            cur[better] = (dd * sgn)[better]
            tdist[sel] = cur
    for nm_, arr in (("gully", gully), ("scree", scree), ("track", tdist)):
        at_ = me.attributes.new(nm_, "FLOAT", "POINT")
        at_.data.foreach_set("value", arr.astype(np.float32))
    me.update()
    # scattered scrub (dark leafy clumps) on gentle ground and boulders on the scree
    rng = np.random.default_rng(707)
    vp = geo.proto_collection("P_scrub")
    scrub_m = look.cel("scrub", core.hexc("#5d6b3f"), shadow=(0.5, 0.55, 0.65, 1), paint=0.03, soft=0.2, ao=0.5,
                       base_node=look.instancer_palette([core.hexc("#5d6b3f"), core.hexc("#717a45"), core.hexc("#4b5838"), core.hexc("#8a8a52")]))
    for i in range(3):
        plants.crown(f"scrub_{i}", scrub_m, vp, seed=700 + i, radius=1.0, height=0.8, n_clumps=10, leaves=40, leaf=0.2, core=True)
    boulder_m = look.cel("boulder", core.hexc("#a2a6b2"), shadow=(0.5, 0.52, 0.7, 1), paint=0.04, soft=0.2, ao=0.5,
                         base_node=look.instancer_palette([core.hexc("#a2a6b2"), core.hexc("#c2a07c"), core.hexc("#8d92a2")]))
    for i in range(3):
        geo.knobbly(f"zboulder_{i}", boulder_m, vp, seed=730 + i, subdiv=2, knob=0.45, flat=0.6, lumps=4)
    pts = geo.poisson(rng, 1400, x0, y0, x1, y1, 0.9)
    hs = hgrid(pts[:, 0], pts[:, 1])
    gx2 = np.clip(((pts[:, 0] - x0) / step).astype(int), 0, Hg.shape[1] - 1)
    gy2 = np.clip(((pts[:, 1] - y0) / step).astype(int), 0, Hg.shape[0] - 1)
    sl2 = slope[gy2, gx2]
    sc2 = scree_g[gy2, gx2]
    is_scrub = (sl2 < 0.5) & (rng.random(len(pts)) < 0.5)
    is_boulder = (sc2 > 0.05) | ((sl2 > 0.6) & (rng.random(len(pts)) < 0.2))
    keep = is_scrub | is_boulder
    pts, hs, is_b = pts[keep], hs[keep], is_boulder[keep]
    nk = len(pts)
    var = np.where(is_b, 3 + rng.integers(0, 3, nk), rng.integers(0, 3, nk))
    sz_ = np.where(is_b, rng.uniform(0.25, 0.8, nk), rng.uniform(0.35, 0.9, nk))
    geo.instances("scrub_boulders", vp, np.c_[pts, hs - 0.05], rot=np.c_[np.zeros(nk), np.zeros(nk), rng.uniform(0, 6.28, nk)],
                  scl=np.c_[sz_, sz_, sz_ * np.where(is_b, 0.7, 1.0)], variant=var, tint=rng.random(nk), coll=env)


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
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.55, 0.78
        a = _math(nt, "MINIMUM", _math(nt, "MULTIPLY", mr.outputs["Result"], dens, (-150, 0)), 0.92, (-80, 0))
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
    for i, (z, dens) in enumerate(((22.0, 1.3), (40.0, 1.1))):
        w = geo.grid(f"wisps{i}", x0 - 20, y0 - 20, x1 + 20, y1 + 20, 4, 4, None, env, wisp_mat(f"wisp{i}", i * 0.37, dens))
        w.location.z = z
        w.visible_shadow = i == 0

    # paraglider canopy + pilot
    teal = look.cel("canopy", core.hexc("#2f9692"), shadow=(0.55, 0.65, 0.78, 1), high=(1.2, 1.18, 1.12, 1), t1=0.4, t2=0.9, paint=0.04, soft=0.22, hero=True)
    teal2 = look.cel("canopy_b", core.hexc("#287f80"), shadow=(0.55, 0.65, 0.78, 1), high=(1.2, 1.18, 1.12, 1), t1=0.4, t2=0.9, paint=0.04, soft=0.22, hero=True)
    lead = look.cel("canopy_le", core.hexc("#1b4c57"), paint=0.0, soft=0.22, hero=True)
    under = look.cel("canopy_under", core.hexc("#d8e0dd"), shadow=(0.7, 0.75, 0.85, 1), paint=0.0, soft=0.22, hero=True)
    canopy = canopy_mesh("canopy", [teal, teal2, lead, under], ink)
    hm = dict(top=look.cel("pilot_top", core.hexc("#ece8e2"), paint=0.03), legs=look.cel("pilot_legs", core.hexc("#3a3a48"), paint=0.0),
              shoes=look.cel("pilot_shoes", core.hexc("#2a2628"), paint=0.0), hands=look.cel("pilot_hands", core.hexc("#d6a98f"), paint=0.0),
              skin=look.cel("pilot_skin", core.hexc("#d6a98f"), paint=0.0), hair=look.cel("pilot_hair", core.hexc("#2b2124"), paint=0.0))
    pilot = human.Human("pilot", hm, hair="long", coll=ink)
    harness = geo.knobbly("harness", look.cel("harness", core.hexc("#40465a"), paint=0.0), ink, seed=3, subdiv=2, knob=0.1, flat=0.7, lumps=2)
    harness.scale = (0.32, 0.55, 0.3)

    def glider_world(t):
        p = rig.screen_to_world(t, *GLIDER_SCREEN, GLIDER_Z)
        swing = math.radians(5.0) * math.sin(2 * math.pi * t / 110.0)
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
    hawk_b = look.cel("hawk", core.hexc("#7a5a3e"), paint=0.0, soft=0.22, hero=True)
    hawk_d = look.cel("hawk_d", core.hexc("#4e3a2a"), paint=0.0, soft=0.22, hero=True)
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
    mot = rope_io.C.owner_motion(SCENE)
    def harness_pt(t):
        p, swing, yaw = glider_world(t)
        return np.array([p[0] + mot(t)[0], p[1] - 0.4 - math.sin(swing) * 6.0, GLIDER_Z - 6.5])
    rope = rope_io.Owner("A", SCENE, rig, harness_pt, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,
                         heading_fn=lambda t: glider_world(t)[2],
                         ground_fn=lambda x, y: np.full_like(np.asarray(x, float), -1e4), surface_fn=lambda x, y: hgrid(x, y))
    # suspension lines: thin ribbons from the harness to the canopy underside (canopy local space)
    lines_m = look.cel("lines", core.hexc("#d9dcdc"), paint=0.0, soft=0.3, hero=True)
    lv_, lf_ = [], []
    for k_ in range(14):
        s_ = -0.9 + 1.8 * k_ / 13
        a_ = s_ * math.radians(62)
        top = np.array([math.sin(a_) * 6.0 * 1.1 * 0.97, 0.45 - 1.2 * s_ * s_, math.cos(a_) * 6.0 - 6.0 - 0.05])
        bot = np.array([0.0, -0.4, -6.5])
        dvec = top - bot
        side = np.cross(dvec, [0, 0, 1.0])
        side = side / (np.linalg.norm(side) + 1e-9) * 0.012
        i0 = len(lv_)
        lv_ += [bot - side, bot + side, top + side, top - side]
        lf_.append((i0, i0 + 1, i0 + 2, i0 + 3))
    lines_ob = geo.mesh_from_arrays("susp_lines", np.array(lv_), lf_, ink, False, lines_m)

    st = look.freestyle(ink, thickness=1.7, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.985, 0.995, 1.03), gain=(1.04, 1.01, 0.97),
                         vignette=0.24, ink=0.35, ink_normal=(0.45, 1.3)), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        p, swing, yaw = glider_world(d)
        breathe = 1.0 + 0.012 * math.sin(2 * math.pi * d / 40.0)
        Mc = Matrix.Translation((p[0] + mot(d)[0], p[1], GLIDER_Z)) @ Euler((-swing, 0, yaw)).to_matrix().to_4x4()
        canopy.matrix_world = Mc @ Matrix.Diagonal((breathe, 1, 1 / breathe, 1))
        lines_ob.matrix_world = Mc
        hp = harness_pt(d)
        M = Matrix.Translation(Vector(hp.tolist())) @ Euler((-swing, 0, yaw)).to_matrix().to_4x4()
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
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])
    return r
