p = "blender/scenes/s10.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''from kit import core, look, geo, human, thread''', '''from kit import core, look, geo, human, rope_io''')
rep('''PAINT_BOIL = 0.45''', '''POST = dict(light_deg=70.0, flow_deg=90.0, stroke_px=11.0, boil_mean=2.1, thread_shadow_px=2.4, thread_shadow_per_m=6.0, repaint=0.5)
CANOPY = 1.05                          # flower-head height (the rope rides over it when the wind pushes it off the path)''')

i = s.index("def sunflower_proto(")
j = s.index("def build(opt):")
s = s[:i] + '''def seedhead_image(name="seedhead", size=512, n=900):
    """phyllotaxis seed disc painted procedurally (Vogel spiral, golden angle): dark seeds, lighter florets at the rim"""
    img = bpy.data.images.get(name)
    if img:
        return img
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size - 0.5
    rr = np.sqrt(xx * xx + yy * yy)
    base = np.zeros((size, size, 3), np.float32)
    base[:] = np.array([0.16, 0.09, 0.04])
    acc = np.zeros((size, size), np.float32)
    ga = math.pi * (3 - math.sqrt(5))
    for k in range(n):
        r = 0.47 * math.sqrt((k + 0.5) / n)
        a = k * ga
        cx, cy = 0.5 + r * math.cos(a), 0.5 + r * math.sin(a)
        rad = 0.0105 * (0.7 + 0.6 * r / 0.47)
        x0, x1 = int((cx - rad * 2) * size), int((cx + rad * 2) * size) + 1
        y0, y1 = int((cy - rad * 2) * size), int((cy + rad * 2) * size) + 1
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, size), min(y1, size)
        gy, gx = np.mgrid[y0:y1, x0:x1].astype(np.float32) / size
        d2 = (gx - cx) ** 2 + (gy - cy) ** 2
        acc[y0:y1, x0:x1] = np.maximum(acc[y0:y1, x0:x1], np.exp(-d2 / (2 * (rad * 0.55) ** 2)))
    seed = np.array([0.33, 0.2, 0.09])
    col = base * (1 - acc[..., None]) + seed * acc[..., None]
    # greenish centre, golden florets ring at the rim
    centre = np.exp(-(rr / 0.09) ** 2)[..., None]
    col = col * (1 - centre * 0.6) + np.array([0.32, 0.3, 0.1]) * centre * 0.6
    rim = np.clip((rr - 0.38) / 0.1, 0, 1)[..., None]
    col = col * (1 - rim * 0.55) + np.array([0.62, 0.42, 0.1]) * rim * 0.55
    rgba = np.concatenate([col, np.ones((size, size, 1), np.float32)], 2)
    img = bpy.data.images.new(name, size, size)
    img.colorspace_settings.name = "sRGB"
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    return img


def disc_material(name):
    def base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-800, 0), attribute_type="GEOMETRY", attribute_name="uvd")
        tx = _n(nt, "ShaderNodeTexImage", (-550, 0))
        tx.image = seedhead_image()
        _l(nt, at.outputs["Vector"], tx.inputs["Vector"])
        return tx.outputs["Color"]
    return look.cel(name, core.hexc("#4c311b"), shadow=(0.62, 0.55, 0.62, 1), high=(1.1, 1.08, 1.0, 1), paint=0.0, base_node=base, soft=0.22,
                    ao=0.4, ao_dist=0.05)


def sunflower_proto(name, coll, mats, seed, tilt=0.55, n_petals=24):
    """one mesh: stem, 5-6 heart-shaped drooping leaves, green sepals, 21-28 cupped petals with value variation
    ('pv' attribute), and the seed disc ('uvd' attribute -> painted phyllotaxis texture). Head faces the sun."""
    rng = np.random.default_rng(seed)
    V, F, M, UV, PV = [], [], [], [], []

    def add(verts, faces, mat, uv=None, pv=0.5):
        i0 = len(V)
        V.extend(verts)
        for f in faces:
            F.append(tuple(i0 + k for k in f))
            M.append(mat)
        UV.extend(uv if uv is not None else [(0.5, 0.5)] * len(verts))
        PV.extend([pv] * len(verts))
    # stem
    sides = 6
    for k in range(2):
        z0, z1 = k * 0.75, (k + 1) * 0.75
        ring0 = [(0.022 * math.cos(2 * math.pi * i / sides), 0.022 * math.sin(2 * math.pi * i / sides), z0) for i in range(sides)]
        ring1 = [(0.017 * math.cos(2 * math.pi * i / sides), 0.017 * math.sin(2 * math.pi * i / sides), z1) for i in range(sides)]
        add(ring0 + ring1, [(i, (i + 1) % sides, sides + (i + 1) % sides, sides + i) for i in range(sides)], 0)
    # leaves: heart shape, midrib fold, drooping tip
    for i in range(int(rng.integers(5, 7))):
        a = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(0.3, 0.46)
        z = 0.45 + i * 0.16 + rng.uniform(-0.03, 0.03)
        pts = []
        prof = [(0.0, 0.0), (0.18, 0.2), (0.4, 0.3), (0.62, 0.27), (0.82, 0.16), (1.0, 0.0)]
        for u, w in prof:
            pts.append((u, w))
        for u, w in reversed(prof[1:-1]):
            pts.append((u, -w))
        ca, sa = math.cos(a), math.sin(a)
        verts = [(0.0, 0.0, z)]
        for u, w in pts:
            droop = -0.18 * u * u * L
            fold = 0.04 * L * (1 - abs(w) / 0.3)
            x, y = u * L, w * L
            verts.append((x * ca - y * sa, x * sa + y * ca, z + droop + fold))
        nring = len(pts)
        add(verts, [(0, 1 + k, 1 + (k + 1) % nring) for k in range(nring)], 1, pv=rng.uniform(0.2, 0.8))
    # head frame: centre at the stem top, face normal toward the sun
    hz = 1.52
    axis = np.array([-0.94, 0.35, 0.0])
    axis /= np.linalg.norm(axis)
    c, s_ = math.cos(tilt), math.sin(tilt)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + s_ * K + (1 - c) * K @ K
    H = lambda p: tuple(R @ np.asarray(p, float) + np.array([0, 0, hz]))
    # sepals: ring of pointed green bracts behind the petals
    for k in range(14):
        a = 2 * math.pi * k / 14 + rng.uniform(-0.1, 0.1)
        ca, sa = math.cos(a), math.sin(a)
        r0, L = 0.09, rng.uniform(0.06, 0.09)
        add([H((r0 * ca - 0.02 * sa, r0 * sa + 0.02 * ca, -0.02)), H(((r0 + L) * ca, (r0 + L) * sa, -0.035)),
             H((r0 * ca + 0.02 * sa, r0 * sa - 0.02 * ca, -0.02))], [(0, 1, 2)], 1, pv=0.3)
    # petals: two layers, cupped, value variation
    npet = int(n_petals)
    for layer in range(2):
        for k in range(npet):
            a = 2 * math.pi * (k + 0.5 * layer) / npet + rng.uniform(-0.04, 0.04)
            ca, sa = math.cos(a), math.sin(a)
            L = rng.uniform(0.09, 0.13) * (0.92 if layer else 1.0)
            r0 = 0.083
            w = 0.022
            lift = 0.012 + 0.012 * layer
            pts = [(r0 * ca - w * sa, r0 * sa + w * ca, 0.0), ((r0 + L * 0.6) * ca - w * 1.15 * sa, (r0 + L * 0.6) * sa + w * 1.15 * ca, lift),
                   ((r0 + L) * ca, (r0 + L) * sa, lift * 0.6), ((r0 + L * 0.6) * ca + w * 1.15 * sa, (r0 + L * 0.6) * sa - w * 1.15 * ca, lift),
                   (r0 * ca + w * sa, r0 * sa - w * ca, 0.0)]
            add([H(q) for q in pts], [(0, 1, 2, 3, 4)], 2, pv=rng.uniform(0, 1))
    # seed disc: fan with uv
    nseg = 28
    verts = [H((0, 0, 0.012))]
    uv = [(0.5, 0.5)]
    for k in range(nseg):
        a = 2 * math.pi * k / nseg
        verts.append(H((0.088 * math.cos(a), 0.088 * math.sin(a), 0.0)))
        uv.append((0.5 + 0.5 * math.cos(a), 0.5 + 0.5 * math.sin(a)))
    add(verts, [(0, 1 + k, 1 + (k + 1) % nseg) for k in range(nseg)], 3, uv=uv)
    ob = geo.mesh_from_faces(name, np.array(V), F, coll, smooth=True)
    me = ob.data
    for m in (mats["stem"], mats["leaf"], mats["petal"], mats["disc"]):
        me.materials.append(m)
    me.polygons.foreach_set("material_index", np.array(M, np.int32))
    a = me.attributes.new("uvd", "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", np.c_[np.array(UV, np.float32), np.zeros(len(UV), np.float32)].ravel())
    b = me.attributes.new("pv", "FLOAT", "POINT")
    b.data.foreach_set("value", np.array(PV, np.float32))
    me.update()
    return ob


''' + s[j:]

rep('''    sc = core.reset(opt.scale, getattr(opt, "samples", 8))''', '''    sc = core.reset(opt.scale, getattr(opt, "samples", 2))''')
# materials: muted olive leaves with per-leaf value, golden petals with per-petal value, painted seed disc
rep('''    mats = dict(stem=look.cel("sf_stem", core.hexc("#6b7440"), paint=0.0),
                leaf=look.cel("sf_leaf", core.hexc("#7e7d4f"), shadow=(0.6, 0.6, 0.62, 1), high=(1.15, 1.13, 1.05, 1), paint=0.08, backface=True),
                disc=look.cel("sf_disc", core.hexc("#4c311b"), paint=0.15, paint_scale=30.0),
                petal=look.cel("sf_petal", core.hexc("#e7b52f"), shadow=(0.75, 0.62, 0.55, 1), high=(1.1, 1.08, 0.98, 1), paint=0.05, backface=True))
    for i in range(4):
        sunflower_proto(f"sf_{i}", protos, mats, seed=100 + i, tilt=0.45 + 0.08 * i)''', '''    def pv_ramp(c0, c1):
        def build_(nt):
            at = _n(nt, "ShaderNodeAttribute", (-700, 100), attribute_type="GEOMETRY", attribute_name="pv")
            it = _n(nt, "ShaderNodeAttribute", (-700, -100), attribute_type="INSTANCER", attribute_name="tint")
            v = _math(nt, "ADD", _math(nt, "MULTIPLY", at.outputs["Fac"], 0.7, (-550, 100)), _math(nt, "MULTIPLY", it.outputs["Fac"], 0.3, (-550, -100)), (-450, 0))
            return _mixrgb(nt, "MIX", v, core.hexc(c0), core.hexc(c1), (-300, 0))
        return build_
    mats = dict(stem=look.cel("sf_stem", core.hexc("#6b6c3c"), paint=0.0, soft=0.2),
                leaf=look.cel("sf_leaf", core.hexc("#6f6d3e"), shadow=(0.55, 0.55, 0.6, 1), high=(1.15, 1.12, 1.02, 1), paint=0.04, backface=True,
                              base_node=pv_ramp("#575a30", "#8a8550"), soft=0.2, ao=0.55, ao_dist=0.3),
                disc=disc_material("sf_disc"),
                petal=look.cel("sf_petal", core.hexc("#e7b52f"), shadow=(0.75, 0.6, 0.55, 1), high=(1.1, 1.07, 0.97, 1), paint=0.03, backface=True,
                               base_node=pv_ramp("#d99a22", "#f4cc48"), soft=0.22, ao=0.35, ao_dist=0.05))
    for i in range(5):
        sunflower_proto(f"sf_{i}", protos, mats, seed=100 + i, tilt=0.42 + 0.07 * i, n_petals=21 + i * 2)''')
rep('''    sf = geo.instances("sunflowers", protos, np.c_[pts, np.zeros(n)], rot=np.c_[np.zeros(n), np.zeros(n), sf_rot0],
                       scl=np.c_[sf_scale, sf_scale, sf_scale], variant=rng.integers(0, 4, n), coll=env)''', '''    sf = geo.instances("sunflowers", protos, np.c_[pts, np.zeros(n)], rot=np.c_[np.zeros(n), np.zeros(n), sf_rot0],
                       scl=np.c_[sf_scale, sf_scale, sf_scale], variant=rng.integers(0, 5, n), tint=rng.random(n), coll=env)''')
# denser, less grid-like planting
rep('''    for xr in np.arange(x0, x1, 0.62):
        for yr in np.arange(y0, y1, 0.46):
            x = xr + rng.normal(0, 0.05)
            y = yr + rng.normal(0, 0.05) + (0.23 if int((xr - x0) / 0.62) % 2 else 0)''', '''    for xr in np.arange(x0, x1, 0.55):
        for yr in np.arange(y0, y1, 0.42):
            x = xr + rng.normal(0, 0.07)
            y = yr + rng.normal(0, 0.08) + (0.21 if int((xr - x0) / 0.55) % 2 else 0)''')
# ground: CC0 soil and straw detail
rep('''        soil = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#4a3420"), core.hexc("#64482b"), (-1400, 400))''', '''        soil = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#4a3420"), core.hexc("#64482b"), (-1400, 400))
        soil = look.mul_color(nt, soil, look.tex_value_detail(nt, "forest_ground_04", size_m=1.5, amount=0.3, loc=(-1800, 700)), (-1300, 450))''')
rep('''        dirt = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#c9b07a"), core.hexc("#d8c18c"), (-1200, -100))''', '''        dirt = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#c9b07a"), core.hexc("#d8c18c"), (-1200, -100))
        dirt = look.mul_color(nt, dirt, look.tex_value_detail(nt, "brown_mud_02", size_m=1.4, amount=0.25, loc=(-1800, -500)), (-1100, -150))''')
rep('''    return look.cel("ground", core.hexc("#c9a865"), shadow=(0.55, 0.45, 0.6, 1), high=(1.08, 1.05, 1.0, 1), t1=0.42, t2=0.97,
                    paint=0.18, paint_scale=2.2, base_node=base, rough=0.9)''', '''    return look.cel("ground", core.hexc("#c9a865"), shadow=(0.55, 0.45, 0.6, 1), high=(1.08, 1.05, 1.0, 1), t1=0.42, t2=0.97,
                    paint=0.06, paint_scale=2.2, base_node=base, rough=0.9, soft=0.16, ao=0.5, ao_dist=0.4)''')
# walker: hat, hero flags, rope
rep('''    walker = human.Human("walker", hm, hair="long", coll=ink)''', '''    for m_ in hm.values():
        g_ = [x for x in m_.node_tree.nodes if x.type == "GROUP"][0]
        g_.inputs["Hero"].default_value = 1.0
        g_.inputs["Soft"].default_value = 0.22
    walker = human.Human("walker", hm, hair="long", height=1.8, coll=ink, bulk={"top": 1.2})
    hat_m = look.cel("w_hat", core.hexc("#e6cf93"), shadow=(0.62, 0.55, 0.6, 1), high=(1.1, 1.08, 1.0, 1), paint=0.06, paint_scale=60, soft=0.2,
                     rim=0.3, hero=True)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.23, radius2=0.2, depth=0.02)
    hat_brim = geo.bm_to_object(bm, "w_hat_brim", hat_m, ink)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=8, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.11, 0.12, 0.08), verts=bm.verts)
    hat_crown = geo.bm_to_object(bm, "w_hat_crown", hat_m, ink)''')
rep('''    wk = human.Walker(path.pos, path.heading, start - 120, end + 20, height=1.72, ground=gfun, arm_swing=0.38)''', '''    mot = rope_io.C.owner_motion(SCENE)
    wk = human.Walker(lambda t: (path.pos(t)[0] + mot(t)[0], path.pos(t)[1]), path.heading, start - 120, end + 20, height=1.8, ground=gfun,
                      arm_swing=0.42)''')
rep('''    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    def attach(t):
        Jw, hd, _ = wk.pose(t)
        return wk.waist_back(Jw, hd)
    def breeze(x, y, t):
        return 0.9 * np.sin(y * 1.3 + t * 0.02) + 0.5 * np.sin(y * 3.1 - t * 0.035), np.zeros_like(y)
    cord = thread.Cord(n_seg=200, length=12.0, mode="ground", ground=lambda x, y: np.zeros_like(x) + 0.01, friction=0.55,
                       substeps=6, iters=22, push=breeze, bend=0.1)
    sim = cord.run(list(range(start, end)), attach, (0.0, -1.0), warm=110)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.6)''', '''    # rope: lies on the path; where the wind pushes it over the field it rides on the flower heads
    def canopy(x, y):
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        on_path = np.abs(x - PATH_X - 0.06 * np.sin(y * 0.3)) < 0.62
        field = (~on_path) & ~((x < PATH_X - 0.48) & ((y - (ROAD_Y0 + ROAD_K * x)) * 0.978 > 0.35) & (y < 15.5))
        return np.where(field, CANOPY, 0.01)
    rope = rope_io.Owner("A", SCENE, rig, wk.attach, list(range(start, end, 2)), trail=(0.0, -1.0), ground_fn=canopy, surface_fn=canopy,
                         warm=150, cfg_motion=False)''')
rep('''    look.compositor(dict(kuwahara=10, bloom=0.45, bloom_threshold=0.92, streak=0.12, lift=(0.99, 0.99, 1.02), gain=(1.05, 1.01, 0.94),
                         vignette=0.3, grain=0.03, ink=0.5, ink_normal=(0.5, 1.4), saturation=1.05), res_scale=opt.scale)''',
    '''    look.compositor(dict(kuwahara=3, bloom=0.4, bloom_threshold=0.92, streak=0.08, lift=(1.0, 0.99, 1.0), gain=(1.05, 1.01, 0.93),
                         vignette=0.3, ink=0.35, ink_normal=(0.5, 1.4), saturation=0.95), res_scale=opt.scale)''')
rep('''        walker.set_world(Jw, hd)
        t = d - start
        # wind sway: a gust field travelling across the field
        sw = 0.06 * np.sin(pts[:, 0] * 0.7 + pts[:, 1] * 0.4 - t * 0.06 + sway_ph * 0.3)
        geo.update_points(sf, np.c_[pts, np.zeros(n)], rot=np.c_[sw, sw * 0.6, sf_rot0])
        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})
        look.boil(st, d // 2)
        look.grain_seed(d // 2)
        look.set_drawing(d // 2, PAINT_BOIL)''', '''        walker.set_world(Jw, hd)
        hp = Jw["head"] + np.array([0, 0, 0.1])
        hat_brim.location = Vector(hp.tolist())
        hat_crown.location = Vector((hp + np.array([0, 0, 0.04])).tolist())
        t = d - start
        # wind sway: gust waves travelling across the field; plants near the walker part and sway more
        sw = 0.07 * np.sin(pts[:, 0] * 0.7 + pts[:, 1] * 0.4 - t * 0.06 + sway_ph * 0.3) + 0.025 * np.sin(pts[:, 0] * 2.1 - t * 0.17 + sway_ph)
        bx, by = Jw["pelvis"][0], Jw["pelvis"][1]
        dxw, dyw = pts[:, 0] - bx, pts[:, 1] - by
        near = np.exp(-(dxw * dxw + dyw * dyw) / 0.5)
        part_x = -np.sign(dxw) * 0.25 * near
        geo.update_points(sf, np.c_[pts, np.zeros(n)], rot=np.c_[sw + 0.08 * near * np.sin(t * 0.5 + sway_ph), sw * 0.6 + part_x, sf_rot0])
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)''')
rep('''    r.update = update
    r.finish = lambda out: json.dump(log, open(os.path.join(out, "thread_log.json"), "w"))''', '''    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])''')
open(p, "w").write(s)
print("s10 patched")
