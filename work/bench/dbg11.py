import sys
sys.path.insert(0, "C:/About You/blender")
import bpy, numpy as np
class O: scale = 0.5; samples = 8
from scenes import s11
r = s11.build(O())
me = bpy.data.objects["clouds"].data
co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
print("DBG clouds z", co[:, 2].min(), co[:, 2].max(), np.percentile(co[:, 2], [10, 50, 90]), len(me.vertices))
print("DBG below z", bpy.data.objects["below"].location.z, "cam h", bpy.context.scene.camera.location.z)
