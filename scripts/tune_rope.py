# Offline tuning of the v3 rope per scene against work/thread_stats.json (no rendering).
# The camera follows the measured speed profile; the owner sits at its measured screen position plus the scene's
# owner motion (gait sway, meander, stroke surge, pendulum). The same ROPE configs are imported by the Blender scenes
# (blender/scenes/sXX.py -> rope_cfg.ROPE[s]), so what is tuned here is what renders.
#   python scripts/tune_rope.py [scene ...]
import json, os, sys, time
import numpy as np
sys.path.insert(0, "blender")
from kit import rope as R          # noqa: E402
from kit import rope_cfg as C      # noqa: E402

CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
ST = json.load(open("work/thread_stats.json"))["scenes"]
PROF = json.load(open("work/cam_profile.json"))


def target(s):
    t = ST[str(s)]
    if not t.get("used") or t["used"] < 30:
        # thread mostly hidden in the original (scene 1, 8): use the film median of the well-measured scenes
        good = [ST[str(k)] for k in range(1, 13) if ST[str(k)].get("used", 0) >= 30]
        return dict(rms=float(np.median([g["rms_dev_px"] for g in good])), hz=float(np.median([g["sway_mid_centroid_hz"] for g in good])),
                    std=float(np.median([g["sway_mid_std_px"] for g in good])), fallback=True)
    return dict(rms=t["rms_dev_px"], hz=t["sway_mid_centroid_hz"], std=t["sway_mid_std_px"], fallback=False)


def freq(sig, fs=12.0):
    sig = np.asarray(sig, float)
    if len(sig) < 16:
        return 0.0, 0.0
    tt = np.arange(len(sig))
    sig = sig - np.polyval(np.polyfit(tt, sig, 1), tt)
    sp = np.abs(np.fft.rfft(sig * np.hanning(len(sig)))) ** 2
    fr = np.fft.rfftfreq(len(sig), 1 / fs)
    band = (fr >= 0.1) & (fr <= 3.0)
    return float((sp[band] * fr[band]).sum() / (sp[band].sum() + 1e-9)), float(np.std(sig))


def simulate(s, cfg=None):
    cfg = cfg or C.ROPE[s]
    a, b = CUTS[s - 1], CUTS[s]
    prof = PROF[str(s)]
    ppm = C.PPM[s]
    lens, sensor = 60.0, 24.0
    cam_h = (1920 / ppm) * lens / sensor
    ksc = json.load(open("work/v3/speed_scale.json")).get(str(s), 1.0) if os.path.exists("work/v3/speed_scale.json") else 1.0
    if s == 8:
        prof, ksc = [4.0], 1.0                           # the new scene 8 runs at a constant 4 px/frame
    v = np.array([prof[min(i, len(prof) - 1)] * ksc for i in range(b - a + 2)], float)
    ys = np.concatenate([[0.0], np.cumsum(v)])[: b - a + 2] / ppm

    def cam(t):
        i = np.clip(t - a, 0, b - a)
        return 0.0, float(np.interp(i, np.arange(len(ys)), ys))

    owner = C.owner_motion(s, cfg.get("motion"))
    ox, oy = cfg["owner_px"]
    z = cfg.get("z", 1.0)
    k = ppm * cam_h / (cam_h - z)

    def anchor(t):
        cx, cy = cam(t)
        dx, dy, dz = owner(t)
        return np.array([cx + (ox - 540) / k + dx, cy - (oy - 960) / k + dy, z + dz])

    rp = C.make_rope(s, ppm)
    frames = list(range(a, b, 2))
    t0 = time.time()
    sim = rp.run(frames, anchor, cfg.get("trail", (0.0, -1.0)), warm=cfg.get("warm", 150))
    el = time.time() - t0
    res = []
    for f in frames:
        S, _ = R.screen_points(cam(f), ppm, cam_h, sim[f])
        st = R.chord_stats(S)
        if st:
            res.append(st)
    return res, el, sim, cam, cam_h


def report(s, quiet=False):
    res, el, *_ = simulate(s)
    tg = target(s)
    if not res:
        return f"s{s:02d} no visible thread"
    rms = float(np.median([r["rms"] for r in res]))
    hz, std = freq([r["dev_mid"] for r in res])
    ok_r = 0.6 <= rms / tg["rms"] <= 1.4
    ok_f = 0.6 <= hz / max(tg["hz"], 1e-6) <= 1.4
    line = (f"s{s:02d} rms {rms:6.2f} (orig {tg['rms']:5.2f}, x{rms / tg['rms']:.2f} {'ok' if ok_r else '--'})  sway {hz:.2f} Hz "
          f"(orig {tg['hz']:.2f}, x{hz / max(tg['hz'], 1e-6):.2f} {'ok' if ok_f else '--'})  std {std:5.1f} (orig {tg['std']:.1f})  "
          f"len {np.median([r['length_px'] for r in res]):.0f}px  sim {el:.1f}s{'  [fallback target]' if tg['fallback'] else ''}")
    return line


# ---------------------------------------------------------------- automatic search
def score(s, cfg):
    res, *_ = simulate(s, cfg)
    tg = target(s)
    if not res:
        return 9.0, 0, 0
    rms = float(np.median([r["rms"] for r in res]))
    hz, std = freq([r["dev_mid"] for r in res])
    return abs(np.log(max(rms, 1e-3) / tg["rms"])) + 0.6 * abs(np.log(max(hz, 1e-3) / tg["hz"])), rms, hz


def _job2(args):
    """v4 search: amplitude (capped at plausible values) x wavelength of the lateral wind/current field"""
    s, amp, scale = args
    import copy
    cfg = copy.deepcopy(C.ROPE[s])
    mo = copy.deepcopy(C.MOTION[s])
    key = "current" if cfg["mode"] == "water" else "wind"
    w = cfg[key]
    w["lateral"] = amp
    w["lateral_hz"] = target(s)["hz"]
    w["scale"] = scale
    w["curl"] = min(w.get("curl", 0.3), amp * 0.5)
    if cfg["mode"] == "ground":
        cfg["friction"] = min(cfg.get("friction", 5.0), 8.0)
    cfg["motion"] = mo
    C.ROPE[s] = cfg
    sc, rms, hz = score(s, cfg)
    return s, amp, scale, sc, rms, hz, cfg


def search2(scenes):
    from multiprocessing import Pool
    jobs = []
    for s in scenes:
        cap = 0.6 if C.ROPE[s]["mode"] == "water" else 4.0
        for amp in np.linspace(cap / 6, cap, 6):
            for scale in (0.6, 1.2, 2.5):
                jobs.append((s, float(amp), scale))
    with Pool(15) as pool:
        out = pool.map(_job2, jobs)
    best = {}
    for r in out:
        if r[0] not in best or r[3] < best[r[0]][3]:
            best[r[0]] = r
    for s in scenes:
        b = best[s]
        tg = target(s)
        w = b[6]["current" if b[6]["mode"] == "water" else "wind"]
        print(f"s{s:02d} amp {b[1]:.2f} scale {b[2]}: rms {b[4]:.2f}/{tg['rms']:.2f} hz {b[5]:.2f}/{tg['hz']:.2f}  -> {json_cfg(b[6])}")
    return best


def json_cfg(c):
    import json as _j
    return _j.dumps({k: v for k, v in c.items() if k != "motion"})


def _job(args):
    """knob: the owner's path meander amplitude (ground/water) or the wind sway (air), at the target frequency"""
    s, m, hzf = args
    import copy
    cfg = copy.deepcopy(C.ROPE[s])
    mo = copy.deepcopy(C.MOTION[s])
    th = target(s)["hz"] * hzf
    # v4: the owner travels straight, so the knob is always the wind / current lateral sway at the target frequency
    key = "current" if cfg["mode"] == "water" else "wind"
    w = cfg[key]
    base = w.get("lateral", 0.0) or (0.1 if cfg["mode"] == "water" else 0.3)
    w["lateral"] = base * m
    w["lateral_hz"] = th
    knob = w["lateral"]
    cfg["motion"] = mo
    C.ROPE[s] = cfg                       # make_rope reads the module config
    sc, rms, hz = score(s, cfg)
    return s, m, hzf, sc, rms, hz, knob, th


def search(scenes, mults=(0.5, 1.0, 2.0, 4.0, 8.0, 16.0), hzfs=(0.7, 1.0)):
    from multiprocessing import Pool
    jobs = [(s, m, h) for s in scenes for m in mults for h in hzfs]
    with Pool(15) as pool:
        out = pool.map(_job, jobs)
    best = {}
    for r in out:
        if r[0] not in best or r[3] < best[r[0]][3]:
            best[r[0]] = r
    for s in scenes:
        b = best[s]
        tg = target(s)
        print(f"s{s:02d} best x{b[1]} hzf {b[2]}: score {b[3]:.2f} rms {b[4]:.2f}/{tg['rms']:.2f} hz {b[5]:.2f}/{tg['hz']:.2f} "
              f"-> knob {b[6]:.3f} at {b[7]:.3f} Hz")
    return best


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--search2":
    search2([int(x) for x in sys.argv[2:]])
elif __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--search":
    search([int(x) for x in sys.argv[2:]] or list(range(1, 13)))
elif __name__ == "__main__":
    scenes = [int(x) for x in sys.argv[1:]] or list(range(1, 13))
    from multiprocessing import Pool
    with Pool(min(12, len(scenes))) as pool:
        for line in pool.map(report, scenes):
            print(line)
