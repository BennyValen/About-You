# Thread gate v2: trace each cord in the rendered image from its owner (attach point from the simulation
# log) toward the frame edge where its free end lies, following the crimson line row by row.
# A cord passes if the trace reaches within 45 px of that edge (the edge DOF softens the last px) without a gap longer than 50 rows
# (short occlusions by foam, hull or wings are allowed).
# Unowned red curves: strong crimson components longer than 220 px that do not lie on any traced cord.
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from threadmask import render_thread_mask

CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]


def score_map(rgb):
    f = rgb.astype(np.float32)
    sat = f[..., 0] - np.maximum(f[..., 1], f[..., 2])
    orange = np.maximum(f[..., 1] - f[..., 2] - 18, 0)
    return sat - 0.8 * orange


def trace(S, x0, y0, direction, h, w, win=7, thr=48.0, max_gap=50):
    x = float(x0)
    path = []
    gap = 0
    y = int(round(y0))
    y_end = h - 1 if direction > 0 else 0
    last_hit = y
    # skip the first few rows under the owner (body/hull may cover the attach point)
    for yy in range(y, y_end + direction, direction):
        lo, hi = int(max(0, x - win)), int(min(w, x + win + 1))
        row = S[yy, lo:hi]
        if row.size == 0:
            break
        # prefer continuity: penalise distance from the current x
        pen = np.abs(np.arange(lo, hi) - x) * 2.0
        i = int(np.argmax(row - pen))
        t = thr if 120 < yy < h - 120 else thr * 0.5
        if row[i] > t:
            x = float(lo + i)
            path.append((yy, lo + i))
            gap = 0
            last_hit = yy
        else:
            gap += 1
            if gap > max_gap and abs(yy - y) > 120:
                break
    reach = (last_hit >= h - 46) if direction > 0 else (last_hit <= 45)
    return reach, path, last_hit


def gate(scene, d, lines):
    a, b = CUTS[scene - 1], CUTS[scene]
    log = {r["A"]["f"]: r for r in json.load(open(os.path.join(d, "thread_log.json")))}
    issues = []
    checked = 0
    owners_seen = {}
    for f in range(a, b, 2):
        p = os.path.join(d, f"f{f:04d}.png")
        if f not in log or not os.path.exists(p):
            continue
        rgb = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]
        k = w / 1080
        S = score_map(rgb)
        traced = np.zeros((h, w), np.uint8)
        rec = log[f]
        checked += 1
        for name, v in rec.items():
            if v.get("visible_px", 1e9) < 30:
                continue
            owners_seen[name] = owners_seen.get(name, 0) + 1
            ox, oy = v["owner_end"][0] * k, v["owner_end"][1] * k
            fy = v["free_end"][1] * k
            direction = 1 if fy > oy else -1
            if oy < 0 or oy > h:      # owner off-screen: start the trace at the edge the cord enters from
                oy = 0 if oy < 0 else h - 1
                direction = 1 if oy == 0 else -1
            # seed: first clearly crimson pixel within 40 px of the owner, scanning toward the free end
            sx, sy = ox, min(max(oy + direction * 6 * k, 0), h - 1)
            for yy in range(int(sy), int(min(max(sy + direction * 160 * k, 0), h - 1)), direction):
                lo, hi = int(max(0, ox - 40 * k)), int(min(w, ox + 40 * k + 1))
                i = int(np.argmax(S[yy, lo:hi]))
                if S[yy, lo + i] > 100:
                    sx, sy = lo + i, yy
                    break
            ok, path, last = trace(S, sx, sy, direction, h, w, win=int(9 * k) + 2)
            for yy, xx in path:
                cv2.circle(traced, (xx, yy), int(10 * k) + 2, 1, -1)
            if not ok:
                issues.append(f"f{f} thread {name}: trace from owner ({ox:.0f},{oy:.0f}) stopped at row {last}")
        strong = render_thread_mask(rgb).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(strong, 8)
        for i in range(1, n):
            if max(st[i][2], st[i][3]) < 220 * k:
                continue
            comp = lab == i
            if (comp & (traced == 0)).sum() > 0.5 * comp.sum():
                issues.append(f"f{f}: unowned red curve {st[i][:4].tolist()}")
    lines.append(f"## thread gate v2 (trace), scene {scene}: drawings checked {checked}, owners traced {owners_seen}")
    for x in issues[:30]:
        lines.append("  " + x)
    if len(issues) > 30:
        lines.append(f"  ... {len(issues) - 30} more")
    ok = not issues
    lines.append(f"thread gate scene {scene}: {'PASS' if ok else 'FAIL'} ({len(issues)} issues)")
    return ok


if __name__ == "__main__":
    scene, d = int(sys.argv[1]), sys.argv[2]
    L = []
    gate(scene, d, L)
    print("\n".join(L))
