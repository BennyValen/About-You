p = "blender/scenes/s11.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


# smooth cloud edges: keep a one-cell skirt of the grid, store the normalised density per vertex and cut the surface
# with alpha at the density contour (interpolated across faces -> smooth outlines instead of grid stair-steps)
rep('''        keep = D > thr - 0.35 * w
        ids = -np.ones(X.shape, np.int64)''', '''        keep = D > thr - 0.35 * w
        from scipy.ndimage import binary_dilation
        keep = binary_dilation(keep, iterations=2)
        ids = -np.ones(X.shape, np.int64)''')
rep('''        ob = geo.mesh_from_arrays(name, V, F, env, True, mat)
        return ob, float(keep.mean())''', '''        ob = geo.mesh_from_arrays(name, V, F, env, True, mat)
        at = ob.data.attributes.new("dens", "FLOAT", "POINT")
        at.data.foreach_set("value", ((D[keep] - thr) / w).astype(np.float32))
        return ob, float((D > thr).mean())''')
rep('''        H = hmax * np.sign(u) * np.abs(u) ** 0.6''', '''        H = hmax * np.sign(u) * np.abs(u) ** 0.6
        H = np.where(u < 0, H * 2.5, H)        # edges roll down steeply (shadowed flanks)''')
rep('''        H = H + 0.12 * hmax * geo.fbm2(X * f0 * 6, Y * f0 * 6, 3, seed + 9) * np.clip(u * 3, 0, 1)''',
    '''        # cauliflower relief at two scales (a field, not repeated lobes)
        H = H + (0.22 * hmax * np.abs(geo.fbm2(X * f0 * 5, Y * f0 * 5, 3, seed + 9))
                 + 0.10 * hmax * np.abs(geo.fbm2(X * f0 * 14, Y * f0 * 14, 3, seed + 10))) * np.clip(u * 3 + 0.3, 0, 1)''')
rep('''        return look.cel(name, core.hexc(lit), shadow=shadow, high=(1.04, 1.0, 0.96, 1), t1=0.58, t2=0.93, paint=0.03, base_node=base,
                        height_node=height, bump=0.25, bump_dist=0.06, rough=0.9, soft=0.26, ao=deep_ao, ao_dist=1.2, rim=rim)''',
    '''        m = look.cel(name, core.hexc(lit), shadow=shadow, high=(1.04, 1.0, 0.96, 1), t1=0.68, t2=0.94, paint=0.03, base_node=base,
                     height_node=height, bump=0.35, bump_dist=0.06, rough=0.9, soft=0.3, ao=deep_ao, ao_dist=1.2, rim=rim)
        nt = m.node_tree
        grp = [n for n in nt.nodes if n.type == "GROUP"][0]
        at = _n(nt, "ShaderNodeAttribute", (-300, -500))
        at.attribute_name = "dens"
        at.attribute_type = "GEOMETRY"
        cut = _math(nt, "GREATER_THAN", at.outputs["Fac"], 0.0, (-100, -500))
        _l(nt, cut, grp.inputs["Alpha"])
        m.surface_render_method = "DITHERED"
        return m''')
rep('''    main_m = cloud_mat("cloud_main", "#F6E5D9", "#DCC6C2", (0.34, 0.3, 0.55, 1), 0.85, 0.35)
    far_m = cloud_mat("cloud_far", "#C9BCCB", "#AFA3BE", (0.42, 0.42, 0.66, 1), 0.6, 0.15)
    main_cloud, cov_main = cloud_layer("clouds_main", 0.0, 31, 0.11, 0.6, 1.3, 0.08, main_m)
    far_cloud, cov_far = cloud_layer("clouds_far", -22.0, 37, 0.15, 0.45, 0.9, 0.16, far_m)''',
    '''    main_m = cloud_mat("cloud_main", "#F6E5D9", "#D8BFC6", (0.30, 0.26, 0.56, 1), 0.9, 0.35)
    far_m = cloud_mat("cloud_far", "#B9ABC8", "#9C91BA", (0.40, 0.40, 0.68, 1), 0.7, 0.12)
    main_cloud, cov_main = cloud_layer("clouds_main", 0.0, 31, 0.11, 0.5, 1.5, 0.07, main_m)
    far_cloud, cov_far = cloud_layer("clouds_far", -22.0, 37, 0.15, 0.36, 0.9, 0.14, far_m)''')
open(p, "w").write(s)
print("s11 patched b")
