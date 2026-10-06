import re

def patch(p, pairs):
    s = open(p).read()
    for a, b in pairs:
        if a not in s:
            print("MISSING in", p, ":", a[:70])
        s = s.replace(a, b)
    open(p, "w").write(s)

# ---- scene 1: dark spruces with sparse snow tips, later pond, stronger window light + headlight
patch("blender/scenes/s01.py", [
    ('mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.12, 1.2',
     'mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.33, 1.4'),
    ("return np.hypot((x + 14.0) * 0.82, y - 44.0) - 9.0 + 1.2 * geo.fbm2(x * 0.1, y * 0.1, 3, 3)",
     "return np.hypot((x + 15.0) * 0.82, y - 88.0) - 7.5 + 1.2 * geo.fbm2(x * 0.1, y * 0.1, 3, 3)"),
    ("            li.energy = 900.0", "            li.energy = 4500.0"),
    ('window=look.emissive("window", (1.0, 0.62, 0.22, 1), 4.0)', 'window=look.emissive("window", (1.0, 0.62, 0.22, 1), 9.0)'),
    ("    head.energy = 60000.0", "    head.energy = 250000.0"),
    ('    vol.inputs["Density"].default_value = 0.012', '    vol.inputs["Density"].default_value = 0.03'),
    ("core.sun(MOON_DIR, core.sun_irradiance_for(0.5, MOON_DIR, 0.2)", "core.sun(MOON_DIR, core.sun_irradiance_for(0.42, MOON_DIR, 0.16)"),
    ('core.world_ambient(core.hexc("#2c3766"), 0.38)', 'core.world_ambient(core.hexc("#2c3766"), 0.3)'),
])
# ---- scene 2: more fingerprint-like flow (stronger warp), more lime
patch("blender/scenes/s02.py", [
    ("    qx, qy = X + wx * 2.0, Y + wy * 2.0", "    qx, qy = X + wx * 4.2, Y + wy * 4.2"),
])
# ---- scene 4: darker ice, random-oriented sparse cracks (rotate before stretch), faint network
s4 = open("blender/scenes/s04.py").read()
s4 = s4.replace('''            m2 = _n(nt, "ShaderNodeMapping", (-1600, -100 - i * 150))
            _l(nt, geo_n.outputs["Position"], m2.inputs[0])
            m2.inputs["Rotation"].default_value = (0, 0, ang)
            m2.inputs["Scale"].default_value = (1.0, 0.02, 1)''', '''            vr = _n(nt, "ShaderNodeVectorRotate", (-1700, -100 - i * 150), rotation_type="Z_AXIS")
            _l(nt, geo_n.outputs["Position"], vr.inputs["Vector"])
            vr.inputs["Angle"].default_value = ang
            m2 = _n(nt, "ShaderNodeMapping", (-1600, -100 - i * 150))
            _l(nt, vr.outputs[0], m2.inputs[0])
            m2.inputs["Scale"].default_value = (1.0, 0.02, 1)''')
s4 = s4.replace('''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#0f2353"), core.hexc("#2a4589"), (-1200, 300))''',
                '''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#0c1b44"), core.hexc("#21386f"), (-1200, 300))''')
s4 = s4.replace('''        hv.inputs["From Min"].default_value, hv.inputs["From Max"].default_value = 0.012, 0.003
        cracks = _math(nt, "MAXIMUM", out, _math(nt, "MULTIPLY", hv.outputs["Result"], 0.55, (-1050, -750)), (-800, -400))
        c = _mixrgb(nt, "MIX", cracks, c, core.hexc("#5fb4d3"), (-700, 200))''', '''        hv.inputs["From Min"].default_value, hv.inputs["From Max"].default_value = 0.008, 0.002
        cracks = _math(nt, "MAXIMUM", _math(nt, "MULTIPLY", out, 0.7, (-900, -400)), _math(nt, "MULTIPLY", hv.outputs["Result"], 0.22, (-1050, -750)), (-800, -400))
        c = _mixrgb(nt, "MIX", cracks, c, core.hexc("#4f9ec0"), (-700, 200))''')
s4 = s4.replace('''    vo.inputs["Scale"].default_value = 0.55''', '''    vo.inputs["Scale"].default_value = 0.3''')
s4 = s4.replace('''        vo.inputs["Scale"].default_value = 0.55
        hv''', '''        vo.inputs["Scale"].default_value = 0.3
        hv''')
s4 = s4.replace('''    em.inputs[1].default_value = 1.15''', '''    em.inputs[1].default_value = 0.95''')
open("blender/scenes/s04.py", "w").write(s4)
patch("blender/scenes/s04.py", [
    ('        vo.inputs["Scale"].default_value = 0.55', '        vo.inputs["Scale"].default_value = 0.3'),
])
# ---- scene 5: striation lines painted in colour too (light lines on orange, lavender lines in shadow)
s5 = open("blender/scenes/s05.py").read()
s5 = s5.replace('''def sand_material():
    def height(nt):''', '''def sand_material():
    def ripple(nt, loc=(-1600, -300)):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (loc[0], loc[1]))
        sx = _n(nt, "ShaderNodeSeparateXYZ", (loc[0] + 150, loc[1]))
        _l(nt, geo_n.outputs["Position"], sx.inputs[0])
        s1 = _math(nt, "SINE", _math(nt, "MULTIPLY", sx.outputs[1], 0.44, (loc[0] + 300, loc[1] - 100)), None, (loc[0] + 400, loc[1] - 100))
        s2 = _math(nt, "SINE", _math(nt, "MULTIPLY", sx.outputs[1], 1.16, (loc[0] + 300, loc[1] - 180)), None, (loc[0] + 400, loc[1] - 180))
        meander = _math(nt, "ADD", _math(nt, "MULTIPLY", s1, 0.74, (loc[0] + 500, loc[1] - 100)), _math(nt, "MULTIPLY", s2, 0.36, (loc[0] + 500, loc[1] - 180)), (loc[0] + 600, loc[1] - 140))
        xw = _math(nt, "SUBTRACT", sx.outputs[0], _math(nt, "MULTIPLY", meander, 0.85, (loc[0] + 700, loc[1] - 140)), (loc[0] + 800, loc[1] - 50))
        comb = _n(nt, "ShaderNodeCombineXYZ", (loc[0] + 900, loc[1] - 50))
        _l(nt, xw, comb.inputs[0])
        _l(nt, sx.outputs[1], comb.inputs[1])
        wv = _n(nt, "ShaderNodeTexWave", (loc[0] + 1050, loc[1] - 50), wave_type="BANDS", bands_direction="X", wave_profile="SIN")
        _l(nt, comb.outputs[0], wv.inputs["Vector"])
        wv.inputs["Scale"].default_value = 3.3
        wv.inputs["Distortion"].default_value = 1.3
        wv.inputs["Detail"].default_value = 1.5
        wv.inputs["Detail Scale"].default_value = 0.5
        return wv.outputs["Fac"]
    def height(nt):''')
s5 = s5.replace('''        return _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#e8a072"), core.hexc("#efb27b"), (-800, 300))
    return look.cel("sand",''', '''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#e39a70"), core.hexc("#efb07a"), (-800, 300))
        lines = _n(nt, "ShaderNodeMapRange", (-700, 0), clamp=True)
        _l(nt, ripple(nt, (-2400, 0)), lines.inputs["Value"])
        lines.inputs["From Min"].default_value, lines.inputs["From Max"].default_value = 0.78, 0.92
        return _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", lines.outputs["Result"], 0.75, (-550, 0)), c, core.hexc("#fbd6a6"), (-400, 200))
    return look.cel("sand",''')
s5 = s5.replace('''        wv.inputs["Scale"].default_value = 2.9''', '''        wv.inputs["Scale"].default_value = 3.3''')
open("blender/scenes/s05.py", "w").write(s5)
# ---- scene 8: wider turbulent glow, fainter sparks, visible swimmer, less grain
patch("blender/scenes/s08.py", [
    ("    glow_light.energy = 140.0", "    glow_light.energy = 60.0"),
    ("                v = v / (np.linalg.norm(v) + 1e-9) * spd * rng.random() + np.array([0.06, -0.15, 0])",
     "                v = v / (np.linalg.norm(v) + 1e-9) * spd * 2.5 * rng.random() + np.array([0.08, -0.25, 0])"),
    ('geo.bm_to_object(bm, "spark", look.emissive("spark", (0.45, 1.6, 1.9, 1), 2.2), pproto)',
     'geo.bm_to_object(bm, "spark", look.emissive("spark", (0.3, 1.0, 1.25, 1), 1.4), pproto)'),
    ("    width = _math(nt, \"ADD\", _math(nt, \"MULTIPLY\", _math(nt, \"SUBTRACT\", 1.0, sx.outputs[1], (-500, 250)), 0.32, (-400, 250)), 0.06, (-300, 250))",
     "    width = _math(nt, \"ADD\", _math(nt, \"MULTIPLY\", _math(nt, \"SUBTRACT\", 1.0, sx.outputs[1], (-500, 250)), 0.36, (-400, 250)), 0.14, (-300, 250))"),
    ("        wake.scale = (1.4, 4.2, 1)", "        wake.scale = (2.0, 4.6, 1)"),
    ("                         gain=(1.0, 1.02, 1.04), vignette=0.38, grain=0.04, ink=0.25), res_scale=opt.scale)",
     "                         gain=(1.0, 1.02, 1.04), vignette=0.38, grain=0.018, ink=0.25), res_scale=opt.scale)"),
    ("look.compositor(dict(kuwahara=8, bloom=1.4, bloom_threshold=0.45, bloom_size=0.75,", "look.compositor(dict(kuwahara=8, bloom=1.0, bloom_threshold=0.55, bloom_size=0.8,"),
])
# ---- scene 11: cauliflower micro-puffs as bump (voronoi domes at two scales)
patch("blender/scenes/s11.py", [
    ('''    def cloud_h(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, -200))
        nz = _n(nt, "ShaderNodeTexNoise", (-700, -200))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 2.6
        nz.inputs["Detail"].default_value = 6
        nz.inputs["Distortion"].default_value = 1.5
        return nz.outputs["Fac"]''', '''    def cloud_h(nt):
        geo_n = _n(nt, "ShaderNodeNewGeometry", (-900, -200))
        out = None
        for i, sc_ in enumerate((1.1, 2.6)):
            vo = _n(nt, "ShaderNodeTexVoronoi", (-700, -200 - i * 200), feature="F1")
            _l(nt, geo_n.outputs["Position"], vo.inputs["Vector"])
            vo.inputs["Scale"].default_value = sc_
            dome = _math(nt, "SQRT", _math(nt, "SUBTRACT", 1.0, _math(nt, "MULTIPLY", vo.outputs["Distance"], vo.outputs["Distance"], (-500, -200 - i * 200)), (-400, -200 - i * 200), clamp=True), None, (-300, -200 - i * 200))
            dome = _math(nt, "MULTIPLY", dome, 1.0 / (i + 1.6), (-200, -200 - i * 200))
            out = dome if out is None else _math(nt, "ADD", out, dome, (-100, -300))
        nz = _n(nt, "ShaderNodeTexNoise", (-700, -600))
        _l(nt, geo_n.outputs["Position"], nz.inputs["Vector"])
        nz.inputs["Scale"].default_value = 3.0
        nz.inputs["Detail"].default_value = 5
        return _math(nt, "ADD", out, _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.3, (-500, -600)), (0, -400))'''),
    ("height_node=cloud_h, bump=0.6, bump_dist=0.08, rough=0.9)", "height_node=cloud_h, bump=0.9, bump_dist=0.12, rough=0.9)"),
])
# ---- global: stronger paint filter
patch("blender/kit/look.py", [("    kuwahara=7, uniformity=4,", "    kuwahara=10, uniformity=4,")])
for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
    p = f"blender/scenes/s{i:02d}.py"
    s = open(p).read()
    s = re.sub(r"look\.compositor\(dict\(kuwahara=(\d+),", lambda m: f"look.compositor(dict(kuwahara={int(m.group(1)) + 2},", s)
    open(p, "w").write(s)
print("done")
