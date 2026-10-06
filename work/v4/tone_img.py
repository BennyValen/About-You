import sys, cv2, numpy as np
for p in sys.argv[1:]:
    im = cv2.resize(cv2.imread(p), (540, 960), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).ravel()
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    sat = hsv[hsv[:, 2] > 40, 1].mean() / 255
    full = cv2.imread(p)
    print("%s mean %.1f p5 %d p95 %d sat %.2f  maxR %d maxG %d" % (p[-12:], g.mean(), np.percentile(g, 5), np.percentile(g, 95), sat,
          full[..., 2].max(), full[..., 1].max()))
