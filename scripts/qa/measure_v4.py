# Corrected measurement tools (brief v4, section 5) + hero tracker.
#   python scripts/qa/measure_v4.py baseline          -> work/baseline.json (original vs v3) and a printed table
#   python scripts/qa/measure_v4.py camera VIDEO      -> camera px per drawing per scene
#   python scripts/qa/measure_v4.py tone VIDEO        -> tone at the target frames
import json, os, subprocess, sys
import numpy as np, cv2

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
ORIG_CAM = {1: 12.3, 2: 14.0, 3: 4.3, 4: 9.8, 5: 5.9, 6: 7.0, 7: 3.4, 8: 8.0, 9: 8.2, 10: 6.2, 11: 9.8, 12: 16.8}


# ---------------------------------------------------------------- section 5: camera speed by phase correlation
def gray_frames(p, start, n=8):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{start/24:.4f}", "-i", p,
                          "-vf", "scale=540:960,format=gray", "-frames:v", str(n), "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 960, 540).astype(np.float32)


def distinct_pair(f):
    for i in range(len(f) - 1):
        if np.abs(f[i + 1] - f[i]).mean() > 0.3:
            return f[i], f[i + 1]
    return f[0], f[1]


def camera_px_per_drawing(p, start):          # at 1080 px wide
    a, b = distinct_pair(gray_frames(p, start))
    r = [cv2.phaseCorrelate(a[150:850, x0:x1], b[150:850, x0:x1]) for x0, x1 in ((20, 170), (370, 520))]
    (dx, dy), _ = max(r, key=lambda t: t[1])
    return abs(dy) * 2


def camera_table(p):
    out = {}
    for i in range(12):
        a, b = CUTS[i], CUTS[i + 1]
        pts = [a + int((b - a) * q) for q in (0.25, 0.55, 0.8)]
        out[i + 1] = [round(camera_px_per_drawing(p, x), 1) for x in pts]
    return out


# ---------------------------------------------------------------- tone
def tone(p, n):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{n/24:.4f}", "-i", p, "-vf", "scale=540:960",
                          "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    im = np.frombuffer(raw, np.uint8).reshape(960, 540, 3)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).ravel()
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    sat = hsv[hsv[:, 2] > 40, 1].mean() / 255
    return round(float(g.mean()), 1), int(np.percentile(g, 5)), int(np.percentile(g, 95)), round(float(sat), 2)


# ---------------------------------------------------------------- connectivity
def one_piece(alpha):                  # alpha: uint8 mask (0 or 255) of the hero rendered alone
    m = (alpha > 127).astype(np.uint8)
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))      # tolerate 1 px seams only
    n, _ = cv2.connectedComponents(m)
    return (n - 1) == 1


# ---------------------------------------------------------------- collisions (scene 6)
def collider_overlaps(path="work/colliders.csv", verbose=True):
    import csv, itertools
    from shapely.geometry import Point
    from shapely import affinity

    def ell(cx, cy, rx, ry, deg):
        return affinity.rotate(affinity.scale(Point(cx, cy).buffer(1), rx, ry), deg, origin=(cx, cy))
    rows = list(csv.DictReader(open(path)))
    by = {}
    for r in rows:
        by.setdefault((r["frame"], r["layer"]), []).append(r)
    bad = 0
    for (fr, layer), objs in by.items():
        shp = [(o["id"], ell(*(float(o[k]) for k in ("cx", "cy", "rx", "ry", "deg")))) for o in objs]
        for (ia, a), (ib, b) in itertools.combinations(shp, 2):
            if a.buffer(-1).intersects(b.buffer(-1)):    # allow 1 px touching
                bad += 1
                if verbose and bad <= 20:
                    print("OVERLAP", fr, layer, ia, ib)
    print("overlaps:", bad)
    return bad


# ---------------------------------------------------------------- hero tracker (template matching, seeded box)
def video_frames(p, a, b, step=2, scale=0.5):
    w, h = int(1080 * scale), int(1920 * scale)
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{a/24:.4f}", "-i", p, "-frames:v", str(b - a), "-vf", f"scale={w}:{h},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, h, w)
    return f[::step]


def track(p, scene, seed_frame, box, search=40, scale=0.5):
    """box: (cx, cy, w, h) at 1080 px, at seed_frame. Returns {frame: (cx, cy)} at 1080 px for every drawing."""
    a, b = CUTS[scene - 1], CUTS[scene]
    fr = video_frames(p, a, b, 2, scale)
    frames = list(range(a, b, 2))[:len(fr)]
    k0 = frames.index(seed_frame - ((seed_frame - a) % 2))
    cx, cy, w, h = [v * scale for v in box]
    tw, th = int(w), int(h)

    def cut(img, x, y):
        x0, y0 = int(round(x - tw / 2)), int(round(y - th / 2))
        return img[y0:y0 + th, x0:x0 + tw].astype(np.float32)
    out = {}
    for direction in (1, -1):
        x, y = cx, cy
        tmpl = cut(fr[k0], x, y)
        k = k0
        while 0 <= k < len(fr):
            img = fr[k].astype(np.float32)
            s = int(search * scale)
            x0, y0 = int(max(0, x - tw / 2 - s)), int(max(0, y - th / 2 - s))
            x1, y1 = int(min(img.shape[1], x + tw / 2 + s)), int(min(img.shape[0], y + th / 2 + s))
            win = img[y0:y1, x0:x1]
            if win.shape[0] > th and win.shape[1] > tw:
                res = cv2.matchTemplate(win, tmpl, cv2.TM_CCOEFF_NORMED)
                _, _, _, mx = cv2.minMaxLoc(res)
                x, y = x0 + mx[0] + tw / 2, y0 + mx[1] + th / 2
                new = cut(fr[k], x, y)
                if new.shape == tmpl.shape:
                    tmpl = 0.85 * tmpl + 0.15 * new
            out[frames[k]] = (x / scale, y / scale)
            k += direction
    return dict(sorted(out.items()))


def excursion(xs, frames, win=48):
    """median over 48-frame windows of the peak-to-peak lateral position after removing linear drift"""
    xs, frames = np.asarray(xs, float), np.asarray(frames)
    vals = []
    for f0 in range(frames[0], frames[-1] - win + 1, 12):
        m = (frames >= f0) & (frames < f0 + win)
        if m.sum() < 6:
            continue
        t, x = frames[m], xs[m]
        x = x - np.polyval(np.polyfit(t, x, 1), t)
        vals.append(x.max() - x.min())
    return float(np.median(vals)) if vals else 0.0


SEEDS = {7: (2300, (540, 1185, 300, 110)), 12: (3700, (403, 1300, 90, 90))}


def baseline():
    res = {"camera": {}, "tone": {}, "hero": {}}
    for tag, p in (("original", "source/original.mp4"), ("v3", "source/v3.mp4")):
        res["camera"][tag] = camera_table(p)
        res["tone"][tag] = {str(n): tone(p, n) for n in (146, 2570, 3482)}
        for s, (sf, box) in SEEDS.items():
            tr = track(p, s, sf, box)
            fr = list(tr)
            res["hero"].setdefault(tag, {})[str(s)] = dict(excursion_px=round(excursion([tr[f][0] for f in fr], fr), 1),
                                                         x_range=[round(min(v[0] for v in tr.values())), round(max(v[0] for v in tr.values()))])
    json.dump(res, open("work/baseline.json", "w"), indent=1)
    print("camera px per drawing (3 samples per scene)        original | v3")
    for s in range(1, 13):
        o, v = res["camera"]["original"][s], res["camera"]["v3"][s]
        print(f"  s{s:02d}  {o}  mean {np.mean(o):5.1f}   |  {v}  mean {np.mean(v):5.1f}   (brief: {ORIG_CAM[s]})")
    print("tone (mean luma, p5, p95, sat)        original | v3")
    for n in ("146", "2570", "3482"):
        print(f"  f{n}: {res['tone']['original'][n]}  |  {res['tone']['v3'][n]}")
    print("hero lateral excursion per 4 s (template tracker)   original | v3")
    for s in ("7", "12"):
        print(f"  s{s}: {res['hero']['original'][s]}  |  {res['hero']['v3'][s]}")
    return res


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "baseline":
        baseline()
    elif mode == "camera":
        t = camera_table(sys.argv[2])
        for s, v in t.items():
            print(s, v, "mean", round(float(np.mean(v)), 1), "orig", ORIG_CAM[s], "ratio", round(float(np.mean(v)) / ORIG_CAM[s], 2))
    elif mode == "tone":
        for n in (146, 2570, 3482):
            print(n, tone(sys.argv[2], n))
    elif mode == "collide":
        collider_overlaps()
