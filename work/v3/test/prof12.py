import sys, time, cProfile, pstats
sys.argv = ["x", "--", "--scene", "12", "--only", "3700"]
sys.path.insert(0, r"C:\About You\blender")
from kit import core, look
import importlib
mod = importlib.import_module("scenes.s12")
class O: scale=1.0; samples=8
pr = cProfile.Profile(); pr.enable()
r = mod.build(O())
pr.disable()
pstats.Stats(pr).sort_stats("cumulative").print_stats(18)
