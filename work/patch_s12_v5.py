import json, numpy as np

p = 'blender/kit/thread.py'
s = open(p).read()
s = s.replace('''                    if low.any():
                        P[low, 2] = gz[low]
                        # friction: kill most tangential velocity of points in contact
                        Pp[low, :2] = P[low, :2] - (P[low, :2] - Pp[low, :2]) * (1.0 - self.mu)''', '''                    if low.any():
                        P[low, 2] = gz[low]
                        # friction: kill most tangential velocity of points in contact (mu may vary by surface)
                        mu = self.mu(P[low, 0], P[low, 1])[:, None] if callable(self.mu) else self.mu
                        Pp[low, :2] = P[low, :2] - (P[low, :2] - Pp[low, :2]) * (1.0 - mu)''')
s = s.replace('''    S = np.array([rig.world_to_screen(f, p) for p in P[::4]])
    inside = (S[:, 0] >= 0) & (S[:, 0] <= 1080) & (S[:, 1] >= 0) & (S[:, 1] <= 1920)''', '''    S = np.array([rig.world_to_screen(f, p) for p in P])
    inside = (S[:, 0] >= 0) & (S[:, 0] <= 1080) & (S[:, 1] >= 0) & (S[:, 1] <= 1920)
    seg = np.linalg.norm(np.diff(S, axis=0), axis=1)
    vis_len = float(seg[inside[1:] & inside[:-1]].sum())''')
s = s.replace('''"free_end_outside": bool(b[0] < -2 or b[0] > 1082 or b[1] < -2 or b[1] > 1922), "visible": bool(inside.any()),''', '''"free_end_outside": bool(b[0] < -2 or b[0] > 1082 or b[1] < -2 or b[1] > 1922), "visible": bool(vis_len > 30.0),
            "visible_px": round(vis_len, 1),''')
open(p, 'w').write(s)

p = 'blender/scenes/s12.py'
s = open(p).read()
s = s.replace("PAINT_BOIL = 0.55 ", "PAINT_BOIL = 0.6 ")
s = s.replace('''        mp = _n(nt, "ShaderNodeMapping", (-1600, -500))
        _l(nt, geo_n.outputs["Position"], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, -0.62)''', '''        wn = _n(nt, "ShaderNodeTexNoise", (-1800, -650))
        _l(nt, geo_n.outputs["Position"], wn.inputs["Vector"])
        wn.inputs["Scale"].default_value = 0.7
        wn.inputs["Detail"].default_value = 2
        wv_off = _n(nt, "ShaderNodeVectorMath", (-1700, -650), operation="SCALE")
        _l(nt, wn.outputs["Color"], wv_off.inputs[0])
        wv_off.inputs["Scale"].default_value = 0.55
        wpos = _n(nt, "ShaderNodeVectorMath", (-1650, -550), operation="ADD")
        _l(nt, geo_n.outputs["Position"], wpos.inputs[0])
        _l(nt, wv_off.outputs[0], wpos.inputs[1])
        mp = _n(nt, "ShaderNodeMapping", (-1600, -500))
        _l(nt, wpos.outputs[0], mp.inputs[0])
        mp.inputs["Rotation"].default_value = (0, 0, -0.62)''')
s = s.replace('''        wv.inputs["Scale"].default_value = 2.2
        wv.inputs["Distortion"].default_value = 3.2
        wv.inputs["Detail"].default_value = 1.0
        wv.inputs["Detail Scale"].default_value = 0.3''', '''        wv.inputs["Scale"].default_value = 2.0
        wv.inputs["Distortion"].default_value = 1.2
        wv.inputs["Detail"].default_value = 2.0
        wv.inputs["Detail Scale"].default_value = 0.8''')
s = s.replace('''height_node=height, bump=1.25, bump_dist=0.018)''', '''height_node=height, bump=0.7, bump_dist=0.018)''')
s = s.replace('''    c1 = band(r1, 0.011, loc_y - 100, 0.3)
    near1 = band(r1, 0.13, loc_y - 160, 0.2)
    c2 = _math(nt, "MULTIPLY", band(r2, 0.012, loc_y - 250, 0.3), near1, (-700, loc_y - 250))
    near2 = _math(nt, "MULTIPLY", band(r2, 0.09, loc_y - 310, 0.2), near1, (-700, loc_y - 310))
    c3 = _math(nt, "MULTIPLY", band(r3, 0.014, loc_y - 400, 0.3), near2, (-700, loc_y - 400))''', '''    c1 = band(r1, 0.028, loc_y - 100, 0.35)
    near1 = band(r1, 0.16, loc_y - 160, 0.2)
    c2 = _math(nt, "MULTIPLY", band(r2, 0.026, loc_y - 250, 0.35), near1, (-700, loc_y - 250))
    near2 = _math(nt, "MULTIPLY", band(r2, 0.11, loc_y - 310, 0.2), near1, (-700, loc_y - 310))
    c3 = _math(nt, "MULTIPLY", band(r3, 0.026, loc_y - 400, 0.35), near2, (-700, loc_y - 400))''')
s = s.replace('''        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", cr, 0.85, (-700, 100)), c, core.hexc("#9884a8"), (-600, 200))''',
              '''        c = _mixrgb(nt, "MIX", cr, c, core.hexc("#7f6c9b"), (-600, 200))''')
s = s.replace('''core.hexc("#dcc0ba"), core.hexc("#c8acb2")''', '''core.hexc("#dfc0b6"), core.hexc("#c9a9b3")''')
s = s.replace('''        mp.inputs["Scale"].default_value = (0.1, 2.6, 1.0)''', '''        mp.inputs["Scale"].default_value = (0.07, 3.2, 1.0)
        dr = mp.inputs["Location"].driver_add("default_value", 0).driver
        dr.type = "SCRIPTED"
        dr.expression = "frame * 0.004"''')
s = s.replace('''        c2 = _mixrgb(nt, "MIX", mr.outputs["Result"], core.hexc("#b29fbb"), core.hexc("#dcbfc0"), (-850, 0))
        c = _mixrgb(nt, "MIX", 0.38, c1, c2, (-700, 150))''', '''        c2 = _mixrgb(nt, "MIX", mr.outputs["Result"], core.hexc("#a796bf"), core.hexc("#e8cac4"), (-850, 0))
        c = _mixrgb(nt, "MIX", 0.55, c1, c2, (-700, 150))''')
s = s.replace('''        d.expression = "frame / 40.0"''', '''        d.expression = "frame / 12.0"''')
s = s.replace('''base_node=base, height_node=height, bump=0.12, bump_dist=0.02)''', '''base_node=base, height_node=height, bump=0.2, bump_dist=0.02)''')
s = s.replace('''    def current(x, y, t):
        k = min(max((t - 3925.0) / 50.0, 0.0), 1.0)
        return np.full_like(x, -2.6 * k), np.zeros_like(y)
    cord_a = thread.Cord(n_seg=200, length=17.0, mode="ground", ground=gfun, friction=0.8, substeps=6, iters=22, push=current)''', '''    def current(sign, t_on):
        def f(x, y, t):
            k = min(max((t - t_on) / 40.0, 0.0), 1.0)
            return np.full_like(x, sign * 16.0 * k), np.zeros_like(y)
        return f
    mu = lambda x, y: np.where(sand_height(x, y) > 0.0, 0.75, 0.28)
    cord_a = thread.Cord(n_seg=200, length=17.0, mode="ground", ground=gfun, friction=mu, substeps=6, iters=22, push=current(-1, 3915.0))''')
s = s.replace('''    cord_b = thread.Cord(n_seg=200, length=17.0, mode="ground", ground=gfun, friction=0.8, substeps=6, iters=22)''',
              '''    cord_b = thread.Cord(n_seg=200, length=17.0, mode="ground", ground=gfun, friction=mu, substeps=6, iters=22, push=current(1, 3940.0))''')
s = s.replace('''lift=(0.99, 0.985, 1.03), gain=(1.03, 1.0, 0.975), vignette=0.24, grain=0.03, ink=0.55,
                         ink_normal=(0.35, 1.1))''', '''lift=(0.99, 0.985, 1.03), gain=(1.03, 1.0, 0.975), vignette=0.24, grain=0.03, ink=0.45,
                         ink_normal=(0.6, 1.5), saturation=1.14)''')
open(p, 'w').write(s)
for key in ("frame / 12.0", "friction=mu", "saturation=1.14", "bump=0.7", "wv_off"):
    print(key, key in s)

prof = json.load(open('work/cam_profile.json'))
n = 356
tt = np.arange(n, dtype=float)
ss = lambda x: np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))
v = 8.5 + (13.7 - 8.5) * ss((tt - 34) / 46.0)
v = v * (1 - ss((tt - 268) / 40.0))
prof['12'] = [round(float(x), 4) for x in v]
json.dump(prof, open('work/cam_profile.json', 'w'))
