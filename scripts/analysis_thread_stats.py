# Measure the red thread in the original, per scene (brief v3, section 4):
#   red line mask (local red contrast + crimson hue) -> trace row by row from the bottom edge up to the owner
#   -> lateral deviation from the straight chord (owner end to far end), curvature, inflections,
#   sway over time (signed deviation at 1/2 and 3/4 of the chord, chord angle) -> work/thread_stats.json
#   Overlays for checking: work/v3/thread_trace/sXX.jpg
#   python scripts/analysis_thread_stats.py [video] [out.json]
import json, os, subprocess, sys
import numpy as np, cv2
from scipy.signal import savgol_filter

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
W, H = 1080, 1920


def line_mask(rgb, scene=0):
    f = rgb.astype(np.float32)
    if scene == 5:
        # scene 5: a darker crimson line on orange sand, so the red-excess contrast is tiny; use green-channel darkness
        g = f[..., 1]
        gl = cv2.GaussianBlur(g, (11, 11), 0)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        return ((gl - g) > 20) & ((f[..., 0] - g) > 85) & (hsv[..., 0] <= 8)
    red = f[..., 0] - np.maximum(f[..., 1], f[..., 2])
    local = cv2.GaussianBlur(red, (9, 9), 0)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    hue = hsv[..., 0].astype(np.int16)
    crimson = (hue >= 168) | (hue <= 8)
    return ((red - local) > 12) & (red > 34) & (f[..., 0] > 100) & crimson


def trace(m, x_hint, max_gap=60, win=6):
    """trace the line upward from the bottom edge; returns array of (y, x) with x the sub-pixel row centroid"""
    h, w = m.shape
    xs = np.arange(w)
    start = None
    for y in range(h - 1, int(h * 0.80), -1):
        row = np.nonzero(m[y])[0]
        if len(row):
            # cluster nearest to the hint
            c = row[np.argmin(np.abs(row - x_hint))]
            if abs(c - x_hint) < 260:
                start = (y, float(c))
                break
    if start is None:
        return None
    pts = [start]
    y, x = start
    gap = 0
    vx = 0.0
    yy = y - 1
    while yy > 0:
        xp = x + vx * (gap + 1)
        lo, hi = int(max(0, xp - win - gap * 0.6)), int(min(w, xp + win + gap * 0.6 + 1))
        seg = m[yy, lo:hi]
        if seg.any():
            cx = lo + np.nonzero(seg)[0]
            nx = float(cx[np.argmin(np.abs(cx - xp))])
            # use the centroid of the run around the nearest pixel
            run = cx[np.abs(cx - nx) <= 3]
            nx = float(run.mean())
            vx = 0.8 * vx + 0.2 * (nx - x) / (gap + 1)
            vx = float(np.clip(vx, -2.5, 2.5))
            x = nx
            pts.append((yy, x))
            gap = 0
        else:
            gap += 1
            if gap > max_gap:
                break
        yy -= 1
    p = np.array(pts)
    return p if len(p) > 60 else None


def stats_of(p):
    """p: (n,2) y,x from bottom to top. chord from the top end (owner) to the bottom end."""
    y, x = p[:, 0], p[:, 1]
    # resample on uniform rows (fill gaps linearly)
    order = np.argsort(y)
    y, x = y[order], x[order]
    yu = np.arange(int(y[0]), int(y[-1]) + 1)
    xu = np.interp(yu, y, x)
    if len(yu) > 41:
        xs = savgol_filter(xu, 41, 3)
    else:
        xs = xu
    a = np.array([xs[0], yu[0]], float)       # top end (owner)
    b = np.array([xs[-1], yu[-1]], float)     # bottom end
    d = b - a
    L = np.linalg.norm(d) + 1e-6
    nrm = np.array([-d[1], d[0]]) / L
    P = np.stack([xs, yu], 1)
    dev = (P - a) @ nrm                       # signed lateral deviation (px)
    t = ((P - a) @ d) / L ** 2
    dx = np.gradient(xs)
    ddx = np.gradient(dx)
    kappa = ddx / (1 + dx ** 2) ** 1.5
    sgn = np.sign(savgol_filter(ddx, 61, 2) if len(ddx) > 61 else ddx)
    infl = int(np.sum(np.abs(np.diff(sgn[np.abs(ddx) > 2e-4])) > 0)) if len(ddx) > 2 else 0
    def at(tt):
        i = np.argmin(np.abs(t - tt))
        return float(dev[i])
    return dict(rms=float(np.sqrt(np.mean(dev ** 2))), maxdev=float(np.max(np.abs(dev))), mean_abs_curv=float(np.mean(np.abs(kappa))),
                inflections_per_1000px=float(infl / max(1.0, L) * 1000), length_px=float(L), top=[float(a[0]), float(a[1])],
                bottom=[float(b[0]), float(b[1])], angle_deg=float(np.degrees(np.arctan2(d[0], d[1]))), dev_mid=at(0.5), dev_34=at(0.75),
                dev_14=at(0.25))


def dominant_freq(sig, fs):
    sig = np.asarray(sig, float)
    if len(sig) < 16:
        return 0.0, 0.0, 0.0
    tt = np.arange(len(sig))
    sig = sig - np.polyval(np.polyfit(tt, sig, 1), tt)
    win = np.hanning(len(sig))
    sp = np.abs(np.fft.rfft(sig * win)) ** 2
    fr = np.fft.rfftfreq(len(sig), 1 / fs)
    ok = fr >= 0.1
    if not ok.any():
        return 0.0, float(np.std(sig)), 0.0
    k = np.argmax(sp * ok)
    # spectral centroid over 0.1..3 Hz as a robust "sway frequency"
    band = (fr >= 0.1) & (fr <= 3.0)
    cen = float((sp[band] * fr[band]).sum() / (sp[band].sum() + 1e-9))
    return float(fr[k]), float(np.std(sig)), cen


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "source/original.mp4"
    outp = sys.argv[2] if len(sys.argv) > 2 else "work/thread_stats.json"
    tag = os.path.splitext(os.path.basename(outp))[0]
    os.makedirs("work/v3/thread_trace", exist_ok=True)
    proc = subprocess.Popen([FF, "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    per = {s: [] for s in range(1, 13)}
    hint = {s: 540.0 for s in range(1, 13)}
    shots = {}
    f = 0
    fsz = W * H * 3
    while True:
        buf = proc.stdout.read(fsz)
        if len(buf) < fsz:
            break
        s = next(i for i in range(12) if CUTS[i] <= f < CUTS[i + 1]) + 1
        a = CUTS[s - 1]
        if (f - a) % 2 == 0:
            rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            m = line_mask(rgb, s)
            p = trace(m, hint[s])
            if p is not None:
                st = stats_of(p)
                st["f"] = f
                per[s].append(st)
                hint[s] = st["bottom"][0]
                mid = (a + CUTS[s]) // 2
                if s not in shots and f >= mid:
                    vis = rgb[..., ::-1].copy()
                    for (yy, xx) in p[::3]:
                        cv2.circle(vis, (int(xx) + 6, int(yy)), 1, (255, 255, 0), -1)
                    cv2.line(vis, tuple(int(v) for v in st["top"]), tuple(int(v) for v in st["bottom"]), (0, 255, 0), 1)
                    shots[s] = cv2.resize(vis, (540, 960))
        f += 1
    proc.wait()
    res = {}
    for s in range(1, 13):
        L = per[s]
        n_draw = (CUTS[s] - CUTS[s - 1]) // 2
        if not L:
            res[s] = dict(found=0, drawings=n_draw)
            continue
        good = [x for x in L if x["length_px"] > 250]
        if not good:
            good = L
        fs = 12.0
        mid = [x["dev_mid"] for x in good]
        q34 = [x["dev_34"] for x in good]
        ang = [x["angle_deg"] for x in good]
        fm = dominant_freq(mid, fs)
        f34 = dominant_freq(q34, fs)
        fa = dominant_freq(ang, fs)
        res[s] = dict(found=len(L), used=len(good), drawings=n_draw,
                      rms_dev_px=float(np.median([x["rms"] for x in good])), rms_dev_p90=float(np.percentile([x["rms"] for x in good], 90)),
                      max_dev_px=float(np.median([x["maxdev"] for x in good])),
                      mean_abs_curv=float(np.median([x["mean_abs_curv"] for x in good])),
                      inflections_per_1000px=float(np.median([x["inflections_per_1000px"] for x in good])),
                      length_px=float(np.median([x["length_px"] for x in good])),
                      owner_xy=[float(np.median([x["top"][0] for x in good])), float(np.median([x["top"][1] for x in good]))],
                      exit_xy=[float(np.median([x["bottom"][0] for x in good])), float(np.median([x["bottom"][1] for x in good]))],
                      chord_angle_deg=float(np.median(ang)),
                      sway_mid_peak_hz=fm[0], sway_mid_std_px=fm[1], sway_mid_centroid_hz=fm[2],
                      sway_34_peak_hz=f34[0], sway_34_std_px=f34[1], sway_34_centroid_hz=f34[2],
                      angle_peak_hz=fa[0], angle_std_deg=fa[1])
        print(s, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res[s].items()})
    json.dump(dict(source=src, method="line mask (red - local red > 12, crimson hue) -> bottom-up row trace -> chord deviation; "
                   "sway = detrended signed deviation at 1/2 and 3/4 of the chord sampled per drawing (12 Hz)", scenes=res, per_drawing=per),
              open(outp, "w"), indent=1)
    if shots:
        keys = sorted(shots)
        cv2.imwrite(f"work/v3/thread_trace/{tag}.jpg", np.hstack([shots[k] for k in keys]), [cv2.IMWRITE_JPEG_QUALITY, 85])


if __name__ == "__main__":
    main()
