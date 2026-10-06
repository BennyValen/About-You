p = "blender/scenes/s01.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''from kit import core, look, geo, thread, vehicles''', '''from kit import core, look, geo, vehicles, rope_io''')
rep('''CAR_LEN, GAP = 7.6, 0.45
PAINT_BOIL = 0.3''', '''CAR_LEN, GAP = 4.4, 0.32
N_CARS = 7
POST = dict(light_deg=140.0, flow_deg=90.0, stroke_px=12.0, boil_mean=1.8, thread_shadow_px=1.4, thread_glow=0.25, repaint=0.5, grain=1.2)''')
rep('''    sc = core.reset(opt.scale, getattr(opt, "samples", 8))''', '''    sc = core.reset(opt.scale, getattr(opt, "samples", 2))''')
# denser two-layer forest
rep('''    pts = geo.poisson(rng, 4000, x0, y0, x1, y1, 3.6, accept=lambda x, y: abs(x) > 4.2 and pond_sdf(x, y) > 1.5)
    n = len(pts)
    s = rng.uniform(0.62, 0.95, n)''', '''    pts = geo.poisson(rng, 6000, x0, y0, x1, y1, 2.7, accept=lambda x, y: abs(x) > 4.0 and pond_sdf(x, y) > 1.5)
    n = len(pts)
    # two canopy layers: tall spruces and a lower understorey between them
    s = np.where(rng.random(n) < 0.6, rng.uniform(0.75, 1.0, n), rng.uniform(0.42, 0.6, n))''')
rep('''    return look.cel("spruce", core.hexc("#262e4c"), shadow=(0.55, 0.55, 0.75, 1), high=(1.25, 1.25, 1.3, 1), t1=0.35, t2=0.9,
                    paint=0.12, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0)''', '''    return look.cel("spruce", core.hexc("#262e4c"), shadow=(0.55, 0.55, 0.75, 1), high=(1.25, 1.25, 1.3, 1), t1=0.35, t2=0.9,
                    paint=0.04, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0, soft=0.18, ao=0.55, ao_dist=1.5)''')
# train: 7 carriages, individual window panes, softer light; rim on the dark roofs
rep('''    tmats = dict(body=look.cel("car", core.hexc("#2a2c3c"), shadow=(0.6, 0.6, 0.75, 1), high=(1.5, 1.5, 1.6, 1), paint=0.05),
                 window=look.emissive("window", (1.0, 0.62, 0.22, 1), 5.0), roof=look.cel("fan", core.hexc("#3c3f58"), paint=0.0),
                 under=look.cel("bogie", core.hexc("#15161f"), paint=0.0))
    cars = []
    for i in range(3):
        root, parts = vehicles.train_car(f"car{i}", tmats, ink, length=CAR_LEN, width=1.9, height=2.3, nose=(i == 0), fans=3)
        cars.append(root)
        # warm window light spilling sideways onto the snow
        for side in (-1, 1):
            li = bpy.data.lights.new(f"win{i}{side}", "AREA")
            li.shape = "RECTANGLE"
            li.size, li.size_y = CAR_LEN * 0.9, 0.4
            li.energy = 700.0
            li.color = (1.0, 0.5, 0.14)''', '''    tmats = dict(body=look.cel("car", core.hexc("#2a2c3c"), shadow=(0.6, 0.6, 0.75, 1), high=(1.5, 1.5, 1.6, 1), paint=0.03, soft=0.22,
                               rim=0.45, hero=True),
                 window=look.emissive("window", (1.0, 0.58, 0.2, 1), 1.6, hero=True),
                 roof=look.cel("fan", core.hexc("#3c3f58"), paint=0.0, soft=0.2, rim=0.4, hero=True),
                 under=look.cel("bogie", core.hexc("#15161f"), paint=0.0, hero=True))
    cars = []
    for i in range(N_CARS):
        root, parts = vehicles.train_car(f"car{i}", tmats, ink, length=CAR_LEN, width=1.9, height=2.3, nose=(i == 0), fans=2, windows=True)
        cars.append(root)
        # warm window light spilling sideways onto the snow and the crowns (soft falloff, shadowed by the trees)
        for side in (-1, 1):
            li = bpy.data.lights.new(f"win{i}{side}", "AREA")
            li.shape = "RECTANGLE"
            li.size, li.size_y = CAR_LEN * 0.9, 0.6
            li.energy = 260.0
            li.color = (1.0, 0.52, 0.16)''')
rep('''            lo.location = (side * 1.15, CAR_LEN / 2, 1.6)''', '''            lo.location = (side * 1.15, CAR_LEN / 2, 1.5)''')
rep('''    def coupler(t):
        return np.array([0.0, front_y(t) - 3 * CAR_LEN - 2 * GAP - 0.1, 0.5])
    cord = thread.Cord(n_seg=200, length=16.0, mode="ground", ground=lambda x, y: np.zeros_like(x) + 0.08, friction=0.7, substeps=6, iters=22)
    sim = cord.run(list(range(start, end)), coupler, (0.0, -1.0), warm=100)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.4)''', '''    def coupler(t):
        return np.array([0.0, front_y(t) - N_CARS * CAR_LEN - (N_CARS - 1) * GAP - 0.1, 0.5])
    rope = rope_io.Owner("A", SCENE, rig, coupler, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150,
                         ground_fn=lambda x, y: np.full_like(np.asarray(x, float), 0.12))
    # steam plume: puffs leave the locomotive, rise, billow and drift with the wind over the forest; lit by the train
    puff_m = look.cel("steam", core.hexc("#dfe3f4"), shadow=(0.55, 0.58, 0.8, 1), high=(1.05, 1.05, 1.05, 1), paint=0.03, soft=0.4, alpha=0.6,
                      ao=0.0, light_tint=1.0)
    pg = [x for x in puff_m.node_tree.nodes if x.type == "GROUP"][0]
    pat = _n(puff_m.node_tree, "ShaderNodeAttribute", (-400, -300), attribute_type="INSTANCER", attribute_name="tint")
    _l(puff_m.node_tree, pat.outputs["Fac"], pg.inputs["Alpha"])
    pprot = geo.proto_collection("P_steam")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        v.co *= 1.0 + 0.12 * math.sin(v.co.x * 5 + v.co.y * 3)
    geo.bm_to_object(bm, "puff", puff_m, pprot)
    NP = 140
    puff_t = np.linspace(start - 140, end, NP)
    prng = np.random.default_rng(111)
    puff_j = prng.normal(0, 1, (NP, 3))
    puff_obj = geo.instances("steam", pprot, np.tile([0.0, -1e4, -50.0], (NP, 1)), tint=np.zeros(NP), coll=env)''')
rep('''    look.compositor(dict(kuwahara=10, bloom=1.0, bloom_threshold=0.62, bloom_size=0.72, streak=0.32, streak_threshold=1.05,
                         lift=(0.98, 0.99, 1.06), gain=(1.03, 0.99, 0.96), vignette=0.36, grain=0.02, ink=0.45, ink_normal=(0.45, 1.3)),
                    res_scale=opt.scale)''', '''    look.compositor(dict(kuwahara=3, bloom=0.7, bloom_threshold=0.85, bloom_size=0.7, streak=0.16, streak_threshold=1.1,
                         lift=(0.98, 0.99, 1.06), gain=(1.03, 0.99, 0.96), vignette=0.34, ink=0.35, ink_normal=(0.45, 1.3)),
                    res_scale=opt.scale)''')
rep('''        beam.location = (0.0, fy + 0.2, 1.6)
        beam.scale = (7.0, 30.0, 1.0)
        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})
        look.boil(st, d // 2)
        look.grain_seed(d // 2)
        look.set_drawing(d // 2, PAINT_BOIL)''', '''        beam.location = (0.0, fy + 0.2, 1.6)
        beam.scale = (7.0, 30.0, 1.0)
        # steam: emitted at the chimney position of the locomotive at time te, then left behind in world space,
        # rising and drifting with a crosswind, growing and fading
        age = (d - puff_t) / 24.0
        alive = (age >= 0) & (age < 5.0)
        P = np.tile([0.0, -1e4, -50.0], (NP, 1))
        S = np.full((NP, 3), 0.01)
        T = np.zeros(NP)
        for k in np.nonzero(alive)[0]:
            a_ = age[k]
            ey = front_y(puff_t[k]) - 1.2
            P[k] = (2.2 * a_ + 0.6 * puff_j[k, 0] * a_, ey + 1.1 * a_ + 0.4 * puff_j[k, 1] * a_, 2.8 + 1.4 * a_ + 0.3 * puff_j[k, 2])
            r_ = 0.9 + 1.1 * a_ ** 0.8
            S[k] = (r_, r_ * 0.9, r_ * 0.6)
            T[k] = 0.62 * (1 - a_ / 5.0) ** 1.3
        me = puff_obj.data
        me.vertices.foreach_set("co", P.astype(np.float32).ravel())
        me.attributes["scl"].data.foreach_set("vector", S.astype(np.float32).ravel())
        me.attributes["tint"].data.foreach_set("value", T.astype(np.float32))
        me.update()
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)''')
rep('''    r.update = update
    r.finish = lambda out: json.dump(log, open(os.path.join(out, "thread_log.json"), "w"))''', '''    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])''')
open(p, "w").write(s)
print("s01 patched")
