# Subject screen position per frame: topmost point of the largest thin-red-line component (A's thread
# attaches at A). Full-res coordinates. Output work/subject_track.json
import subprocess, sys, json, numpy as np, cv2
sys.path.insert(0, "scripts/qa")
from threadmask import thread_mask
FF = "./tools/ffmpeg.exe"; W, H = 540, 960
raw = subprocess.run([FF, "-v", "error", "-i", "source/original.mp4", "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
track = []
for n in range(len(fr)):
    m = thread_mask(fr[n], 0.5).astype(np.uint8)
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))
    nl, lab, st, ce = cv2.connectedComponentsWithStats(m, 8)
    best = None
    for i in range(1, nl):
        if st[i][4] < 25 or st[i][3] < 20: continue
        if best is None or st[i][3] > st[best][3]: best = i
    if best is None: track.append(None); continue
    ys, xs = np.where(lab == best)
    top = ys.min(); xt = int(np.median(xs[ys <= top + 2]))
    bot = ys.max(); xb = int(np.median(xs[ys >= bot - 2]))
    track.append([xt * 2, int(top) * 2, xb * 2, int(bot) * 2, int(st[best][3]) * 2])
json.dump(track, open("work/subject_track.json", "w"))
for s in range(12):
    a, b = CUTS[s], CUTS[s + 1]
    T = [t for t in track[a:b] if t]
    if not T: print(f"scene {s+1}: no thread"); continue
    T = np.array(T)
    q = len(T) // 4
    print(f"scene {s+1:2d}: thread top (attach) x {np.median(T[:,0]):5.0f}  y {np.median(T[:,1]):5.0f}  [y quartiles {[int(np.median(T[i*q:(i+1)*q,1])) for i in range(4)]}]  "
          f"x quartiles {[int(np.median(T[i*q:(i+1)*q,0])) for i in range(4)]}  bottom y {np.median(T[:,3]):5.0f} x {np.median(T[:,2]):5.0f}  found {len(T)}/{b-a}")
