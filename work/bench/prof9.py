import sys, time
sys.path.insert(0, "C:/About You/blender")
import bpy
class O: scale = 0.75; samples = 5
from scenes import s09
r = s09.build(O())
sc = bpy.context.scene
def t(label):
    r.update(2800)
    sc.render.filepath = "C:/About You/work/bench/prof9.png"
    t0 = time.time(); bpy.ops.render.render(write_still=True); print(f"PROF {label}: {time.time()-t0:.2f}s", flush=True)
t("warm"); t("full")



