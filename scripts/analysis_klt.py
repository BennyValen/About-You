# Sparse KLT tracking of background corners with forward-backward check -> robust camera flow.
import numpy as np, cv2, sys, json
fr = np.load("work/gray540.npy")
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
def klt(n, k=12, exclude=None):
    a = fr[n]; b = fr[n + k]
    mask = np.full(a.shape, 255, np.uint8)
    if exclude is not None:
        x0, y0, x1, y1 = exclude; mask[y0:y1, x0:x1] = 0
    p0 = cv2.goodFeaturesToTrack(a, 400, 0.01, 8, mask=mask, blockSize=7)
    if p0 is None or len(p0) < 8: return None
    lk = dict(winSize=(31, 31), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p0, None, **lk)
    pb, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, p1, None, **lk)
    fb = np.linalg.norm((p0 - pb).reshape(-1, 2), axis=1)
    ok = (st.ravel() == 1) & (st2.ravel() == 1) & (fb < 0.6)
    if ok.sum() < 6: return None
    d = (p1 - p0).reshape(-1, 2)[ok]
    return float(np.median(d[:, 1])) * 2 / k, float(np.median(d[:, 0])) * 2 / k, int(ok.sum())
res = {}
for s in range(12):
    a, b = CUTS[s], CUTS[s + 1]
    rows = []
    for n in range(a + 2, b - 14, 12):
        r = klt(n, 12, exclude=(170, 450, 370, 760))
        if r: rows.append((n, *r))
    R = np.array(rows)
    res[s + 1] = rows
    per_s = [round(float(np.median(R[(R[:, 0] >= t) & (R[:, 0] < t + 24), 1])), 2) for t in range(a, b - 14, 24) if ((R[:, 0] >= t) & (R[:, 0] < t + 24)).any()]
    print(f"scene {s+1:2d}: median dy {np.median(R[:,1]):5.2f} dx {np.median(R[:,2]):5.2f} pts {int(np.median(R[:,3]))}  per-second dy {per_s}")
json.dump({str(k): v for k, v in res.items()}, open("work/klt.json", "w"))
