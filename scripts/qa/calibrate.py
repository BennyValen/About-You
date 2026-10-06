# Per-scene calibration of the painting layer and the camera speed against gates 4 (speed parity) and 8 (wiggle).
#   1) boil: try candidates at the scene's three gate-8 places (short windows), pick the one whose mean residual
#      flow is closest to the original's (scene 8: scene 4's value) -> work/v3/calib/sXX.json
#   2) after a full post with that boil: camera factor k from the clean and painted per-step motion:
#      MAD(k) ~ m_clean * k + (m_paint - m_clean)  ->  k = (MAD_orig - (m_paint - m_clean)) / m_clean
#   python scripts/qa/calibrate.py boil SCENE      |   python scripts/qa/calibrate.py speed SCENE
import json, os, shutil, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import wiggle_gate as WG                    # noqa: E402
from scene_check import gray_seq, mad       # noqa: E402

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
CAL = "work/v3/calib"


def window_clip(s, paint_dir, a, b, a0, tag):
    seq = f"work/v3/cal_seq_{tag}"
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    for i, f in enumerate(range(a, b)):
        d = f - ((f - a0) % 2)
        os.link(os.path.join(paint_dir, f"f{d:04d}.jpg"), os.path.join(seq, f"{i:05d}.jpg"))
    clip = f"work/v3/cal_{tag}.mp4"
    subprocess.run([FF, "-v", "error", "-y", "-framerate", "24", "-i", os.path.join(seq, "%05d.jpg"), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "16", "-pix_fmt", "yuv420p", clip], check=True)
    shutil.rmtree(seq, ignore_errors=True)
    return clip


def boil(s, cands=(0.6, 0.9, 1.3, 1.8)):
    os.makedirs(CAL, exist_ok=True)
    a0, b0 = CUTS[s - 1], CUTS[s]
    sdir = f"render/v3/scene_{s:02d}"
    places = WG.places(s)
    ref_places = WG.places(4) if s == 8 else places
    target = float(np.mean([WG.wiggle("source/original.mp4", f)[0] for f in ref_places]))
    res = {}
    for bm in cands:
        out = f"work/v3/cal_paint_s{s:02d}"
        shutil.rmtree(out, ignore_errors=True)
        vals = []
        for f in places:
            for attempt in range(3):
                r = subprocess.run([sys.executable, "scripts/post/paint.py", "--scene", str(s), "--dir", sdir, "--out", out, "--frames",
                                    f"{f}-{f + 8}", "--jobs", "4", "--force", "--set", f"boil_mean={bm},wobble={min(0.55, 0.25 * bm):.3f}"],
                                   capture_output=True, text=True)
                if all(os.path.exists(os.path.join(out, f"f{g:04d}.jpg")) for g in range(f, f + 9, 2)):
                    break
                print("post retry", r.stdout[-300:], r.stderr[-600:], flush=True)
            clip = window_clip(s, out, f, f + 8, a0, f"s{s:02d}")
            vals.append(WG.wiggle(clip, 0)[0])
        res[bm] = float(np.mean(vals))
        print(f"s{s:02d} boil {bm}: residual {res[bm]:.2f} (target {target:.2f})  {vals}", flush=True)
    best = min(res, key=lambda k: abs(np.log(max(res[k], 1e-3) / target)))
    json.dump(dict(scene=s, target=target, results=res, boil_mean=best, wobble=min(0.55, 0.25 * best)), open(f"{CAL}/s{s:02d}.json", "w"), indent=1)
    print(f"s{s:02d} -> boil_mean {best}", flush=True)
    return best


def speed(s):
    a, b = CUTS[s - 1], CUTS[s]
    sdir = f"render/v3/scene_{s:02d}"
    org = mad(gray_seq("source/original.mp4", n=b - a, start_frame=a))[: b - a - 1]
    clean = mad(gray_seq(window_clip(s, os.path.join(sdir, "clean"), a, b, a, f"c{s:02d}")))[: b - a - 1]
    paint = mad(gray_seq(window_clip(s, os.path.join(sdir, "paint"), a, b, a, f"p{s:02d}")))[: b - a - 1]
    dist = lambda x: x[x >= 0.05].mean() if (x >= 0.05).any() else 0
    mo, mc, mp = dist(org), dist(clean), dist(paint)
    k = (mo - (mp - mc)) / max(mc, 1e-6)
    cur = 1.0
    sp = "work/v3/speed_scale.json"
    allk = json.load(open(sp)) if os.path.exists(sp) else {}
    cur = float(allk.get(str(s), 1.0))
    knew = float(np.clip(cur * k, 0.5, 2.2))
    print(f"s{s:02d} per-step motion: orig {mo:.2f} clean {mc:.2f} painted {mp:.2f}  ratio {mp / mo:.2f}  -> camera factor x{k:.2f} "
          f"(current {cur:.2f} -> {knew:.2f})", flush=True)
    return mp / mo, knew


if __name__ == "__main__":
    mode, scenes = sys.argv[1], [int(x) for x in sys.argv[2:]]
    for s in scenes:
        if mode == "boil":
            boil(s)
        else:
            speed(s)
