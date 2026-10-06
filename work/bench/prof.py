# profile scene 12 render cost by toggling features
import sys, os, time
sys.path.insert(0, "C:/About You/blender")
import bpy
import importlib
class O: scale = 0.5; samples = 16
from scenes import s12
from kit import look
r = s12.build(O())
sc = bpy.context.scene
def t(label):
    r.update(3940)
    sc.render.filepath = "C:/About You/work/bench/prof.png"
    t0 = time.time(); bpy.ops.render.render(write_still=True); print(f"PROF {label}: {time.time()-t0:.2f}s", flush=True)
t("warm"); t("full")
sc.render.use_freestyle = False; t("no freestyle")
sc.use_nodes = False; t("no freestyle, no compositor")
sc.eevee.taa_render_samples = 8; t("8 samples")
