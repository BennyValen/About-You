p = 'blender/scenes/s01.py'
s = open(p).read()

def rep(a, b):
    global s
    if a not in s:
        print("MISSING:", a[:90])
    s = s.replace(a, b)

# snow on the outer branch tips (radial distance in each tree's object space) + some top-facing dabs
rep('''        snow = _math(nt, "MULTIPLY", _n(nt, "ShaderNodeMapRange", (-600, 200), clamp=True).outputs[0], 1.0, (-450, 200))
        mr = nt.nodes[-2]
        _l(nt, _math(nt, "ADD", sz.outputs[2], _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.5, (-700, 100)), (-650, 150)), mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 1.22, 1.3''',
    '''        tc = _n(nt, "ShaderNodeTexCoord", (-1000, 400))
        ox = _n(nt, "ShaderNodeSeparateXYZ", (-800, 400))
        _l(nt, tc.outputs["Object"], ox.inputs[0])
        rxy = _math(nt, "SQRT", _math(nt, "ADD", _math(nt, "MULTIPLY", ox.outputs[0], ox.outputs[0], (-650, 450)),
                                        _math(nt, "MULTIPLY", ox.outputs[1], ox.outputs[1], (-650, 350)), (-550, 400)), None, (-450, 400))
        tipv = _math(nt, "ADD", _math(nt, "DIVIDE", rxy, 3.6, (-350, 400)), _math(nt, "MULTIPLY", nz.outputs["Fac"], 0.55, (-450, 300)), (-250, 350))
        mr = _n(nt, "ShaderNodeMapRange", (-150, 350), clamp=True)
        _l(nt, tipv, mr.inputs["Value"])
        mr.inputs["From Min"].default_value, mr.inputs["From Max"].default_value = 0.98, 1.04
        snow = mr.outputs["Result"]''')
# brighter moonlit snow, near-white moonlight so the light tint only colours the practical lights
rep('''    core.sun(MOON_DIR, core.sun_irradiance_for(0.5, MOON_DIR, 0.18), core.hexc("#a9b8ff"), angle_deg=1.5)''',
    '''    core.sun(MOON_DIR, core.sun_irradiance_for(0.62, MOON_DIR, 0.2), core.hexc("#dfe5ff"), angle_deg=1.5)''')
rep('''    core.world_ambient(core.hexc("#2c3766"), 0.3)''', '''    core.world_ambient(core.hexc("#8d97c8"), 0.26)''')
# no world volume (noisy); the beam is a soft emissive cone over the track, plus a real spot for the light on the ties
rep('''    w = sc.world
    vol = w.node_tree.nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.006
    vol.inputs["Color"].default_value = (0.75, 0.8, 1.0, 1)
    w.node_tree.links.new(vol.outputs[0], w.node_tree.nodes["World Output"].inputs["Volume"])
    sc.eevee.volumetric_start = rig.h - 30
    sc.eevee.volumetric_end = rig.h + 2
    sc.eevee.volumetric_samples = 32''', '''    beam_m = bpy.data.materials.new("beam")
    beam_m.use_nodes = True
    bnt = beam_m.node_tree
    bnt.nodes.clear()
    bout = _n(bnt, "ShaderNodeOutputMaterial", (600, 0))
    btc = _n(bnt, "ShaderNodeTexCoord", (-900, 0))
    bsx = _n(bnt, "ShaderNodeSeparateXYZ", (-700, 0))
    _l(bnt, btc.outputs["UV"], bsx.inputs[0])
    lat = _math(bnt, "ABSOLUTE", _math(bnt, "SUBTRACT", bsx.outputs[0], 0.5, (-550, 100)), None, (-450, 100))
    halfw = _math(bnt, "ADD", _math(bnt, "MULTIPLY", bsx.outputs[1], 0.42, (-550, 200)), 0.06, (-450, 200))
    side = _math(bnt, "SUBTRACT", 1.0, _math(bnt, "DIVIDE", lat, halfw, (-350, 150)), (-250, 150), clamp=True)
    along = _math(bnt, "POWER", _math(bnt, "SUBTRACT", 1.0, bsx.outputs[1], (-350, 0)), 1.8, (-250, 0))
    bnz = _n(bnt, "ShaderNodeTexNoise", (-550, -200), noise_dimensions="4D")
    _l(bnt, btc.outputs["Generated"], bnz.inputs["Vector"])
    bnz.inputs["Scale"].default_value = 5.0
    bdr = bnz.inputs["W"].driver_add("default_value").driver
    bdr.type = "SCRIPTED"
    bdr.expression = "floor(frame / 2) * 0.04"
    ba = _math(bnt, "MULTIPLY", _math(bnt, "MULTIPLY", _math(bnt, "POWER", side, 0.8, (-150, 150)), along, (0, 100)),
               _math(bnt, "ADD", _math(bnt, "MULTIPLY", bnz.outputs["Fac"], 0.6, (-350, -200)), 0.55, (-200, -200)), (100, 50), clamp=True)
    bem = _n(bnt, "ShaderNodeEmission", (300, 100))
    bem.inputs[0].default_value = (0.86, 0.9, 1.0, 1)
    bem.inputs[1].default_value = 1.15
    btr = _n(bnt, "ShaderNodeBsdfTransparent", (300, -100))
    bmx = _n(bnt, "ShaderNodeMixShader", (450, 0))
    _l(bnt, _math(bnt, "MULTIPLY", ba, 0.75, (250, -250)), bmx.inputs[0])
    _l(bnt, btr.outputs[0], bmx.inputs[1])
    _l(bnt, bem.outputs[0], bmx.inputs[2])
    _l(bnt, bmx.outputs[0], bout.inputs[0])
    beam_m.surface_render_method = "BLENDED"''')
rep('''            li.energy = 2200.0''', '''            li.energy = 520.0''')
rep('''    head.volume_factor = 6.0''', '''    head.volume_factor = 0.0''')
rep('''    head.energy = 250000.0''', '''    head.energy = 9000.0''')
rep('''    for i, (z, dens) in enumerate(((8.0, 0.55), (16.0, 0.45))):''', '''    beam = geo.grid("beam", -1, 0, 1, 1, 2, 2, None, env, beam_m)
    beam.visible_shadow = False
    for i, (z, dens) in enumerate(((8.0, 0.3), (16.0, 0.24))):''')
rep('''        em.inputs[0].default_value = core.hexc("#a9b3e0")''', '''        em.inputs[0].default_value = core.hexc("#b6bfe8")''')
rep('''        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})''', '''        beam.location = (0.0, fy + 0.2, 1.6)
        beam.scale = (7.0, 30.0, 1.0)
        curve.set(sim[d])
        log.append({"A": thread.endpoint_record(rig, f, sim[d])})''')
rep('''lift=(0.98, 0.99, 1.06), gain=(1.03, 0.99, 0.96), vignette=0.4, grain=0.035,''', '''lift=(0.98, 0.99, 1.06), gain=(1.03, 0.99, 0.96), vignette=0.36, grain=0.02,''')
open(p, 'w').write(s)

p = 'blender/kit/look.py'
t = open(p).read()
t = t.replace('''    _l(nt, _math(nt, "MULTIPLY", over, 0.8, (0, -1000)), glowc.inputs["Scale"])''', '''    _l(nt, _math(nt, "MULTIPLY", over, 0.35, (0, -1000)), glowc.inputs["Scale"])''')
open(p, 'w').write(t)
print("ok")
