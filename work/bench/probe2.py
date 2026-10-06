import bpy
sc = bpy.context.scene; sc.use_nodes = True; nt = sc.node_tree
n = nt.nodes.new("CompositorNodeImageCoordinates"); print("IC inputs", [i.name for i in n.inputs], "outputs", [o.name for o in n.outputs])
n = nt.nodes.new("CompositorNodeSeparateXYZ"); print("SXYZ", [i.name for i in n.inputs], [o.name for o in n.outputs])
n = nt.nodes.new("CompositorNodeMath"); print("MATH ops ok")
n = nt.nodes.new("CompositorNodeTexture"); print("TEX", [i.name for i in n.inputs], [o.name for o in n.outputs])
n = nt.nodes.new("CompositorNodeDisplace"); print("DISP", [i.name for i in n.inputs])
