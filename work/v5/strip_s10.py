import cv2, numpy as np, json, sys
d = sys.argv[1] if len(sys.argv) > 1 else "render/v5test/s10"
f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 3100
L = {r["f"]: r for r in json.load(open(f"{d}/walk_log.json"))}
print("max foot lateral px:", max(max(r["foot"]) for r in L.values()), " max hand lateral px:", max(max(r["hand"]) for r in L.values()))
tiles = []
for i, f in enumerate(range(f0, f0 + 24, 2)):
    im = cv2.imread(f"{d}/paint/f{f:04d}.jpg")
    x, y = [int(v) for v in L[f]["hat"]]
    c = im[y - 75:y + 65, x - 70:x + 70]
    t = cv2.resize(c, (c.shape[1] * 2, c.shape[0] * 2), interpolation=cv2.INTER_CUBIC)
    cv2.putText(t, f"d{i}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    tiles.append(t)
cv2.imwrite("work/gates/walker_s10.jpg", np.vstack([np.hstack(tiles[:6]), np.hstack(tiles[6:])]))
