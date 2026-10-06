# out/v5_changes.jpg: per changed scene, v4 on top and v5 below, 4 drawings each (labelled).
import cv2, numpy as np

SAMPLES = {3: (640, 720, 820, 920), 6: (1700, 1800, 1900, 2000), 10: (3000, 3100, 3200, 3300), 11: (3316, 3318, 3400, 3600),
           12: (3700, 3800, 3900, 3990)}
W, H = 216, 384
rows = []
for s, frs in SAMPLES.items():
    for tag, root in (("v4", "render/v4"), ("v5", "render/v5")):
        tiles = []
        for f in frs:
            im = cv2.resize(cv2.imread(f"{root}/scene_{s:02d}/paint/f{f:04d}.jpg"), (W, H), interpolation=cv2.INTER_AREA)
            for col, th in (((0, 0, 0), 4), ((255, 255, 255), 1)):
                cv2.putText(im, f"{tag} s{s} f{f}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, th, cv2.LINE_AA)
            tiles.append(im)
        rows.append(np.hstack(tiles))
    rows.append(np.full((8, 4 * W, 3), 255, np.uint8))
cv2.imwrite("out/v5_changes.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
print("out/v5_changes.jpg")
