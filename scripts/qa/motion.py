# Motion parity: per-second mean absolute frame difference (108x192 gray), original vs render.
# usage: python scripts/qa/motion.py <render.mp4> [start_frame end_frame] [--json out.json]
import subprocess, sys, json, numpy as np
FF = "./tools/ffmpeg.exe"
def load(p):
    raw = subprocess.run([FF, "-v", "error", "-i", p, "-vf", "scale=108:192,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(np.int16)
def mad(a): return np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    o, r = load("source/original.mp4"), load(args[0])
    mo, mr = mad(o), mad(r)
    s0 = int(args[1]) // 24 if len(args) > 2 else 0
    s1 = int(args[2]) // 24 if len(args) > 2 else min(len(mo), len(mr)) // 24
    rows = []
    for s in range(s0, s1):
        a, b = mo[s*24:(s+1)*24].mean(), mr[s*24:(s+1)*24].mean()
        rows.append((s, round(float(a), 2), round(float(b), 2), round(float(b / (a + 1e-6)), 2)))
        print(*rows[-1])
    if "--json" in sys.argv[-2:]:
        json.dump(rows, open(sys.argv[-1], "w"))
