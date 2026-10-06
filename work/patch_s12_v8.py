p = 'blender/scenes/s12.py'
s = open(p).read()
s = s.replace("(0.15, 24.6, 5.4, 2.5, -0.18),", "(0.15, 24.6, 5.4, 2.5, -0.18), (2.3, 19.6, 2.3, 3.1, 0.2),")
s = s.replace('''height_node=height, bump=0.7, bump_dist=0.018)''', '''height_node=height, bump=0.45, bump_dist=0.018)''')
s = s.replace('''        c = _mixrgb(nt, "MIX", cr, c, core.hexc("#8a76a4"), (-600, 200))''', '''        c = _mixrgb(nt, "MIX", _math(nt, "MULTIPLY", cr, 0.85, (-700, 100)), c, core.hexc("#9a88b2"), (-600, 200))''')
open(p, 'w').write(s)
print("ok")
