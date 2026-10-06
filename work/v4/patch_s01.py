p = "blender/scenes/s01.py"
s = open(p).read()


def rep(a, b, cnt=1):
    global s
    assert s.count(a) == cnt, (s.count(a), a[:90])
    s = s.replace(a, b)


rep('''CAR_LEN, GAP = 4.4, 0.32''', '''CAR_LEN, GAP = 3.0, 0.3            # v4: seven short carriages (~690 px train, as in the source)''')
rep('''POST = dict(light_deg=140.0, flow_deg=90.0, stroke_px=12.0, boil_mean=1.8, thread_shadow_px=1.4, thread_glow=0.25, repaint=0.5, grain=1.2)''',
    '''POST = dict(light_deg=140.0, flow_deg=90.0, stroke_px=12.0, boil_mean=1.8, thread_shadow_px=1.4, thread_glow=0.25, repaint=0.5, grain=1.2)
WIN_X = 0.95                         # window strips (m from the track axis)
CORRIDOR_PX = 100.0                  # no crown within 100 px of the window strips
CROWN_R = 3.95 * 1.15                # crown radius of a scale-1 spruce (longest blade), m''')
rep('''FRONT_SCREEN_Y = 990''', '''FRONT_SCREEN_Y = 990
PLUME_SX, PLUME_LEN = 2.6, 700.0 / 30.0        # plume plane half-width and length (m)''')
# trees: slate needles, frost speckles on the upward tips, moon rim on the crowns
rep('''        needles = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#1d2440"), core.hexc("#2b3456"), (-500, 0))
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", snow, 0.7, (-350, 300)), needles, core.hexc("#a9b3dc"), (-300, 100))
    return look.cel("spruce", core.hexc("#262e4c"), shadow=(0.55, 0.55, 0.75, 1), high=(1.25, 1.25, 1.3, 1), t1=0.35, t2=0.9,
                    paint=0.04, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0, soft=0.18, ao=0.55, ao_dist=1.5)''',
    '''        needles = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#1E253E"), core.hexc("#3B4160"), (-500, 0))
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", snow, 0.7, (-350, 300)), needles, core.hexc("#8F96BA"), (-300, 100))
        # frost speckles: small bright flecks along the blades (fine noise, thresholded), more towards the tips
        fz = _n(nt, "ShaderNodeTexNoise", (-800, -250))
        _l(nt, geo_n.outputs["Position"], fz.inputs["Vector"])
        fz.inputs["Scale"].default_value = 16.0
        fz.inputs["Detail"].default_value = 2
        fr = _n(nt, "ShaderNodeMapRange", (-600, -250), clamp=True)
        _l(nt, fz.outputs["Fac"], fr.inputs["Value"])
        fr.inputs["From Min"].default_value, fr.inputs["From Max"].default_value = 0.6, 0.66
        fk = _math(nt, "MULTIPLY", fr.outputs["Result"], _math(nt, "ADD", at.outputs["Fac"], 0.25, (-500, -350)), (-400, -300), clamp=True)
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", fk, 0.8, (-300, -300)), c, core.hexc("#C4C9E0"), (-200, 0))
    return look.cel("spruce", core.hexc("#2B324F"), shadow=(0.6, 0.62, 0.78, 1), high=(1.3, 1.3, 1.36, 1), t1=0.35, t2=0.9,
                    paint=0.04, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0, soft=0.35, ao=0.45, ao_dist=1.5,
                    rim=0.45)''')
rep('''    core.world_ambient(core.hexc("#c9cff0"), 0.15)
    core.sun(MOON_DIR, core.sun_irradiance_for(0.5, MOON_DIR, 0.15), core.hexc("#d4daf6"), angle_deg=1.5)''',
    '''    core.world_ambient(core.hexc("#c4c8dc"), 0.28)
    core.sun(MOON_DIR, core.sun_irradiance_for(0.72, MOON_DIR, 0.28), core.hexc("#d8dcf0"), angle_deg=1.5)       # moon, upper left''')
# the old headlight beam slab becomes the steam plume: a streaky translucent ribbon along the track ahead of the engine,
# 35 px wide at the chimney, widening to 140 px over 700 px; core opacity <= 0.45, edges 0.1-0.2, rails show through
rep('''    lat = _math(bnt, "ABSOLUTE", _math(bnt, "SUBTRACT", bsx.outputs[0], 0.5, (-550, 100)), None, (-450, 100))
    halfw = _math(bnt, "ADD", _math(bnt, "MULTIPLY", bsx.outputs[1], 0.42, (-550, 200)), 0.06, (-450, 200))
    side = _math(bnt, "SUBTRACT", 1.0, _math(bnt, "DIVIDE", lat, halfw, (-350, 150)), (-250, 150), clamp=True)
    along = _math(bnt, "POWER", _math(bnt, "SUBTRACT", 1.0, bsx.outputs[1], (-350, 0)), 1.8, (-250, 0))
    bnz = _n(bnt, "ShaderNodeTexNoise", (-550, -200), noise_dimensions="4D")
    _l(bnt, btc.outputs["Generated"], bnz.inputs["Vector"])
    bnz.inputs["Scale"].default_value = 5.0
    bdr = bnz.inputs["W"].driver_add("default_value").driver
    bdr.type = "SCRIPTED"
    bdr.expression = "floor(frame / 2) * 0.04"
    ba = _math(bnt, "MULTIPLY", _math(bnt, "MULTIPLY", _math(bnt, "POWER", side, 0.8, (-150, 150)), along, (0, 100)),
               _math(bnt, "ADD", _math(bnt, "MULTIPLY", bnz.outputs["Fac"], 0.6, (-350, -200)), 0.55, (-200, -200)), (100, 50), clamp=True)
    bem = _n(bnt, "ShaderNodeEmission", (300, 100))
    bem.inputs[0].default_value = (0.86, 0.9, 1.0, 1)
    bem.inputs[1].default_value = 1.15''',
    '''    # plane: x in [-1, 1] * PLUME_SX m, y in [0, 1] * PLUME_LEN m; UV x 0..1 across, y 0..1 along (from the chimney)
    lat = _math(bnt, "ABSOLUTE", _math(bnt, "SUBTRACT", bsx.outputs[0], 0.5, (-550, 100)), None, (-450, 100))
    halfw = _math(bnt, "ADD", _math(bnt, "MULTIPLY", bsx.outputs[1], 52.5 / PPM / (2 * PLUME_SX), (-550, 200)),
                  17.5 / PPM / (2 * PLUME_SX), (-450, 200))
    q = _math(bnt, "DIVIDE", lat, halfw, (-350, 150))                     # 0 on the axis, 1 at the plume edge
    prof = _math(bnt, "ADD", 0.15, _math(bnt, "MULTIPLY", 0.3, _math(bnt, "SUBTRACT", 1.0, _math(bnt, "POWER", q, 2.0, (-250, 250)),
                                                                     (-150, 250)), (-50, 250)), (50, 250))
    edge = _math(bnt, "SUBTRACT", 1.0, _math(bnt, "MULTIPLY", _math(bnt, "SUBTRACT", q, 0.85, (-250, 120)), 1.0 / 0.25, (-150, 120)),
                 (-50, 120), clamp=True)                                   # soft fade just past the edge
    fin = _math(bnt, "MULTIPLY", _math(bnt, "MINIMUM", _math(bnt, "MULTIPLY", bsx.outputs[1], 20.0, (-350, 0)), 1.0, (-250, 0)),
                _math(bnt, "MINIMUM", _math(bnt, "MULTIPLY", _math(bnt, "SUBTRACT", 1.0, bsx.outputs[1], (-450, -50)), 5.0, (-350, -50)),
                      1.0, (-250, -50)), (-150, 0))
    # streaks along the track, drifting backwards (the train runs into still air)
    bgeo = _n(bnt, "ShaderNodeNewGeometry", (-900, -250))
    bmp = _n(bnt, "ShaderNodeMapping", (-700, -250))
    _l(bnt, bgeo.outputs["Position"], bmp.inputs[0])
    bmp.inputs["Scale"].default_value = (2.6, 0.12, 1.0)
    bnz = _n(bnt, "ShaderNodeTexNoise", (-550, -200), noise_dimensions="4D")
    _l(bnt, bmp.outputs[0], bnz.inputs["Vector"])
    bnz.inputs["Scale"].default_value = 2.0
    bnz.inputs["Detail"].default_value = 6
    bdr = bnz.inputs["W"].driver_add("default_value").driver
    bdr.type = "SCRIPTED"
    bdr.expression = "floor(frame / 2) * 0.03"
    streak = _math(bnt, "ADD", 0.55, _math(bnt, "MULTIPLY", bnz.outputs["Fac"], 0.75, (-350, -200)), (-200, -200))
    ba = _math(bnt, "MINIMUM", _math(bnt, "MULTIPLY", _math(bnt, "MULTIPLY", _math(bnt, "MULTIPLY", prof, edge, (150, 200)), fin, (200, 100)),
                                     streak, (250, 50)), 0.45, (300, 0), clamp=True)
    bem = _n(bnt, "ShaderNodeEmission", (300, 100))
    bem.inputs[0].default_value = core.hexc("#C9CFE6")
    bem.inputs[1].default_value = 0.62''')
rep('''    _l(bnt, _math(bnt, "MULTIPLY", ba, 0.75, (250, -250)), bmx.inputs[0])''', '''    _l(bnt, ba, bmx.inputs[0])''')
# snow: slate blue, moonlight pools come from the sun through the thinner canopy
rep('''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#3d4882"), core.hexc("#56629f"), (-600, 200))''',
    '''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#495175"), core.hexc("#656C90"), (-600, 200))''')
rep('''        ice = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#3a4170"), core.hexc("#545d96"), (-600, -100))''',
    '''        ice = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#3B4160"), core.hexc("#565E84"), (-600, -100))''')
rep('''             look.cel("snow", core.hexc("#4b579c"), shadow=(0.5, 0.52, 0.75, 1), high=(1.15, 1.15, 1.2, 1), t1=0.36, t2=0.92,''',
    '''             look.cel("snow", core.hexc("#565E84"), shadow=(0.55, 0.57, 0.76, 1), high=(1.2, 1.2, 1.24, 1), t1=0.36, t2=0.92,''')
# forest: 30 % sparser, two heights, crowns kept CORRIDOR_PX clear of the window strips (scene-graph gate)
rep('''    pts = geo.poisson(rng, 6000, x0, y0, x1, y1, 2.7, accept=lambda x, y: abs(x) > 2.9 and pond_sdf(x, y) > 1.5)
    n = len(pts)
    # two canopy layers: tall spruces and a lower understorey between them
    s = np.where(rng.random(n) < 0.6, rng.uniform(0.75, 1.0, n), rng.uniform(0.42, 0.6, n))''',
    '''    clear_m = WIN_X + CORRIDOR_PX / PPM            # crowns must stay outside |x| >= clear_m
    pts = geo.poisson(rng, 6000, x0, y0, x1, y1, 2.7 / math.sqrt(0.7),
                      accept=lambda x, y: abs(x) - 0.42 * CROWN_R >= clear_m and pond_sdf(x, y) > 1.5)
    n = len(pts)
    # two canopy layers: tall spruces and a lower understorey between them; near the corridor only trees small
    # enough to keep the clearance grow (the edge of a cut line)
    s = np.where(rng.random(n) < 0.6, rng.uniform(0.75, 1.0, n), rng.uniform(0.42, 0.6, n))
    s = np.minimum(s, (np.abs(pts[:, 0]) - clear_m) / CROWN_R)
    CORRIDOR_LOG.update(trees=int(n), min_clear_px=float(((np.abs(pts[:, 0]) - s * CROWN_R) - WIN_X).min() * PPM),
                        density_per_100m2=float(n / ((x1 - x0) * (y1 - y0)) * 100))''')
rep('''    rng = np.random.default_rng(101)''', '''    rng = np.random.default_rng(101)
    CORRIDOR_LOG = {}''')
# train: warm windows never clipped, light falls off smoothly (no tree shadows -> no spikes)
rep('''                 window=look.emissive("window", (1.0, 0.58, 0.2, 1), 1.6, hero=True),''',
    '''                 window=look.emissive("window", core.hexc("#E8A24A"), 0.85, hero=True),''')
rep('''            li.size, li.size_y = CAR_LEN * 0.9, 0.6
            li.energy = 320.0
            li.color = (1.0, 0.52, 0.16)''', '''            li.size, li.size_y = CAR_LEN * 1.05, 2.4
            li.energy = 70.0
            li.color = (0.91, 0.64, 0.33)
            li.use_shadow = False''')
rep('''    head.energy = 9000.0''', '''    head.energy = 2600.0''')
# no puffs drifting over the train (the plume is the ribbon above)
rep('''    NP = 140''', '''    NP = 1''')
rep('''        alive = (age >= 0) & (age < 5.0)''', '''        alive = (age >= 0) & (age < 5.0) & False''')
rep('''        beam.location = (0.0, fy + 0.2, 1.6)
        beam.scale = (7.0, 30.0, 1.0)''', '''        beam.location = (0.0, fy + 0.1, 2.6)
        beam.scale = (PLUME_SX, PLUME_LEN, 1.0)''')
rep('''    look.compositor(dict(kuwahara=3, bloom=0.7, bloom_threshold=0.85, bloom_size=0.7, streak=0.16, streak_threshold=1.1,''',
    '''    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=1.0, bloom_size=0.7, streak=0.0, streak_threshold=1.5,''')
rep('''    r.finish = lambda out: rope_io.export(out, [rope])''', '''    def finish(out):
        rope_io.export(out, [rope])
        CORRIDOR_LOG.update(window_x_px=WIN_X * PPM, required_px=CORRIDOR_PX, pass_=CORRIDOR_LOG["min_clear_px"] >= CORRIDOR_PX)
        json.dump(CORRIDOR_LOG, open(os.path.join(out, "corridor.json"), "w"), indent=1)
    r.finish = finish''')
open(p, "w").write(s)
print("s01 patched")
