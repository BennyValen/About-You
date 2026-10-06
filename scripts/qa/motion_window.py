# Motion ratio for a frame window: original vs a render dir of drawings (on twos).
#   python scripts/qa/motion_window.py <dir> a b
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from gates import load_original, load_render, mad
d, a, b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
o, r = load_original(a, b), load_render(d, a, b)
mo, mr = mad(o), mad(r)
print(f"window {a}-{b}: orig {mo.mean():.2f} render {mr.mean():.2f} ratio {mr.mean() / (mo.mean() + 1e-6):.2f}")
