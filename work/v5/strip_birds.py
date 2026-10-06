import cv2, numpy as np, json, sys
d = sys.argv[1] if len(sys.argv) > 1 else "render/v5test/s12"
f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 3760
ids = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else "3,5").split(",")]
B = {r["f"]: r["birds"] for r in json.load(open(f"{d}/bird_log.json"))}
rows = []
for b in ids:
    tiles = []
    for i, f in enumerate(range(f0, f0 + 24, 2)):
        im = cv2.imread(f"{d}/paint/f{f:04d}.jpg")
        x, y = [int(v) for v in B[f][b][:2]]
        c = im[max(0, y - 45):y + 45, max(0, x - 45):x + 45]
        c = cv2.copyMakeBorder(c, 0, 90 - c.shape[0], 0, 90 - c.shape[1], cv2.BORDER_REPLICATE)
        t = cv2.resize(c, (180, 180), interpolation=cv2.INTER_CUBIC)
        cv2.putText(t, f"b{b} d{i} {B[f][b][3]:.0f}px", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
        tiles.append(t)
    rows.append(np.hstack(tiles))
cv2.imwrite("work/gates/birds_s12.jpg", np.vstack(rows))
