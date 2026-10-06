p = "blender/scenes/s08.py"
s = open(p).read()


def rep(a, b, cnt=1):
    global s
    assert s.count(a) == cnt, (s.count(a), a[:90])
    s = s.replace(a, b)


rep('''TURN_A, TURN_HZ = 0.04, 0.22         # v4: a straight run with only tiny corrections (half-width m, rate)''',
    '''TURN_A, TURN_HZ = 0.022, 0.22        # v4: a straight run with only tiny corrections (half-width m, rate)''')
# v4 palette: lit #D8E2F0, mid #93A3C6, shaded #56648F, deep #2C3764, headlamp #F2C98A (direct base colours)
rep('''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#343d60"), core.hexc("#46507c"), (-1200, 300))''',
    '''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#C2CDE4"), core.hexc("#D8E2F0"), (-1200, 300))''')
rep('''    return look.cel("snow", core.hexc("#3a4878"), shadow=(0.42, 0.48, 0.85, 1), high=(1.35, 1.35, 1.4, 1), t1=0.45, t2=0.95, paint=0.04,''',
    '''    return look.cel("snow", core.hexc("#D8E2F0"), shadow=(0.40, 0.44, 0.60, 1), high=(1.06, 1.06, 1.06, 1), t1=0.45, t2=0.95, paint=0.04,''')
rep('''    core.world_ambient(core.hexc("#1c2448"), 0.1)
    core.sun(MOON_DIR, core.sun_irradiance_for(0.26, MOON_DIR, 0.06), core.hexc("#b6c8ff"), angle_deg=1.2, name="moon")''',
    '''    core.world_ambient(core.hexc("#8a96c0"), 0.28)
    core.sun(MOON_DIR, core.sun_irradiance_for(0.78, MOON_DIR, 0.2), core.hexc("#dfe6f6"), angle_deg=1.2, name="moon")''')
# pines: star-shaped crowns laden with snow (moonlit tips, deep blue-green needles), not black spikes
rep('''    tm = tree_material()
    for i in range(4):''', '''    tm = snow_pine_material()
    for i in range(4):''')
rep('''def ski_local(t, edge, height=1.8):''', '''def snow_pine_material():
    def base(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-1000, 200))
        nz = _n(nt, "ShaderNodeTexNoise", (-800, 0))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 3.0
        nz.inputs["Detail"].default_value = 3
        at = _n(nt, "ShaderNodeAttribute", (-1000, 400), attribute_type="GEOMETRY", attribute_name="tip")
        tipv = _math(nt, "ADD", at.outputs["Fac"], _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.7, (-450, 300)), (-250, 350))
        mr = _n(nt, "ShaderNodeMapRange", (-150, 350), clamp=True)
        _l(nt, tipv, mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.85, 1.05
        needles = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#2C3764"), core.hexc("#3E4A7A"), (-500, 0))
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", mr.outputs["Result"], 0.85, (-350, 300)), needles, core.hexc("#D8E2F0"), (-300, 100))
    return look.cel("snowpine", core.hexc("#3E4A7A"), shadow=(0.5, 0.54, 0.7, 1), high=(1.1, 1.1, 1.12, 1), t1=0.38, t2=0.92,
                    paint=0.04, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0, soft=0.3, ao=0.4, ao_dist=1.0, rim=0.5)


def ski_local(t, edge, height=1.8):''')
# poles trail back close to the body (a tuck on a straight run), skis parallel
rep('''        poles[s] = (J[f"hnd_{s}"], np.array([sx * 0.55 * k, -0.45 * k, 0.0]))''',
    '''        poles[s] = (J[f"hnd_{s}"], np.array([sx * 0.34 * k, -0.95 * k, 0.05]))''')
rep('''            plant = math.cos(2 * math.pi * TURN_HZ * d / 24.0) ** 8''', '''            plant = 0.0                   # v4: straight run, no pole plants''')
rep('''            skis[sd].rotation_euler = (0, 0.35 * edge, hd)''', '''            skis[sd].rotation_euler = (0, 0.15 * edge, hd)       # both skis share the heading: always parallel''')
# helmet goggles
rep('''    skis, poles = {}, {}
    for sd in ("l", "r"):''', '''    gog_m = look.cel("goggles", core.hexc("#F2C98A"), shadow=(0.4, 0.35, 0.5, 1), high=(1.5, 1.4, 1.2, 1), paint=0.0, soft=0.15, rim=0.6, hero=True)
    strap_m = look.cel("gog_strap", core.hexc("#232838"), paint=0.0, hero=True)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.19, 0.05, 0.07), verts=bm.verts)
    goggles = geo.bm_to_object(bm, "goggles", gog_m, ink, smooth=False)
    bm = bmesh.new()
    bmesh.ops.create_cylinder(bm, cap_ends=False, segments=20, radius1=0.125, radius2=0.125, depth=0.035)
    strap = geo.bm_to_object(bm, "gog_strap", strap_m, ink, smooth=True)
    skis, poles = {}, {}
    for sd in ("l", "r"):''')
rep('''        head = Jw["head"]
        hlo.location = Vector((head + rot_z(hd) @ np.array([0, 0.3, 0.35])).tolist())
        aim = Vector((-math.sin(hd), math.cos(hd), -1.7)).normalized()''', '''        head = Jw["head"]
        hc = head + rot_z(hd) @ np.array([0, 0.0, 0.1])
        goggles.location = Vector((hc + rot_z(hd) @ np.array([0, 0.12, 0.0])).tolist())
        goggles.rotation_euler = (0, 0, hd)
        strap.location = Vector(hc.tolist())
        strap.rotation_euler = (0, 0, hd)
        hlo.location = Vector((head + rot_z(hd) @ np.array([0, 0.3, 0.35])).tolist())
        aim = Vector((-math.sin(hd), math.cos(hd), -0.62)).normalized()      # low: a long soft pool ahead
        cone.location = Vector((head[0], head[1], hg(float(head[0]), float(head[1])) + 0.9).tolist())
        cone.rotation_euler = (0, 0, hd)''')
# headlamp: warm #F2C98A, soft elongated pool plus a faint visible cone (beam through the cold air)
rep('''    hl.energy = 340.0
    hl.color = (1.0, 0.72, 0.42)
    hl.spot_size = math.radians(58)''', '''    hl.energy = 420.0
    hl.color = core.hexc("#F2C98A")[:3]
    hl.spot_size = math.radians(46)''')
rep('''    hlo = bpy.data.objects.new("headlamp", hl)
    env.objects.link(hlo)''', '''    hlo = bpy.data.objects.new("headlamp", hl)
    env.objects.link(hlo)
    cone_m = bpy.data.materials.new("lamp_cone")
    cone_m.use_nodes = True
    cnt = cone_m.node_tree
    cnt.nodes.clear()
    cout = _n(cnt, "ShaderNodeOutputMaterial", (600, 0))
    ctc = _n(cnt, "ShaderNodeTexCoord", (-900, 0))
    csx = _n(cnt, "ShaderNodeSeparateXYZ", (-700, 0))
    _l(cnt, ctc.outputs["Object"], csx.inputs[0])
    along = _math(cnt, "DIVIDE", csx.outputs[1], 6.0, (-550, 0), clamp=True)                 # 0 at the head, 1 at 6 m
    halfw = _math(cnt, "ADD", 0.08, _math(cnt, "MULTIPLY", along, 1.5, (-450, 100)), (-350, 100))
    q = _math(cnt, "DIVIDE", _math(cnt, "ABSOLUTE", csx.outputs[0], None, (-450, 200)), halfw, (-250, 150))
    side = _math(cnt, "POWER", _math(cnt, "SUBTRACT", 1.0, q, (-150, 150), clamp=True), 1.5, (-50, 150))
    fade = _math(cnt, "MULTIPLY", _math(cnt, "POWER", _math(cnt, "SUBTRACT", 1.0, along, (-350, -100)), 1.6, (-250, -100)),
                 _math(cnt, "GREATER_THAN", csx.outputs[1], 0.25, (-250, -200)), (-150, -100))
    ca = _math(cnt, "MULTIPLY", _math(cnt, "MULTIPLY", side, fade, (50, 50)), 0.22, (150, 50))
    cem = _n(cnt, "ShaderNodeEmission", (300, 100))
    cem.inputs[0].default_value = core.hexc("#F2C98A")
    cem.inputs[1].default_value = 1.0
    ctr = _n(cnt, "ShaderNodeBsdfTransparent", (300, -100))
    cmx = _n(cnt, "ShaderNodeMixShader", (450, 0))
    _l(cnt, ca, cmx.inputs[0])
    _l(cnt, ctr.outputs[0], cmx.inputs[1])
    _l(cnt, cem.outputs[0], cmx.inputs[2])
    _l(cnt, cmx.outputs[0], cout.inputs[0])
    cone_m.surface_render_method = "BLENDED"
    cone = geo.grid("lamp_cone", -2.0, 0.0, 2.0, 6.0, 2, 2, None, env, cone_m)
    cone.visible_shadow = False''')
# twin tracks: a groove per ski with a ridge of pushed-up snow on both sides
rep('''            a = np.full(len(P), 0.55 if not rim else 0.35)
            if rim:
                P = P + moon_side * 0.045
            out.append((P[::2], a[::2], np.ones(len(P[::2]))))''', '''            a = np.full(len(P), 0.55 if not rim else 0.35)
            if rim:
                perp = np.c_[np.cos(T[:, 3]), np.sin(T[:, 3])]
                for sg in (-1.0, 1.0):
                    out.append(((P + perp * 0.06 * sg)[::2], a[::2], np.ones(len(P[::2]))))
                continue
            out.append((P[::2], a[::2], np.ones(len(P[::2]))))''')
rep('''    groove_m = line_material("groove", core.hexc("#141b3a"), 0.8)
    rim_m = line_material("track_rim", core.hexc("#8ea2e0"), 1.0)''', '''    groove_m = line_material("groove", core.hexc("#56648F"), 0.9)
    rim_m = line_material("track_rim", core.hexc("#E4EAF6"), 0.95)''')
# continuous light powder spray off both ski tails (not only at turns)
rep('''        if abs(edge) > 0.55 and t % 2 == 0:
            outside = "l" if edge > 0 else "r"
            spray.append((t, skw[outside][0], skw[outside][1], hd, 1.0 if edge > 0 else -1.0))''',
    '''        if t % 2 == 0:
            for sd_, sg_ in (("l", 1.0), ("r", -1.0)):
                tail = skw[sd_] - np.array([-math.sin(hd), math.cos(hd), 0.0]) * 0.7
                spray.append((t, tail[0], tail[1], hd, sg_))''')
rep('''    NS = 10''', '''    NS = 5''')
rep('''    sp_m = look.cel("powder", core.hexc("#a9b8e8"), paint=0.0, soft=0.4, alpha=0.6, ao=0.0, light_tint=1.0)''',
    '''    sp_m = look.cel("powder", core.hexc("#E4EAF6"), paint=0.0, soft=0.4, alpha=0.6, ao=0.0, light_tint=1.0)''')
rep('''            P[alive, :2] = bx[alive] + (outv[alive] * (0.5 + 0.35 * np.abs(srng[alive, 0]))[:, None] + back[alive] * 0.4 +
                                        srng[alive, :2] * 0.12) * u[alive, None]
            P[alive, 2] = hg(P[alive, 0], P[alive, 1]) + 0.25 * np.sin(np.pi * np.clip(age[alive] / 0.9, 0, 1)) + 0.02
            S = np.repeat((0.7 + 2.2 * np.clip(age, 0, 1.4))[:, None], 3, 1)
            T = np.where(alive, 0.55 * (1 - age / 1.4) ** 1.4, 0.0)''',
    '''            P[alive, :2] = bx[alive] + (outv[alive] * (0.12 + 0.12 * np.abs(srng[alive, 0]))[:, None] + back[alive] * 0.25 +
                                        srng[alive, :2] * 0.06) * u[alive, None]
            P[alive, 2] = hg(P[alive, 0], P[alive, 1]) + 0.12 * np.sin(np.pi * np.clip(age[alive] / 0.9, 0, 1)) + 0.02
            S = np.repeat((0.5 + 1.4 * np.clip(age, 0, 1.4))[:, None], 3, 1)
            T = np.where(alive, 0.32 * (1 - age / 1.4) ** 1.4, 0.0)''')
rep('''    look.compositor(dict(kuwahara=3, bloom=0.55, bloom_threshold=0.8, streak=0.12, streak_threshold=1.05, lift=(0.98, 0.99, 1.05),''',
    '''    look.compositor(dict(kuwahara=3, bloom=0.3, bloom_threshold=0.95, streak=0.05, streak_threshold=1.1, lift=(0.99, 0.99, 1.02),''')
open(p, "w").write(s)
print("s08 patched")
