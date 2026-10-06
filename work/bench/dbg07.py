import sys
sys.path.insert(0, "C:/About You/blender")
import bpy, numpy as np
class O: scale = 0.5; samples = 8
from scenes import s07
r = s07.build(O())
me = bpy.data.objects["terrain"].data
co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
print("DBG terrain z", co[:, 2].min(), co[:, 2].max(), np.percentile(co[:, 2], [10, 50, 90]))
for o in bpy.data.objects:
    if o.name.startswith("wisps"): o.hide_render = True
bpy.context.scene.use_nodes = False
r.update(2224)
bpy.context.scene.render.filepath = "C:/About You/work/bench/dbg07.png"
bpy.ops.render.render(write_still=True)
