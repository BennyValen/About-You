p = "blender/scenes/s03.py"
s = open(p).read()


def rep(a, b, cnt=1):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b, cnt)


rep('''from kit import core, look, geo, human, thread, boats, creatures''', '''from kit import core, look, geo, human, boats, creatures, plants, rope_io''')
rep('''PAINT_BOIL = 0.06''', '''POST = dict(light_deg=132.0, flow_deg=90.0, stroke_px=12.0, boil_mean=1.7, thread_shadow_px=1.5, repaint=0.5)''')

# ---- pad material: more veins, secondary veins, lighter rims, wet highlight, centre-to-rim shading
rep('''        fr = _math(nt, "FRACT", _math(nt, "MULTIPLY", ang, 22 / (2 * math.pi), (-650, 40)), None, (-520, 40))
        dv = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", fr, 0.5, (-400, 40)), None, (-300, 40))
        width = _math(nt, "MULTIPLY", r, 0.07, (-400, -90))
        vein = _math(nt, "LESS_THAN", _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 0.5, dv, (-200, 40)), r, (-100, 40)), width, (0, 40))
        vein = _math(nt, "MULTIPLY", vein, _math(nt, "LESS_THAN", r, 0.8, (-100, -150)), (100, 0))
        hub = _math(nt, "LESS_THAN", r, 0.06, (100, -150))
        lit = _mixrgb(nt, "MULTIPLY", 1.0, ramp.outputs[0], (1.32, 1.34, 1.18, 1), (150, 300))
        c = _mixrgb(nt, "MIX", _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", vein, 0.75, (200, 0)), hub, (300, 0)), ramp.outputs[0], lit, (400, 200))
        return c''', '''        def veins(count, w, y):
            fr = _math(nt, "FRACT", _math(nt, "MULTIPLY", ang, count / (2 * math.pi), (-650, y)), None, (-520, y))
            dv = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", fr, 0.5, (-400, y)), None, (-300, y))
            d = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 0.5, dv, (-200, y)), r, (-100, y))
            mr = _n(nt, "ShaderNodeMapRange", (0, y), clamp=True)
            _l(nt, d, mr.inputs["Value"])
            mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = w * 1.6, w * 0.4
            return mr.outputs["Result"]
        v1 = veins(26, 0.022, 40)
        v2 = _math(nt, "MULTIPLY", veins(52, 0.012, -40), _math(nt, "GREATER_THAN", r, 0.45, (-100, -60)), (100, -40))
        vein = _math(nt, "MAXIMUM", v1, _math(nt, "MULTIPLY", v2, 0.6, (150, -40)), (200, 0))
        vein = _math(nt, "MULTIPLY", vein, _math(nt, "LESS_THAN", r, 0.86, (-100, -150)), (250, 0))
        hub = _math(nt, "LESS_THAN", r, 0.07, (100, -150))
        lit = _mixrgb(nt, "MULTIPLY", 1.0, ramp.outputs[0], (1.36, 1.36, 1.16, 1), (150, 300))
        c = _mixrgb(nt, "MIX", _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", vein, 0.8, (300, 0)), hub, (350, 0)), ramp.outputs[0], lit, (400, 200))
        # centre lighter, rim band lighter still with a darker inner edge (rolled rim), wet sheen near the centre
        shade = _n(nt, "ShaderNodeMapRange", (300, -250), clamp=True)
        _l(nt, r, shade.inputs["Value"])
        shade.inputs["From Min"].default_value, shade.inputs["From Max"].default_value = 0.1, 0.84
        shade.inputs["To Min"].default_value, shade.inputs["To Max"].default_value = 1.06, 0.88
        c = look.mul_color(nt, c, shade.outputs["Result"], (500, 150))
        rim = _n(nt, "ShaderNodeMapRange", (300, -400), clamp=True, interpolation_type="SMOOTHSTEP")
        _l(nt, r, rim.inputs["Value"])
        rim.inputs["From Min"].default_value, rim.inputs["From Max"].default_value = 0.86, 0.93
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", rim.outputs["Result"], 0.55, (450, -400)), c, (0.62, 0.78, 0.32, 1), (600, 100))
        wet = _math(nt, "EXPONENT", _math(nt, "MULTIPLY", _math(nt, "MULTIPLY", r, r, (300, -550)), -18.0, (400, -550)), None, (500, -550))
        c = _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", wet, 0.18, (600, -550)), c, (0.9, 0.95, 0.85, 1), (700, 50))
        return c''')
rep('''    return look.cel(name, colors[0], shadow=(0.6, 0.66, 0.66, 1), high=(1.12, 1.12, 1.02, 1), t1=0.42, t2=0.96,
                    paint=0.07 if not dark else 0.12, paint_scale=2.4, base_node=base, rough=0.5)''',
    '''    return look.cel(name, colors[0], shadow=(0.6, 0.66, 0.66, 1), high=(1.12, 1.12, 1.02, 1), t1=0.42, t2=0.96,
                    paint=0.04 if not dark else 0.08, paint_scale=2.4, base_node=base, rough=0.5, soft=0.2, ao=0.55, ao_dist=0.3)''')

rep('''    sc = core.reset(opt.scale, getattr(opt, "samples", 8))''', '''    sc = core.reset(opt.scale, getattr(opt, "samples", 2))''')

# ---- water: drifting ripples with the current, glints, sky sheen
rep('''        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", mr.outputs["Result"], 0.5, (-450, -50)), c, core.hexc("#3f6450"), (-300, 100))''',
    '''        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", mr.outputs["Result"], 0.5, (-450, -50)), c, core.hexc("#3f6450"), (-300, 100))
        # soft sky reflections: large pale sheen patches drifting slowly
        sk = _n(nt, "ShaderNodeTexNoise", (-800, -300))
        _l(nt, geo_n.outputs["Position"], sk.inputs["Vector"])
        sk.inputs["Scale"].default_value = 0.09
        sk.inputs["Detail"].default_value = 2
        skm = _n(nt, "ShaderNodeMapRange", (-600, -300), clamp=True)
        _l(nt, sk.outputs["Fac"], skm.inputs["Value"])
        skm.inputs["From Min"].default_value, skm.inputs["From Max"].default_value = 0.5, 0.75
        c = _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", skm.outputs["Result"], 0.16, (-450, -300)), c, core.hexc("#a9c7c2"), (-200, 50))
        # glints: tiny bright specks where ripples catch the sun (move with the current)
        mpg = _n(nt, "ShaderNodeMapping", (-1000, -500))
        _l(nt, geo_n.outputs["Position"], mpg.inputs[0])
        dr = mpg.inputs["Location"].driver_add("default_value", 1).driver
        dr.type = "SCRIPTED"
        dr.expression = "frame * 0.004"
        gl = _n(nt, "ShaderNodeTexNoise", (-800, -500), noise_dimensions="4D")
        _l(nt, mpg.outputs[0], gl.inputs["Vector"])
        gl.inputs["Scale"].default_value = 7.0
        dg = gl.inputs["W"].driver_add("default_value").driver
        dg.type = "SCRIPTED"
        dg.expression = "floor(frame / 2) * 0.08"
        glm = _n(nt, "ShaderNodeMapRange", (-600, -500), clamp=True)
        _l(nt, gl.outputs["Fac"], glm.inputs["Value"])
        glm.inputs["From Min"].default_value, glm.inputs["From Max"].default_value = 0.74, 0.8
        c = _mixrgb(nt, "SCREEN", _math(nt, "MULTIPLY", glm.outputs["Result"], 0.5, (-450, -500)), c, core.hexc("#e8f2df"), (-100, 0))
        return c''')
rep('''        wn = _n(nt, "ShaderNodeTexNoise", (-1000, -400), noise_dimensions="4D")
        _l(nt, geo_n.outputs["Position"], wn.inputs["Vector"])''', '''        mpw = _n(nt, "ShaderNodeMapping", (-1100, -400))
        _l(nt, geo_n.outputs["Position"], mpw.inputs[0])
        dw = mpw.inputs["Location"].driver_add("default_value", 1).driver
        dw.type = "SCRIPTED"
        dw.expression = "frame * 0.004"
        wn = _n(nt, "ShaderNodeTexNoise", (-1000, -400), noise_dimensions="4D")
        _l(nt, mpw.outputs[0], wn.inputs["Vector"])''')
rep('''        d.expression = "frame / 48.0"''', '''        d.expression = "floor(frame / 2) / 24.0"''')
rep('''                    base_node=water_base, height_node=water_h, bump=0.1, bump_dist=0.02, alpha=0.82, rough=0.1)''',
    '''                    base_node=water_base, height_node=water_h, bump=0.1, bump_dist=0.02, alpha=0.8, rough=0.1, soft=0.2, ao=0.0)''')

# ---- pads pushed aside near the boat, bobbing; flowers, buds, reeds
rep('''    P = place(900, 0.42, 1.75, 0.15, 0.01)
    n = len(P)
    geo.instances("pads", protos, np.c_[P[:, 0], P[:, 1], P[:, 3]], rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)],
                  scl=np.c_[P[:, 2], P[:, 2], P[:, 2] * 0.6], variant=rng.integers(0, 5, n), tint=rng.random(n), coll=env)''',
    '''    P = place(900, 0.42, 1.75, 0.15, 0.01)
    n = len(P)
    pad_rot = np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)]
    pads_obj = geo.instances("pads", protos, np.c_[P[:, 0], P[:, 1], P[:, 3]], rot=pad_rot,
                             scl=np.c_[P[:, 2], P[:, 2], P[:, 2] * 0.6], variant=rng.integers(0, 5, n), tint=rng.random(n), coll=env)
    pad_ph = rng.uniform(0, 6.28, n)
    # water lilies (pink flowers with a yellow centre) and closed buds, sitting on some pads
    fprotos = geo.proto_collection("FLOWER_PROTOS")
    petal = look.cel("lily_petal", core.hexc("#f2b6c8"), shadow=(0.75, 0.62, 0.78, 1), high=(1.06, 1.04, 1.04, 1), paint=0.03, soft=0.25, ao=0.4,
                     base_node=look.instancer_palette([core.hexc("#f4bfd0"), core.hexc("#eaa2ba"), core.hexc("#f7d3de"), core.hexc("#e48fae")]))
    centre = look.cel("lily_centre", core.hexc("#f2c84b"), paint=0.0, soft=0.2)
    def lily(name, seed, rings=((10, 0.2, 0.55), (8, 0.14, 0.9)), closed=False):
        lr = np.random.default_rng(seed)
        V, F = [], []
        for nring, (np_, ln, lift) in enumerate(rings):
            for i in range(np_):
                a = 2 * math.pi * (i + 0.5 * nring) / np_ + lr.normal(0, 0.05)
                d = np.array([math.cos(a), math.sin(a), 0.0])
                sd = np.array([-math.sin(a), math.cos(a), 0.0])
                L = ln * lr.uniform(0.85, 1.1) * (0.5 if closed else 1.0)
                up = lift * (2.2 if closed else 1.0)
                base = d * 0.02
                tip = d * L + np.array([0, 0, L * up])
                mid = d * L * 0.5 + np.array([0, 0, L * up * 0.35])
                i0 = len(V)
                V += [base, mid + sd * L * 0.22, tip, mid - sd * L * 0.22]
                F.append((i0, i0 + 1, i0 + 2, i0 + 3))
        ob = geo.mesh_from_faces(name, np.array(V), F, fprotos, smooth=True, mat=petal)
        return ob
    for i in range(3):
        lily(f"lily_{i}", 30 + i)
    lily("lily_bud", 40, rings=((6, 0.12, 1.0),), closed=True)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=0.045)
    cen = geo.bm_to_object(bm, "lily_zc", centre, fprotos)
    cen.location.z = 0.03
    picks = rng.choice(n, 34, replace=False)
    fl_pos = np.c_[P[picks, 0] + rng.normal(0, 0.15, 34) * P[picks, 2], P[picks, 1] + rng.normal(0, 0.15, 34) * P[picks, 2], np.full(34, 0.06)]
    fl_var = np.where(np.arange(34) < 24, rng.integers(0, 3, 34), 3)
    geo.instances("lilies", fprotos, fl_pos, rot=np.c_[np.zeros(34), np.zeros(34), rng.uniform(0, 6.28, 34)],
                  scl=np.repeat(rng.uniform(0.8, 1.3, 34)[:, None], 3, 1), variant=fl_var, tint=rng.random(34), coll=env)
    geo.instances("lily_centres", fprotos, fl_pos[:24] + np.array([0, 0, 0.0]), variant=np.full(24, 4), coll=env)
    # reeds at the outer edges of the pond
    rprotos = geo.proto_collection("REED_PROTOS")
    reedm = look.cel("reed", core.hexc("#6e8c45"), shadow=(0.55, 0.62, 0.6, 1), high=(1.12, 1.1, 1.0, 1), paint=0.04, soft=0.22, ao=0.4,
                     base_node=look.instancer_palette([core.hexc("#6e8c45"), core.hexc("#86a253"), core.hexc("#5b7a3c"), core.hexc("#9bb064")]))
    for i in range(4):
        plants.grass_tuft(f"reed_{i}", reedm, rprotos, seed=60 + i, n=(10, 22), height=rng.uniform(0.8, 1.3), lean=0.25)
    rp = []
    for side in (-1, 1):
        for y in np.arange(y0, y1, 0.55):
            if rng.random() < 0.7:
                rp.append((side * rng.uniform(4.6, 5.8), y + rng.normal(0, 0.2)))
    rp = np.array(rp)
    nr = len(rp)
    geo.instances("reeds", rprotos, np.c_[rp, np.full(nr, 0.0)], rot=np.c_[np.zeros(nr), np.zeros(nr), rng.uniform(0, 6.28, nr)],
                  scl=np.repeat(rng.uniform(0.8, 1.3, nr)[:, None], 3, 1), variant=rng.integers(0, 4, nr), tint=rng.random(nr), coll=env)''')

# koi: more translucent / softer under water
rep('''    kmat = look.cel("koi", core.hexc("#e6d8b2"), shadow=(0.72, 0.7, 0.62, 1), paint=0.05)''',
    '''    kmat = look.cel("koi", core.hexc("#d9d0ad"), shadow=(0.72, 0.7, 0.62, 1), paint=0.03, soft=0.3, alpha=0.8, ao=0.0)''')
rep('''        k = creatures.Koi(f"koi{i}", kmat, kfin, length=rng.uniform(1.05, 1.55), coll=ink, seed=i * 1.7)''',
    '''        k = creatures.Koi(f"koi{i}", kmat, kfin, length=rng.uniform(1.05, 1.55), coll=env, seed=i * 1.7)''')

# hero flags on boat / oars / rower materials
for nm in ('"hull"', '"hull_in"', '"trim"', '"seat"', '"metal"', '"oar"', '"blade"', '"grip"', '"rower_top"', '"rower_legs"', '"rower_shoes"',
           '"rower_hands"', '"rower_skin"', '"rower_hair"'):
    i = s.index(f"look.cel({nm},")
    j = s.index(")", s.index("paint=", i))
    s = s[:j] + ", soft=0.22, hero=True" + s[j:]

# ---- swirl puddles at each release + V-wake foam
rep('''    rmat = ring_material()
    rings = [ring_mesh(f"ring{i}", rmat, env) for i in range(8)]''', '''    rmat = ring_material()
    rings = [ring_mesh(f"ring{i}", rmat, env) for i in range(8)]
    # swirl puddles left by each blade at the release: a darker eddy with a light rim, drifting back, fading
    pmat_ = look.cel("puddle", core.hexc("#1c3529"), paint=0.0, soft=0.3, alpha=0.6, ao=0.0)
    pgrp = [x for x in pmat_.node_tree.nodes if x.type == "GROUP"][0]
    oi_ = _n(pmat_.node_tree, "ShaderNodeObjectInfo", (-300, -300))
    _l(pmat_.node_tree, oi_.outputs["Alpha"], pgrp.inputs["Alpha"])
    puddles = []
    for i in range(6):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=1.0)
        puddles.append(geo.bm_to_object(bm, f"puddle{i}", pmat_, env))
        rim_ = ring_mesh(f"puddle_rim{i}", rmat, env)
        rim_.parent = puddles[-1]
    # V-wake: closed-form foam particles from the bow shoulders and the stern
    def hull_frame(t):
        M = boat_matrix(t)
        o = M @ Vector((0, 0, 0))
        sp = speed_profile()(int(min(max(t - start, 0), end - start))) / PPM
        return (o.x, o.y), (0.0, 1.0), (1.0, 0.0), sp
    wake = geo.Wake(hull_frame, start - 60, end + 2, rate=5, life=70.0, spread=0.55, decay=0.045, seed=33,
                    emit_points=((-0.5, 1.0, -1), (0.5, 1.0, 1), (-0.45, -1.6, -1), (0.45, -1.6, 1)), jitter=0.05)
    foam = look.cel("foam", core.hexc("#e5efe2"), paint=0.0, soft=0.3, alpha=0.75, ao=0.0)
    fgrp = [x for x in foam.node_tree.nodes if x.type == "GROUP"][0]
    fat = _n(foam.node_tree, "ShaderNodeAttribute", (-300, -300), attribute_type="INSTANCER", attribute_name="tint")
    _l(foam.node_tree, fat.outputs["Fac"], fgrp.inputs["Alpha"])
    wproto = geo.proto_collection("P_foam")
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=10, radius=0.05)
    geo.bm_to_object(bm, "foam_dot", foam, wproto)
    NW = 700
    foam_obj = geo.instances("foam", wproto, np.tile([0.0, -1e4, -50.0], (NW, 1)), tint=np.zeros(NW), coll=env)''')

# ---- rope (v3): floats from the stern
rep('''    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    frames = list(range(start, end))
    def stern(t):
        M = boat_matrix(t)
        return np.array(M @ Vector((0, -1.79, 0.08)))
    def flow(x, y, t):
        fx = 0.05 * np.sin(y * 0.8 + t * 0.03) + 0.03 * np.sin(y * 2.1 - t * 0.05)
        fy = np.zeros_like(x)
        return fx, fy
    cord = thread.Cord(n_seg=200, length=11.0, mode="water", water_level=0.0, water_drag=5.0, flow=flow, substeps=6, iters=22, bend=0.12)
    sim = cord.run(frames, stern, (0.0, -1.0), warm=96)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.6)''', '''    frames = list(range(start, end, 2))
    def stern(t):
        M = boat_matrix(t)
        return np.array(M @ Vector((0, -1.79, 0.08)))
    rope = rope_io.Owner("A", SCENE, rig, stern, frames, trail=(0.0, -1.0), warm=150, cfg_motion=False)''')

# boat follows the rope_cfg weave (boat yaw/weave shared with the rope attach point)
rep('''    def boat_matrix(t):
        p = rig.screen_to_world(t, *BOAT_SCREEN, 0.0)''', '''    mot = rope_io.C.owner_motion(SCENE)
    def boat_matrix(t):
        tt = min(max(t, start), end)
        p = rig.screen_to_world(tt, *BOAT_SCREEN, 0.0)
        p = Vector((p[0] + mot(t)[0], p[1] + (min(t - start, 0) + max(t - end, 0)) * 2.3 / PPM, 0.0))''')
rep('''        return Matrix.Translation((p[0], p[1], heave)) @ Euler((pitch, roll, 0.0)).to_matrix().to_4x4()''',
    '''        yaw = -0.3 * (mot(t + 1)[0] - mot(t - 1)[0]) * PPM / 2.3
        return Matrix.Translation((p[0], p[1], heave)) @ Euler((pitch, roll, yaw)).to_matrix().to_4x4()''')

rep('''    look.compositor(dict(kuwahara=10, bloom=0.35, bloom_threshold=0.95, streak=0.08, lift=(0.98, 1.0, 1.01), gain=(1.03, 1.02, 0.97),
                         vignette=0.28, grain=0.03, ink=0.6), res_scale=opt.scale)''', '''    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.98, 1.0, 1.01), gain=(1.03, 1.02, 0.97),
                         vignette=0.26, ink=0.4), res_scale=opt.scale)''')

# update: pads pushed aside + bob, puddles, foam, rope export
rep('''        for fi in fish:''', '''        # pads near the boat are pushed aside by the bow wave and bob in the wake, then drift back
        bo = boat.matrix_world.translation
        dy = P[:, 1] - bo.y
        dx = P[:, 0] - bo.x
        env_ = np.exp(-np.maximum(dy - 1.2, 0) ** 2 / 0.6) * np.exp(-np.maximum(-dy - 1.0, 0) / 3.5) * (dy > -12)
        prox = np.exp(-np.maximum(np.abs(dx) - 0.9 - P[:, 2], 0) / 0.5)
        push = 0.28 * env_ * prox
        pos = np.c_[P[:, 0] + np.sign(dx) * push, P[:, 1] - 0.05 * push, P[:, 3] + 0.012 * env_ * prox * np.sin(d * 0.35 + pad_ph)]
        rot = pad_rot.copy()
        rot[:, 0] = 0.03 * env_ * prox * np.sin(d * 0.3 + pad_ph)
        rot[:, 1] = 0.03 * env_ * prox * np.cos(d * 0.27 + pad_ph)
        geo.update_points(pads_obj, pos, rot=rot)
        # swirl puddles at the last releases
        k2 = 0
        for back in range(3):
            cf = math.floor((d - start + CATCH_OFFSET - 0.42 * STROKE) / STROKE) - back
            tr_ = start - CATCH_OFFSET + 0.42 * STROKE + cf * STROKE
            age = d - tr_
            if age < 0 or age > 72:
                continue
            Mr = boat_matrix(tr_)
            _, inf_r = boats.row_pose(0.42, seat_pos, lock_l, lock_r)
            for s_ in ("l", "r"):
                if k2 >= len(puddles):
                    break
                bp = Mr @ Vector(inf_r[s_]["blade"].tolist())
                pr_ = 0.14 + age * 0.004
                puddles[k2].location = (bp.x, bp.y - age * 0.004, 0.011)
                puddles[k2].scale = (pr_, pr_ * 0.85, 1)
                puddles[k2].rotation_euler = (0, 0, age * 0.04 * (1 if s_ == "r" else -1))
                puddles[k2].color = (1, 1, 1, max(0.0, 0.45 * (1 - age / 72.0)))
                for ch in puddles[k2].children:
                    ch.color = (1, 1, 1, max(0.0, 0.5 * (1 - age / 72.0)))
                puddles[k2].hide_render = False
                k2 += 1
        for j in range(k2, len(puddles)):
            puddles[j].hide_render = True
        W_ = wake.at(d, NW)
        alive = W_[:, 2] > 0
        fp = np.c_[W_[:, 0], W_[:, 1], np.full(NW, 0.012)]
        fp[~alive] = (0.0, -1e4, -50.0)
        fs = np.repeat(np.maximum(W_[:, 2], 0.01)[:, None], 3, 1) * np.array([1.6, 1.0, 1.0])
        me = foam_obj.data
        me.vertices.foreach_set("co", fp.astype(np.float32).ravel())
        me.attributes["scl"].data.foreach_set("vector", fs.astype(np.float32).ravel())
        me.attributes["rot"].data.foreach_set("vector", np.c_[np.zeros(NW), np.zeros(NW), W_[:, 3]].astype(np.float32).ravel())
        me.attributes["tint"].data.foreach_set("value", (0.7 * (1 - W_[:, 4]) * alive).astype(np.float32))
        me.update()
        for fi in fish:''')
rep('''        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})
        look.boil(st, d // 2)
        look.grain_seed(d // 2)
        look.set_drawing(d // 2, PAINT_BOIL)''', '''        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)''')
rep('''    r.update = update
    r.finish = lambda out: json.dump(log, open(os.path.join(out, "thread_log.json"), "w"))''', '''    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])''')
open(p, "w").write(s)
print("s03 patched")
