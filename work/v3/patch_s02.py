p = "blender/scenes/s02.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''"""Scene 2 (frames 294-607): a bright forest drawn as raised contour hedges (fingerprint-like rings of
clipped hedge with dark gaps), lime to deep green with teal patches. A white modern train runs straight up
the central track. The hedge pattern is real displaced geometry that re-draws on twos: fast until ~17.2 s,
then slowly. Round bushes and pale rocks are scattered; mist drifts over in the second half."""''',
    '''"""Scene 2 (frames 294-607): a tea garden seen from above: curving terraces of clipped tea hedges (rounded rows made of
leaf dabs, lighter tops, shadowed sides, dark gaps and narrow paths), teal to yellow-green, a few round shade trees.
A white modern train runs straight up the central track.

v3: the ground does NOT morph: it is a static world-space field sampled on a fixed world lattice, so it scrolls rigidly
with the camera (~14 px per distinct drawing, on twos). 22 tea pickers at fixed places along the rows: conical pale
straw hats (bright), coloured clothes, baskets on their backs, walking slowly and bending to pick, arms reaching into
the bushes, small cast shadows. Roof units and a pantograph on the train, light mist drifting above."""''')
rep('''from kit import core, look, geo, thread, vehicles''', '''from kit import core, look, geo, vehicles, plants, rope_io''')
rep('''PAINT_BOIL = 0.2''', '''M_FIXED = 1.6 * MORPH_END / 24.0       # the frozen state of the contour field (no morphing in v3)
POST = dict(light_deg=132.0, flow_deg=90.0, stroke_px=11.0, boil_mean=2.0, thread_shadow_px=1.6, repaint=0.5)''')
rep('''    sc = core.reset(opt.scale, getattr(opt, "samples", 8))''', '''    sc = core.reset(opt.scale, getattr(opt, "samples", 2))''')

# leaf-dab texture on the hedge tops
rep('''        gap = _n(nt, "ShaderNodeMapRange", (-1000, 300), clamp=True)
        _l(nt, sz.outputs[2], gap.inputs["Value"])
        gap.inputs["From Min"].default_value, gap.inputs["From Max"].default_value = 0.03, 0.09
        return _mixrgb(nt, "MIX", gap.outputs["Result"], core.hexc("#224b2b"), c, (-500, 100))''', '''        # clipped tea leaves: small dabs with random value (voronoi cells), lighter on the tops
        vo = _n(nt, "ShaderNodeTexVoronoi", (-1200, -600))
        _l(nt, geo_n.outputs["Position"], vo.inputs["Vector"])
        vo.inputs["Scale"].default_value = 7.0
        dab = _n(nt, "ShaderNodeMapRange", (-1000, -600), clamp=True)
        _l(nt, _n(nt, "ShaderNodeRGBToBW", (-1100, -650)).outputs[0] if False else vo.outputs["Color"], dab.inputs["Value"])
        dab.inputs["To Min"].default_value, dab.inputs["To Max"].default_value = 0.86, 1.14
        top = _n(nt, "ShaderNodeMapRange", (-1000, -800), clamp=True)
        _l(nt, sz.outputs[2], top.inputs["Value"])
        top.inputs["From Min"].default_value, top.inputs["From Max"].default_value = 0.18, 0.3
        top.inputs["To Min"].default_value, top.inputs["To Max"].default_value = 0.92, 1.1
        c = look.mul_color(nt, look.mul_color(nt, c, dab.outputs["Result"], (-800, -600)), top.outputs["Result"], (-650, -600))
        gap = _n(nt, "ShaderNodeMapRange", (-1000, 300), clamp=True)
        _l(nt, sz.outputs[2], gap.inputs["Value"])
        gap.inputs["From Min"].default_value, gap.inputs["From Max"].default_value = 0.03, 0.1
        return _mixrgb(nt, "MIX", gap.outputs["Result"], core.hexc("#1f4328"), c, (-500, 100))''')
rep('''    return look.cel("hedge", core.hexc("#5aae50"), shadow=(0.66, 0.75, 0.71, 1), high=(1.11, 1.08, 1.0, 1), t1=0.45, t2=0.95,
                    paint=0.14, paint_scale=1.6, base_node=base, rough=0.9)''', '''    return look.cel("hedge", core.hexc("#5aae50"), shadow=(0.6, 0.72, 0.7, 1), high=(1.12, 1.09, 1.0, 1), t1=0.45, t2=0.95,
                    paint=0.04, paint_scale=1.6, base_node=base, rough=0.9, soft=0.2, ao=0.6, ao_dist=0.25)''')

# shade trees: leaf-card crowns; no pale rocks
rep('''    for i in range(3):
        geo.spiky(f"bush_{i}", bush_m, bproto, seed=20 + i, subdiv=3, spikes=120, sharp=14, amp=0.3, flat=0.85)
    bp = geo.poisson(rng, 600, x0, y0, x1, y1, 3.8, accept=lambda x, y: abs(x) > 3.0)
    nb = len(bp)
    bs = rng.uniform(0.5, 0.9, nb)''', '''    def tree_base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-700, 200), attribute_type="GEOMETRY", attribute_name="lv")
        return _mixrgb(nt, "MIX", at.outputs["Fac"], core.hexc("#1d4a2a"), core.hexc("#6fa851"), (-400, 100))
    bush_m = look.cel("bush", core.hexc("#2f6b3e"), shadow=(0.5, 0.6, 0.55, 1), high=(1.15, 1.15, 1.05, 1), paint=0.03, base_node=tree_base,
                      soft=0.2, ao=0.6, ao_dist=0.5)
    for i in range(3):
        plants.crown(f"bush_{i}", bush_m, bproto, seed=20 + i, radius=1.0, height=1.0, n_clumps=30, leaves=60, leaf=0.12, core=True)
    bp = geo.poisson(rng, 120, x0, y0, x1, y1, 9.0, accept=lambda x, y: abs(x) > 3.5)
    nb = len(bp)
    bs = rng.uniform(1.2, 2.0, nb)''')
rep('''    geo.instances("bushes", bproto, np.c_[bp, np.full(nb, 0.25)], scl=np.c_[bs, bs, bs * 0.8], rot=np.c_[np.zeros(nb), np.zeros(nb), rng.uniform(0, 6.28, nb)],
                  variant=rng.integers(0, 3, nb), tint=rng.random(nb), coll=env)
    rproto = geo.proto_collection("ROCK_PROTOS")
    geo.knobbly("rock", look.cel("rock", core.hexc("#e2ded2"), paint=0.04), rproto, seed=7, subdiv=1, knob=0.4, flat=0.6, lumps=3)
    rp = geo.poisson(rng, 150, x0, y0, x1, y1, 7.0, accept=lambda x, y: abs(x) > 3.0)
    nr = len(rp)
    rs = rng.uniform(0.2, 0.32, nr)
    geo.instances("rocks", rproto, np.c_[rp, np.full(nr, 0.3)], scl=np.c_[rs, rs * 1.2, rs * 0.7], rot=np.c_[np.zeros(nr), np.zeros(nr), rng.uniform(0, 6.28, nr)], coll=env)''',
    '''    geo.instances("bushes", bproto, np.c_[bp, np.full(nb, 0.6)], scl=np.c_[bs, bs, bs * 0.9], rot=np.c_[np.zeros(nb), np.zeros(nb), rng.uniform(0, 6.28, nb)],
                  variant=rng.integers(0, 3, nb), tint=rng.random(nb), coll=env)
    # tea pickers: conical straw hat, coloured clothes, basket on the back; slow walk + bending + reaching arms
    hat_m = look.cel("picker_hat", core.hexc("#f6ecc8"), shadow=(0.7, 0.68, 0.7, 1), high=(1.06, 1.05, 1.02, 1), paint=0.03, soft=0.22, rim=0.3, hero=True)
    basket_m = look.cel("picker_basket", core.hexc("#a8763f"), shadow=(0.6, 0.55, 0.6, 1), paint=0.08, paint_scale=60, soft=0.2, hero=True)
    skin_m = look.cel("picker_skin", core.hexc("#c99a76"), paint=0.0, soft=0.25, hero=True)
    clothes = [look.cel(f"picker_cloth{i}", core.hexc(h), shadow=(0.58, 0.55, 0.7, 1), paint=0.03, soft=0.22, hero=True)
               for i, h in enumerate(("#d23b3b", "#e8892e", "#3b6fc4", "#c43b9a", "#e3c23a", "#2e9a8a"))]
    def prim(name, mat, kind, scale):
        bm = bmesh.new()
        if kind == "cone":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=1.0, radius2=0.02, depth=1.0)
        elif kind == "cyl":
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=1.0, radius2=0.85, depth=1.0)
        else:
            bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
        bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
        return geo.bm_to_object(bm, name, mat, ink)
    pickers = []
    pk = geo.poisson(rng, 22, -16, y0 + 8, 16, y1 - 8, 6.0, accept=lambda x, y: 3.6 < abs(x) < 16)
    for i, (px_, py_) in enumerate(pk):
        cm = clothes[i % len(clothes)]
        parts = dict(body=prim(f"pk{i}_body", cm, "sph", (0.2, 0.15, 0.3)), hat=prim(f"pk{i}_hat", hat_m, "cone", (0.36, 0.36, 0.2)),
                     basket=prim(f"pk{i}_basket", basket_m, "cyl", (0.14, 0.14, 0.18)),
                     arm_l=prim(f"pk{i}_arml", cm, "sph", (0.05, 0.22, 0.05)), arm_r=prim(f"pk{i}_armr", cm, "sph", (0.05, 0.22, 0.05)),
                     hand_l=prim(f"pk{i}_hl", skin_m, "sph", (0.04, 0.04, 0.04)), hand_r=prim(f"pk{i}_hr", skin_m, "sph", (0.04, 0.04, 0.04)))
        pickers.append(dict(parts=parts, x=px_, y=py_, hd=rng.uniform(0, 6.28), ph=rng.uniform(0, 6.28), v=rng.uniform(0.004, 0.009),
                            span=rng.uniform(1.0, 2.5)))

    def pose_picker(pkr, t):
        hd = pkr["hd"]
        f_ = np.array([-math.sin(hd), math.cos(hd), 0.0])
        r_ = np.array([math.cos(hd), math.sin(hd), 0.0])
        walk = pkr["span"] * math.sin(t * pkr["v"] + pkr["ph"])
        base = np.array([pkr["x"], pkr["y"], 0.0]) + f_ * walk
        bend = 0.55 + 0.35 * max(0.0, math.sin(t * 0.045 + pkr["ph"] * 1.7))
        pel = base + np.array([0, 0, 0.85])
        chest = pel + np.array([0, 0, 0.45 * math.cos(bend)]) + f_ * 0.45 * math.sin(bend)
        head = chest + np.array([0, 0, 0.2 * math.cos(bend)]) + f_ * 0.22 * math.sin(bend)
        P = pkr["parts"]
        M = Matrix.Translation(Vector(((pel + chest) / 2).tolist())) @ Matrix.Rotation(hd, 4, "Z") @ Matrix.Rotation(-bend, 4, "X")
        P["body"].matrix_world = M @ Matrix.Diagonal((0.2, 0.15, 0.3, 1))
        P["hat"].matrix_world = Matrix.Translation(Vector((head + np.array([0, 0, 0.08])).tolist())) @ Matrix.Rotation(hd, 4, "Z") @ \\
            Matrix.Rotation(-bend * 0.6, 4, "X") @ Matrix.Diagonal((0.36, 0.36, 0.2, 1))
        back = (pel + chest) / 2 - f_ * 0.2 + np.array([0, 0, 0.12])
        P["basket"].matrix_world = Matrix.Translation(Vector(back.tolist())) @ Matrix.Rotation(hd, 4, "Z") @ Matrix.Rotation(-bend * 0.5, 4, "X") @ \\
            Matrix.Diagonal((0.14, 0.14, 0.18, 1))
        for side, arm, hand in ((-1, "arm_l", "hand_l"), (1, "arm_r", "hand_r")):
            reach = 0.35 + 0.18 * math.sin(t * 0.22 + pkr["ph"] + side)
            sh = chest + r_ * side * 0.17
            hnd = sh + f_ * reach + np.array([0, 0, -0.38]) + r_ * side * 0.05
            mid = (sh + hnd) / 2
            dv = hnd - sh
            ang = math.atan2(-dv[0], dv[1])
            tilt = math.atan2(-dv[2], math.hypot(dv[0], dv[1]))
            P[arm].matrix_world = Matrix.Translation(Vector(mid.tolist())) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(tilt, 4, "X") @ \\
                Matrix.Diagonal((0.05, max(0.1, np.linalg.norm(dv) / 2), 0.05, 1))
            P[hand].location = Vector(hnd.tolist())''')

# train roof details: a pantograph on the second car
rep('''    for i in range(3):
        root, parts = vehicles.train_car(f"wcar{i}", tmats, ink, length=CAR_LEN, width=2.0, height=2.4, nose=(i == 0), fans=2, modern=True, windows=True)
        cars.append(root)''', '''    for m_ in tmats.values():
        g_ = [x for x in m_.node_tree.nodes if x.type == "GROUP"][0]
        g_.inputs["Hero"].default_value = 1.0
        g_.inputs["Soft"].default_value = 0.2
    for i in range(3):
        root, parts = vehicles.train_car(f"wcar{i}", tmats, ink, length=CAR_LEN, width=2.0, height=2.4, nose=(i == 0), fans=2, modern=True, windows=True)
        cars.append(root)
    panto_m = look.cel("panto", core.hexc("#55575e"), paint=0.0, soft=0.2, hero=True)
    pv, pf = [], []
    for k_, (a_, b_) in enumerate((((-0.5, -0.6, 2.45), (0.5, 0.0, 2.95)), ((0.5, -0.6, 2.45), (-0.5, 0.0, 2.95)), ((-0.7, 0.0, 2.95), (0.7, 0.0, 2.95)))):
        a_, b_ = np.array(a_), np.array(b_)
        sd = np.array([0, 0.03, 0])
        i0 = len(pv)
        pv += [a_ - sd, a_ + sd, b_ + sd, b_ - sd]
        pf.append((i0, i0 + 1, i0 + 2, i0 + 3))
    panto = geo.mesh_from_arrays("pantograph", np.array(pv), pf, ink, False, panto_m)
    panto.parent = cars[1]''')

# rope v3 from the last coupler
rep('''    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99, paint=0.0, glow=0.35, rough=0.5)
    def coupler(t):
        return np.array([0.0, front_y(t) - 3 * CAR_LEN - 2 * GAP - 0.1, 0.6])
    cord = thread.Cord(n_seg=200, length=16.0, mode="ground", ground=lambda x, y: np.where(np.abs(x) < 2.25, 0.2, 0.1), friction=0.7, substeps=6, iters=22)
    sim = cord.run(list(range(start, end)), coupler, (0.0, -1.0), warm=100)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.4)''', '''    def coupler(t):
        return np.array([0.0, front_y(t) - 3 * CAR_LEN - 2 * GAP - 0.1, 0.6])
    rope = rope_io.Owner("A", SCENE, rig, coupler, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150,
                         ground_fn=lambda x, y: np.where(np.abs(np.asarray(x, float)) < 2.25, 0.2, 0.1))''')
rep('''    look.compositor(dict(kuwahara=6, bloom=0.4, bloom_threshold=0.95, streak=0.1, lift=(0.99, 1.0, 1.01), gain=(1.03, 1.02, 0.97),
                         vignette=0.28, grain=0.03, ink=0.5, ink_normal=(0.45, 1.3), saturation=1.08), res_scale=opt.scale)''', '''    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.99, 1.0, 1.01), gain=(1.03, 1.02, 0.97),
                         vignette=0.26, ink=0.4, ink_normal=(0.45, 1.3), saturation=1.05), res_scale=opt.scale)''')
# rigid ground: frozen field, window snapped to a fixed world lattice
rep('''        cx, cy = rig.pos(f)
        hedge.location = (cx, cy, 0.0)
        X = base_co[:, 0] + cx
        Y = base_co[:, 1] + cy
        Z = ring_height(X, Y, morph_clock(d - start))''', '''        cx, cy = rig.pos(f)
        sx_, sy_ = round(cx / step) * step, round(cy / step) * step
        hedge.location = (sx_, sy_, 0.0)
        key = (round(sx_ / step), round(sy_ / step))
        X = base_co[:, 0] + sx_
        Y = base_co[:, 1] + sy_
        Z = ring_height(X, Y, M_FIXED)''')
rep('''        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})
        look.boil(st, d // 2)
        look.grain_seed(d // 2)
        look.set_drawing(d // 2, PAINT_BOIL)''', '''        for pkr in pickers:
            pose_picker(pkr, d)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)''')
rep('''    r.update = update
    r.finish = lambda out: json.dump(log, open(os.path.join(out, "thread_log.json"), "w"))''', '''    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])''')
# the teal driver tied the colour to time (a slow change); keep colours static in v3
rep('''        d.expression = "0.35 + 0.65 * min(1, max(0, (frame - 354) / 140.0))"''', '''        d.expression = "0.75"''')
open(p, "w").write(s)
print("s02 patched")
