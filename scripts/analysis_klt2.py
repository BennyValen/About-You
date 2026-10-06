# Feature tracking that separates moving background features from screen-fixed texture:
# corners detected on a blurred (sigma 2) image, KLT with forward-backward check, then the dominant
# NON-static displacement cluster is taken as the camera flow.
import numpy as np, cv2, json, sys
fr = np.load("work/gray540.npy", mmap_mode="r")
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
lk = dict(winSize=(41, 41), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.01))
def flow(n, k=6):
    a = cv2.GaussianBlur(np.asarray(fr[n]), (0, 0), 2); b = cv2.GaussianBlur(np.asarray(fr[n + k]), (0, 0), 2)
    m = np.full(a.shape, 255, np.uint8); m[:, 190:350] = 0; m[:20] = 0; m[-20:] = 0
    p0 = cv2.goodFeaturesToTrack(a, 600, 0.003, 10, mask=m, blockSize=9)
    if p0 is None: return None
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, **lk)
    pb, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, **lk)
    ok = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm((p0 - pb).reshape(-1, 2), axis=1) < 0.5)
    d = (p1 - p0).reshape(-1, 2)[ok] * 2 / k
    if len(d) < 6: return None
    moving = d[np.abs(d[:, 1]) > 0.6]
    frac = len(moving) / len(d)
    if frac > 0.12 and len(moving) >= 5:
        return float(np.median(moving[:, 1])), float(np.median(moving[:, 0])), frac, len(d)
    return float(np.median(d[:, 1])), float(np.median(d[:, 0])), frac, len(d)
res = {}
scenes = [int(x) for x in sys.argv[1:]] or list(range(1, 13))
for s in scenes:
    a, b = CUTS[s - 1], CUTS[s]
    rows = [(n + 3,) + r for n in range(a, b - 8, 6) if (r := flow(n)) is not None]
    R = np.array(rows); res[s] = rows
    per_s = [round(float(np.median(R[(R[:, 0] >= t) & (R[:, 0] < t + 24), 1])), 2) for t in range(a, b - 8, 24)]
    print(f"scene {s:2d}: dy {np.median(R[:,1]):6.2f}  per-second {per_s}")
json.dump({str(k): v for k, v in res.items()}, open("work/klt2.json", "w"))
