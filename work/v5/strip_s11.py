import cv2, numpy as np, sys
src = sys.argv[1] if len(sys.argv) > 1 else "render/v5test/s11"
fr = list(range(3316, 3332, 2))
lab = lambda im, t: cv2.putText(im.copy(), t, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
def row(d, tag):
    return np.hstack([lab(cv2.resize(cv2.imread(f"{d}/paint/f{f}.jpg")[1050:1950, 40:1040], (250, 225)), f"{tag} d{i}") for i, f in enumerate(fr)])
cv2.imwrite("work/gates/s11_start.jpg", np.vstack([row("render/v4/scene_11", "v4"), row(src, "v5")]))
