import sys, numpy as np
sys.path.insert(0, r"C:\About You\blender")
import importlib
mod = importlib.import_module("scenes.s11")
class O: scale=1.0; samples=2
r = mod.build(O())
import bpy
for nm in ("clouds0","clouds1","clouds2"):
    ob = bpy.data.objects[nm]
    co = np.zeros(len(ob.data.vertices)*3, np.float32); ob.data.vertices.foreach_get("co", co); co=co.reshape(-1,3)
    h,_ = np.histogram(co[:,1], bins=12, range=(-20, 40))
    print("DBG", nm, len(co), co[:,1].min().round(1), co[:,1].max().round(1), h.tolist())
print("DBG rect", [r.rig.path_rect(z,1.3) for z in (-3,-14,-30)])
