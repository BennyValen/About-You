import cv2, numpy as np, json, sys
d = sys.argv[1] if len(sys.argv) > 1 else "render/v5test/s12"
f0 = int(sys.argv[2]) if len(sys.argv) > 2 else 3760
R = json.load(open(f"{d}/runner_log.json"))
L = {r["f"]: r for r in R["log"]}
tiles = []
for i, f in enumerate(range(f0, f0 + 32, 2)):
    im = cv2.imread(f"{d}/paint/f{f:04d}.jpg")
    x, y = [int(v) for v in L[f]["pelvis"]]
    c = im[y - 70:y + 90, x - 90:x + 70]
    t = cv2.resize(c, (c.shape[1] * 3 // 2 * 2 // 2, c.shape[0] * 3 // 2 * 2 // 2), interpolation=cv2.INTER_CUBIC)
    t = cv2.resize(c, (240, 240), interpolation=cv2.INTER_CUBIC)
    cv2.putText(t, f"d{i} fl{L[f]['flight']:.1f}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    tiles.append(t)
cv2.imwrite("work/gates/runner_s12.jpg", np.vstack([np.hstack(tiles[:8]), np.hstack(tiles[8:16])]))
la = [r["foot_lat"] for r in L.values()]; ha = [r["hand_lat"] for r in L.values()]
print("foot lat max", max(abs(v) for q in la for v in q), " hand lat max", max(abs(v) for q in ha for v in q),
      " hand fwd range", min(min(r["hand_fwd"]) for r in L.values()), max(max(r["hand_fwd"]) for r in L.values()))
