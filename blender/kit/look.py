"""The look pass: cel surfaces, ink, and the cinematic compositor layer, switchable in one place.

look = "cel"   : 3-step toon (Shader-to-RGB + constant bands), painterly brush modulation, Kuwahara paint
                 filter, pass-based tinted ink + Freestyle hero ink with line boil, bloom/streaks/CA/grade/
                 vignette/grain.
look = "photo" : the same scenes rendered through Principled BSDF, no ink, no paint filter (grade kept).
Every material goes through the shared node group "CelSurface"; its internal Value node "LOOK"
(0 = cel, 1 = photo) flips all materials at once.
"""
import bpy, math
from .core import hexc

# ------------------------------------------------------------------ helpers
def _n(nt, kind, loc=(0, 0), **props):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def _l(nt, a, b):
    nt.links.new(a, b)


def _math(nt, op, a=None, b=None, loc=(0, 0), clamp=False):
    n = _n(nt, "ShaderNodeMath", loc, operation=op, use_clamp=clamp)
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            _l(nt, v, n.inputs[i])
    return n.outputs[0]


def _mixrgb(nt, blend, fac, a, b, loc=(0, 0)):
    n = _n(nt, "ShaderNodeMix", loc, data_type="RGBA", blend_type=blend)
    for sock, v in ((n.inputs[0], fac), (n.inputs[6], a), (n.inputs[7], b)):
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, tuple):
            sock.default_value = v
        else:
            _l(nt, v, sock)
    return n.outputs[2]


# ------------------------------------------------------------------ cel surface group
def cel_group():
    g = bpy.data.node_groups.get("CelSurface")
    if g:
        return g
    g = bpy.data.node_groups.new("CelSurface", "ShaderNodeTree")
    it = g.interface
    def sin(name, typ, default=None, mn=None, mx=None):
        s = it.new_socket(name, in_out="INPUT", socket_type=typ)
        if default is not None:
            s.default_value = default
        if mn is not None:
            s.min_value = mn
        if mx is not None:
            s.max_value = mx
        return s
    sin("Base", "NodeSocketColor", (0.5, 0.5, 0.5, 1))
    sin("ShadowTint", "NodeSocketColor", (0.55, 0.55, 0.72, 1))
    sin("HighTint", "NodeSocketColor", (1.12, 1.1, 1.04, 1))
    sin("T1", "NodeSocketFloat", 0.42)
    sin("T2", "NodeSocketFloat", 0.95)
    sin("Paint", "NodeSocketFloat", 0.1)
    sin("PaintScale", "NodeSocketFloat", 3.0)
    sin("Glow", "NodeSocketFloat", 0.0)
    sin("Roughness", "NodeSocketFloat", 0.6)
    sin("Alpha", "NodeSocketFloat", 1.0, 0.0, 1.0)
    sin("Height", "NodeSocketFloat", 0.0)
    sin("BumpStrength", "NodeSocketFloat", 0.0)
    sin("BumpDistance", "NodeSocketFloat", 0.05)
    sin("LightTint", "NodeSocketFloat", 0.0, 0.0, 1.0)
    sin("Soft", "NodeSocketFloat", 0.2, 0.0, 1.0)
    sin("AO", "NodeSocketFloat", 0.6, 0.0, 1.0)
    sin("AODistance", "NodeSocketFloat", 0.6)
    sin("Rim", "NodeSocketFloat", 0.0)
    sin("Hero", "NodeSocketFloat", 0.0, 0.0, 1.0)
    it.new_socket("Shader", in_out="OUTPUT", socket_type="NodeSocketShader")
    nt = g
    gi = _n(nt, "NodeGroupInput", (-1400, 0))
    go = _n(nt, "NodeGroupOutput", (900, 0))
    look = _n(nt, "ShaderNodeValue", (300, 400), name="LOOK", label="LOOK 0=cel 1=photo")
    look.outputs[0].default_value = 0.0
    bump = _n(nt, "ShaderNodeBump", (-1150, -300))
    _l(nt, gi.outputs["BumpStrength"], bump.inputs["Strength"])
    _l(nt, gi.outputs["BumpDistance"], bump.inputs["Distance"])
    _l(nt, gi.outputs["Height"], bump.inputs["Height"])
    diff = _n(nt, "ShaderNodeBsdfDiffuse", (-950, -200))
    diff.inputs[0].default_value = (1, 1, 1, 1)
    _l(nt, bump.outputs[0], diff.inputs["Normal"])
    s2r = _n(nt, "ShaderNodeShaderToRGB", (-780, -200))
    _l(nt, diff.outputs[0], s2r.inputs[0])
    bw = _n(nt, "ShaderNodeRGBToBW", (-620, -200))
    _l(nt, s2r.outputs[0], bw.inputs[0])
    def band(t_sock, y):
        # v3: soft painted shading; Soft = half width of the shadow/highlight transitions (0.035 = old hard cel)
        lo = _math(nt, "SUBTRACT", t_sock, gi.outputs["Soft"], (-620, y))
        hi = _math(nt, "ADD", t_sock, gi.outputs["Soft"], (-620, y - 60))
        mr = _n(nt, "ShaderNodeMapRange", (-450, y), interpolation_type="SMOOTHSTEP", clamp=True)
        _l(nt, bw.outputs[0], mr.inputs["Value"])
        _l(nt, lo, mr.inputs["From Min"])
        _l(nt, hi, mr.inputs["From Max"])
        return mr.outputs["Result"]
    s1 = band(gi.outputs["T1"], -350)
    s2 = band(gi.outputs["T2"], -500)
    # painterly brush modulation in world space (painted backgrounds stay fixed to the world)
    geo = _n(nt, "ShaderNodeNewGeometry", (-1150, 300))
    noi = _n(nt, "ShaderNodeTexNoise", (-950, 300), noise_dimensions="4D")
    drw = _n(nt, "ShaderNodeValue", (-1150, 450), name="DRAWING", label="drawing index (on twos)")
    drw.outputs[0].default_value = 0.0
    bst = _n(nt, "ShaderNodeValue", (-1150, 550), name="BOIL", label="paint boil per drawing")
    bst.outputs[0].default_value = 0.0
    _l(nt, _math(nt, "MULTIPLY", drw.outputs[0], bst.outputs[0], (-1050, 500)), noi.inputs["W"])
    noi.inputs["Detail"].default_value = 4.0
    noi.inputs["Distortion"].default_value = 2.2
    noi.inputs["Roughness"].default_value = 0.6
    mp = _n(nt, "ShaderNodeMapping", (-1050, 300))
    _l(nt, geo.outputs["Position"], mp.inputs[0])
    mp.inputs["Scale"].default_value = (1.0, 0.35, 1.0)
    mp.inputs["Rotation"].default_value = (0, 0, 0.6)
    _l(nt, mp.outputs[0], noi.inputs["Vector"])
    _l(nt, gi.outputs["PaintScale"], noi.inputs["Scale"])
    v = _math(nt, "SUBTRACT", noi.outputs["Fac"], 0.5, (-780, 300))
    v = _math(nt, "MULTIPLY", v, gi.outputs["Paint"], (-640, 300))
    v = _math(nt, "MULTIPLY", v, 2.0, (-520, 300))
    pf = _math(nt, "ADD", v, 1.0, (-400, 300))
    base = gi.outputs["Base"]
    c_sh = _mixrgb(nt, "MULTIPLY", 1.0, base, gi.outputs["ShadowTint"], (-300, 100))
    c_hi = _mixrgb(nt, "MULTIPLY", 1.0, base, gi.outputs["HighTint"], (-300, -50))
    col = _mixrgb(nt, "MIX", s1, c_sh, base, (-100, 50))
    col = _mixrgb(nt, "MIX", s2, col, c_hi, (60, 50))
    pfc = _n(nt, "ShaderNodeCombineColor", (-250, 300))
    for i in range(3):
        _l(nt, pf, pfc.inputs[i])
    col = _mixrgb(nt, "MULTIPLY", 1.0, col, pfc.outputs[0], (200, 50))
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
    _l(nt, tint, glowc.inputs[0])
    _l(nt, _math(nt, "MULTIPLY", over, 0.35, (0, -1000)), glowc.inputs["Scale"])
    addg = _n(nt, "ShaderNodeVectorMath", (400, -300), operation="ADD")
    _l(nt, col, addg.inputs[0])
    _l(nt, glowc.outputs[0], addg.inputs[1])
    col = addg.outputs[0]
    # ambient occlusion in gaps and contacts
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
    em = _n(nt, "ShaderNodeEmission", (380, 50))
    _l(nt, col, em.inputs["Color"])
    _l(nt, glow, em.inputs["Strength"])
    pr = _n(nt, "ShaderNodeBsdfPrincipled", (380, -250))
    _l(nt, base, pr.inputs["Base Color"])
    _l(nt, gi.outputs["Roughness"], pr.inputs["Roughness"])
    _l(nt, bump.outputs[0], pr.inputs["Normal"])
    _l(nt, base, pr.inputs["Emission Color"])
    _l(nt, gi.outputs["Glow"], pr.inputs["Emission Strength"])
    mix = _n(nt, "ShaderNodeMixShader", (600, 0))
    _l(nt, look.outputs[0], mix.inputs[0])
    _l(nt, em.outputs[0], mix.inputs[1])
    _l(nt, pr.outputs[0], mix.inputs[2])
    tr = _n(nt, "ShaderNodeBsdfTransparent", (600, -200))
    am = _n(nt, "ShaderNodeMixShader", (760, 0))
    _l(nt, gi.outputs["Alpha"], am.inputs[0])
    _l(nt, tr.outputs[0], am.inputs[1])
    _l(nt, mix.outputs[0], am.inputs[2])
    _l(nt, am.outputs[0], go.inputs[0])
    return g


def set_drawing(index, boil=None):
    """advance the painterly texture boil (the paint re-draws every drawing, like the original)"""
    g = cel_group()
    g.nodes["DRAWING"].outputs[0].default_value = float(index)
    if boil is not None:
        g.nodes["BOIL"].outputs[0].default_value = float(boil)


def set_look(mode):
    g = cel_group()
    g.nodes["LOOK"].outputs[0].default_value = 1.0 if mode == "photo" else 0.0


def cel(name, base, shadow=(0.55, 0.55, 0.72, 1), high=(1.12, 1.1, 1.04, 1), t1=0.42, t2=0.95, paint=0.1,
        paint_scale=3.0, glow=0.0, rough=0.6, line=None, alpha=1.0, base_node=None, height_node=None,
        bump=0.0, bump_dist=0.05, blend="OPAQUE", backface=True, light_tint=0.0, soft=None, ao=None, ao_dist=None,
        rim=None, hero=False):
    """A cel material. base_node(nt) -> socket may replace the flat base colour (textures, palettes)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial", (500, 0))
    grp = _n(nt, "ShaderNodeGroup", (250, 0))
    grp.node_tree = cel_group()
    vals = dict(Base=base, ShadowTint=shadow, HighTint=high, T1=t1, T2=t2, Paint=paint, PaintScale=paint_scale,
                Glow=glow, Roughness=rough, Alpha=alpha, BumpStrength=bump, BumpDistance=bump_dist, LightTint=light_tint,
                Soft=soft, AO=ao, AODistance=ao_dist, Rim=rim, Hero=1.0 if hero else 0.0)
    for k, v in vals.items():
        if v is not None:
            grp.inputs[k].default_value = v
    if base_node is not None:
        _l(nt, base_node(nt), grp.inputs["Base"])
    if height_node is not None:
        _l(nt, height_node(nt), grp.inputs["Height"])
    _l(nt, grp.outputs[0], out.inputs[0])
    if alpha < 1.0 or blend != "OPAQUE":
        m.surface_render_method = "BLENDED"
    m.use_backface_culling = not backface
    lc = line if line is not None else (base[0] * 0.42 + 0.01, base[1] * 0.38 + 0.01, base[2] * 0.48 + 0.02, 1)
    m.line_color = lc
    m.diffuse_color = base
    return m


def instancer_palette(colors, attr="tint"):
    """base_node factory: picks a palette colour per instance from a float attribute in [0,1)."""
    def build(nt):
        at = _n(nt, "ShaderNodeAttribute", (-500, 0), attribute_type="INSTANCER", attribute_name=attr)
        ramp = _n(nt, "ShaderNodeValToRGB", (-300, 0))
        cr = ramp.color_ramp
        cr.interpolation = "CONSTANT"
        n = len(colors)
        while len(cr.elements) < n:
            cr.elements.new(0.5)
        for i, c in enumerate(colors):
            cr.elements[i].position = i / n
            cr.elements[i].color = c
        _l(nt, at.outputs["Fac"], ramp.inputs[0])
        return ramp.outputs[0]
    return build


def emissive(name, color, strength=1.0, alpha=1.0, hero=False):
    """Unlit glowing material (practical lights, bioluminescence). Same in both looks."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    if hero:
        a = _n(nt, "ShaderNodeOutputAOV", (300, 200))
        a.aov_name = "hero"
        a.inputs["Value"].default_value = 1.0
    out = _n(nt, "ShaderNodeOutputMaterial", (300, 0))
    em = _n(nt, "ShaderNodeEmission", (0, 0))
    em.inputs[0].default_value = color
    em.inputs[1].default_value = strength
    if alpha < 1:
        tr = _n(nt, "ShaderNodeBsdfTransparent", (0, -150))
        mx = _n(nt, "ShaderNodeMixShader", (150, 0))
        mx.inputs[0].default_value = alpha
        _l(nt, tr.outputs[0], mx.inputs[1])
        _l(nt, em.outputs[0], mx.inputs[2])
        _l(nt, mx.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
    else:
        _l(nt, em.outputs[0], out.inputs[0])
    m.line_color = (color[0] * 0.3, color[1] * 0.3, color[2] * 0.3, 1)
    return m


# ------------------------------------------------------------------ freestyle hero ink
def freestyle(ink_coll, thickness=2.4, res_scale=1.0, crease=134.0):
    sc = bpy.context.scene
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = 1.0
    # Freestyle builds its view map from every object in the view layer, which is very slow with large
    # environments. The hero ink is therefore computed on a separate view layer that contains only the
    # INK collection; occlusion by the environment is restored in the compositor with a depth test.
    main = sc.view_layers[0]
    main.use_freestyle = False
    vl = sc.view_layers.get("INKLAYER") or sc.view_layers.new("INKLAYER")
    vl.use_freestyle = True
    vl.use_pass_z = True
    for lc in vl.layer_collection.children:
        lc.exclude = lc.collection.name != ink_coll.name
    fs = vl.freestyle_settings
    fs.as_render_pass = True
    fs.crease_angle = math.radians(crease)
    for l in list(fs.linesets):
        fs.linesets.remove(l)
    ls = fs.linesets.new("hero_ink")
    ls.select_by_visibility = True
    ls.select_by_edge_types = True
    ls.select_by_collection = True
    ls.collection = ink_coll
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.select_external_contour = True
    st = bpy.data.linestyles.new("ink")
    ls.linestyle = st
    st.thickness = thickness * res_scale
    st.thickness_position = "CENTER"
    st.use_chaining = True
    st.chaining = "PLAIN"
    st.caps = "ROUND"
    st.color = (0.1, 0.08, 0.12)
    cm = st.color_modifiers.new("mat", "MATERIAL")
    cm.material_attribute = "LINE"
    cm.blend = "MIX"
    cm.influence = 1.0
    tk = st.thickness_modifiers.new("taper", "ALONG_STROKE")
    tk.mapping = "CURVE"
    tk.value_min, tk.value_max = 0.25, 1.15
    c = tk.curve.curves[0]
    c.points[0].location = (0.0, 0.0)
    c.points[1].location = (1.0, 0.0)
    c.points.new(0.15, 0.85)
    c.points.new(0.5, 1.0)
    c.points.new(0.85, 0.8)
    tk.curve.update()
    tn = st.thickness_modifiers.new("wobble", "NOISE")
    tn.amplitude = 0.9 * res_scale
    tn.period = 18.0 * res_scale
    st.geometry_modifiers.new("samp", "SAMPLING").sampling = 2.0
    pn = st.geometry_modifiers.new("boil", "PERLIN_NOISE_1D")
    pn.frequency = 12.0
    pn.amplitude = 1.1 * res_scale
    pn.octaves = 2
    return st


def boil(linestyle, drawing_index):
    """Line boil: new noise seed for every drawing (on twos)."""
    if linestyle is None:
        return
    for m in linestyle.geometry_modifiers:
        if m.type == "PERLIN_NOISE_1D":
            m.seed = 101 + int(drawing_index) * 7


# ------------------------------------------------------------------ compositor
DEFAULT_POST = dict(
    kuwahara=3, uniformity=4, sharpness=0.55, eccentricity=1.0,
    ink=0.75, ink_normal=(0.25, 0.9), ink_depth=(0.04, 0.25), ink_color=(0.34, 0.31, 0.42),
    bloom=0.55, bloom_threshold=0.85, bloom_size=0.62,
    streak=0.18, streak_threshold=1.15,
    ca=0.006, lift=(0.985, 1.0, 1.03), gamma=(1.0, 1.0, 1.0), gain=(1.035, 1.0, 0.965),
    saturation=1.0, vignette=0.28, grain=0.0, edge_blur=4.0, exposure=0.0,
)


def compositor(params=None, res_scale=1.0, mode="cel", freestyle_on=True):
    p = dict(DEFAULT_POST)
    p.update(params or {})
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    vl.use_pass_normal = True
    vl.use_pass_z = True
    sc.use_nodes = True
    nt = sc.node_tree
    nt.nodes.clear()
    L = lambda a, b: nt.links.new(a, b)
    def node(kind, x, y, **kw):
        n = nt.nodes.new(kind)
        n.location = (x, y)
        for k, v in kw.items():
            setattr(n, k, v)
        return n
    def inp(n, name, v):
        n.inputs[name].default_value = v
    rl = node("CompositorNodeRLayers", -1600, 0)
    img = rl.outputs["Image"]
    cel_mode = mode == "cel"
    if cel_mode and p["kuwahara"] > 0:
        kw = node("CompositorNodeKuwahara", -1350, 200, variation="ANISOTROPIC")
        inp(kw, "Size", max(2, int(round(p["kuwahara"] * res_scale))))
        inp(kw, "Uniformity", int(p["uniformity"]))
        inp(kw, "Sharpness", p["sharpness"])
        inp(kw, "Eccentricity", p["eccentricity"])
        L(img, kw.inputs["Image"])
        img = kw.outputs[0]
    if cel_mode and p["ink"] > 0:
        # tinted ink from geometry passes: normal creases and depth jumps -> darker tint of the colour below
        sn = node("CompositorNodeFilter", -1350, -200, filter_type="SOBEL")
        L(rl.outputs["Normal"], sn.inputs["Image"])
        bn = node("CompositorNodeRGBToBW", -1180, -200)
        L(sn.outputs[0], bn.inputs[0])
        mn = node("CompositorNodeMapRange", -1020, -200, use_clamp=True)
        L(bn.outputs[0], mn.inputs[0])
        inp(mn, "From Min", p["ink_normal"][0]); inp(mn, "From Max", p["ink_normal"][1])
        dz = node("CompositorNodeMath", -1350, -400, operation="LOGARITHM")
        L(rl.outputs["Depth"], dz.inputs[0]); inp(dz, 1, 2.718)
        sd = node("CompositorNodeFilter", -1180, -400, filter_type="SOBEL")
        L(dz.outputs[0], sd.inputs["Image"])
        bd = node("CompositorNodeRGBToBW", -1020, -400)
        L(sd.outputs[0], bd.inputs[0])
        md = node("CompositorNodeMapRange", -860, -400, use_clamp=True)
        L(bd.outputs[0], md.inputs[0])
        inp(md, "From Min", p["ink_depth"][0]); inp(md, "From Max", p["ink_depth"][1])
        mx = node("CompositorNodeMath", -700, -300, operation="MAXIMUM")
        L(mn.outputs[0], mx.inputs[0]); L(md.outputs[0], mx.inputs[1])
        sm = node("CompositorNodeMath", -560, -300, operation="MULTIPLY")
        L(mx.outputs[0], sm.inputs[0]); inp(sm, 1, p["ink"])
        ink = node("CompositorNodeMixRGB", -400, 0, blend_type="MULTIPLY")
        L(sm.outputs[0], ink.inputs[0]); L(img, ink.inputs[1])
        ink.inputs[2].default_value = (*p["ink_color"], 1)
        img = ink.outputs[0]
    if cel_mode and freestyle_on and sc.render.use_freestyle and "INKLAYER" in sc.view_layers:
        ri = node("CompositorNodeRLayers", -1600, -700)
        ri.layer = "INKLAYER"
        # hero pixels hidden behind environment geometry (main depth closer than ink-layer depth)
        dz = node("CompositorNodeMath", -1350, -800, operation="SUBTRACT")
        L(ri.outputs["Depth"], dz.inputs[0]); L(rl.outputs["Depth"], dz.inputs[1])
        occ = node("CompositorNodeMath", -1200, -800, operation="GREATER_THAN")
        L(dz.outputs[0], occ.inputs[0]); occ.inputs[1].default_value = 0.08
        cov = node("CompositorNodeMath", -1200, -950, operation="GREATER_THAN")
        L(ri.outputs["Alpha"], cov.inputs[0]); cov.inputs[1].default_value = 0.5
        oc = node("CompositorNodeMath", -1050, -850, operation="MULTIPLY")
        L(occ.outputs[0], oc.inputs[0]); L(cov.outputs[0], oc.inputs[1])
        dil = node("CompositorNodeDilateErode", -900, -850, mode="DISTANCE")
        dil.distance = max(2, int(round(4 * res_scale)))
        L(oc.outputs[0], dil.inputs[0])
        keep = node("CompositorNodeMath", -750, -850, operation="SUBTRACT")
        keep.inputs[0].default_value = 1.0; L(dil.outputs[0], keep.inputs[1])
        sa = node("CompositorNodeSetAlpha", -600, -700, mode="APPLY")
        L(ri.outputs["Freestyle"], sa.inputs["Image"]); L(keep.outputs[0], sa.inputs["Alpha"])
        ao = node("CompositorNodeAlphaOver", -250, 0)
        L(img, ao.inputs[1]); L(sa.outputs[0], ao.inputs[2])
        img = ao.outputs[0]
    if p["exposure"]:
        ex = node("CompositorNodeExposure", -150, 0)
        L(img, ex.inputs[0]); inp(ex, "Exposure", p["exposure"])
        img = ex.outputs[0]
    if p["bloom"] > 0:
        gb = node("CompositorNodeGlare", 0, 0, glare_type="BLOOM")
        L(img, gb.inputs["Image"])
        inp(gb, "Threshold", p["bloom_threshold"]); inp(gb, "Strength", p["bloom"]); inp(gb, "Size", p["bloom_size"])
        img = gb.outputs[0]
    if p["streak"] > 0:
        gs = node("CompositorNodeGlare", 180, 0, glare_type="STREAKS")
        L(img, gs.inputs["Image"])
        inp(gs, "Threshold", p["streak_threshold"]); inp(gs, "Strength", p["streak"])
        inp(gs, "Streaks", 2); inp(gs, "Streaks Angle", 0.0); inp(gs, "Fade", 0.92)
        img = gs.outputs[0]
    # analytic masks from image coordinates (no large blurs)
    ic = node("CompositorNodeImageCoordinates", 200, -500)
    L(img, ic.inputs[0])
    sx = node("CompositorNodeSeparateXYZ", 360, -500)
    L(ic.outputs["Normalized"], sx.inputs[0])
    def centred(sock, y):
        a1 = node("CompositorNodeMath", 520, y, operation="SUBTRACT"); L(sock, a1.inputs[0]); a1.inputs[1].default_value = 0.5
        a2 = node("CompositorNodeMath", 660, y, operation="MULTIPLY"); L(a1.outputs[0], a2.inputs[0]); a2.inputs[1].default_value = 2.0
        a3 = node("CompositorNodeMath", 800, y, operation="ABSOLUTE"); L(a2.outputs[0], a3.inputs[0])
        return a3.outputs[0]
    cu, cv = centred(sx.outputs["X"], -480), centred(sx.outputs["Y"], -600)
    def ramp(sock, lo, hi, y):
        m = node("CompositorNodeMapRange", 960, y, use_clamp=True)
        L(sock, m.inputs[0]); m.inputs["From Min"].default_value = lo; m.inputs["From Max"].default_value = hi
        q = node("CompositorNodeMath", 1100, y, operation="MULTIPLY"); L(m.outputs[0], q.inputs[0]); L(m.outputs[0], q.inputs[1])
        return q.outputs[0]
    if p["edge_blur"] > 0:
        bl = node("CompositorNodeBlur", 360, -200, filter_type="FAST_GAUSS")
        bl.size_x = bl.size_y = max(1, int(p["edge_blur"] * res_scale))
        L(img, bl.inputs[0])
        my = ramp(cv, 0.8, 1.0, -720)
        mxm = ramp(cu, 0.85, 1.0, -840)
        mm = node("CompositorNodeMath", 1240, -760, operation="ADD", use_clamp=True); L(my, mm.inputs[0]); L(mxm, mm.inputs[1])
        mb = node("CompositorNodeMixRGB", 1300, -100)
        L(mm.outputs[0], mb.inputs[0]); L(img, mb.inputs[1]); L(bl.outputs[0], mb.inputs[2])
        img = mb.outputs[0]
    if p["ca"] > 0:
        ld = node("CompositorNodeLensdist", 980, 0)
        L(img, ld.inputs["Image"]); inp(ld, "Dispersion", p["ca"]); inp(ld, "Fit", True)
        img = ld.outputs[0]
    cb = node("CompositorNodeColorBalance", 1140, 0, correction_method="LIFT_GAMMA_GAIN")
    cb.lift = p["lift"]; cb.gamma = p["gamma"]; cb.gain = p["gain"]
    L(img, cb.inputs["Image"])
    img = cb.outputs[0]
    if p["saturation"] != 1.0:
        hs = node("CompositorNodeHueSat", 1260, 0)
        L(img, hs.inputs["Image"]); inp(hs, "Saturation", p["saturation"])
        img = hs.outputs[0]
    if p["vignette"] > 0:
        u2 = node("CompositorNodeMath", 1500, -500, operation="MULTIPLY"); L(cu, u2.inputs[0]); L(cu, u2.inputs[1])
        vv0 = node("CompositorNodeMath", 1500, -620, operation="MULTIPLY"); L(cv, vv0.inputs[0]); vv0.inputs[1].default_value = 0.92
        v2 = node("CompositorNodeMath", 1640, -620, operation="MULTIPLY"); L(vv0.outputs[0], v2.inputs[0]); L(vv0.outputs[0], v2.inputs[1])
        r2 = node("CompositorNodeMath", 1780, -560, operation="ADD"); L(u2.outputs[0], r2.inputs[0]); L(v2.outputs[0], r2.inputs[1])
        rr = node("CompositorNodeMath", 1920, -560, operation="SQRT"); L(r2.outputs[0], rr.inputs[0])
        w = ramp(rr.outputs[0], 0.45, 1.45, -560)
        vm = node("CompositorNodeMapRange", 2060, -560, use_clamp=True)
        L(w, vm.inputs[0]); vm.inputs["To Min"].default_value = 1.0; vm.inputs["To Max"].default_value = 1.0 - p["vignette"]
        vv = node("CompositorNodeMixRGB", 2200, 0, blend_type="MULTIPLY")
        vv.inputs[0].default_value = 1.0
        L(img, vv.inputs[1]); L(vm.outputs[0], vv.inputs[2])
        img = vv.outputs[0]
    if p["grain"] > 0:
        tex = bpy.data.textures.get("grain") or bpy.data.textures.new("grain", "CLOUDS")
        tex.noise_scale = 0.0012
        tex.noise_depth = 0
        tex.noise_basis = "BLENDER_ORIGINAL"
        tn = node("CompositorNodeTexture", 1760, -300, name="GRAIN")
        tn.texture = tex
        gm = node("CompositorNodeMath", 1920, -300, operation="SUBTRACT")
        L(tn.outputs["Value"], gm.inputs[0]); inp(gm, 1, 0.5)
        gk = node("CompositorNodeMath", 2060, -300, operation="MULTIPLY")
        L(gm.outputs[0], gk.inputs[0]); inp(gk, 1, p["grain"] * 2)
        ga = node("CompositorNodeMixRGB", 2200, 0, blend_type="ADD")
        ga.inputs[0].default_value = 1.0
        L(img, ga.inputs[1]); L(gk.outputs[0], ga.inputs[2])
        img = ga.outputs[0]
    comp = node("CompositorNodeComposite", 2400, 0)
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
            nt.nodes[nm].base_path = path


def grain_seed(drawing_index):
    sc = bpy.context.scene
    if sc.node_tree and "GRAIN" in sc.node_tree.nodes:
        t = sc.node_tree.nodes["GRAIN"]
        k = drawing_index * 0.6180339
        t.inputs["Offset"].default_value = ((k * 7.31) % 1.0 * 50, (k * 3.77) % 1.0 * 50, 0)


# ------------------------------------------------------------------ CC0 textures (assets/textures, see CREDITS.md)
def _tex_path(asset, m):
    import os
    from .core import ROOT
    d = os.path.join(ROOT, "assets", "textures", asset)
    for ext in (".jpg", ".png"):
        p = os.path.join(d, m + ext)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"{asset}/{m}")


def tex_image(nt, asset, m, size_m=2.0, loc=(-1600, 0), coord=None, rot=0.0, noncolor=False):
    """image texture sampled in world XY (size_m metres per tile); returns the image node"""
    img = bpy.data.images.load(_tex_path(asset, m), check_existing=True)
    if noncolor:
        img.colorspace_settings.name = "Non-Color"
    if coord is None:
        g = _n(nt, "ShaderNodeNewGeometry", (loc[0] - 400, loc[1]))
        coord = g.outputs["Position"]
    mp = _n(nt, "ShaderNodeMapping", (loc[0] - 200, loc[1]))
    _l(nt, coord, mp.inputs[0])
    mp.inputs["Scale"].default_value = (1.0 / size_m, 1.0 / size_m, 1.0 / size_m)
    mp.inputs["Rotation"].default_value = (0, 0, rot)
    tx = _n(nt, "ShaderNodeTexImage", loc)
    tx.image = img
    tx.extension = "REPEAT"
    tx.interpolation = "Cubic"
    _l(nt, mp.outputs[0], tx.inputs["Vector"])
    return tx


def tex_value_detail(nt, asset, size_m=2.0, amount=0.35, loc=(-1600, 0), coord=None, rot=0.0):
    """multiplier around 1.0 from the texture's luminance (fine material detail in the scene palette)"""
    tx = tex_image(nt, asset, "diffuse", size_m, loc, coord, rot)
    bw = _n(nt, "ShaderNodeRGBToBW", (loc[0] + 200, loc[1]))
    _l(nt, tx.outputs["Color"], bw.inputs[0])
    # normalise around the texture's typical mid value
    v = _math(nt, "SUBTRACT", bw.outputs[0], 0.35, (loc[0] + 350, loc[1]))
    v = _math(nt, "MULTIPLY", v, amount * 2.0, (loc[0] + 480, loc[1]))
    return _math(nt, "ADD", v, 1.0, (loc[0] + 600, loc[1]))


def tex_height(nt, asset, size_m=2.0, loc=(-1600, -400), coord=None, rot=0.0, m="displacement"):
    """height socket from a displacement map (or the diffuse luminance if no displacement map)"""
    try:
        tx = tex_image(nt, asset, m, size_m, loc, coord, rot, noncolor=True)
        return tx.outputs["Color"]
    except FileNotFoundError:
        tx = tex_image(nt, asset, "diffuse", size_m, loc, coord, rot)
        bw = _n(nt, "ShaderNodeRGBToBW", (loc[0] + 200, loc[1]))
        _l(nt, tx.outputs["Color"], bw.inputs[0])
        return bw.outputs[0]


def mul_color(nt, col, fac, loc=(0, 0)):
    """colour * scalar socket"""
    vm = _n(nt, "ShaderNodeVectorMath", loc, operation="SCALE")
    if isinstance(col, tuple):
        vm.inputs[0].default_value = col[:3]
    else:
        _l(nt, col, vm.inputs[0])
    if isinstance(fac, (int, float)):
        vm.inputs["Scale"].default_value = fac
    else:
        _l(nt, fac, vm.inputs["Scale"])
    return vm.outputs[0]


def add_mask_aov(material, name):
    """write value 1 to a named AOV from this material (a per-object mask, e.g. the manta for its continuity gate)"""
    nt = material.node_tree
    a = _n(nt, "ShaderNodeOutputAOV", (300, 300))
    a.aov_name = name
    a.inputs["Value"].default_value = 1.0


def register_mask_output(name):
    """add a view-layer AOV and an 8-bit PNG file slot aux/<name>_NNNN.png (call after compositor())"""
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    if name not in [a.name for a in vl.aovs]:
        a = vl.aovs.add()
        a.name, a.type = name, "VALUE"
    nt = sc.node_tree
    rl = [n for n in nt.nodes if n.type == "R_LAYERS" and n.layer == vl.name][0]
    fh = nt.nodes["AUX_HERO"]
    fh.file_slots.new(f"{name}_")
    nt.links.new(rl.outputs[name], fh.inputs[f"{name}_"])
