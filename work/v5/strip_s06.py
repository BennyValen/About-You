import cv2, numpy as np, csv, sys
d = sys.argv[1] if len(sys.argv) > 1 else "render/v5test/s06"
f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 1700
rows = list(csv.DictReader(open(f"{d}/colliders.csv")))
pos = {}
for r in rows:
    pos[(int(r["frame"]), r["id"])] = (float(r["cx"]), float(r["cy"]))
for who, half, out in (("manta", 230, "work/gates/swim_manta.jpg"), ("turtle1", 90, "work/gates/swim_turtle.jpg")):
    tiles = []
    for i, f in enumerate(range(f0, f0 + 24, 2)):
        im = cv2.imread(f"{d}/paint/f{f:04d}.jpg")
        if (f, who) not in pos:
            continue
        x, y = [int(v) for v in pos[(f, who)]]
        c = im[max(0, y - half):y + half, max(0, x - half):x + half]
        c = cv2.copyMakeBorder(c, 0, 2 * half - c.shape[0], 0, 2 * half - c.shape[1], cv2.BORDER_REPLICATE)
        t = cv2.resize(c, (230, 230), interpolation=cv2.INTER_AREA if half > 115 else cv2.INTER_CUBIC)
        cv2.putText(t, f"{who} d{i}", (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        tiles.append(t)
    if tiles:
        cv2.imwrite(out, np.vstack([np.hstack(tiles[:6]), np.hstack(tiles[6:12])]) if len(tiles) >= 12 else np.hstack(tiles))
        print(out, len(tiles))
