# Ending analysis: red thread components and dark figure blobs, full-res frames 3840..4002 (every 6)
import numpy as np, cv2, glob, os
for p in sorted(glob.glob("work/ref_end_full/f*.png")):
    n = int(os.path.basename(p)[1:5])
    im = cv2.imread(p).astype(np.int16)
    b, g, r = im[..., 0], im[..., 1], im[..., 2]
    red = ((r - np.maximum(g, b)) > 70) & (r > 150)
    red = cv2.morphologyEx(red.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    nlab, lab, stats, cent = cv2.connectedComponentsWithStats(red, 8)
    comps = []
    for i in range(1, nlab):
        x, y, w, h, area = stats[i]
        if area < 40: continue
        touch = ("T" if y <= 2 else "") + ("B" if y + h >= 1918 else "") + ("L" if x <= 2 else "") + ("R" if x + w >= 1078 else "")
        comps.append(f"[x{x}-{x+w} y{y}-{y+h} a{area} {touch or '-'}]")
    dark = ((r + g + b) < 150).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    nl, lb, st, ce = cv2.connectedComponentsWithStats(dark, 8)
    heads = [f"({int(ce[i][0])},{int(ce[i][1])} a{st[i][4]})" for i in range(1, nl) if 150 < st[i][4] < 5000]
    print(f"f{n} t={n/24:.2f}  red:{' '.join(comps)}  dark:{' '.join(heads)}")
