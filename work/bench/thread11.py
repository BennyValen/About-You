import sys
sys.path.insert(0, "C:/About You/blender")
import numpy as np, bpy
class O: scale = 0.25; samples = 1
from scenes import s11
import kit.thread as T
orig_run = T.Cord.run
def run(self, frames, anchor, td, warm=72, fps=24):
    out = orig_run(self, frames, anchor, td, warm, fps)
    for f in (frames[0], frames[len(frames)//2], frames[-1]):
        P = out[f]; print("THR", f, "z range", P[:,2].min().round(2), P[:,2].max().round(2), "y span", (P[0,1]-P[-1,1]).round(2))
    return out
T.Cord.run = run
s11.build(O())
