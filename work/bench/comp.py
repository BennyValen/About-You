import bpy, sys, time, random
args = sys.argv[sys.argv.index("--") + 1:]
variant, dev = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.eevee.taa_render_samples = 16
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, 0, 40); cam.data.sensor_fit = "VERTICAL"
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.rotation_euler = (0.6, 0, -0.5)
bpy.ops.mesh.primitive_monkey_add(size=10)
sc.use_nodes = True; sc.render.compositor_device = dev
nt = sc.node_tree; nt.nodes.clear()
rl = nt.nodes.new("CompositorNodeRLayers"); comp = nt.nodes.new("CompositorNodeComposite"); last = rl.outputs[0]
if variant.startswith("kw"):
    kw = nt.nodes.new("CompositorNodeKuwahara"); kw.variation = "ANISOTROPIC" if variant == "kwa" else "CLASSIC"
    nt.links.new(last, kw.inputs[0]); last = kw.outputs[0]
if variant == "glare":
    g = nt.nodes.new("CompositorNodeGlare"); g.glare_type = "BLOOM"; nt.links.new(last, g.inputs[0]); last = g.outputs[0]
    g2 = nt.nodes.new("CompositorNodeGlare"); g2.glare_type = "STREAKS"; nt.links.new(last, g2.inputs[0]); last = g2.outputs[0]
nt.links.new(last, comp.inputs[0])
sc.render.filepath = "C:/About You/work/bench/comp.png"
for i in range(3):
    t = time.time(); sc.frame_set(1 + i); bpy.ops.render.render(write_still=True); print(f"COMP {variant} {dev} {i}: {time.time()-t:.2f}s", flush=True)
