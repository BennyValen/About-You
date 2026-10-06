p = 'blender/kit/look.py'
s = open(p).read()
s = s.replace('''    sin("BumpDistance", "NodeSocketFloat", 0.05)''', '''    sin("BumpDistance", "NodeSocketFloat", 0.05)
    sin("LightTint", "NodeSocketFloat", 0.0, 0.0, 1.0)''')
s = s.replace('''    col = _mixrgb(nt, "MULTIPLY", 1.0, col, pfc.outputs[0], (200, 50))''', '''    col = _mixrgb(nt, "MULTIPLY", 1.0, col, pfc.outputs[0], (200, 50))
    # optional: coloured practical lights tint the cel colour (chromaticity of the incoming light),
    # and over-bright light pools glow; LightTint = 0 keeps the classic white-light cel look
    lum = _math(nt, "MAXIMUM", bw.outputs[0], 0.02, (-450, -700))
    chroma = _n(nt, "ShaderNodeVectorMath", (-300, -700), operation="DIVIDE")
    _l(nt, s2r.outputs[0], chroma.inputs[0])
    lc = _n(nt, "ShaderNodeCombineXYZ", (-400, -800))
    for i in range(3):
        _l(nt, lum, lc.inputs[i])
    _l(nt, lc.outputs[0], chroma.inputs[1])
    tint = _mixrgb(nt, "MIX", gi.outputs["LightTint"], (1, 1, 1, 1), chroma.outputs[0], (-150, -700))
    col = _mixrgb(nt, "MULTIPLY", 1.0, col, tint, (300, -100))
    over = _math(nt, "MULTIPLY", _math(nt, "MAXIMUM", _math(nt, "SUBTRACT", bw.outputs[0], 1.0, (-300, -900)), 0.0, (-200, -900)),
                 gi.outputs["LightTint"], (-100, -900))
    glowc = _mixrgb(nt, "MULTIPLY", 1.0, tint, base, (0, -900))
    glowc = _n(nt, "ShaderNodeVectorMath", (100, -900), operation="SCALE")
    _l(nt, _mixrgb(nt, "MULTIPLY", 1.0, tint, base, (0, -950)), glowc.inputs[0])
    _l(nt, _math(nt, "MULTIPLY", over, 0.8, (0, -1000)), glowc.inputs["Scale"])
    addg = _n(nt, "ShaderNodeVectorMath", (400, -300), operation="ADD")
    _l(nt, col, addg.inputs[0])
    _l(nt, glowc.outputs[0], addg.inputs[1])
    col = addg.outputs[0]''')
s = s.replace('''        bump=0.0, bump_dist=0.05, blend="OPAQUE", backface=True):''', '''        bump=0.0, bump_dist=0.05, blend="OPAQUE", backface=True, light_tint=0.0):''')
s = s.replace('''                Glow=glow, Roughness=rough, Alpha=alpha, BumpStrength=bump, BumpDistance=bump_dist)''', '''                Glow=glow, Roughness=rough, Alpha=alpha, BumpStrength=bump, BumpDistance=bump_dist, LightTint=light_tint)''')
open(p, 'w').write(s)

p = 'blender/scenes/s01.py'
s = open(p).read()
s = s.replace('''    return look.cel("spruce", core.hexc("#262e4c"), shadow=(0.55, 0.55, 0.75, 1), high=(1.25, 1.25, 1.3, 1), t1=0.35, t2=0.9,
                    paint=0.12, paint_scale=4.0, base_node=base, backface=True)''', '''    return look.cel("spruce", core.hexc("#262e4c"), shadow=(0.55, 0.55, 0.75, 1), high=(1.25, 1.25, 1.3, 1), t1=0.35, t2=0.9,
                    paint=0.12, paint_scale=4.0, base_node=base, backface=True, light_tint=1.0)''')
s = s.replace('''                      paint=0.2, paint_scale=0.6, base_node=snow_base, rough=0.9))''', '''                      paint=0.2, paint_scale=0.6, base_node=snow_base, rough=0.9, light_tint=1.0))''')
s = s.replace('''mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.33, 1.4''', '''mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.22, 1.3''')
open(p, 'w').write(s)

p = 'blender/scenes/s08.py'
s = open(p).read()
s = s.replace('''t1=0.3, t2=0.75, paint=0.0),
              legs=''', '''t1=0.3, t2=0.75, paint=0.0, light_tint=1.0),
              legs=''')
s = s.replace('''high=(1.4, 1.8, 2.0, 1), t1=0.3, t2=0.75, paint=0.0),
              shoes=''', '''high=(1.4, 1.8, 2.0, 1), t1=0.3, t2=0.75, paint=0.0, light_tint=1.0),
              shoes=''')
open(p, 'w').write(s)
print("light_tint" in open('blender/kit/look.py').read(), open('blender/scenes/s01.py').read().count("light_tint=1.0"))
