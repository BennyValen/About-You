def patch(p, pairs):
    s = open(p).read()
    for a, b in pairs:
        if a not in s:
            print("MISSING in", p, ":", a[:80])
        s = s.replace(a, b)
    open(p, "w").write(s)

patch("blender/scenes/s01.py", [
    ('    vol.inputs["Density"].default_value = 0.03', '    vol.inputs["Density"].default_value = 0.006'),
    ("core.sun(MOON_DIR, core.sun_irradiance_for(0.42, MOON_DIR, 0.16)", "core.sun(MOON_DIR, core.sun_irradiance_for(0.5, MOON_DIR, 0.18)"),
    ("            li.energy = 4500.0", "            li.energy = 2200.0"),
    ("            lo.rotation_euler = (0, side * math.radians(90), math.radians(90))",
     "            zl = -Vector((side, 0.0, -0.55)).normalized()\n"
     "            xl = Vector((0.0, 1.0, 0.0))\n"
     "            yl = zl.cross(xl)\n"
     "            lo.matrix_basis = Matrix.Translation(lo.location) @ Matrix((xl, yl, zl)).transposed().to_4x4()"),
    ('window=look.emissive("window", (1.0, 0.62, 0.22, 1), 9.0)', 'window=look.emissive("window", (1.0, 0.62, 0.22, 1), 5.0)'),
])
patch("blender/scenes/s04.py", [
    ('''            mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = w, w * 0.3''',
     '''            mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = w * 0.4, w * 0.1'''),
    ('''        c = _mixrgb(nt, "MIX", cracks, c, core.hexc("#4f9ec0"), (-700, 200))''',
     '''        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", cracks, 0.6, (-750, 200)), c, core.hexc("#4f9ec0"), (-700, 200))'''),
])
patch("blender/scenes/s05.py", [
    ("        h = np.maximum(h, hs * np.where(u < 0, wind, lee) * 1.4)", "        h = np.maximum(h, hs * np.where(u < 0, wind, lee) * 0.75)"),
    ('''        lines.inputs["From Min"].default_value, lines.inputs["From Max"].default_value = 0.78, 0.92
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", lines.outputs["Result"], 0.75, (-550, 0)), c, core.hexc("#fbd6a6"), (-400, 200))''',
     '''        lines.inputs["From Min"].default_value, lines.inputs["From Max"].default_value = 0.7, 0.88
        return _mixrgb(nt, "MIX", lines.outputs["Result"], c, core.hexc("#ffeccc"), (-400, 200))'''),
])
patch("blender/scenes/s08.py", [
    ("        wake.scale = (2.0, 4.6, 1)", "        wake.scale = (3.0, 4.8, 1)"),
    ('''    em.inputs[1].default_value = 1.6
    tr = _n(nt, "ShaderNodeBsdfTransparent", (380, -100))''', '''    em.inputs[1].default_value = 2.2
    tr = _n(nt, "ShaderNodeBsdfTransparent", (380, -100))'''),
])
patch("blender/scenes/s11.py", [
    ('''        return _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#ecd6cd"), core.hexc("#e2cad0"), (-500, 200))''',
     '''        return _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#f3dccd"), core.hexc("#e6cbd0"), (-500, 200))'''),
    ('''cmat = look.cel("cloud", core.hexc("#ead4cc"), shadow=(0.6, 0.55, 0.8, 1), high=(1.07, 1.05, 1.04, 1), t1=0.66, t2=0.9,''',
     '''cmat = look.cel("cloud", core.hexc("#ead4cc"), shadow=(0.5, 0.42, 0.82, 1), high=(1.08, 1.03, 0.96, 1), t1=0.66, t2=0.9,'''),
    ("    Z = np.full_like(X, -9.0)", "    Z = np.full_like(X, -1.6)"),
    ("            cap = np.where((d2 < r[i] ** 2) & m, cap, -9.0)", "            cap = np.where((d2 < r[i] ** 2) & m, cap, -1.6)"),
    ("    return Z - 1.0", "    return Z - 0.4"),
    ("    below.location.z = -8.5", "    below.location.z = -1.4"),
])
print("ok")
