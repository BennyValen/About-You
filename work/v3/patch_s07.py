p = "blender/scenes/s07.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''from kit import core, look, geo, thread, human''', '''from kit import core, look, geo, human, plants, rope_io''')
rep('''PAINT_BOIL = 2.4''', '''POST = dict(light_deg=24.0, flow_deg=70.0, stroke_px=12.0, boil_mean=1.6, thread_shadow_px=0.0, thread_shadow_alpha=0.0, repaint=0.55)
TRACKS = [[(-30, -40), (-14, -20), (-6, 0), (-12, 18), (-2, 36), (8, 52), (4, 75), (14, 100), (6, 130)],
          [(30, -30), (18, -6), (22, 14), (10, 30), (16, 50), (26, 70), (18, 95), (24, 125)]]''')

# ---- eroded heightfield terrain (replaces the analytic noise terrain)
i = s.index("def terrain(X, Y):")
j = s.index("def terrain_material():")
s = s[:i] + '''def terrain_base(X, Y):
    """ridged canyon relief + plateaus (metres)"""
    r = 1.0 - np.abs(geo.fbm2(X * 0.018 + 3, Y * 0.018, 4, 13) * 2.0)
    h = 13.0 * r ** 2.2 + 6.0 * geo.fbm2(X * 0.03, Y * 0.03, 4, 71) + 2.0 * geo.fbm2(X * 0.12, Y * 0.12, 3, 5)
    plateau = np.clip((h - 8.0) * 0.6, 0, 1)
    return h - plateau * (h - 8.0) * 0.55


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


def terrain_material():''' + s[j:]

# material: use baked attributes; strata bands; scree; tracks; haze; CC0 rock
rep('''        # rock: blue-grey with darker valleys
        hval = _n(nt, "ShaderNodeMapRange", (-1500, 300), clamp=True)
        _l(nt, sx.outputs[2], hval.inputs["Value"])
        hval.inputs["From Min"].default_value, hval.inputs["From Max"].default_value = -4.0, 13.0''', '''        # rock: blue-grey with darker valleys
        hval = _n(nt, "ShaderNodeMapRange", (-1500, 300), clamp=True)
        _l(nt, sx.outputs[2], hval.inputs["Value"])
        hval.inputs["From Min"].default_value, hval.inputs["From Max"].default_value = -2.0, 13.0''')
rep('''        rockc = _mixrgb(nt, "MULTIPLY", 1.0, rock.outputs[0], rkc.outputs[0], (-900, 450))''', '''        rockc = _mixrgb(nt, "MULTIPLY", 1.0, rock.outputs[0], rkc.outputs[0], (-900, 450))
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
        rockc = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", gm.outputs["Result"], 0.6, (-1000, 1250)), rockc, core.hexc("#3b4258"), (-750, 750))''')
rep('''        # winding double tracks: zero set of a smooth field, drawn as two thin pale lines
        tn = _n(nt, "ShaderNodeTexNoise", (-1100, -900))
        _l(nt, geo_n.outputs["Position"], tn.inputs["Vector"])
        tn.inputs["Scale"].default_value = 0.012
        tn.inputs["Detail"].default_value = 1.5
        dd = _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", tn.outputs["Fac"], 0.5, (-900, -900)), None, (-780, -900))
        l1 = _n(nt, "ShaderNodeMapRange", (-650, -900), clamp=True)
        _l(nt, dd, l1.inputs["Value"])
        l1.inputs["From Min"].default_value, l1.inputs["From Max"].default_value = 0.0016, 0.0008
        l2 = _n(nt, "ShaderNodeMapRange", (-650, -1050), clamp=True)
        _l(nt, _math(nt, "ABSOLUTE", _math(nt, "SUBTRACT", dd, 0.0032, (-780, -1050)), None, (-700, -1050)), l2.inputs["Value"])
        l2.inputs["From Min"].default_value, l2.inputs["From Max"].default_value = 0.0008, 0.0003
        trk = _math(nt, "MAXIMUM", l1.outputs["Result"], l2.outputs["Result"], (-500, -950))
        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", trk, 0.85, (-400, -950)), c, core.hexc("#c5c9cf"), (-300, 50))
        return c''', '''        # dirt tracks from the baked signed distance across each track: a pale bed with two darker tyre ruts
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
        return c''')
rep('''    return look.cel("terrain", core.hexc("#8c909c"), shadow=(0.5, 0.54, 0.72, 1), high=(1.12, 1.1, 1.05, 1), t1=0.7, t2=0.95,
                    paint=0.32, paint_scale=1.6, base_node=base, rough=0.9)''', '''    return look.cel("terrain", core.hexc("#8c909c"), shadow=(0.48, 0.52, 0.72, 1), high=(1.12, 1.1, 1.05, 1), t1=0.55, t2=0.95,
                    paint=0.05, paint_scale=1.6, base_node=base, rough=0.9, soft=0.18, ao=0.6, ao_dist=2.0)''')
# note: the lichen mask used the (removed) analytic terrain heights -> keep using z
rep('''        high.inputs["From Min"].default_value, high.inputs["From Max"].default_value = -1.0, 2.0''',
    '''        high.inputs["From Min"].default_value, high.inputs["From Max"].default_value = 5.0, 8.0''')
rep('''        rm.inputs["From Min"].default_value, rm.inputs["From Max"].default_value = 0.62, 0.68''',
    '''        rm.inputs["From Min"].default_value, rm.inputs["From Max"].default_value = 0.64, 0.7''')

rep('''    sc = core.reset(opt.scale, getattr(opt, "samples", 8))''', '''    sc = core.reset(opt.scale, getattr(opt, "samples", 2))''')
rep('''SUN_DIR = (0.86, 0.38, 3.6)        # high sun from the right: glider shadow lands lower-left within frame''',
    '''SUN_DIR = (0.86, 0.38, 1.1)        # sun from the right, ~45 deg: ridges throw long soft shadows; glider shadow lower-left''')
rep('''    step = 0.3
    nx, ny = int((x1 - x0) / step), int((y1 - y0) / step)
    ground = geo.grid("terrain", x0, y0, x1, y1, nx, ny, terrain, env, terrain_material())''', '''    step = 0.2
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
''')
rep('''    def harness_pt(t):
        p, swing, yaw = glider_world(t)
        return np.array([p[0] + math.sin(swing) * 6.0, p[1] - 0.4, GLIDER_Z - 6.5])
    def wind(x, y, z, t):
        return 0.4 * np.sin(y * 0.05 + t * 0.02), np.full_like(x, -7.5), np.zeros_like(x)
    cord = thread.Cord(n_seg=200, length=34.0, mode="air", ground=lambda x, y: terrain(x, y) + 0.3, air_drag=6.0, wind=wind,
                       substeps=8, iters=24, bend=0.15, friction=0.7)
    sim = cord.run(list(range(start, end)), harness_pt, (0.0, -1.0), warm=120)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.2)''', '''    mot = rope_io.C.owner_motion(SCENE)
    def harness_pt(t):
        p, swing, yaw = glider_world(t)
        return np.array([p[0] + math.sin(swing) * 6.0 + mot(t)[0], p[1] - 0.4, GLIDER_Z - 6.5])
    rope = rope_io.Owner("A", SCENE, rig, harness_pt, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,
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
    lines_ob = geo.mesh_from_arrays("susp_lines", np.array(lv_), lf_, ink, False, lines_m)''')
rep('''    look.compositor(dict(kuwahara=5, bloom=0.4, bloom_threshold=0.95, streak=0.1, lift=(0.985, 0.995, 1.03), gain=(1.04, 1.01, 0.97),
                         vignette=0.26, grain=0.03, ink=0.5, ink_normal=(0.45, 1.3)), res_scale=opt.scale)''', '''    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.985, 0.995, 1.03), gain=(1.04, 1.01, 0.97),
                         vignette=0.24, ink=0.35, ink_normal=(0.45, 1.3)), res_scale=opt.scale)''')
rep('''        canopy.matrix_world = Matrix.Translation((p[0], p[1], GLIDER_Z)) @ Euler((0, swing, yaw)).to_matrix().to_4x4() @ Matrix.Diagonal((breathe, 1, 1 / breathe, 1))''',
    '''        Mc = Matrix.Translation((p[0] + mot(d)[0], p[1], GLIDER_Z)) @ Euler((0, swing, yaw)).to_matrix().to_4x4()
        canopy.matrix_world = Mc @ Matrix.Diagonal((breathe, 1, 1 / breathe, 1))
        lines_ob.matrix_world = Mc''')
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
# canopy / pilot / hawks: hero + soft
for nm in ('"canopy"', '"canopy_b"', '"canopy_le"', '"canopy_under"', '"hawk"', '"hawk_d"'):
    i = s.index(f"look.cel({nm},")
    j = s.index(")", s.index("paint=", i))
    s = s[:j] + ", soft=0.22, hero=True" + s[j:]
open(p, "w").write(s)
print("s07 patched")
open(p, "w").write(s)
print("s07 patched (part 1)")
