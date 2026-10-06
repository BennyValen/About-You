p = 'blender/scenes/s12.py'
s = open(p).read()
s = s.replace("PAINT_BOIL = 0.6 ", "PAINT_BOIL = 1.0 ")
s = s.replace('''        c2 = _mixrgb(nt, "MIX", mr.outputs["Result"], core.hexc("#a796bf"), core.hexc("#e8cac4"), (-850, 0))
        c = _mixrgb(nt, "MIX", 0.46, c1, c2, (-700, 150))''', '''        c2 = _mixrgb(nt, "MIX", mr.outputs["Result"], core.hexc("#b29fbb"), core.hexc("#dcbfc0"), (-850, 0))
        c = _mixrgb(nt, "MIX", 0.36, c1, c2, (-700, 150))''')
s = s.replace('''        d.expression = "frame / 12.0"''', '''        d.expression = "frame / 30.0"''')
s = s.replace('''paint=0.2, paint_scale=2.4, rough=0.15, base_node=base, height_node=height, bump=0.2, bump_dist=0.02)''',
              '''paint=0.3, paint_scale=2.4, rough=0.15, base_node=base, height_node=height, bump=0.14, bump_dist=0.02)''')
s = s.replace('''paint=0.18, paint_scale=3.0, rough=0.8, base_node=base, height_node=height, bump=0.7, bump_dist=0.018)''',
              '''paint=0.26, paint_scale=3.0, rough=0.8, base_node=base, height_node=height, bump=0.7, bump_dist=0.018)''')
open(p, 'w').write(s)
p = 'blender/kit/look.py'
s = open(p).read()
s = s.replace("    ca=0.012, lift=", "    ca=0.006, lift=")
open(p, 'w').write(s)
p = 'scripts/qa/threadmask.py'
s = open(p).read()
s = s.replace("    return (sat > 55) & (f[..., 0] > 120)", "    return (sat > 75) & (f[..., 0] > 140) & (f[..., 1] < 120)")
open(p, 'w').write(s)
print("ok")
