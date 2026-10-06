import sys, cv2, numpy as np
im = cv2.imread(sys.argv[1])
sm = cv2.resize(im, (540, 960))
g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY)
print("tone mean %.1f p5 %d p95 %d" % (g.mean(), np.percentile(g, 5), np.percentile(g, 95)))
b, gg, r = [sm[..., i].astype(int) for i in range(3)]
gap = (b > r + 25) & (g < 120)
lav = (~gap) & (g >= 90) & (g < 170) & (b >= r - 5)
pale = (~gap) & (g >= 170)
print("gaps %.2f  lavender/violet %.2f  pale %.2f" % (gap.mean(), lav.mean(), pale.mean()))
