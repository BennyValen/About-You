# Detect hard cuts in a rendered video by frame differencing and compare with the source cuts.
# usage: python scripts/check_cuts.py video.mp4 [every_nth=1]
import subprocess, sys, numpy as np
F = "./tools/ffmpeg.exe"
path = sys.argv[1]
nth = int(sys.argv[2]) if len(sys.argv) > 2 else 1
EXPECTED = [294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648]
W, H = 72, 128
p = subprocess.Popen([F, "-hide_banner", "-loglevel", "error", "-i", path, "-vf", f"scale={W}:{H}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
fr = []
while True:
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3:
        break
    fr.append(np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32))
d = np.array([0.0] + [float(np.mean(np.abs(fr[i] - fr[i - 1]))) for i in range(1, len(fr))])
print("frames decoded:", len(fr))
found = []
for i in range(1, len(d)):
    local = np.median(d[max(1, i - 12):i + 12])
    if d[i] > 25 and d[i] > 4 * max(local, 1.0):
        found.append(i * nth)
print("detected cuts:", found)
print("expected cuts:", EXPECTED)
ok = all(any(abs(f - e) <= nth for f in found) for e in EXPECTED) and len(found) == len(EXPECTED)
print("CUTS MATCH" if ok else "CUT MISMATCH")
