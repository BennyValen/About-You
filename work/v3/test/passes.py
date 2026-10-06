import bpy
bpy.ops.wm.read_factory_settings(use_empty=False)
sc=bpy.context.scene
sc.render.engine="BLENDER_EEVEE_NEXT"
vl=sc.view_layers[0]
print("PASSPROPS", [p for p in dir(vl) if p.startswith("use_pass")])
print("EEVEE props", [p for p in dir(vl.eevee) if p.startswith("use_pass")])
# AOV inside group test
mat=bpy.data.materials.new("m"); mat.use_nodes=True
g=bpy.data.node_groups.new("G","ShaderNodeTree")
try:
    n=g.nodes.new("ShaderNodeOutputAOV"); n.aov_name="hero"; print("AOV in group node created OK")
except Exception as e: print("AOV group fail", e)
