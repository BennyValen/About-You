import bpy
sc = bpy.context.scene
sc.use_nodes = True
nt = sc.node_tree
names = [t for t in dir(bpy.types) if t.startswith("CompositorNode")]
print("COMP NODES:", " ".join(sorted(n.replace("CompositorNode", "") for n in names)))
g = nt.nodes.new("CompositorNodeGlare"); print("GLARE TYPES:", [e.identifier for e in g.bl_rna.properties["glare_type"].enum_items])
print("GLARE PROPS:", [p.identifier for p in g.bl_rna.properties if not p.is_readonly][:40])
print("GLARE INPUTS:", [i.name for i in g.inputs])
k = nt.nodes.new("CompositorNodeKuwahara"); print("KUWA INPUTS:", [i.name for i in k.inputs], [p.identifier for p in k.bl_rna.properties if not p.is_readonly][:30])
f = nt.nodes.new("CompositorNodeFilter"); print("FILTER:", [e.identifier for e in f.bl_rna.properties["filter_type"].enum_items])
cb = nt.nodes.new("CompositorNodeColorBalance"); print("CB inputs", [i.name for i in cb.inputs], [p.identifier for p in cb.bl_rna.properties if not p.is_readonly][:30])
ld = nt.nodes.new("CompositorNodeLensdist"); print("LD inputs", [i.name for i in ld.inputs])
em = nt.nodes.new("CompositorNodeEllipseMask"); print("EM inputs", [i.name for i in em.inputs])
vl = sc.view_layers[0]
vl.use_pass_normal = True; vl.use_pass_z = True; vl.use_pass_object_index = True
sc.render.use_freestyle = True; vl.freestyle_settings.as_render_pass = True
rl = nt.nodes.new("CompositorNodeRLayers"); print("RL outputs:", [o.name for o in rl.outputs if o.enabled])
me = bpy.data.meshes.new("s"); me.from_pydata([(0,0,0),(0,0,1)], [(0,1)], []); o = bpy.data.objects.new("s", me); sc.collection.objects.link(o)
m = o.modifiers.new("skin", "SKIN"); print("skin verts layers:", len(me.skin_vertices), me.skin_vertices[0].data[0].radius[:] if len(me.skin_vertices) else None)
ls = bpy.data.linestyles.new("t")
print("LS thickness mods:", [e.identifier for e in bpy.types.LineStyleThicknessModifier.bl_rna.properties["type"].enum_items])
print("LS geom mods:", [e.identifier for e in bpy.types.LineStyleGeometryModifier.bl_rna.properties["type"].enum_items])
print("LS color mods:", [e.identifier for e in bpy.types.LineStyleColorModifier.bl_rna.properties["type"].enum_items])
print("EEVEE props:", [p.identifier for p in sc.eevee.bl_rna.properties if not p.is_readonly])
