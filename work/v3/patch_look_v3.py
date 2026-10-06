p = "blender/kit/look.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:80]
    s = s.replace(a, b)


rep('''    sin("LightTint", "NodeSocketFloat", 0.0, 0.0, 1.0)
    it.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")''', '''    sin("LightTint", "NodeSocketFloat", 0.0, 0.0, 1.0)
    sin("Soft", "NodeSocketFloat", 0.2, 0.0, 1.0)
    sin("AO", "NodeSocketFloat", 0.6, 0.0, 1.0)
    sin("AODistance", "NodeSocketFloat", 0.6)
    sin("Rim", "NodeSocketFloat", 0.0)
    sin("Hero", "NodeSocketFloat", 0.0, 0.0, 1.0)
    it.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")''')

rep('''    def band(t_sock, y):
        lo = _math(nt, "SUBTRACT", t_sock, 0.035, (-620, y))
        hi = _math(nt, "ADD", t_sock, 0.035, (-620, y - 60))''', '''    def band(t_sock, y):
        # v3: soft painted shading; Soft = half width of the shadow/highlight transitions (0.035 = old hard cel)
        lo = _math(nt, "SUBTRACT", t_sock, gi.outputs["Soft"], (-620, y))
        hi = _math(nt, "ADD", t_sock, gi.outputs["Soft"], (-620, y - 60))''')

rep('''    glow = _math(nt, "ADD", gi.outputs["Glow"], 1.0, (200, -150))
    em = _n(nt, "ShaderNodeEmission", (380, 50))''', '''    # ambient occlusion in gaps and contacts
    aon = _n(nt, "ShaderNodeAmbientOcclusion", (200, 300), samples=8)
    _l(nt, gi.outputs["AODistance"], aon.inputs["Distance"])
    aof = _math(nt, "SUBTRACT", 1.0, aon.outputs["AO"], (350, 300))
    aof = _math(nt, "MULTIPLY", aof, gi.outputs["AO"], (450, 300))
    aof = _math(nt, "SUBTRACT", 1.0, aof, (550, 300))
    aoc = _n(nt, "ShaderNodeCombineColor", (650, 300))
    for i in range(3):
        _l(nt, aof, aoc.inputs[i])
    col = _mixrgb(nt, "MULTIPLY", 1.0, col, aoc.outputs[0], (700, 150))
    # rim light on the lit side of silhouettes
    lw = _n(nt, "ShaderNodeLayerWeight", (200, 500))
    lw.inputs["Blend"].default_value = 0.35
    rim = _math(nt, "POWER", lw.outputs["Facing"], 2.5, (350, 500))
    lit = _n(nt, "ShaderNodeMapRange", (350, 650), interpolation_type="SMOOTHSTEP", clamp=True)
    _l(nt, bw.outputs[0], lit.inputs["Value"])
    lit.inputs["From Min"].default_value = 0.35
    lit.inputs["From Max"].default_value = 0.95
    rim = _math(nt, "MULTIPLY", rim, lit.outputs["Result"], (500, 550))
    rim = _math(nt, "MULTIPLY", rim, gi.outputs["Rim"], (600, 550))
    rimc = _n(nt, "ShaderNodeVectorMath", (700, 550), operation="SCALE")
    _l(nt, gi.outputs["HighTint"], rimc.inputs[0])
    _l(nt, rim, rimc.inputs["Scale"])
    rimadd = _n(nt, "ShaderNodeVectorMath", (800, 300), operation="ADD")
    _l(nt, col, rimadd.inputs[0])
    _l(nt, rimc.outputs[0], rimadd.inputs[1])
    col = rimadd.outputs[0]
    aov = _n(nt, "ShaderNodeOutputAOV", (800, 700))
    aov.aov_name = "hero"
    _l(nt, gi.outputs["Hero"], aov.inputs["Value"])
    glow = _math(nt, "ADD", gi.outputs["Glow"], 1.0, (200, -150))
    em = _n(nt, "ShaderNodeEmission", (380, 50))''')

rep('''        bump=0.0, bump_dist=0.05, blend="OPAQUE", backface=True, light_tint=0.0):''', '''        bump=0.0, bump_dist=0.05, blend="OPAQUE", backface=True, light_tint=0.0, soft=None, ao=None, ao_dist=None,
        rim=None, hero=False):''')
rep('''                Glow=glow, Roughness=rough, Alpha=alpha, BumpStrength=bump, BumpDistance=bump_dist, LightTint=light_tint)''',
    '''                Glow=glow, Roughness=rough, Alpha=alpha, BumpStrength=bump, BumpDistance=bump_dist, LightTint=light_tint,
                Soft=soft, AO=ao, AODistance=ao_dist, Rim=rim, Hero=1.0 if hero else 0.0)''')

rep('''def emissive(name, color, strength=1.0, alpha=1.0):
    """Unlit glowing material (practical lights, bioluminescence). Same in both looks."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()''', '''def emissive(name, color, strength=1.0, alpha=1.0, hero=False):
    """Unlit glowing material (practical lights, bioluminescence). Same in both looks."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    if hero:
        a = _n(nt, "ShaderNodeOutputAOV", (300, 200))
        a.aov_name = "hero"
        a.inputs["Value"].default_value = 1.0''')

rep("    kuwahara=10, uniformity=4, sharpness=0.55, eccentricity=1.0,", "    kuwahara=3, uniformity=4, sharpness=0.55, eccentricity=1.0,")
rep("    saturation=1.0, vignette=0.28, grain=0.035, edge_blur=4.0, exposure=0.0,", "    saturation=1.0, vignette=0.28, grain=0.0, edge_blur=4.0, exposure=0.0,")

rep('''    comp = node("CompositorNodeComposite", 2400, 0)
    L(img, comp.inputs[0])
    return nt''', '''    comp = node("CompositorNodeComposite", 2400, 0)
    L(img, comp.inputs[0])
    aux_outputs(nt, rl)
    return nt


POS_PERIOD = (256.0, 256.0, 128.0)
POS_ZOFF = 32.0


def aux_outputs(nt, rl):
    """v3 post inputs: hero mask (AOV) and the encoded world position (fract(p / period)) at half resolution."""
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    vl.use_pass_position = True
    if "hero" not in [a.name for a in vl.aovs]:
        a = vl.aovs.add()
        a.name, a.type = "hero", "VALUE"
    sep = nt.nodes.new("CompositorNodeSeparateXYZ")
    sep.location = (1600, -1200)
    nt.links.new(rl.outputs["Position"], sep.inputs[0])
    comb = nt.nodes.new("CompositorNodeCombineXYZ")
    comb.location = (2100, -1200)
    for i, ax in enumerate("XYZ"):
        src = sep.outputs[i]
        if ax == "Z":
            off = nt.nodes.new("CompositorNodeMath")
            off.operation = "ADD"
            nt.links.new(src, off.inputs[0])
            off.inputs[1].default_value = POS_ZOFF
            src = off.outputs[0]
        dv = nt.nodes.new("CompositorNodeMath")
        dv.operation = "DIVIDE"
        nt.links.new(src, dv.inputs[0])
        dv.inputs[1].default_value = POS_PERIOD[i]
        fr = nt.nodes.new("CompositorNodeMath")
        fr.operation = "FRACT"
        nt.links.new(dv.outputs[0], fr.inputs[0])
        nt.links.new(fr.outputs[0], comb.inputs[i])
    scl = nt.nodes.new("CompositorNodeScale")
    scl.space = "RELATIVE"
    scl.location = (2300, -1200)
    try:
        scl.interpolation = "Nearest"
    except Exception:
        pass
    scl.inputs["X"].default_value = 0.5
    scl.inputs["Y"].default_value = 0.5
    nt.links.new(comb.outputs[0], scl.inputs[0])
    fo = nt.nodes.new("CompositorNodeOutputFile")
    fo.name = "AUX_POS"
    fo.location = (2500, -1200)
    fo.format.file_format = "PNG"
    fo.format.color_depth = "16"
    fo.format.color_mode = "RGB"
    fo.format.compression = 15
    fo.format.color_management = "OVERRIDE"
    fo.format.view_settings.view_transform = "Raw"
    fo.file_slots.clear()
    fo.file_slots.new("pos_")
    nt.links.new(scl.outputs[0], fo.inputs[0])
    fh = nt.nodes.new("CompositorNodeOutputFile")
    fh.name = "AUX_HERO"
    fh.location = (2500, -1400)
    fh.format.file_format = "PNG"
    fh.format.color_depth = "8"
    fh.format.color_mode = "BW"
    fh.format.compression = 15
    fh.format.color_management = "OVERRIDE"
    fh.format.view_settings.view_transform = "Raw"
    fh.file_slots.clear()
    fh.file_slots.new("hero_")
    nt.links.new(rl.outputs["hero"], fh.inputs[0])


def set_aux_dir(path):
    nt = bpy.context.scene.node_tree
    for nm in ("AUX_POS", "AUX_HERO"):
        if nt and nm in nt.nodes:
            nt.nodes[nm].base_path = path''')
open(p, "w").write(s)
print("look.py patched")
