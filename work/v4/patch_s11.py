p = "blender/scenes/s11.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''SUN_DIR = (0.5, 0.42, 0.76)''', '''SUN_DIR = (-0.55, 0.45, 0.62)       # v4: light from the upper left''')
rep('''POST = dict(light_deg=40.0, flow_deg=80.0, stroke_px=12.0, boil_mean=2.0, thread_shadow_px=0.0, thread_shadow_alpha=0.0, repaint=0.55)''',
    '''POST = dict(light_deg=140.0, flow_deg=80.0, stroke_px=24.0, fine_px=9.0, elong=3.0, boil_mean=2.0, thread_shadow_px=0.0,
            thread_shadow_alpha=0.0, repaint=0.62)       # long swirling strokes along the cloud contours''')
i = s.index("    # ---------------------------------------------------------------- cumulus lobes, three layers")
j = s.index("    # the sea far below, seen through the gaps")
s = s[:i] + '''    # ---------------------------------------------------------------- v4 clouds: a density field, no circles
    # domain-warped fractal noise (7 octaves, billowy + ridged mix, warped), smooth-thresholded into big irregular masses
    # with a fractal edge (bumps from ~4 m = 400 px down to ~0.2 m = 20 px); the cloud top is a height field derived from
    # the smoothed density, lit from the upper left (real shading, AO in the hollows). Main layer on the camera's
    # reference plane (z = 0) so it scrolls at the camera speed; a far, bluer layer below; near wisps above.
    def density(X, Y, seed, f0):
        wx = geo.fbm2(X * f0 * 0.6 + seed, Y * f0 * 0.6, 4, seed + 1)
        wy = geo.fbm2(X * f0 * 0.6 - seed, Y * f0 * 0.6 + 3.1, 4, seed + 2)
        Xw, Yw = X + 5.0 * wx, Y + 5.0 * wy
        b = geo.fbm2(Xw * f0, Yw * f0, 7, seed + 3)
        billow = 1.0 - np.abs(geo.fbm2(Xw * f0 * 2.1, Yw * f0 * 2.1, 6, seed + 4))
        ridge = 1.0 - np.abs(geo.fbm2(Xw * f0 * 4.3, Yw * f0 * 4.3, 5, seed + 5))
        return b + 0.35 * billow + 0.15 * ridge

    def cloud_layer(name, z, seed, f0, cover, hmax, step, mat):
        lx0, ly0, lx1, ly1 = rig.path_rect(z, 1.3)
        nx_, ny_ = int((lx1 - lx0) / step) + 1, int((ly1 - ly0) / step) + 1
        X, Y = np.meshgrid(lx0 + np.arange(nx_) * step, ly0 + np.arange(ny_) * step)
        D = density(X, Y, seed, f0)
        thr = np.quantile(D, 1.0 - cover)
        w = np.std(D) * 0.9
        u = np.clip((D - thr) / w, -0.4, 1.0)
        H = hmax * np.sign(u) * np.abs(u) ** 0.6
        # small billows on the top for the painted cauliflower relief (still a field, no repeated lobes)
        H = H + 0.12 * hmax * geo.fbm2(X * f0 * 6, Y * f0 * 6, 3, seed + 9) * np.clip(u * 3, 0, 1)
        Z = z + H
        keep = D > thr - 0.35 * w
        ids = -np.ones(X.shape, np.int64)
        ids[keep] = np.arange(keep.sum())
        V = np.c_[X[keep], Y[keep], Z[keep]]
        a, b_, c, d_ = ids[:-1, :-1], ids[:-1, 1:], ids[1:, 1:], ids[1:, :-1]
        ok = (a >= 0) & (b_ >= 0) & (c >= 0) & (d_ >= 0)
        F = np.c_[a[ok], b_[ok], c[ok], d_[ok]]
        ob = geo.mesh_from_arrays(name, V, F, env, True, mat)
        return ob, float(keep.mean())

    def cloud_mat(name, lit, mid, shadow, deep_ao, rim):
        def base(nt):
            g = _n(nt, "ShaderNodeNewGeometry", (-900, 200))
            nz = _n(nt, "ShaderNodeTexNoise", (-700, 200))
            _l(nt, g.outputs["Position"], nz.inputs["Vector"])
            nz.inputs["Scale"].default_value = 0.18
            nz.inputs["Detail"].default_value = 4
            return _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc(lit), core.hexc(mid), (-500, 200))
        def height(nt):
            g = _n(nt, "ShaderNodeNewGeometry", (-900, -300))
            nz = _n(nt, "ShaderNodeTexNoise", (-700, -300))
            _l(nt, g.outputs["Position"], nz.inputs["Vector"])
            nz.inputs["Scale"].default_value = 2.2
            nz.inputs["Detail"].default_value = 6
            return nz.outputs["Fac"]
        return look.cel(name, core.hexc(lit), shadow=shadow, high=(1.04, 1.0, 0.96, 1), t1=0.58, t2=0.93, paint=0.03, base_node=base,
                        height_node=height, bump=0.25, bump_dist=0.06, rough=0.9, soft=0.26, ao=deep_ao, ao_dist=1.2, rim=rim)

    main_m = cloud_mat("cloud_main", "#F6E5D9", "#DCC6C2", (0.34, 0.3, 0.55, 1), 0.85, 0.35)
    far_m = cloud_mat("cloud_far", "#C9BCCB", "#AFA3BE", (0.42, 0.42, 0.66, 1), 0.6, 0.15)
    main_cloud, cov_main = cloud_layer("clouds_main", 0.0, 31, 0.11, 0.6, 1.3, 0.08, main_m)
    far_cloud, cov_far = cloud_layer("clouds_far", -22.0, 37, 0.15, 0.45, 0.9, 0.16, far_m)
    print(f"CLOUDS coverage main {cov_main:.2f} far {cov_far:.2f}", flush=True)
    # near wisps: thin semi-transparent streaks above the main layer, drifting faster (5-15 % of the frame)
    def wisp_mat(name, seed, dens):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = _n(nt, "ShaderNodeOutputMaterial", (500, 0))
        g = _n(nt, "ShaderNodeNewGeometry", (-900, 0))
        mp = _n(nt, "ShaderNodeMapping", (-700, 0))
        _l(nt, g.outputs["Position"], mp.inputs[0])
        mp.inputs["Scale"].default_value = (0.1, 0.022, 0.0)
        mp.inputs["Rotation"].default_value = (0, 0, 0.35 + seed)
        drv = mp.inputs["Location"].driver_add("default_value", 1).driver
        drv.type = "SCRIPTED"
        drv.expression = "floor(frame / 2) * 2 * -0.012"
        nz = _n(nt, "ShaderNodeTexNoise", (-500, 0), noise_dimensions="4D")
        _l(nt, mp.outputs[0], nz.inputs["Vector"])
        nz.inputs["W"].default_value = seed * 10
        nz.inputs["Detail"].default_value = 7
        mr = _n(nt, "ShaderNodeMapRange", (-300, 0), clamp=True)
        _l(nt, nz.outputs["Fac"], mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.62, 0.8
        a = _math(nt, "MULTIPLY", mr.outputs["Result"], dens, (-150, 0))
        em = _n(nt, "ShaderNodeEmission", (0, 50))
        em.inputs[0].default_value = core.hexc("#F4E8E6")
        em.inputs[1].default_value = 0.95
        tr = _n(nt, "ShaderNodeBsdfTransparent", (0, -100))
        mx = _n(nt, "ShaderNodeMixShader", (250, 0))
        _l(nt, a, mx.inputs[0])
        _l(nt, tr.outputs[0], mx.inputs[1])
        _l(nt, em.outputs[0], mx.inputs[2])
        _l(nt, mx.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
        return m
    wx0, wy0, wx1, wy1 = rig.path_rect(1.5, 1.4)
    wisp = geo.grid("wisps_near", wx0, wy0, wx1, wy1, 4, 4, None, env, wisp_mat("wisp_near", 0.2, 0.5))
    wisp.location.z = 1.5
    wisp.visible_shadow = False
    lobe_objs = []
''' + s[j:]
# sea: sits below the far layer
rep('''    bx0, by0, bx1, by1 = rig.path_rect(-80.0, 1.4)''', '''    bx0, by0, bx1, by1 = rig.path_rect(-80.0, 1.4)       # deep blue sea far below the gaps''')
# birds: stable formation and heading, banking at most 4 degrees
rep('''        acc += 0.0015 * np.c_[np.sin(f * 0.031 + np.arange(n) * 1.7), np.cos(f * 0.023 + np.arange(n) * 2.3)]''',
    '''        acc += 0.0002 * np.c_[np.sin(f * 0.031 + np.arange(n) * 1.7), np.cos(f * 0.023 + np.arange(n) * 2.3)]''')
rep('''            b.body.rotation_euler = (0.04, max(-0.5, min(0.5, -turn * 25.0)) + 0.04 * math.sin(d * 0.04 + i), hd)''',
    '''            b.body.rotation_euler = (0.04, max(-0.04, min(0.04, -turn * 25.0)) + 0.02 * math.sin(d * 0.04 + i), hd)''')
rep('''        for ob, P0, S0, ph, small in lobe_objs:''', '''        for ob, P0, S0, ph, small in []:''')
open(p, "w").write(s)
print("s11 patched")
