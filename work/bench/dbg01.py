import sys
sys.path.insert(0, "C:/About You/blender")
import bpy, numpy as np
from mathutils import Vector
class O: scale = 0.5; samples = 8
from scenes import s01
r = s01.build(O())
r.update(147); bpy.context.view_layer.update()
for o in bpy.data.objects:
    if o.type == "LIGHT" and o.data.type == "AREA":
        mw = o.matrix_world
        d = mw.to_3x3() @ Vector((0, 0, -1))
        print("DBG", o.name, "loc", tuple(round(v, 2) for v in mw.translation), "dir", tuple(round(v, 2) for v in d), "E", o.data.energy)
        break
print("DBG cam", tuple(bpy.context.scene.camera.location))
