# Wiggle calibration (brief v4, 3.1 item 5): for a scene, paint 12 consecutive drawings from the cached clean frames with
#   floor : boil off (v4 stroke jitter)        v3 : v3's settings (coarse boil, v3 jitter)        new : v4 fine boil at scale s
# and measure the residual paint motion between consecutive drawings (phase-correlation alignment + Farneback, mean px
# at 1080). Pick s so that (new - floor) ~ 0.55 x (v3 - floor).  -> work/v4/calib/sXX.json
#   python scripts/qa/wiggle_calib.py SCENE [START_FRAME]
import json, os, shutil, subprocess, sys
import numpy as np, cv2

CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]


def residual(a, b):
    a = cv2.resize(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY), (540, 960)).astype(np.float32)
    b = cv2.resize(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY), (540, 960)).astype(np.float32)
    (dx, dy), _ = cv2.phaseCorrelate(a[150:800, 40:500], b[150:800, 40:500])
    bw = cv2.warpAffine(b, np.float32([[1, 0, -dx], [0, 1, -dy]]), (540, 960), flags=cv2.INTER_CUBIC)
    fl = cv2.calcOpticalFlowFarneback(a.astype(np.uint8), bw.astype(np.uint8), None, 0.5, 4, 25, 5, 7, 1.5, 0)
    return float(np.linalg.norm(fl[200:760, 60:480], axis=2).mean()) * 2


def paint(s, src, out, f0, n, sets):
    shutil.rmtree(out, ignore_errors=True)
    r = subprocess.run([sys.executable, "scripts/post/paint.py", "--scene", str(s), "--dir", src, "--out", out, "--frames",
                        f"{f0}-{f0 + 2 * (n - 1)}", "--jobs", "6", "--force", "--set", sets], capture_output=True, text=True)
    fr = [cv2.imread(os.path.join(out, f"f{f:04d}.jpg")) for f in range(f0, f0 + 2 * n, 2)]
    if any(x is None for x in fr):
        print(r.stdout[-400:], r.stderr[-800:])
        raise SystemExit("paint failed")
    return fr


def mean_residual(fr):
    return float(np.mean([residual(fr[i], fr[i + 1]) for i in range(len(fr) - 1)]))


def calib(s, f0=None, src=None, v3cal=None):
    a, b = CUTS[s - 1], CUTS[s]
    f0 = f0 or a + (((a + b) // 2 - a) // 2) * 2 + 2
    src = src or f"render/v3/scene_{s:02d}"
    v3 = json.load(open(v3cal or f"work/v3/calib/s{s:02d}.json"))
    tmp = f"work/v4/wcal_s{s:02d}"
    floor = mean_residual(paint(s, src, tmp, f0, 12, "boil_mode=fine,boil_scale=0.0"))
    v3r = mean_residual(paint(s, src, tmp, f0, 12, f"boil_mode=coarse,boil_mean={v3['boil_mean']},wobble={v3['wobble']:.3f},"
                                                   f"value_jitter=8,pos_jitter=1.8,angle_jitter=4"))
    target = floor + 0.55 * (v3r - floor)
    res = {}
    for sc in (0.4, 0.6, 0.8, 1.0, 1.3):
        res[sc] = mean_residual(paint(s, src, tmp, f0, 12, f"boil_mode=fine,boil_scale={sc}"))
    best = min(res, key=lambda k: abs(res[k] - target))
    print(f"s{s:02d} frames {f0}..{f0 + 22}: floor {floor:.2f}  v3 {v3r:.2f}  target {target:.2f}  new {{" +
          ", ".join(f"{k}: {v:.2f}" for k, v in res.items()) + f"}}  -> boil_scale {best}  (extra over floor: v3 {v3r - floor:.2f}, "
          f"new {res[best] - floor:.2f}, ratio {(res[best] - floor) / max(v3r - floor, 1e-6):.2f})", flush=True)
    os.makedirs("work/v4/calib", exist_ok=True)
    json.dump(dict(scene=s, frames=[f0, f0 + 22], floor=floor, v3=v3r, target=target, new=res, boil_scale=best),
              open(f"work/v4/calib/s{s:02d}.json", "w"), indent=1)
    shutil.rmtree(tmp, ignore_errors=True)
    return best


if __name__ == "__main__":
    s = int(sys.argv[1])
    calib(s, int(sys.argv[2]) if len(sys.argv) > 2 else None)
