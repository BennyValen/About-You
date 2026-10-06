import sys, glob, cv2, numpy as np
for d in sys.argv[1:]:
    sub = "paint" if glob.glob(d + "/paint/f*.jpg") else "clean"
    ps = sorted(glob.glob(f"{d}/{sub}/f*.jpg"))
    out = []
    for q in (0.25, 0.55, 0.8):
        i = int(len(ps) * q)
        a = cv2.resize(cv2.imread(ps[i], 0), (540, 960)); b = cv2.resize(cv2.imread(ps[i + 1], 0), (540, 960))
        fl = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 5, 31, 5, 7, 1.5, 0)
        out.append(round(float(np.median(np.r_[fl[150:850, 20:170, 1].ravel(), fl[150:850, 370:520, 1].ravel()])) * 2, 2))
    print(d, sub, out, "mean", round(float(np.mean(out)), 2))
