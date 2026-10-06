"""Scene 11 (frames 3316-3647): a loose V of white cranes flies over peach-lavender cumulus; the camera keeps a
constant 4.97 px/frame right up to the cut at 3648.

v3: the cumulus is built from instanced billowy lobes (big domes, medium lobes on top, small cauliflower lobes at the
edges) with soft lavender undersides, bright peach rims on the lit side, ambient occlusion in the crevices and slow
churn at the edges, in three layers at different depths (nearer layers scroll faster), with wisps between them and
cloud-on-cloud shadows. Deep blue gaps open onto the rippled sea far below. Ten cranes with dark wingtips flap and
glide, banking with boid-like spacing, casting soft shadows on the clouds; the red thread streams from the lead."""
import json, math, os
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector, Euler
from kit import core, look, geo, creatures, rope_io
from kit.look import _n, _l, _math, _mixrgb

SCENE = 11
PPM = 92.0
BIRD_Z = 2.4
SUN_DIR = (-0.6, 0.5, 0.42)       # v4: light from the upper left
POST = dict(light_deg=140.0, flow_deg=80.0, stroke_px=24.0, fine_px=9.0, elong=3.0, boil_mean=2.0, thread_shadow_px=0.0,
            thread_shadow_alpha=0.0, repaint=0.62)       # long swirling strokes along the cloud contours
LAYERS = [(-3.0, 0.52, 31), (-14.0, 0.62, 37), (-30.0, 0.7, 41)]      # (z, coverage, seed): near -> far
# formation: screen positions measured from the source (lead first)
V = [(540, 1190), (370, 1320), (690, 1350), (230, 1450), (840, 1484), (110, 1616), (980, 1650), (700, 1800), (430, 1760), (300, 1900)]


def speed_profile():
    prof = json.load(open(os.path.join(core.ROOT, "work", "cam_profile.json")))[str(SCENE)]
    return lambda i: prof[min(i, len(prof) - 1)]


def cloud_height(X, Y, rng):
    """cauliflower cumulus: max of sphere caps at three scales inside a cover mask that thins along +Y"""
    Z = np.full_like(X, -1.6)
    x0, x1, y0, y1 = X.min(), X.max(), Y.min(), Y.max()
    dx = X[0, 1] - X[0, 0]
    cover = geo.fbm2(X * 0.07, Y * 0.07, 4, 31) + 0.5 - 0.010 * (Y - y0) + 0.12 * geo.fbm2(X * 0.3, Y * 0.3, 2, 3)
    inside = cover > 0.0
    for scale, n, rr, hh in ((1.0, 260, (2.6, 4.8), 0.55), (0.5, 900, (1.0, 2.0), 0.6), (0.25, 2600, (0.35, 0.8), 0.65)):
        cx = rng.uniform(x0, x1, n)
        cy = rng.uniform(y0, y1, n)
        r = rng.uniform(*rr, n)
        for i in range(n):
            i0, i1 = int((cx[i] - r[i] - x0) / dx), int((cx[i] + r[i] - x0) / dx) + 1
            j0, j1 = int((cy[i] - r[i] - y0) / dx), int((cy[i] + r[i] - y0) / dx) + 1
            i0, j0 = max(i0, 0), max(j0, 0)
            sx, sy = X[j0:j1, i0:i1], Y[j0:j1, i0:i1]
            if sx.size == 0:
                continue
            m = inside[j0:j1, i0:i1]
            if not m.any():
                continue
            c = cover[j0:j1, i0:i1]
            d2 = (sx - cx[i]) ** 2 + (sy - cy[i]) ** 2
            cap = np.sqrt(np.maximum(r[i] ** 2 - d2, 0)) * hh + np.minimum(c, 0.6) * 1.6 - 1.2 * (1 - scale)
            cap = np.where((d2 < r[i] ** 2) & m, cap, -1.6)
            Z[j0:j1, i0:i1] = np.maximum(Z[j0:j1, i0:i1], cap)
    return Z - 0.95


def build(opt):
    sc = core.reset(opt.scale, getattr(opt, "samples", 2))
    start, end = core.span(SCENE)
    rig = core.Rig(SCENE, PPM, speed_profile(), lens=60.0)
    core.world_ambient(core.hexc("#c8b8e0"), 0.58)
    core.sun(SUN_DIR, core.sun_irradiance_for(0.92, SUN_DIR, 0.34), core.hexc("#fff0e2"), angle_deg=3.0)
    ink = core.collection("INK")
    env = core.collection("ENV")
    x0, y0, x1, y1 = rig.path_rect(0.0, 1.35)
    rng = np.random.default_rng(1111)
    # ---------------------------------------------------------------- v4 clouds: a density field, no circles
    # domain-warped fractal noise (7 octaves, billowy + ridged mix, warped), smooth-thresholded into big irregular masses
    # with a fractal edge (bumps from ~4 m = 400 px down to ~0.2 m = 20 px); the cloud top is a height field derived from
    # the smoothed density, lit from the upper left (real shading, AO in the hollows). Main layer on the camera's
    # reference plane (z = 0) so it scrolls at the camera speed; a far, bluer layer below; near wisps above.
    def density(X, Y, seed, f0):
        wx = geo.fbm2(X * f0 * 0.6 + seed, Y * f0 * 0.6, 4, seed + 1)
        wy = geo.fbm2(X * f0 * 0.6 - seed, Y * f0 * 0.6 + 3.1, 4, seed + 2)
        Xw, Yw = X + 5.0 * wx, Y + 5.0 * wy
        b = geo.fbm2(Xw * f0, Yw * f0, 7, seed + 3)
        billow = 1.0 - np.abs(geo.fbm2(Xw * f0 * 2.1, Yw * f0 * 2.1, 6, seed + 4))
        ridge = 1.0 - np.abs(geo.fbm2(Xw * f0 * 4.3, Yw * f0 * 4.3, 5, seed + 5))
        return b + 0.35 * billow + 0.15 * ridge

    def cloud_layer(name, z, seed, f0, cover, hmax, step, mat):
        lx0, ly0, lx1, ly1 = rig.path_rect(z, 1.3)
        nx_, ny_ = int((lx1 - lx0) / step) + 1, int((ly1 - ly0) / step) + 1
        X, Y = np.meshgrid(lx0 + np.arange(nx_) * step, ly0 + np.arange(ny_) * step)
        D = density(X, Y, seed, f0)
        thr = np.quantile(D, 1.0 - cover)
        w = np.std(D) * 0.9
        u = np.clip((D - thr) / w, -0.4, 1.0)
        H = hmax * np.sign(u) * np.abs(u) ** 0.6
        H = np.where(u < 0, H * 2.5, H)        # edges roll down steeply (shadowed flanks)
        # small billows on the top for the painted cauliflower relief (still a field, no repeated lobes)
        # cauliflower relief at two scales (a field, not repeated lobes)
        H = H + (0.22 * hmax * np.abs(geo.fbm2(X * f0 * 5, Y * f0 * 5, 3, seed + 9))
                 + 0.10 * hmax * np.abs(geo.fbm2(X * f0 * 14, Y * f0 * 14, 3, seed + 10))) * np.clip(u * 3 + 0.3, 0, 1)
        Z = z + H
        keep = D > thr - 0.35 * w
        for _ in range(2):        # grow by one cell per pass (a skirt for the alpha cut)
            k2 = keep.copy()
            k2[1:] |= keep[:-1]; k2[:-1] |= keep[1:]; k2[:, 1:] |= keep[:, :-1]; k2[:, :-1] |= keep[:, 1:]
            keep = k2
        ids = -np.ones(X.shape, np.int64)
        ids[keep] = np.arange(keep.sum())
        V = np.c_[X[keep], Y[keep], Z[keep]]
        a, b_, c, d_ = ids[:-1, :-1], ids[:-1, 1:], ids[1:, 1:], ids[1:, :-1]
        ok = (a >= 0) & (b_ >= 0) & (c >= 0) & (d_ >= 0)
        F = np.c_[a[ok], b_[ok], c[ok], d_[ok]]
        ob = geo.mesh_from_arrays(name, V, F, env, True, mat)
        at = ob.data.attributes.new("dens", "FLOAT", "POINT")
        at.data.foreach_set("value", ((D[keep] - thr) / w).astype(np.float32))
        return ob, float((D > thr).mean())

    def cloud_mat(name, lit, mid, shadow, deep_ao, rim):
        def base(nt):
            g = _n(nt, "ShaderNodeNewGeometry", (-900, 200))
            nz = _n(nt, "ShaderNodeTexNoise", (-700, 200))
            _l(nt, g.outputs["Position"], nz.inputs["Vector"])
            nz.inputs["Scale"].default_value = 0.18
            nz.inputs["Detail"].default_value = 4
            return _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc(lit), core.hexc(mid), (-500, 200))
        def height(nt):
            g = _n(nt, "ShaderNodeNewGeometry", (-900, -300))
            nz = _n(nt, "ShaderNodeTexNoise", (-700, -300))
            _l(nt, g.outputs["Position"], nz.inputs["Vector"])
            nz.inputs["Scale"].default_value = 2.2
            nz.inputs["Detail"].default_value = 6
            return nz.outputs["Fac"]
        m = look.cel(name, core.hexc(lit), shadow=shadow, high=(1.12, 1.08, 1.02, 1), t1=0.72, t2=0.95, paint=0.03, base_node=base,
                     height_node=height, bump=0.35, bump_dist=0.06, rough=0.9, soft=0.3, ao=deep_ao, ao_dist=1.2, rim=rim)
        nt = m.node_tree
        grp = [n for n in nt.nodes if n.type == "GROUP"][0]
        at = _n(nt, "ShaderNodeAttribute", (-300, -500))
        at.attribute_name = "dens"
        at.attribute_type = "GEOMETRY"
        cut = _math(nt, "GREATER_THAN", at.outputs["Fac"], 0.0, (-100, -500))
        _l(nt, cut, grp.inputs["Alpha"])
        m.surface_render_method = "DITHERED"
        return m

    main_m = cloud_mat("cloud_main", "#FBEDE4", "#D2B9C4", (0.30, 0.26, 0.56, 1), 0.9, 0.35)
    far_m = cloud_mat("cloud_far", "#D2C3D2", "#B9ACC8", (0.44, 0.42, 0.70, 1), 0.6, 0.12)
    main_cloud, cov_main = cloud_layer("clouds_main", 0.0, 31, 0.11, 0.62, 1.5, 0.07, main_m)
    far_cloud, cov_far = cloud_layer("clouds_far", -22.0, 37, 0.15, 0.42, 0.9, 0.14, far_m)
    print(f"CLOUDS coverage main {cov_main:.2f} far {cov_far:.2f}", flush=True)
    # near wisps: thin semi-transparent streaks above the main layer, drifting faster (5-15 % of the frame)
    def wisp_mat(name, seed, dens):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = _n(nt, "ShaderNodeOutputMaterial", (500, 0))
        g = _n(nt, "ShaderNodeNewGeometry", (-900, 0))
        mp = _n(nt, "ShaderNodeMapping", (-700, 0))
        _l(nt, g.outputs["Position"], mp.inputs[0])
        mp.inputs["Scale"].default_value = (0.1, 0.022, 0.0)
        mp.inputs["Rotation"].default_value = (0, 0, 0.35 + seed)
        drv = mp.inputs["Location"].driver_add("default_value", 1).driver
        drv.type = "SCRIPTED"
        drv.expression = "floor(frame / 2) * 2 * -0.012"
        nz = _n(nt, "ShaderNodeTexNoise", (-500, 0), noise_dimensions="4D")
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["W"].default_value = seed * 10
        nz.inputs["Detail"].default_value = 7
        mr = _n(nt, "ShaderNodeMapRange", (-300, 0), clamp=True)
        _l(nt, nz.outputs["Fac"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.62, 0.8
        a = _math(nt, "MULTIPLY", mr.outputs["Result"], dens, (-150, 0))
        em = _n(nt, "ShaderNodeEmission", (0, 50))
        em.inputs[0].default_value = core.hexc("#F4E8E6")
        em.inputs[1].default_value = 0.95
        tr = _n(nt, "ShaderNodeBsdfTransparent", (0, -100))
        mx = _n(nt, "ShaderNodeMixShader", (250, 0))
        _l(nt, a, mx.inputs[0])
        _l(nt, tr.outputs[0], mx.inputs[1])
        _l(nt, em.outputs[0], mx.inputs[2])
        _l(nt, mx.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
        return m
    wx0, wy0, wx1, wy1 = rig.path_rect(1.5, 1.4)
    wisp = geo.grid("wisps_near", wx0, wy0, wx1, wy1, 4, 4, None, env, wisp_mat("wisp_near", 0.2, 0.5))
    wisp.location.z = 1.5
    wisp.visible_shadow = False
    lobe_objs = []
    # the sea far below, seen through the gaps: deep blue with fine wind ripples
    def below_base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, 200))
        mp = _n(nt, "ShaderNodeMapping", (-700, 200))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, 0.2)
        mp.inputs["Scale"].default_value = (0.08, 1.6, 1)
        nz = _n(nt, "ShaderNodeTexNoise", (-500, 200))
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 0.6
        nz.inputs["Detail"].default_value = 6
        fac = _math(nt, "POWER", nz.outputs["Fac"], 0.6, (-400, 200))       # bias towards the lighter gap blue
        return _mixrgb(nt, "MIX", fac, core.hexc("#2E3766"), core.hexc("#475082"), (-300, 200))
    bx0, by0, bx1, by1 = rig.path_rect(-80.0, 1.4)       # deep blue sea far below the gaps
    below = geo.grid("below", bx0, by0, bx1, by1, 4, 4, None, env,
                     look.cel("below", core.hexc("#3a4576"), paint=0.05, base_node=below_base, soft=0.2, ao=0.0))
    below.location.z = -80.0
    below.visible_shadow = False

    # cranes
    mw = look.cel("crane_white", core.hexc("#f6f4f1"), shadow=(0.72, 0.7, 0.86, 1), high=(1.04, 1.04, 1.04, 1), paint=0.03, soft=0.22, rim=0.3,
                  hero=True)
    mb = look.cel("crane_black", core.hexc("#2a2730"), paint=0.0, soft=0.2, hero=True)
    ml = look.cel("crane_leg", core.hexc("#3b3640"), paint=0.0, hero=True)
    birds = [creatures.Crane(f"crane{i}", mw, mb, ml, span=2.25 if i == 0 else 2.05, coll=ink) for i in range(len(V))]
    # simple boids: slot seeking + separation + alignment, deterministic integration over the scene
    n = len(V)
    frames = np.arange(start - 48, end + 2)
    slots = lambda f: np.array([rig.screen_to_world(f, sx, sy, BIRD_Z)[:2] for sx, sy in V])
    pos = slots(frames[0]) + rng.normal(0, 0.15, (n, 2))
    vel = np.tile(slots(frames[0] + 1)[0] - slots(frames[0])[0], (n, 1))
    track = {}
    for f in frames:
        tgt = slots(f)
        acc = (tgt - pos) * 0.02 - (vel - (slots(f + 1) - tgt)) * 0.08
        for i in range(n):
            dv = pos[i] - pos
            dist = np.linalg.norm(dv, axis=1) + 1e-6
            near = (dist < 1.6) & (dist > 1e-5)
            acc[i] += (dv[near] / dist[near][:, None] ** 2).sum(0) * 0.004
        acc[1:] += (vel.mean(0) - vel[1:]) * 0.02
        acc += 0.0002 * np.c_[np.sin(f * 0.031 + np.arange(n) * 1.7), np.cos(f * 0.023 + np.arange(n) * 2.3)]
        vel = vel + acc
        pos = pos + vel
        track[int(f)] = pos.copy()
    track_lead_z = lambda f: BIRD_Z + 0.08 * math.sin(f * 0.05)

    # cord streaming behind the lead crane (light thread: drag dominates gravity)
    def lead_attach(t):
        f0 = int(math.floor(t))
        a = track.get(f0, track[min(track)])
        b = track.get(f0 + 1, a)
        u = t - f0
        p = a[0] * (1 - u) + b[0] * u
        return np.array([p[0], p[1] - 0.25, track_lead_z(t) - 0.12])
    # the flock flies fast through the air (clouds far below drift slowly), so the cord streams back in the
    # relative wind with a gentle sag and sway, staying clear of the cloud tops
    rope = rope_io.Owner("A", SCENE, rig, lead_attach, list(range(start, end, 2)), trail=(0.0, -1.0), warm=40,
                         heading_fn=lambda t: math.atan2(-(track[int(t) + 2][0][0] - track[int(t)][0][0]), track[int(t) + 2][0][1] - track[int(t)][0][1])
                         if int(t) + 2 in track else 0.0,
                         ground_fn=lambda x, y: np.full_like(np.asarray(x, float), -1e4), surface_fn=lambda x, y: np.full_like(np.asarray(x, float), -3.0))

    st = look.freestyle(ink, thickness=1.6, res_scale=opt.scale)
    look.compositor(dict(kuwahara=3, bloom=0.4, bloom_threshold=0.92, streak=0.06, lift=(0.99, 0.98, 1.03), gain=(1.05, 1.02, 1.0),
                         vignette=0.22, ink=0.12, ink_normal=(0.9, 1.8)), res_scale=opt.scale)
    log = []

    def update(f):
        rig.apply(f)
        d = f - (f % 2)
        P = track[d]
        for i, b in enumerate(birds):
            v = track[d + 2][i] - track[d][i] if d + 2 in track else track[d][i] - track[d - 2][i]
            hd = math.atan2(-v[0], v[1])
            b.body.location = (P[i][0], P[i][1], BIRD_Z + 0.1 * math.sin(d * 0.05 + i))
            # bank into turns (roll from the turn rate)
            v0 = track[d][i] - track[d - 2][i] if d - 2 in track else v
            turn = math.atan2(v0[0] * v[1] - v0[1] * v[0], v0 @ v + 1e-9)
            b.body.rotation_euler = (0.04, max(-0.04, min(0.04, -turn * 25.0)) + 0.02 * math.sin(d * 0.04 + i), hd)
            # flap and glide: each bird alternates flapping bouts and glides (wings held, slightly raised)
            gliding = math.sin(d * 0.021 + i * 1.3) > 0.45
            b.pose(6.5 if gliding else d, phase=0.0 if gliding else i * 0.9)
        # slow churn of the small edge lobes
        for ob, P0, S0, ph, small in []:
            S = S0.copy()
            k = 1.0 + 0.05 * np.sin(d * 0.07 + ph) * small
            S *= k[:, None]
            geo.update_points(ob, P0, scl=S)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)

    class Run:
        pass
    r = Run()
    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])
    return r
