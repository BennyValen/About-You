# Camera motion per scene, measured from the original (background flow). Uses 12-frame spans at
# 540x960 (2-frame pairs are biased low by sub-pixel phase correlation). Output: work/camera.json
import json, numpy as np, cv2
fr = np.load("work/gray540.npy")
W, H = 540, 960
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
win = cv2.createHanningWindow((W, H), cv2.CV_32F)
K = 12
out = {"note": "dx,dy: background flow in px/frame at 1080x1920 (+x right, +y down; dy>0 means the camera moves up the frame). "
               "Measured by phase correlation over 12-frame spans at 540x960. zoom: background scale change per frame.",
       "scenes": []}
for s in range(12):
    a, b = CUTS[s], CUTS[s + 1]
    series = []
    for n in range(a, b - K, 6):
        (sx, sy), r = cv2.phaseCorrelate(fr[n].astype(np.float32), fr[n + K].astype(np.float32), win)
        series.append({"frame": n + K // 2, "dx": round(sx * 2 / K, 3), "dy": round(sy * 2 / K, 3), "conf": round(float(r), 3)})
    dy = np.array([x["dy"] for x in series]); dx = np.array([x["dx"] for x in series])
    # smooth for the camera path (robust: rolling median over 1 s)
    sm = [float(np.median(dy[max(0, i - 2):i + 3])) for i in range(len(dy))]
    for x, v in zip(series, sm): x["dy_smooth"] = round(v, 3)
    out["scenes"].append({"scene": s + 1, "start": a, "end": b, "dx": round(float(np.median(dx)), 3), "dy": round(float(np.median(dy)), 3),
                          "speed_px_per_s": round(float(np.median(np.hypot(dx, dy))) * 24, 1), "series": series})
    print(f"scene {s+1:2d}: dx {np.median(dx):6.2f}  dy {np.median(dy):6.2f} px/f ({np.median(dy)*24:6.1f} px/s)  per-second dy:",
          np.round([np.median(dy[i:i+4]) for i in range(0, len(dy), 4)], 1).tolist())
json.dump(out, open("work/camera.json", "w"), indent=1)
