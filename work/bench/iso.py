import bpy, sys, time, math, random
args = sys.argv[sys.argv.index("--") + 1:]
variant = args[0]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.eevee.taa_render_samples = 16
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, 0, 40); cam.data.sensor_fit = "VERTICAL"
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.rotation_euler = (0.6, 0, -0.5)
bpy.ops.mesh.primitive_plane_add(size=60); water = bpy.context.object
if variant == "ocean":
    m = water.modifiers.new("ocean", "OCEAN"); m.resolution = 12; m.spatial_size = 30
if variant in ("pads", "padsinst"):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=0.05); pad = bpy.context.object
    pad.modifiers.new("ss", "SUBSURF")
    random.seed(1)
    for i in range(350):
        o = pad.copy(); o.data = pad.data; sc.collection.objects.link(o); o.location = (random.uniform(-14, 14), random.uniform(-24, 24), 0.05)
if variant == "nomod":
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=0.05); pad = bpy.context.object
    random.seed(1)
    for i in range(350):
        o = pad.copy(); o.data = pad.data; sc.collection.objects.link(o); o.location = (random.uniform(-14, 14), random.uniform(-24, 24), 0.05)
if variant == "joined":
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=0.05); pad = bpy.context.object
    random.seed(1)
    objs = [pad]
    for i in range(350):
        o = pad.copy(); o.data = pad.data.copy(); sc.collection.objects.link(o); o.location = (random.uniform(-14, 14), random.uniform(-24, 24), 0.05); objs.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = pad; bpy.ops.object.join()
if variant == "gn":
    import numpy as np
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=0.05); pad = bpy.context.object; pad.hide_render = True
    me = bpy.data.meshes.new("pts"); random.seed(1)
    me.from_pydata([(random.uniform(-14, 14), random.uniform(-24, 24), 0.05) for i in range(350)], [], [])
    po = bpy.data.objects.new("pts", me); sc.collection.objects.link(po)
    ng = bpy.data.node_groups.new("inst", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
    iop = ng.nodes.new("GeometryNodeInstanceOnPoints"); oi = ng.nodes.new("GeometryNodeObjectInfo"); oi.inputs[0].default_value = pad
    ng.links.new(gi.outputs[0], iop.inputs["Points"]); ng.links.new(oi.outputs["Geometry"], iop.inputs["Instance"]); ng.links.new(iop.outputs[0], go.inputs[0])
    mod = po.modifiers.new("gn", "NODES"); mod.node_group = ng
if variant == "freestyle":
    sc.render.use_freestyle = True
    fs = sc.view_layers[0].freestyle_settings; ls = fs.linesets.new("ink"); ls.linestyle = bpy.data.linestyles.new("ink")
sc.render.filepath = "C:/About You/work/bench/iso.png"
for i in range(3):
    t = time.time(); sc.frame_set(1 + i); bpy.ops.render.render(write_still=True); print(f"ISO {variant} {i}: {time.time()-t:.2f}s", flush=True)
