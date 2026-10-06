import sys, glob, cv2, numpy as np
d = sys.argv[1]
ps = sorted(glob.glob(d + "/paint/f*.jpg"))
n = len(ps)
out = []
for q in (0.25, 0.55, 0.8):
    i = int(n * q)
    a = cv2.resize(cv2.imread(ps[i], 0), (540, 960)).astype(np.float32)
    b = cv2.resize(cv2.imread(ps[i + 1], 0), (540, 960)).astype(np.float32)
    r = [cv2.phaseCorrelate(a[150:850, x0:x1], b[150:850, x0:x1]) for x0, x1 in ((20, 170), (370, 520))]
    (dx, dy), _ = max(r, key=lambda t: t[1])
    out.append(round(abs(dy) * 2, 1))
print(d, out, "mean", round(float(np.mean(out)), 2))
