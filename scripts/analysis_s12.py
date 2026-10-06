# Scene 12: camera flow (phase correlation on masked frames) and A/B figure positions (dark blobs).
import numpy as np, cv2, json, subprocess
FF = "./tools/ffmpeg.exe"; W, H = 540, 960
raw = subprocess.run([FF, "-v", "error", "-i", "source/original.mp4", "-vf", f"select='gte(n\,3640)',scale={W}:{H}", "-vsync", "0",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3); base = 3640
gray = [cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32) for f in fr]
win = cv2.createHanningWindow((W, H), cv2.CV_32F)
out = {"camera": [], "figures": []}
for n in range(3648, 4004 - 6, 6):
    i = n - base
    (sx, sy), r = cv2.phaseCorrelate(gray[i], gray[i + 6], win)
    out["camera"].append([n + 3, round(sx * 2 / 6, 2), round(sy * 2 / 6, 2), round(float(r), 2)])
for n in range(3648, 4004, 2):
    f = fr[n - base].astype(np.int16)
    dark = ((f.sum(axis=2) < 200) & (f[..., 2] - f[..., 0] > -10)).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    nl, lab, st, ce = cv2.connectedComponentsWithStats(dark, 8)
    blobs = sorted([(int(st[k][4]), round(ce[k][0] * 2), round(ce[k][1] * 2)) for k in range(1, nl) if 20 < st[k][4] < 3000], reverse=True)[:3]
    out["figures"].append([n, blobs])
json.dump(out, open("work/s12_track.json", "w"))
for c in out["camera"][::4]: print("cam", c)
for f in out["figures"][::12]: print("fig", f)
