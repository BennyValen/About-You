# v5 Fix 1 gate (scene 3 lily pads) from the scene-graph pad table render/.../scene_03/pads.json:
#   pad_overlap_report.csv (every overlapping pair: depth / smaller radius, layer order, which pad is drawn on top),
#   max depth ratio <= 0.22, zero pairs with the lower-index pad on top, draw order identical in 20 sampled frames,
#   centre-to-centre vectors of 30 overlapping pairs stable within 1.5 px over every drawing.
#   python scripts/qa/pads_gate.py [render/v5/scene_03]
import csv, json, math, sys
import numpy as np

d = sys.argv[1] if len(sys.argv) > 1 else "render/v5/scene_03"
P = json.load(open(f"{d}/pads.json"))
x, y, r = np.array(P["x"]), np.array(P["y"]), np.array(P["r"])
layer, z0, ph = np.array(P["layer"]), np.array(P["z"]), np.array(P["ph"])
hid = np.array(P.get("hidden", [False] * len(x)))
keep = ~hid
x, y, r, layer, z0, ph = x[keep], y[keep], r[keep], layer[keep], z0[keep], ph[keep]
print(f"pads hidden because they could not meet the overlap limit: {int(hid.sum())}")
ppm, start, end = P["ppm"], P["start"], P["end"]
n = len(x)
dist = np.hypot(x[:, None] - x[None, :], y[:, None] - y[None, :]) + np.eye(n) * 1e9
depth = r[:, None] + r[None, :] - dist
pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if depth[i, j] > 0]


def state(dd):                    # same formula as scenes/s03.py pad_state()
    t = dd - start
    phase = 2 * math.pi * t / 150.0 + ph
    xy = np.c_[x, y] + np.array([0.0, -1.0 / 24.0 / ppm]) * t + np.outer(np.sin(phase), [0.6, 0.8]) * (0.5 / ppm)
    z = z0 + 0.004 * np.sin(phase + 0.7)
    return xy, z


rows, bad_order, worst = [], 0, 0.0
for i, j in pairs:
    ratio = depth[i, j] / min(r[i], r[j])
    top = i if layer[i] > layer[j] else j
    low = j if top == i else i
    drawn_top = i if z0[i] > z0[j] else j
    wrong = drawn_top != top
    bad_order += wrong
    worst = max(worst, ratio)
    rows.append(dict(pad_a=i, pad_b=j, r_a=round(r[i], 4), r_b=round(r[j], 4), depth_m=round(depth[i, j], 4), depth_ratio=round(ratio, 4),
                     layer_a=int(layer[i]), layer_b=int(layer[j]), upper_by_index=top, drawn_on_top=drawn_top, lower_index_on_top=int(wrong)))
with open("pad_overlap_report.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["pad_a"])
    w.writeheader()
    w.writerows(rows)
print(f"pads {n}, overlapping pairs {len(pairs)}, max depth ratio {worst:.3f} (limit 0.22), pairs with the lower-index pad on top: {bad_order}")
# draw-order stability over 20 sampled frames
frames = np.linspace(start, end - 2, 20).astype(int)
frames -= (frames - start) % 2
orders = []
min_gap = 1e9
for f in frames:
    _, z = state(f)
    orders.append(tuple(bool(z[i] > z[j]) for i, j in pairs))       # stacking order of every overlapping pair
    for i, j in pairs:
        hi, lo = (i, j) if layer[i] > layer[j] else (j, i)
        min_gap = min(min_gap, z[hi] - z[lo])
same = all(o == orders[0] for o in orders)
print(f"draw order of all overlapping pairs identical in {len(frames)} sampled frames: {same}; min height of an upper pad above the pad it overlaps: {min_gap * 100:.2f} cm")
# relative displacement of 30 overlapping pairs over every drawing
sel = pairs[:: max(1, len(pairs) // 30)][:30]
vec0 = None
worst_rel = 0.0
for f in range(start, end, 2):
    xy, _ = state(f)
    v = np.array([xy[j] - xy[i] for i, j in sel])
    if vec0 is None:
        vec0 = v
    worst_rel = max(worst_rel, float(np.abs(np.linalg.norm(v - vec0, axis=1)).max() * ppm))
print(f"30 overlapping pairs: max change of the centre-to-centre vector over the scene {worst_rel:.2f} px (limit 1.5)")
ok = worst <= 0.22 + 1e-3 and bad_order == 0 and same and worst_rel <= 1.5
print("PADS GATE:", "PASS" if ok else "FAIL")
