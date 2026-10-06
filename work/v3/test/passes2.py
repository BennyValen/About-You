import bpy, os
bpy.ops.wm.read_factory_settings(use_empty=False)
sc=bpy.context.scene
sc.render.engine="BLENDER_EEVEE_NEXT"
sc.render.resolution_x=sc.render.resolution_y=128
vl=sc.view_layers[0]
vl.use_pass_position=True; vl.use_pass_object_index=True; vl.use_pass_shadow=True
aov=vl.aovs.add(); aov.name="hero"; aov.type="VALUE"
cube=bpy.data.objects["Cube"]; cube.pass_index=3
# material with AOV inside a group
mat=bpy.data.materials.new("m"); mat.use_nodes=True
g=bpy.data.node_groups.new("G","ShaderNodeTree")
gi=g.nodes.new("NodeGroupInput"); g.interface.new_socket("H",in_out="INPUT",socket_type="NodeSocketFloat")
a=g.nodes.new("ShaderNodeOutputAOV"); a.aov_name="hero"; g.links.new(gi.outputs[0],a.inputs["Value"])
gn=mat.node_tree.nodes.new("ShaderNodeGroup"); gn.node_tree=g; gn.inputs[0].default_value=0.7
cube.data.materials[0]=mat
a2=mat.node_tree.nodes.new("ShaderNodeOutputAOV"); a2.aov_name="hero2"; a2.inputs["Value"].default_value=0.4
aov2=vl.aovs.add(); aov2.name="hero2"; aov2.type="VALUE"
sc.use_nodes=True
sc.view_settings.view_transform="Standard"
nt=sc.node_tree
rl=nt.nodes["Render Layers"]
print("RL outputs", [o.name for o in rl.outputs if o.enabled])
fo=nt.nodes.new("CompositorNodeOutputFile"); fo.base_path=os.path.abspath("work/v3/test/out"); fo.format.file_format="PNG"; fo.format.color_depth="16"; fo.format.color_mode="RGB"
try:
    fo.format.color_management="OVERRIDE"; fo.format.view_settings.view_transform="Raw"; print("override ok")
except Exception as e: print("override fail", e)
fo.file_slots.clear()
sep=nt.nodes.new("CompositorNodeSeparateXYZ"); nt.links.new(rl.outputs["Position"], sep.inputs[0])
comb=nt.nodes.new("CompositorNodeCombineXYZ")
for i,ax in enumerate("XYZ"):
    m=nt.nodes.new("CompositorNodeMath"); m.operation="MULTIPLY_ADD"; m.inputs[1].default_value=0.1; m.inputs[2].default_value=0.5
    nt.links.new(sep.outputs[i], m.inputs[0]); nt.links.new(m.outputs[0], comb.inputs[i])
fo.file_slots.new("pos"); nt.links.new(comb.outputs[0], fo.inputs["pos"])
fo.file_slots.new("hero"); nt.links.new(rl.outputs["hero"], fo.inputs["hero"])
fo.file_slots.new("hero2"); nt.links.new(rl.outputs["hero2"], fo.inputs["hero2"])
sc.render.filepath=os.path.abspath("work/v3/test/out/combined.png")
bpy.ops.render.render(write_still=True)
