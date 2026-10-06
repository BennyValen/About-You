# Merge the per-scene hero motion logs into work/hero_motion.csv (frame, scene, hero, x, y, yaw_deg).
# Scenes rendered before the v4 log existed (2, 4, 10: re-painted, not re-rendered) are derived from thread_log.json:
# the thread's owner end in screen px; the heading is not logged there, so it is derived from
# the owner end's screen trajectory (scene 4 follows its S-curve path tangent; 2 and 10 walk straight).
import csv, json, os
import numpy as np

CAM_PX_PER_FRAME = {2: 7.0, 4: 4.9, 10: 3.1}       # half the px per drawing (section 5 table)
GAIT_HZ = {2: 0.55, 4: 0.62, 10: 0.9}               # rope_cfg.MOTION gait rates
rows = []
for s in range(1, 13):
    d = f"render/v4/scene_{s:02d}"
    p = os.path.join(d, "hero_motion.csv")
    if os.path.exists(p):
        rows += [r for r in csv.DictReader(open(p))]
        continue
    if not os.path.exists(os.path.join(d, "thread_log.json")):
        print(f"scene {s}: no logs yet")
        continue
    log = json.load(open(os.path.join(d, "thread_log.json")))
    for o in ("A", "B"):
        rec = [(r["f"], r[o]["owner_end"]) for r in log if o in r]
        if not rec:
            continue
        fr = np.array([f for f, _ in rec])
        xy = np.array([p_ for _, p_ in rec], float)
        # the hero holds its screen place while the ground scrolls at the camera speed, so the heading is the lateral
        # screen velocity over the forward ground speed (px/frame)
        # the gait sway of the body centre is not a heading: average over one stride first
        k = max(1, int(round(24.0 / GAIT_HZ[s] / 2)))
        xs = np.convolve(np.pad(xy[:, 0], (k // 2, k - 1 - k // 2), mode="edge"), np.ones(k) / k, mode="valid")
        dx = np.gradient(xs, fr)
        yaw = np.degrees(np.arctan(dx / CAM_PX_PER_FRAME[s]))
        for f, (x, y), yw in zip(fr, xy, yaw):
            rows.append(dict(frame=int(f), scene=s, hero=o, x=f"{x:.2f}", y=f"{y:.2f}", yaw_deg=f"{yw:.3f}"))
with open("work/hero_motion.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["frame", "scene", "hero", "x", "y", "yaw_deg"])
    w.writeheader()
    for r in sorted(rows, key=lambda r: (int(r["frame"]), r["hero"])):
        w.writerow({k: r[k] for k in w.fieldnames})
print("work/hero_motion.csv", len(rows), "rows, scenes", sorted({int(r["scene"]) for r in rows}))
