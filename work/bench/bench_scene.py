# Benchmark: a representative scene-3 frame (water, ~350 instanced lily pads, boat, rower, freestyle, compositor).
import bpy, sys, time, math, random
args = sys.argv[sys.argv.index("--") + 1:]
eng = args[0]; stage = args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.render.fps = 24
if eng == "EEVEE":
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.eevee.taa_render_samples = 16
    sc.eevee.use_shadows = True
else:
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices: d.use = True
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPTIX"
# camera
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.location = (0, 0, 40); cam.data.lens = 50; cam.data.sensor_fit = "VERTICAL"
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
sun.rotation_euler = (math.radians(35), 0, math.radians(-30)); sun.data.energy = 3
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
def mat(name, col):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); d = nt.nodes.new("ShaderNodeBsdfDiffuse"); d.inputs[0].default_value = (*col, 1)
    if eng == "EEVEE":
        s2r = nt.nodes.new("ShaderNodeShaderToRGB"); cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.interpolation = "CONSTANT"
        cr.color_ramp.elements[0].color = (col[0]*.5, col[1]*.5, col[2]*.7, 1); cr.color_ramp.elements[1].position = 0.3
        cr.color_ramp.elements[1].color = (*col, 1); e = cr.color_ramp.elements.new(0.75); e.color = (col[0]*1.2, col[1]*1.2, col[2]*1.1, 1)
        em = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(d.outputs[0], s2r.inputs[0]); nt.links.new(s2r.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs[0], em.inputs[0]); nt.links.new(em.outputs[0], o.inputs[0])
    else:
        nt.links.new(d.outputs[0], o.inputs[0])
    return m
bpy.ops.mesh.primitive_plane_add(size=60); water = bpy.context.object; water.data.materials.append(mat("water", (0.03, 0.12, 0.07)))
mw = water.modifiers.new("ocean", "OCEAN"); mw.resolution = 12; mw.size = 2; mw.spatial_size = 30; mw.wave_scale = 0.05
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=0.05); pad = bpy.context.object; pad.data.materials.append(mat("pad", (0.4, 0.6, 0.15))); pad.hide_render = True
random.seed(1)
pts = []
while len(pts) < 350:
    x, y = random.uniform(-14, 14), random.uniform(-24, 24)
    if abs(x) > 3: pts.append((x, y, 0.05))
me = bpy.data.meshes.new("pts"); me.from_pydata(pts, [], []); po = bpy.data.objects.new("pts", me); sc.collection.objects.link(po)
ng = bpy.data.node_groups.new("inst", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"); ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput"); iop = ng.nodes.new("GeometryNodeInstanceOnPoints"); oi = ng.nodes.new("GeometryNodeObjectInfo"); oi.inputs[0].default_value = pad
rv = ng.nodes.new("FunctionNodeRandomValue"); rv.inputs["Min"].default_value = 0.8; rv.inputs["Max"].default_value = 2.2
ng.links.new(gi.outputs[0], iop.inputs["Points"]); ng.links.new(oi.outputs["Geometry"], iop.inputs["Instance"]); ng.links.new(rv.outputs[1], iop.inputs["Scale"]); ng.links.new(iop.outputs[0], go.inputs[0])
po.modifiers.new("gn", "NODES").node_group = ng
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1); boat = bpy.context.object
boat.scale = (1, 3, 0.5); boat.data.materials.append(mat("wood", (0.5, 0.3, 0.15)))
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35, location=(0, 0, 0.8)); man = bpy.context.object; man.data.materials.append(mat("coat", (0.15, 0.15, 0.5)))
ink = bpy.data.collections.new("INK"); sc.collection.children.link(ink)
for o in (boat, man):
    for c in o.users_collection: c.objects.unlink(o)
    ink.objects.link(o)
if stage in ("fs", "kw", "kwa"):
    sc.render.use_freestyle = True
    vl = sc.view_layers[0]; fs = vl.freestyle_settings
    ls = fs.linesets.new("ink"); ls.linestyle = bpy.data.linestyles.new("ink")
    ls.select_by_collection = True; ls.collection = ink
    for l in fs.linesets:
        if l.linestyle is None: l.linestyle = bpy.data.linestyles.new("d")
# compositor
sc.use_nodes = True; sc.render.compositor_device = "GPU"; nt = sc.node_tree; nt.nodes.clear()
rl = nt.nodes.new("CompositorNodeRLayers"); kw = nt.nodes.new("CompositorNodeKuwahara"); kw.variation = "ANISOTROPIC" if stage == "kwa" else "CLASSIC"
gl = nt.nodes.new("CompositorNodeGlare"); comp = nt.nodes.new("CompositorNodeComposite")
nt.links.new(rl.outputs[0], kw.inputs[0]); nt.links.new(kw.outputs[0], gl.inputs[0]); nt.links.new(gl.outputs[0], comp.inputs[0])
sc.use_nodes = stage in ("kw", "kwa")
sc.render.filepath = f"C:/About You/work/bench/bench_{eng}_{stage}.png"
for i in range(3):
    t = time.time(); sc.frame_set(1 + i); bpy.ops.render.render(write_still=True); print(f"BENCH {eng} {stage} frame {i}: {time.time()-t:.2f}s", flush=True)
