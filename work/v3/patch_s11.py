p = "blender/scenes/s11.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''"""Scene 11 (frames 3316-3647): a V of white cranes flies over peach-lavender cumulus; the camera keeps a
constant 4.97 px/frame right up to the cut. Bird shadows fall on the cloud tops; gaps (widening along the
route) open onto the deep blue world far below. The red cord streams behind the lead crane."""''',
    '''"""Scene 11 (frames 3316-3647): a loose V of white cranes flies over peach-lavender cumulus; the camera keeps a
constant 4.97 px/frame right up to the cut at 3648.

v3: the cumulus is built from instanced billowy lobes (big domes, medium lobes on top, small cauliflower lobes at the
edges) with soft lavender undersides, bright peach rims on the lit side, ambient occlusion in the crevices and slow
churn at the edges, in three layers at different depths (nearer layers scroll faster), with wisps between them and
cloud-on-cloud shadows. Deep blue gaps open onto the rippled sea far below. Ten cranes with dark wingtips flap and
glide, banking with boid-like spacing, casting soft shadows on the clouds; the red thread streams from the lead."""''')
rep('''from kit import core, look, geo, thread, creatures''', '''from kit import core, look, geo, creatures, rope_io''')
rep('''PAINT_BOIL = 0.45''', '''POST = dict(light_deg=40.0, flow_deg=80.0, stroke_px=12.0, boil_mean=2.0, thread_shadow_px=0.0, thread_shadow_alpha=0.0, repaint=0.55)
LAYERS = [(-3.0, 0.38, 31), (-14.0, 0.52, 37), (-30.0, 0.62, 41)]      # (z, coverage, seed): near -> far''')
rep('''V = [(540, 1190), (370, 1320), (690, 1350), (230, 1450), (840, 1484), (110, 1616), (980, 1650), (700, 1800)]''',
    '''V = [(540, 1190), (370, 1320), (690, 1350), (230, 1450), (840, 1484), (110, 1616), (980, 1650), (700, 1800), (430, 1760), (300, 1900)]''')
rep('''    sc = core.reset(opt.scale, getattr(opt, "samples", 8))''', '''    sc = core.reset(opt.scale, getattr(opt, "samples", 2))''')
i = s.index("    step = 0.09\n")
j = s.index("    # cranes\n")
s = s[:i] + '''    # ---------------------------------------------------------------- cumulus lobes, three layers
    def cloud_base(nt):
        it = _n(nt, "ShaderNodeAttribute", (-900, 200), attribute_type="INSTANCER", attribute_name="tint")
        c = _mixrgb(nt, "MIX", it.outputs["Fac"], core.hexc("#f6e4d6"), core.hexc("#e8c9d3"), (-600, 200))
        nz = _n(nt, "ShaderNodeTexNoise", (-900, 0))
        g = _n(nt, "ShaderNodeNewGeometry", (-1100, 0))
        _l(nt, g.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 1.2
        nz.inputs["Detail"].default_value = 4
        v = _n(nt, "ShaderNodeMapRange", (-700, 0), clamp=True)
        _l(nt, nz.outputs["Fac"], v.inputs["Value"])
        v.inputs["To Min"].default_value, v.inputs["To Max"].default_value = 0.92, 1.06
        return look.mul_color(nt, c, v.outputs["Result"], (-400, 100))
    cmat = look.cel("cloud", core.hexc("#ead4cc"), shadow=(0.52, 0.44, 0.84, 1), high=(1.08, 1.03, 0.95, 1), t1=0.5, t2=0.93,
                    paint=0.04, base_node=cloud_base, rough=0.9, soft=0.24, ao=0.75, ao_dist=2.5, rim=0.35)
    lp = geo.proto_collection("P_lobe")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
    for vtx in bm.verts:
        vtx.co *= 1.0 + 0.06 * math.sin(vtx.co.x * 7 + vtx.co.y * 5) * math.cos(vtx.co.z * 6)
    geo.bm_to_object(bm, "lobe", cmat, lp, smooth=True)
    lobe_objs = []
    for li, (lz, cov, seed) in enumerate(LAYERS):
        lx0, ly0, lx1, ly1 = rig.path_rect(lz, 1.3)
        def cover(x, y, seed=seed, cov=cov):
            return geo.fbm2(x * 0.06 + seed, y * 0.06, 4, seed) + (cov - 0.5) * 0.9
        pts, rad, zz, tint = [], [], [], []
        for (r0, r1, spacing, lift, lvl) in ((2.6, 4.6, 3.0, 0.0, 0), (1.1, 2.1, 1.6, 1.0, 1), (0.45, 0.95, 0.9, 1.8, 2)):
            P = geo.poisson(rng, 40000, lx0, ly0, lx1, ly1, spacing, accept=lambda x, y: cover(x, y) > (0.0 if lvl < 2 else -0.04))
            if not len(P):
                continue
            cvals = np.array([cover(x, y) for x, y in P])
            if lvl == 2:
                keep = cvals < 0.22                     # small cauliflower lobes crowd the edges
                P, cvals = P[keep], cvals[keep]
            r = rng.uniform(r0, r1, len(P)) * (0.7 + 0.6 * np.clip(cvals * 2.5, 0, 1))
            dome = 2.2 * np.clip(cvals * 2.0, 0, 1) ** 0.6
            pts.append(P)
            rad.append(r)
            zz.append(lz + dome + lift * np.clip(cvals * 3, 0.3, 1) - r * 0.35)
            tint.append(rng.random(len(P)))
        P = np.concatenate(pts)
        R = np.concatenate(rad)
        Z = np.concatenate(zz)
        T = np.concatenate(tint)
        nl = len(P)
        scl = np.c_[R, R * rng.uniform(0.85, 1.15, nl), R * 0.75]
        ob = geo.instances(f"clouds{li}", lp, np.c_[P, Z], rot=np.c_[np.zeros(nl), np.zeros(nl), rng.uniform(0, 6.28, nl)], scl=scl, tint=T, coll=env)
        lobe_objs.append((ob, np.c_[P, Z], scl, rng.uniform(0, 6.28, nl), R < 1.0))
    # wisps between the layers
    def wisp_mat(name, seed, dens):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = _n(nt, "ShaderNodeOutputMaterial", (500, 0))
        g = _n(nt, "ShaderNodeNewGeometry", (-900, 0))
        mp = _n(nt, "ShaderNodeMapping", (-700, 0))
        _l(nt, g.outputs["Position"], mp.inputs[0])
        mp.inputs["Scale"].default_value = (0.05, 0.02, 0.0)
        mp.inputs["Rotation"].default_value = (0, 0, 0.4 + seed)
        drv = mp.inputs["Location"].driver_add("default_value", 0).driver
        drv.type = "SCRIPTED"
        drv.expression = f"floor(frame / 2) * 2 * {0.002 + seed * 0.001:.5f}"
        nz = _n(nt, "ShaderNodeTexNoise", (-500, 0), noise_dimensions="4D")
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["W"].default_value = seed * 10
        nz.inputs["Detail"].default_value = 6
        mr = _n(nt, "ShaderNodeMapRange", (-300, 0), clamp=True)
        _l(nt, nz.outputs["Fac"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.6, 0.8
        a = _math(nt, "MULTIPLY", mr.outputs["Result"], dens, (-150, 0))
        em = _n(nt, "ShaderNodeEmission", (0, 50))
        em.inputs[0].default_value = core.hexc("#f3e6ec")
        em.inputs[1].default_value = 0.95
        tr = _n(nt, "ShaderNodeBsdfTransparent", (0, -100))
        mx = _n(nt, "ShaderNodeMixShader", (250, 0))
        _l(nt, a, mx.inputs[0])
        _l(nt, tr.outputs[0], mx.inputs[1])
        _l(nt, em.outputs[0], mx.inputs[2])
        _l(nt, mx.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
        return m
    for wi, (wz, dens) in enumerate(((-8.0, 0.45), (-21.0, 0.4))):
        wx0, wy0, wx1, wy1 = rig.path_rect(wz, 1.4)
        w = geo.grid(f"wisp{wi}", wx0, wy0, wx1, wy1, 4, 4, None, env, wisp_mat(f"wisp{wi}", wi * 0.37, dens))
        w.location.z = wz
        w.visible_shadow = False
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
        return _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#26326a"), core.hexc("#4f5c98"), (-300, 200))
    bx0, by0, bx1, by1 = rig.path_rect(-80.0, 1.4)
    below = geo.grid("below", bx0, by0, bx1, by1, 4, 4, None, env,
                     look.cel("below", core.hexc("#3a4576"), paint=0.05, base_node=below_base, soft=0.2, ao=0.0))
    below.location.z = -80.0
    below.visible_shadow = False

''' + s[j:]
rep('''    mw = look.cel("crane_white", core.hexc("#f6f4f1"), shadow=(0.72, 0.7, 0.86, 1), high=(1.04, 1.04, 1.04, 1), paint=0.05, paint_scale=8)
    mb = look.cel("crane_black", core.hexc("#2a2730"), paint=0.0)
    ml = look.cel("crane_leg", core.hexc("#3b3640"), paint=0.0)''', '''    mw = look.cel("crane_white", core.hexc("#f6f4f1"), shadow=(0.72, 0.7, 0.86, 1), high=(1.04, 1.04, 1.04, 1), paint=0.03, soft=0.22, rim=0.3,
                  hero=True)
    mb = look.cel("crane_black", core.hexc("#2a2730"), paint=0.0, soft=0.2, hero=True)
    ml = look.cel("crane_leg", core.hexc("#3b3640"), paint=0.0, hero=True)''')
rep('''    red = look.cel("thread", core.hexc("#d22a2b"), shadow=(0.78, 0.7, 0.8, 1), high=(1.15, 1.1, 1.1, 1), t1=0.2, t2=0.99,
                   paint=0.0, glow=0.35, rough=0.5)
    def lead_attach(t):''', '''    def lead_attach(t):''')
rep('''    def wind(x, y, z, t):
        return 0.5 * np.sin(y * 0.5 + t * 0.04), np.full_like(x, -14.0), np.zeros_like(x)
    cord = thread.Cord(n_seg=200, length=11.0, mode="air", ground=lambda x, y: np.full_like(x, -30.0), air_drag=3.0, wind=wind,
                       substeps=14, iters=60, bend=0.15)
    sim = cord.run(list(range(start, end)), lead_attach, (0.0, -1.0), warm=96)
    curve = thread.CordCurve("thread_A", 201, red, rig, px=3.8)''', '''    rope = rope_io.Owner("A", SCENE, rig, lead_attach, list(range(start, end, 2)), trail=(0.0, -1.0), warm=40,
                         ground_fn=lambda x, y: np.full_like(np.asarray(x, float), -1e4), surface_fn=lambda x, y: np.full_like(np.asarray(x, float), -3.0))''')
rep('''    look.compositor(dict(kuwahara=11, bloom=0.45, bloom_threshold=0.92, streak=0.12, lift=(0.99, 0.98, 1.03), gain=(1.03, 1.0, 0.98),
                         vignette=0.24, grain=0.03, ink=0.45, ink_normal=(0.4, 1.2)), res_scale=opt.scale)''', '''    look.compositor(dict(kuwahara=3, bloom=0.4, bloom_threshold=0.92, streak=0.06, lift=(0.99, 0.98, 1.03), gain=(1.03, 1.0, 0.98),
                         vignette=0.22, ink=0.35, ink_normal=(0.4, 1.2)), res_scale=opt.scale)''')
rep('''            b.body.rotation_euler = (0.04, 0.05 * math.sin(d * 0.04 + i), hd)
            b.pose(d, phase=i * 0.9)
        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})
        look.boil(st, d // 2)
        look.grain_seed(d // 2)
        look.set_drawing(d // 2, PAINT_BOIL)''', '''            # bank into turns (roll from the turn rate)
            v0 = track[d][i] - track[d - 2][i] if d - 2 in track else v
            turn = math.atan2(v0[0] * v[1] - v0[1] * v[0], v0 @ v + 1e-9)
            b.body.rotation_euler = (0.04, max(-0.5, min(0.5, -turn * 25.0)) + 0.04 * math.sin(d * 0.04 + i), hd)
            # flap and glide: each bird alternates flapping bouts and glides (wings held, slightly raised)
            gliding = math.sin(d * 0.021 + i * 1.3) > 0.45
            b.pose(6.5 if gliding else d, phase=0.0 if gliding else i * 0.9)
        # slow churn of the small edge lobes
        for ob, P0, S0, ph, small in lobe_objs:
            S = S0.copy()
            k = 1.0 + 0.05 * np.sin(d * 0.07 + ph) * small
            S *= k[:, None]
            geo.update_points(ob, P0, scl=S)
        look.boil(st, d // 2)
        look.set_drawing(d // 2, 0.0)''')
rep('''    r.update = update
    r.finish = lambda out: json.dump(log, open(os.path.join(out, "thread_log.json"), "w"))''', '''    r.update = update
    r.rig = rig
    r.finish = lambda out: rope_io.export(out, [rope])''')
rep('''import bpy
from mathutils''', '''import bpy, bmesh
from mathutils''')
open(p, "w").write(s)
print("s11 patched")
