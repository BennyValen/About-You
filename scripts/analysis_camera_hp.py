# Robust camera flow: phase correlation on high-pass filtered frames (removes screen-fixed glare/vignette),
# excluding the central subject column. 6-frame spans at 540x960. Output: work/camera.json (overwrites).
import json, numpy as np, cv2
fr = np.load("work/gray540.npy", mmap_mode="r")
W, H = 540, 960
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
win = cv2.createHanningWindow((W, H), cv2.CV_32F)
mask = np.ones((H, W), np.float32); mask[:, 200:340] = 0.15   # de-weight the subject column
def hp(img):
    f = img.astype(np.float32)
    return (f - cv2.GaussianBlur(f, (0, 0), 12)) * mask
K = 6
out = {"note": "dx,dy = background flow in px/frame at 1080x1920 (+y down, so dy>0 = camera travels up the frame / north). "
               "Phase correlation of high-pass frames over 6-frame spans at 540x960; dy_smooth = 1 s rolling median.",
       "scenes": []}
for s in range(12):
    a, b = CUTS[s], CUTS[s + 1]
    series = []
    for n in range(a, b - K, 3):
        (sx, sy), r = cv2.phaseCorrelate(hp(fr[n]), hp(fr[n + K]), win)
        series.append([n + K // 2, round(sx * 2 / K, 3), round(sy * 2 / K, 3), round(float(r), 3)])
    S = np.array(series)
    sm = [float(np.median(S[max(0, i - 4):i + 5, 2])) for i in range(len(S))]
    per_s = [round(float(np.median(S[(S[:, 0] >= t) & (S[:, 0] < t + 24), 2])), 2) for t in range(a, b - K, 24)]
    out["scenes"].append({"scene": s + 1, "start": a, "end": b,
                          "dy_median": round(float(np.median(S[:, 2])), 3), "dx_median": round(float(np.median(S[:, 1])), 3),
                          "speed_px_per_s": round(float(np.median(S[:, 2])) * 24, 1), "dy_per_second": per_s,
                          "series": [[int(x[0]), x[1], x[2], x[3], round(m, 3)] for x, m in zip(series, sm)]})
    print(f"scene {s+1:2d}: dy {np.median(S[:,2]):6.2f} dx {np.median(S[:,1]):6.2f} px/f   per-second dy {per_s}")
json.dump(out, open("work/camera.json", "w"), indent=0)
