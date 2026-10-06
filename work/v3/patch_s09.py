p = "blender/scenes/s09.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''from kit import core, look, geo, human, thread, vehicles''', '''from kit import core, look, geo, human, vehicles, plants, rope_io''')
rep('''PAINT_BOIL = 0.95''', '''POST = dict(light_deg=45.0, flow_deg=90.0, stroke_px=12.0, boil_mean=2.0, thread_shadow_px=2.0, repaint=0.55)''')
rep('''    sc = core.reset(opt.scale, getattr(opt, "samples", 8))''', '''    sc = core.reset(opt.scale, getattr(opt, "samples", 2))''')

# ---- lawn: mowing stripes, CC0 grass detail; path: gravel + wheel marks
rep('''        g = _n(nt, "ShaderNodeValToRGB", (-1200, 100))
        g.color_ramp.elements[0].color = core.hexc("#2c6a30")
        g.color_ramp.elements[1].color = core.hexc("#5ea646")
        e = g.color_ramp.elements.new(0.5)
        e.color = core.hexc("#3f8a3a")
        _l(nt, gn.outputs["Fac"], g.inputs[0])''', '''        g = _n(nt, "ShaderNodeValToRGB", (-1200, 100))
        g.color_ramp.elements[0].color = core.hexc("#2c6a30")
        g.color_ramp.elements[1].color = core.hexc("#5ea646")
        e = g.color_ramp.elements.new(0.5)
        e.color = core.hexc("#3f8a3a")
        _l(nt, gn.outputs["Fac"], g.inputs[0])
        # mowing stripes along the path (alternating light/dark bands ~1.1 m wide), softened by noise
        stw = _math(nt, "SINE", _math(nt, "MULTIPLY", sx.outputs[0], math.pi / 1.1, (-1500, 450)), None, (-1400, 450))
        stv = _n(nt, "ShaderNodeMapRange", (-1300, 450), clamp=True)
        _l(nt, stw, stv.inputs["Value"])
        stv.inputs["From Min"].default_value, stv.inputs["From Max"].default_value = -0.3, 0.3
        stv.inputs["To Min"].default_value, stv.inputs["To Max"].default_value = 0.86, 1.12
        gcol = look.mul_color(nt, g.outputs[0], stv.outputs["Result"], (-1100, 300))
        gcol = look.mul_color(nt, gcol, look.tex_value_detail(nt, "aerial_grass_rock", size_m=2.5, amount=0.25, loc=(-1500, 700)), (-1000, 300))''')
rep('''        path = _mixrgb(nt, "MIX", pn.outputs["Fac"], core.hexc("#d4c296"), core.hexc("#e6d8b0"), (-950, -250))
        c = _mixrgb(nt, "MIX", pm.outputs["Result"], g.outputs[0], path, (-800, 0))''', '''        path = _mixrgb(nt, "MIX", pn.outputs["Fac"], core.hexc("#d4c296"), core.hexc("#e6d8b0"), (-950, -250))
        path = look.mul_color(nt, path, look.tex_value_detail(nt, "gravel_road", size_m=1.2, amount=0.28, loc=(-1500, -600)), (-900, -350))
        # wheel marks: two darker stripes along the path
        for wx_ in (-0.28, 0.24):
            wm = _n(nt, "ShaderNodeMapRange", (-1100, -650), clamp=True, interpolation_type="SMOOTHSTEP")
            _l(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", sx.outputs[0], PATH_X + wx_, (-1300, -650)), None, (-1200, -650)), wm.inputs["Value"])
            wm.inputs["From Min"].default_value, wm.inputs["From Max"].default_value = 0.07, 0.02
            path = _mixrgb(nt, "MULTIPLY", _math(nt, "MULTIPLY", wm.outputs["Result"], 0.22, (-1000, -650)), path, core.hexc("#a8946c"), (-850, -500))
        c = _mixrgb(nt, "MIX", pm.outputs["Result"], gcol, path, (-800, 0))''')
rep('''    return look.cel("ground", core.hexc("#4a8a3c"), shadow=(0.45, 0.55, 0.5, 1), high=(1.1, 1.1, 1.02, 1), t1=0.42, t2=0.97,
                    paint=0.2, paint_scale=2.0, base_node=base, rough=0.9)''', '''    return look.cel("ground", core.hexc("#4a8a3c"), shadow=(0.42, 0.52, 0.5, 1), high=(1.1, 1.1, 1.02, 1), t1=0.42, t2=0.97,
                    paint=0.06, paint_scale=2.0, base_node=base, rough=0.9, soft=0.16, ao=0.5, ao_dist=0.5)''')

# lake: sky sheen + soft shading
rep('''        return _mixrgb(nt, "MIX", mr.outputs["Result"], core.hexc("#10221f"), core.hexc("#3f5545"), (-200, 0))''', '''        c = _mixrgb(nt, "MIX", mr.outputs["Result"], core.hexc("#10221f"), core.hexc("#3f5545"), (-200, 0))
        sk = _n(nt, "ShaderNodeTexNoise", (-600, 200))
        _l(nt, geo_n.outputs["Position"], sk.inputs["Vector"])
        sk.inputs["Scale"].default_value = 0.1
        skm = _n(nt, "ShaderNodeMapRange", (-400, 200), clamp=True)
        _l(nt, sk.outputs["Fac"], skm.inputs["Value"])
        skm.inputs["From Min"].default_value, skm.inputs["From Max"].default_value = 0.5, 0.78
        return _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", skm.outputs["Result"], 0.14, (-250, 200)), c, core.hexc("#9db8b4"), (-100, 50))''')
rep('''        d.expression = "frame / 20.0"''', '''        d.expression = "floor(frame / 2) / 10.0"''')

# trees: leaf-card crowns (dozens of clumps of individual leaves), wind sway
rep('''    leaf = [core.hexc(h) for h in ("#6aa83a", "#86c046", "#a2d052", "#5d9636")]
    tm = look.cel("foliage", leaf[0], shadow=(0.42, 0.55, 0.42, 1), high=(1.18, 1.16, 1.0, 1), t1=0.4, t2=0.9, paint=0.12, paint_scale=7.0,
                  base_node=look.instancer_palette(leaf))
    for i in range(4):
        geo.spiky(f"clump_{i}", tm, tproto, seed=900 + i, subdiv=4, spikes=260, sharp=24, amp=0.6, flat=0.8)''', '''    def foliage_base(nt):
        at = _n(nt, "ShaderNodeAttribute", (-700, 200), attribute_type="GEOMETRY", attribute_name="lv")
        it = _n(nt, "ShaderNodeAttribute", (-700, 0), attribute_type="INSTANCER", attribute_name="tint")
        v = _math(nt, "ADD", at.outputs["Fac"], _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", it.outputs["Fac"], 0.5, (-550, 0)), 0.3, (-450, 0)), (-350, 100))
        ramp = _n(nt, "ShaderNodeValToRGB", (-250, 100))
        cr = ramp.color_ramp
        cr.elements[0].position, cr.elements[0].color = 0.05, core.hexc("#1f4a22")
        cr.elements[1].position, cr.elements[1].color = 0.95, core.hexc("#c8e070")
        for pos_, h_ in ((0.3, "#3d7a2e"), (0.55, "#6aa83a"), (0.75, "#93c64b")):
            e_ = cr.elements.new(pos_)
            e_.color = core.hexc(h_)
        _l(nt, v, ramp.inputs[0])
        return ramp.outputs[0]
    tm = look.cel("foliage", core.hexc("#6aa83a"), shadow=(0.4, 0.52, 0.42, 1), high=(1.16, 1.14, 1.0, 1), t1=0.4, t2=0.92, paint=0.04,
                  base_node=foliage_base, soft=0.2, ao=0.6, ao_dist=0.6, backface=True)
    for i in range(5):
        plants.crown(f"crown_{i}", tm, tproto, seed=900 + i, radius=1.0, n_clumps=30, leaves=60, leaf=0.11)''')
rep('''    cl = []
    for tx, ty, r in trees:
        for i in range(int(5 + r * 3)):
            a = rng.uniform(0, 6.28)
            rr = 0 if i == 0 else rng.uniform(0.25, 0.62) * r
            s = r * (0.55 if i == 0 else rng.uniform(0.32, 0.45))
            cl.append((tx + rr * math.cos(a), ty + rr * math.sin(a), r * 2.2 + rng.uniform(-0.2, 0.5) - rr * 0.3, s))
    cl = np.array(cl)
    k = len(cl)
    geo.instances("trees", tproto, cl[:, :3], rot=np.c_[np.zeros(k), np.zeros(k), rng.uniform(0, 6.28, k)], scl=np.c_[cl[:, 3], cl[:, 3], cl[:, 3]],
                  variant=rng.integers(0, 4, k), tint=rng.random(k), coll=env)''', '''    cl = np.array([(tx, ty, r * 1.2, r) for tx, ty, r in trees])
    k = len(cl)
    tree_rot = np.c_[np.zeros(k), np.zeros(k), rng.uniform(0, 6.28, k)]
    tree_obj = geo.instances("trees", tproto, cl[:, :3], rot=tree_rot, scl=np.c_[cl[:, 3], cl[:, 3], cl[:, 3]],
                             variant=rng.integers(0, 5, k), tint=rng.random(k), coll=env)
    tree_ph = rng.uniform(0, 6.28, k)
    # trunks hinted under the crowns
    bark = look.cel("bark", core.hexc("#5a4632"), paint=0.03, soft=0.2)
    for i, (tx, ty, z_, r) in enumerate(cl):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.12 * r, radius2=0.07 * r, depth=r * 1.4)
        bmesh.ops.translate(bm, vec=(tx, ty, r * 0.7), verts=bm.verts)
        geo.bm_to_object(bm, f"trunk{i}", bark, env)
    # lawn tufts and small flower dots, fallen leaves on the path and lawn, reeds along the shore
    vprot = geo.proto_collection("P_lawn")
    tuftm = look.cel("tuft", core.hexc("#3d7d33"), shadow=(0.45, 0.55, 0.5, 1), paint=0.03, soft=0.2, ao=0.4,
                     base_node=look.instancer_palette([core.hexc("#3d7d33"), core.hexc("#4f9238"), core.hexc("#2f6a2c"), core.hexc("#6aa846")]))
    for i in range(3):
        plants.grass_tuft(f"a_tuft_{i}", tuftm, vprot, seed=950 + i, n=(10, 18), height=0.14, lean=0.6)
    flm = look.cel("flower_dot", core.hexc("#f4f0d6"), paint=0.0, soft=0.3,
                   base_node=look.instancer_palette([core.hexc("#f4f0d6"), core.hexc("#f0d85a"), core.hexc("#e9e2f2")]))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=0.025)
    geo.bm_to_object(bm, "b_flower", flm, vprot)
    lfm = look.cel("fallen_leaf", core.hexc("#a8b84a"), paint=0.0, soft=0.25,
                   base_node=look.instancer_palette([core.hexc("#a8b84a"), core.hexc("#c9a64a"), core.hexc("#8c6e3a"), core.hexc("#7ea33e")]))
    plants.leaf_card("c_leaf", lfm, vprot, size=0.08)
    reedm = look.cel("reed9", core.hexc("#4e7a35"), shadow=(0.45, 0.55, 0.5, 1), paint=0.03, soft=0.2, ao=0.4,
                     base_node=look.instancer_palette([core.hexc("#4e7a35"), core.hexc("#5f8a3c"), core.hexc("#3d6a2e")]))
    plants.grass_tuft("d_reed", reedm, vprot, seed=990, n=(12, 24), height=0.9, lean=0.3)
    lawn = geo.poisson(rng, 1600, 0.95, y0, x1, y1, 0.32)
    nl = len(lawn)
    geo.instances("lawn_tufts", vprot, np.c_[lawn, np.full(nl, 0.0)], rot=np.c_[np.zeros(nl), np.zeros(nl), rng.uniform(0, 6.28, nl)],
                  scl=np.repeat(rng.uniform(0.7, 1.4, nl)[:, None], 3, 1), variant=rng.integers(0, 3, nl), tint=rng.random(nl), coll=env)
    fl = geo.poisson(rng, 700, 0.95, y0, x1, y1, 0.25)
    nf = len(fl)
    geo.instances("lawn_flowers", vprot, np.c_[fl, np.full(nf, 0.02)], variant=np.full(nf, 3), tint=rng.random(nf), coll=env)
    lv = np.c_[rng.uniform(-1.2, x1, 500), rng.uniform(y0, y1, 500)]
    nlv = len(lv)
    geo.instances("fallen_leaves", vprot, np.c_[lv, np.full(nlv, 0.13)], rot=np.c_[np.zeros(nlv), np.zeros(nlv), rng.uniform(0, 6.28, nlv)],
                  scl=np.repeat(rng.uniform(0.7, 1.3, nlv)[:, None], 3, 1), variant=np.full(nlv, 4), tint=rng.random(nlv), coll=env)
    rd = []
    for yv in np.arange(y0, y1, 0.32):
        if rng.random() < 0.75:
            rd.append((shore_x(yv) - rng.uniform(0.0, 0.35), yv + rng.normal(0, 0.1)))
    rd = np.array(rd)
    nrd = len(rd)
    geo.instances("reeds", vprot, np.c_[rd, np.full(nrd, -0.1)], rot=np.c_[np.zeros(nrd), np.zeros(nrd), rng.uniform(0, 6.28, nrd)],
                  scl=np.repeat(rng.uniform(0.7, 1.3, nrd)[:, None], 3, 1), variant=np.full(nrd, 5), tint=rng.random(nrd), coll=env)''')

# cyclist: helmet, hero flags, wobble; rope
rep('''    rider = human.Human("rider", hm, hair="long", coll=ink)''', '''    for m_ in list(bmats.values()) + list(hm.values()):
        nt_ = m_.node_tree
        g_ = [x for x in nt_.nodes if x.type == "GROUP"][0]
        g_.inputs["Hero"].default_value = 1.0
        g_.inputs["Soft"].default_value = 0.22
    rider = human.Human("rider", hm, hair="long", coll=ink, bulk={"top": 1.15})
    helm_m = look.cel("helmet", core.hexc("#d8473b"), shadow=(0.6, 0.5, 0.6, 1), high=(1.3, 1.2, 1.15, 1), paint=0.0, soft=0.18, rim=0.35, hero=True)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.12, 0.15, 0.1), verts=bm.verts)
    helmet = geo.bm_to_object(bm, "helmet", helm_m, ink)''')
rep('''    def bike_pos(t):
        return rig.screen_to_world(t, *BIKE_SCREEN, 0.0)''', '''    mot = rope_io.C.owner_motion(SCENE)
    def bike_pos(t):
        tt = min(max(t, start), end)
        p = rig.screen_to_world(tt, *BIKE_SCREEN, 0.0)
        return Vector((p[0] + mot(t)[0], p[1] + (min(t - start, 0) + max(t - end, 0)) * 4.17 / PPM, 0.0))''')
rep('''    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    def attach(t):
        p = bike_pos(min(max(t, start), end - 1)) if t >= start else bike_pos(start) + Vector((0, (t - start) * 4.17 / PPM, 0))
        return np.array([p[0] - 0.05, p[1] - 0.55, 0.85])
    def breeze(x, y, t):
        return 0.6 * np.sin(y * 1.1 + t * 0.02), np.zeros_like(y)
    cord = thread.Cord(n_seg=200, length=22.0, mode="ground", ground=lambda x, y: ground_h(x, y) + 0.01, friction=0.55,
                       substeps=6, iters=22, push=breeze, bend=0.1)
    sim = cord.run(list(range(start, end)), attach, (0.0, -1.0), warm=110)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.4)''', '''    def attach(t):
        p = bike_pos(t)
        return np.array([p[0] - 0.05, p[1] - 0.55, 0.85])
    hg = geo.HeightGrid(ground_h, x0 - 2, y0 - 2, x1 + 2, y1 + 2, 0.08)
    rope = rope_io.Owner("A", SCENE, rig, attach, list(range(start, end, 2)), trail=(0.0, -1.0), ground_fn=lambda x, y: hg(x, y) + 0.01,
                         warm=150, cfg_motion=False)''')
rep('''    look.compositor(dict(kuwahara=7, bloom=0.4, bloom_threshold=0.94, streak=0.1, lift=(0.98, 1.0, 1.02), gain=(1.04, 1.03, 0.95),
                         vignette=0.32, grain=0.03, ink=0.55, ink_normal=(0.45, 1.3), saturation=1.05), res_scale=opt.scale)''',
    '''    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.94, streak=0.06, lift=(0.98, 1.0, 1.02), gain=(1.04, 1.03, 0.95),
                         vignette=0.3, ink=0.4, ink_normal=(0.45, 1.3), saturation=1.05), res_scale=opt.scale)''')
rep('''        p = bike_pos(d)
        bike["root"].location = (p[0], p[1], 0.0)''', '''        p = bike_pos(d)
        wob = 0.02 * math.sin(d * 0.21) + 0.012 * math.sin(d * 0.53)
        bike["root"].location = (p[0], p[1], 0.0)
        bike["root"].rotation_euler = (0, wob, -0.25 * (mot(d + 1)[0] - mot(d - 1)[0]) * PPM / 4.17)
        # wind sways the crowns (dappled shadows move on path and lawn)
        rr = tree_rot.copy()
        rr[:, 0] = 0.012 * np.sin(d * 0.09 + tree_ph)
        rr[:, 1] = 0.012 * np.cos(d * 0.07 + tree_ph * 1.3)
        geo.update_points(tree_obj, cl[:, :3], rot=rr)''')
rep('''        rider.set_world(Jw, 0.0)
        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})
        look.boil(st, d // 2)
        look.grain_seed(d // 2)
        look.set_drawing(d // 2, PAINT_BOIL)''', '''        rider.set_world(Jw, 0.0)
        hd_ = Jw["head"]
        helmet.location = (hd_[0], hd_[1] - 0.01, hd_[2] + 0.05)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)''')
rep('''    r.update = update
    r.finish = lambda out: json.dump(log, open(os.path.join(out, "thread_log.json"), "w"))''', '''    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])''')
open(p, "w").write(s)
print("s09 patched")
