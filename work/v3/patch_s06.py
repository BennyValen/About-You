p = "blender/scenes/s06.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''from kit import core, look, geo, human, thread, boats, creatures''', '''from kit import core, look, geo, human, boats, creatures, plants, rope_io''')
rep('''PAINT_BOIL = 0.45''', '''POST = dict(light_deg=135.0, flow_deg=60.0, stroke_px=12.0, boil_mean=2.0, thread_shadow_px=1.8, thread_shadow_per_m=0.0, repaint=0.5)''')
rep('''    sc = core.reset(opt.scale, getattr(opt, "samples", 8))''', '''    sc = core.reset(opt.scale, getattr(opt, "samples", 2))''')

# corals: leafy painted clumps with per-clump coral colours, palm-frond fans, pale sand halos
rep('''    cmat = look.cel("coral", coral_cols[0], shadow=(0.55, 0.62, 0.78, 1), high=(1.15, 1.13, 1.05, 1), paint=0.08, paint_scale=5.0,
                    base_node=coral_base, rough=0.9)
    for i in range(6):
        geo.knobbly(f"coral_{i}", cmat, protos, seed=40 + i, subdiv=3, knob=0.5, flat=0.5, lumps=7)''', '''    def coral_leaf_base(nt):
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
    ra.data.foreach_set("value", np.array([0.0] + [1.0] * nh, np.float32))''')
rep('''    geo.instances("corals", protos, pts, rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)], scl=np.array(scl),
                  variant=np.array(var), tint=np.array(tint), coll=env)''', '''    geo.instances("corals", protos, pts, rot=np.c_[np.zeros(n), np.zeros(n), rng.uniform(0, 6.28, n)], scl=np.array(scl),
                  variant=np.array(var), tint=np.array(tint), coll=env)
    hp = np.array([(cx, cy, -float(depth(cx, cy)) + 0.015) for cx, cy, r in CORALS])
    hr = np.array([r * 1.45 for cx, cy, r in CORALS])
    geo.instances("halos", hprot, hp, scl=np.c_[hr, hr, np.ones(len(hr))], coll=env)
    pp = []
    for cx, cy, r in CORALS:
        for _ in range(int(rng.integers(1, 4))):
            a = rng.uniform(0, 6.28)
            rr = r * 0.5 * math.sqrt(rng.random())
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            pp.append((x, y, -float(depth(x, y)) + 0.45))
    pp = np.array(pp)
    npp = len(pp)
    geo.instances("palms", palms, pp, rot=np.c_[np.zeros(npp), np.zeros(npp), rng.uniform(0, 6.28, npp)],
                  scl=np.repeat(rng.uniform(1.4, 2.2, npp)[:, None], 3, 1), variant=rng.integers(0, 3, npp), tint=rng.random(npp), coll=env)''')

# manta: two-tone painted body
rep('''    manta = creatures.Manta("manta", look.cel("manta", core.hexc("#45586a"), shadow=(0.55, 0.6, 0.75, 1), paint=0.05), span=4.0, coll=ink)''',
    '''    def manta_base(nt):
        g = _n(nt, "ShaderNodeNewGeometry", (-700, 0))
        tc = _n(nt, "ShaderNodeTexCoord", (-700, -200))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-550, -200))
        _l(nt, tc.outputs["Object"], sx.inputs[0])
        edge = _n(nt, "ShaderNodeMapRange", (-400, -200), clamp=True)
        _l(nt, _math(nt, "ABSOLUTE", sx.outputs[0], None, (-450, -250)), edge.inputs["Value"])
        edge.inputs["From Min"].default_value, edge.inputs["From Max"].default_value = 0.6, 2.0
        return _mixrgb(nt, "MIX", edge.outputs["Result"], core.hexc("#3c4f63"), core.hexc("#6e8494"), (-200, 0))
    manta = creatures.Manta("manta", look.cel("manta", core.hexc("#45586a"), shadow=(0.55, 0.6, 0.78, 1), high=(1.15, 1.15, 1.15, 1), paint=0.03,
                                              base_node=manta_base, soft=0.22, rim=0.3, hero=True), span=4.0, coll=ink)''')

# fish schools
rep('''    # sailing dinghy, heeled to starboard''', '''    # fish schools: small silvery fish swirling around a drifting school centre
    fish_m = look.cel("fish", core.hexc("#c9d8dc"), shadow=(0.6, 0.7, 0.8, 1), paint=0.0, soft=0.25, ao=0.0)
    fprot = geo.proto_collection("P_fish")
    fv = np.array([(0, 0.11, 0), (0.025, 0.02, 0.01), (0.012, -0.06, 0), (0.035, -0.1, 0), (-0.035, -0.1, 0), (-0.012, -0.06, 0), (-0.025, 0.02, 0.01)])
    geo.mesh_from_faces("fishp", fv, [(0, 1, 2, 5, 6), (2, 3, 4, 5)], fprot, smooth=False, mat=fish_m)
    schools = []
    NF = 26
    for k, (sx_, sy_, vx_, vy_) in enumerate(((-2.5, 9.0, 0.012, 0.02), (3.0, 20.0, -0.01, 0.014), (-1.0, 27.0, 0.008, 0.024))):
        offs = rng.normal(0, 1, (NF, 2)) * np.array([0.55, 0.35])
        ph = rng.uniform(0, 6.28, NF)
        ob_ = geo.instances(f"school{k}", fprot, np.zeros((NF, 3)), coll=env)
        schools.append((ob_, sx_, sy_, vx_, vy_, offs, ph))

    # sailing dinghy, heeled to starboard''')

# sail seams + hero/soft flags
rep('''    sail_mat = look.cel("sail", core.hexc("#f4f2ea"), shadow=(0.7, 0.72, 0.82, 1), high=(1.05, 1.05, 1.05, 1), paint=0.06, paint_scale=6.0,
                        backface=True)''', '''    def sail_base(nt):
        tc = _n(nt, "ShaderNodeTexCoord", (-700, 0))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-550, 0))
        _l(nt, tc.outputs["Object"], sx.inputs[0])
        seam = _math(nt, "LESS_THAN", _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", _math(nt, "FRACT", _math(nt, "MULTIPLY", sx.outputs[2], 2.2, (-400, 0)), None,
                                                                                                   (-300, 0)), 0.5, (-200, 0)), None, (-100, 0)), 0.02, (0, 0))
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", seam, 0.5, (100, 0)), core.hexc("#f4f0e4"), core.hexc("#c9c2b0"), (200, 0))
    sail_mat = look.cel("sail", core.hexc("#f4f2ea"), shadow=(0.7, 0.72, 0.84, 1), high=(1.05, 1.05, 1.05, 1), paint=0.04, base_node=sail_base,
                        backface=True, soft=0.3, hero=True)''')
for nm in ('"hull"', '"hull_in"', '"trim"', '"seat"', '"metal"', '"spar"', '"sailor_top"', '"sailor_legs"', '"sailor_shoes"', '"sailor_hands"',
           '"sailor_skin"', '"sailor_hair"'):
    i = s.index(f"look.cel({nm},")
    j = s.index(")", s.index("paint=", i))
    s = s[:j] + ", soft=0.22, hero=True" + s[j:]

# boat follows the rope_cfg weave; rope v3
rep('''    def boat_frame(t):
        p = rig.screen_to_world(t, *BOAT_SCREEN, 0.0)
        return p''', '''    mot = rope_io.C.owner_motion(SCENE)
    def boat_frame(t):
        tt = min(max(t, start), end)
        p = rig.screen_to_world(tt, *BOAT_SCREEN, 0.0)
        return Vector((p[0] + mot(t)[0], p[1] + (min(t - start, 0) + max(t - end, 0)) * 3.51 / PPM, 0.0))''')
rep('''    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    frames = list(range(start, end))
    def stern(t):
        return np.array(boat_matrix(t) @ Vector((0, -1.69, 0.06)))
    def flow(x, y, t):
        return 0.04 * np.sin(y * 0.7 + t * 0.025), 0.02 * np.sin(x * 1.3 + t * 0.03)
    cord = thread.Cord(n_seg=200, length=13.0, mode="water", water_level=0.0, water_drag=5.0, flow=flow, substeps=6, iters=22, bend=0.12)
    sim = cord.run(frames, stern, (0.0, -1.0), warm=96)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.6)''', '''    def stern(t):
        return np.array(boat_matrix(t) @ Vector((0, -1.69, 0.06)))
    rope = rope_io.Owner("A", SCENE, rig, stern, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False)''')
rep('''    wake = geo.Wake(hull_frame, start, end, rate=10, life=70.0, spread=0.55, decay=0.05, seed=6,''', '''    wake = geo.Wake(hull_frame, start, end, rate=6, life=70.0, spread=0.55, decay=0.05, seed=6,''')
rep('''    look.compositor(dict(kuwahara=10, bloom=0.4, bloom_threshold=0.95, streak=0.1, lift=(0.99, 1.0, 1.01), gain=(1.02, 1.01, 0.99),
                         vignette=0.24, grain=0.03, ink=0.55), res_scale=opt.scale)''', '''    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.99, 1.0, 1.01), gain=(1.02, 1.01, 0.99),
                         vignette=0.22, ink=0.4), res_scale=opt.scale)''')
rep('''        s = W[:, 2] * 1.6
        geo.update_points(foam, np.c_[W[:, 0], W[:, 1], z], rot=np.c_[np.zeros(MAXF), np.zeros(MAXF), W[:, 3]],
                          scl=np.c_[s, s * 0.8, s])
        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})
        look.boil(st, d // 2)
        look.grain_seed(d // 2)
        look.set_drawing(d // 2, PAINT_BOIL)''', '''        s = W[:, 2] * 1.1
        geo.update_points(foam, np.c_[W[:, 0], W[:, 1], z], rot=np.c_[np.zeros(MAXF), np.zeros(MAXF), W[:, 3]],
                          scl=np.c_[s, s * 0.8, s])
        t_ = d - start
        for ob_, sx_, sy_, vx_, vy_, offs, ph in schools:
            cx, cy = sx_ + vx_ * t_ + 0.4 * math.sin(t_ * 0.02), sy_ + vy_ * t_
            heading = math.atan2(-(vx_ + 0.008 * math.cos(t_ * 0.02)), vy_)
            R2 = np.array([[math.cos(heading), -math.sin(heading)], [math.sin(heading), math.cos(heading)]])
            o2 = offs @ R2.T * (1 + 0.15 * np.sin(t_ * 0.05 + ph))[:, None]
            px_ = cx + o2[:, 0] + 0.05 * np.sin(t_ * 0.3 + ph)
            py_ = cy + o2[:, 1]
            pz = np.array([-float(depth(a_, b_)) * 0.5 for a_, b_ in zip(px_, py_)])
            geo.update_points(ob_, np.c_[px_, py_, pz], rot=np.c_[np.zeros(len(px_)), np.zeros(len(px_)), heading + 0.25 * np.sin(t_ * 0.4 + ph)])
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)''')
rep('''    r.update = update
    r.finish = lambda out: json.dump(log, open(os.path.join(out, "thread_log.json"), "w"))''', '''    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])''')
open(p, "w").write(s)
print("s06 patched")
