p = 'blender/scenes/s01.py'
s = open(p).read()

def rep(a, b):
    global s
    if a not in s:
        print("MISSING:", a[:90])
    s = s.replace(a, b)

# per-blade fraction along the branch (base 0 -> tip 1) baked as the 'tip' attribute
rep('''            vs = [bm.verts.new(p) for p in (base_l, mid_l, tip, mid_r, base_r)]
            bm.faces.new(vs)''', '''            vs = [bm.verts.new(p) for p in (base_l, mid_l, tip, mid_r, base_r)]
            bm.faces.new(vs)
            along_vals.extend([0.0, 0.55, 1.0, 0.55, 0.0])''')
rep('''    tiers = 7
    H = rng.uniform(9, 13)''', '''    tiers = 7
    H = rng.uniform(9, 13)
    along_vals = []''')
rep('''    tip = np.hypot(co[:, 0], co[:, 1]) / 3.9
    col = np.c_[tip, tip, tip, np.ones_like(tip)].astype(np.float32)''', '''    tip = np.array(along_vals, np.float32)
    col = np.c_[tip, tip, tip, np.ones_like(tip)].astype(np.float32)''')
rep('''        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.93, 0.99''',
    '''        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.05, 1.12''')
# white snow + blue moonlight (the light colour carries the night tint; window light lands orange)
rep('''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#3d4882"), core.hexc("#5b67a8"), (-600, 200))''',
    '''        c = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#b9bfdc"), core.hexc("#d6dbef"), (-600, 200))''')
rep('''        ice = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#141a40"), core.hexc("#263068"), (-600, -100))''',
    '''        ice = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#3a4170"), core.hexc("#545d96"), (-600, -100))''')
rep('''        needles = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#1c2340"), core.hexc("#2d3658"), (-500, 0))
        return _mixrgb(nt, "MIX", snow, needles, core.hexc("#c8d0ee"), (-300, 100))''',
    '''        needles = _mixrgb(nt, "MIX", nz.outputs["Fac"], core.hexc("#39445e"), core.hexc("#4f5b78"), (-500, 0))
        return _mixrgb(nt, "MIX", snow, needles, core.hexc("#f2f4fb"), (-300, 100))''')
rep('''    core.sun(MOON_DIR, core.sun_irradiance_for(0.5, MOON_DIR, 0.18), core.hexc("#dfe5ff"), angle_deg=1.5)''',
    '''    core.sun(MOON_DIR, core.sun_irradiance_for(0.36, MOON_DIR, 0.12), core.hexc("#7d8cd6"), angle_deg=1.5)''')
rep('''    core.world_ambient(core.hexc("#8d97c8"), 0.22)''', '''    core.world_ambient(core.hexc("#4a5596"), 0.22)''')
rep('''            li.energy = 300.0''', '''            li.energy = 220.0''')
open(p, 'w').write(s)
print("ok")
