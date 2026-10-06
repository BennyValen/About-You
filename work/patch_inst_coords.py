p = 'blender/scenes/s01.py'
s = open(p).read()

def rep(a, b, src=None):
    global s
    if a not in s:
        print("MISSING:", a[:90])
    s = s.replace(a, b)

# spruce prototype: narrower spiky blades + a baked 'tip' attribute (radial distance / max radius)
rep('''            L = R * rng.uniform(0.85, 1.1)
            w = R * 0.32 / max(nb / 12, 1)''', '''            L = R * rng.uniform(0.7, 1.15)
            w = R * 0.15 / max(nb / 12, 1)''')
rep('''        nb = int(rng.integers(11, 16))''', '''        nb = int(rng.integers(13, 19))''')
rep('''    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    return geo.bm_to_object(bm, name, mats, coll, smooth=False)''', '''    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    ob = geo.bm_to_object(bm, name, mats, coll, smooth=False)
    me = ob.data
    co = np.zeros(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    tip = np.hypot(co[:, 0], co[:, 1]) / 3.9
    col = np.c_[tip, tip, tip, np.ones_like(tip)].astype(np.float32)
    ca = me.color_attributes.new("tip", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", col.ravel())
    return ob''')
rep('''        tc = _n(nt, "ShaderNodeTexCoord", (-1000, 400))
        ox = _n(nt, "ShaderNodeSeparateXYZ", (-800, 400))
        _l(nt, tc.outputs["Object"], ox.inputs[0])
        rxy = _math(nt, "SQRT", _math(nt, "ADD", _math(nt, "MULTIPLY", ox.outputs[0], ox.outputs[0], (-650, 450)),
                                        _math(nt, "MULTIPLY", ox.outputs[1], ox.outputs[1], (-650, 350)), (-550, 400)), None, (-450, 400))
        tipv = _math(nt, "ADD", _math(nt, "DIVIDE", rxy, 3.6, (-350, 400)), _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.55, (-450, 300)), (-250, 350))
        mr = _n(nt, "ShaderNodeMapRange", (-150, 350), clamp=True)
        _l(nt, tipv, mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.98, 1.04''', '''        at = _n(nt, "ShaderNodeAttribute", (-1000, 400), attribute_type="GEOMETRY", attribute_name="tip")
        tipv = _math(nt, "ADD", at.outputs["Fac"], _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.6, (-450, 300)), (-250, 350))
        mr = _n(nt, "ShaderNodeMapRange", (-150, 350), clamp=True)
        _l(nt, tipv, mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.93, 0.99''')
rep('''    core.sun(MOON_DIR, core.sun_irradiance_for(0.62, MOON_DIR, 0.2), core.hexc("#dfe5ff"), angle_deg=1.5)''',
    '''    core.sun(MOON_DIR, core.sun_irradiance_for(0.5, MOON_DIR, 0.18), core.hexc("#dfe5ff"), angle_deg=1.5)''')
rep('''    core.world_ambient(core.hexc("#8d97c8"), 0.26)''', '''    core.world_ambient(core.hexc("#8d97c8"), 0.22)''')
rep('''            li.energy = 520.0''', '''            li.energy = 300.0''')
rep('''            lo.location = (side * 1.05, CAR_LEN / 2, 1.5)''', '''            lo.location = (side * 1.15, CAR_LEN / 2, 1.6)''')
open(p, 'w').write(s)

# scene 3: lily pad prototypes get UVs = local xy; the vein shader uses UV (instances keep their UVs)
p = 'blender/scenes/s03.py'
s = open(p).read()
rep('''    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z"))
    ob = geo.bm_to_object(bm, name, mat, coll)
    return ob''', '''    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rng.uniform(0, 6.28), 3, "Z"))
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = (lp.vert.co.x * 0.5 + 0.5, lp.vert.co.y * 0.5 + 0.5)
    ob = geo.bm_to_object(bm, name, mat, coll)
    return ob''')
rep('''        tc = _n(nt, "ShaderNodeTexCoord", (-1100, 0))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-950, 0))
        _l(nt, tc.outputs["Object"], sx.inputs[0])''', '''        tc = _n(nt, "ShaderNodeTexCoord", (-1100, 0))
        uvc = _n(nt, "ShaderNodeVectorMath", (-1000, 0), operation="MULTIPLY_ADD")
        _l(nt, tc.outputs["UV"], uvc.inputs[0])
        uvc.inputs[1].default_value = (2.0, 2.0, 0.0)
        uvc.inputs[2].default_value = (-1.0, -1.0, 0.0)
        sx = _n(nt, "ShaderNodeSeparateXYZ", (-950, 0))
        _l(nt, uvc.outputs[0], sx.inputs[0])''')
open(p, 'w').write(s)
print("ok")
