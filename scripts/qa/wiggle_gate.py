# Section 7 gate 8 (painting wiggle), the brief's measurement: two consecutive distinct drawings, rigid shift removed by
# phase correlation, Farneback residual flow (mean / p90, px at 1080 wide) plus the duplicate fraction of the 7 pairs.
#   python scripts/qa/wiggle_gate.py [ours.mp4]
import subprocess, sys
import numpy as np, cv2

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]


def frames(p, start, n=8):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{start/24:.4f}", "-i", p,
                          "-vf", "scale=540:960,format=gray", "-frames:v", str(n), "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 960, 540).astype(np.float32)


def wiggle(p, start):
    f = frames(p, start)
    d = [np.abs(f[i + 1] - f[i]).mean() for i in range(len(f) - 1)]
    i = next((k for k, v in enumerate(d) if v > 0.3), None)          # first distinct pair
    if i is None:
        return 0.0, 0.0, 1.0
    a, b = f[i], f[i + 1]
    (dx, dy), _ = cv2.phaseCorrelate(a[150:800, 40:500], b[150:800, 40:500])
    bw = cv2.warpAffine(b, np.float32([[1, 0, -dx], [0, 1, -dy]]), (540, 960), flags=cv2.INTER_CUBIC)
    fl = cv2.calcOpticalFlowFarneback(a.astype(np.uint8), bw.astype(np.uint8), None, 0.5, 4, 25, 5, 7, 1.5, 0)
    mag = np.linalg.norm(fl[200:760, 60:480], axis=2)
    dup = sum(v < 0.05 for v in d) / len(d)
    return round(float(mag.mean()) * 2, 2), round(float(np.percentile(mag, 90)) * 2, 2), round(dup, 2)  # px at 1080 wide


def places(s):
    a, b = CUTS[s - 1], CUTS[s]
    # three places per scene (quarter points), each starting on an even drawing frame
    return [a + ((int(a + (b - a) * q) - a) // 2) * 2 for q in (0.25, 0.5, 0.75)]


if __name__ == "__main__":
    ours = sys.argv[1] if len(sys.argv) > 1 else "out/final.mp4"
    ref = [(2, 400), (3, 700), (5, 1500), (7, 2300)]
    print("reference frames (orig mean/p90/dup  vs  ours mean/p90/dup):")
    for s, f0 in ref:
        print(f"  s{s} f{f0}: {wiggle('source/original.mp4', f0)}  {wiggle(ours, f0)}")
    print("per scene, three places (mean residual px): orig vs ours, ratio")
    for s in range(1, 13):
        o = [wiggle("source/original.mp4", f)[0] for f in places(s)]
        r = [wiggle(ours, f)[0] for f in places(s)]
        mo, mr = float(np.mean(o)), float(np.mean(r))
        ok = 0.6 <= mr / max(mo, 1e-6) <= 1.4
        print(f"  s{s:02d} orig {mo:.2f}  ours {mr:.2f}  x{mr / max(mo, 1e-6):.2f} {'ok' if ok else '--'}  (orig {o}, ours {r})")
