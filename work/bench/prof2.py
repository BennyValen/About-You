import sys, time
sys.path.insert(0, "C:/About You/blender")
import bpy
class O: scale = 1.0; samples = 8
from scenes import s12
r = s12.build(O())
sc = bpy.context.scene
def t(label):
    r.update(3940)
    sc.render.filepath = "C:/About You/work/bench/prof_full.png"
    t0 = time.time(); bpy.ops.render.render(write_still=True); print(f"PROF {label}: {time.time()-t0:.2f}s", flush=True)
t("warm"); t("full res 8spp freestyle")
sc.view_layers[0].freestyle_settings.use_culling = True; t("freestyle culling")
sc.render.use_freestyle = False; t("no freestyle")
