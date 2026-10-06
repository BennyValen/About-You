import bpy, time, gpu
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.render.resolution_x, sc.render.resolution_y = 1080, 1920
sc.eevee.taa_render_samples = 16
sc.render.filepath = "work/bench/tiny.png"
for i in range(3):
    t = time.time(); bpy.ops.render.render(write_still=True); print(f"TINY {i}: {time.time()-t:.2f}s", flush=True)
