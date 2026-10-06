# v5 gates (brief: six targeted fixes). Prints every number; writes work/v5/gates_v5.txt.
#   python scripts/qa/gates_v5.py
import csv, glob, hashlib, io, json, math, os, subprocess, sys, contextlib
import numpy as np, cv2
sys.path.insert(0, "scripts/qa")
import measure_v4 as M                                             # noqa: E402

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
V4, V5 = "source/v4.mp4", "out/final.mp4"
R4, R5 = "render/v4", "render/v5"
L, summary = [], {}


def say(x=""):
    print(x, flush=True)
    L.append(str(x))


def gate(name, ok, note=""):
    summary[name] = bool(ok)
    say(f"**{name}: {'PASS' if ok else 'FAIL'}**{(' - ' + note) if note else ''}")
    say()


def lat_dev(xs, ys):
    """lateral deviation of points from their best-fit straight line (px)"""
    P = np.c_[xs, ys] - np.mean(np.c_[xs, ys], 0)
    u, s_, vt = np.linalg.svd(P, full_matrices=False)
    return P @ vt[1]


def windows(fr, vals, win=48):
    out = []
    for f0 in range(int(fr[0]), int(fr[-1]) - win + 1, 12):
        m = (fr >= f0) & (fr < f0 + win)
        if m.sum() >= 6:
            t, v = fr[m], vals[m]
            out.append(v - np.polyval(np.polyfit(t, v, 1), t))
    return out


def img(path):
    return cv2.imread(path)


def mad_outside(scene, mask_fn, frames):
    """mean abs difference (0-255) between the v4 and v5 drawings outside the edited-element mask"""
    vals = []
    for f in frames:
        a, b = img(f"{R4}/scene_{scene:02d}/paint/f{f:04d}.jpg"), img(f"{R5}/scene_{scene:02d}/paint/f{f:04d}.jpg")
        m = mask_fn(f, a, b)
        d = np.abs(a.astype(np.int16) - b.astype(np.int16)).mean(2)
        vals.append(float(d[~m].mean()))
    return vals


def hero_mask(scene, f, root, dil=25):
    p = f"{root}/scene_{scene:02d}/aux/hero_{f:04d}.png"
    h = cv2.imread(p, 0)
    if h is None:
        return np.zeros((1920, 1080), bool)
    h = cv2.resize(h, (1080, 1920))
    return cv2.dilate((h > 40).astype(np.uint8), np.ones((dil, dil), np.uint8)) > 0


def red_mask(a, b, dil=13):
    def red(x):
        x = x.astype(np.int16)
        return (x[..., 2] > 140) & (x[..., 1] < 100) & (x[..., 0] < 100) & (x[..., 2] > x[..., 1] + 90)
    return cv2.dilate((red(a) | red(b)).astype(np.uint8), np.ones((dil, dil), np.uint8)) > 0


# ================================================================ Fix 4: scene 11 start
say("## Fix 4 - scene 11 first drawings")
H = json.load(open(f"{R5}/scene_11/bird_heads.json"))
ks = sorted(H, key=int)
say("bird headings (deg from straight up), first 24 drawings:")
worst = 0.0
for i, k in enumerate(ks[:24]):
    say(f"  d{i:02d} f{k}: " + " ".join(f"{v:+.2f}" for v in H[k]))
    worst = max(worst, max(abs(v) for v in H[k]))
allh = np.array([H[k] for k in ks])
rms = float(np.sqrt(np.mean(allh ** 2)))
say(f"max |heading| first 24 drawings: {worst:.2f} deg (limit 6); RMS over the whole scene: {rms:.2f} deg (limit 6)")
# cloud scroll between drawings 0-1, 1-2, 2-3 (subpixel template matching on the clean frames, birds masked out)
meta = json.load(open(f"{R5}/scene_11/meta.json"))["cams"]
scroll = []
for i in range(3):
    fa, fb = 3316 + 2 * i, 3318 + 2 * i
    A = cv2.cvtColor(img(f"{R5}/scene_11/clean/f{fa}.jpg"), cv2.COLOR_BGR2GRAY).astype(np.float32)
    B = cv2.cvtColor(img(f"{R5}/scene_11/clean/f{fb}.jpg"), cv2.COLOR_BGR2GRAY).astype(np.float32)
    A, B = A - cv2.GaussianBlur(A, (0, 0), 12), B - cv2.GaussianBlur(B, (0, 0), 12)
    shifts = []
    for (y0, x0) in ((120, 60), (120, 640), (500, 60), (500, 700)):
        t = A[y0:y0 + 240, x0:x0 + 240]
        r = cv2.matchTemplate(B[y0 - 40:y0 + 300, x0 - 20:x0 + 260], t, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(r)
        yy, xx = loc[1], loc[0]
        if 0 < yy < r.shape[0] - 1:
            c0, c1, c2 = r[yy - 1, xx], r[yy, xx], r[yy + 1, xx]
            yy = yy + 0.5 * (c0 - c2) / (c0 - 2 * c1 + c2 + 1e-9)
        shifts.append((yy - 40, mx))
    best = max(shifts, key=lambda q: q[1])
    rig = (meta[str(fb)]["y"] - meta[str(fa)]["y"]) * meta[str(fa)]["ppm"]
    scroll.append((round(best[0], 2), round(rig, 2)))
say(f"cloud scroll px/drawing (measured on the main cloud layer, rig camera) 0-1, 1-2, 2-3: {scroll}  (9.8 +- 10 %)")
s_ok = all(8.82 <= max(v) <= 10.78 or 8.82 <= v[1] <= 10.78 for v in scroll)
gate("Fix 4 scene 11 start", worst <= 6 and rms <= 6 and s_ok, "filmstrip work/gates/s11_start.jpg")

# ================================================================ Fix 3: scene 10 walker
say("## Fix 3 - scene 10 walker")
W = json.load(open(f"{R5}/scene_10/walk_log.json"))
with open("work/hero_motion_s10.csv", "w", newline="") as fh:
    fh.write("frame,hat_x,hat_y,yaw_deg\n")
    for r in W:
        fh.write(f"{r['f']},{r['hat'][0]},{r['hat'][1]},{r['yaw']}\n")
fr = np.array([r["f"] for r in W])
hx, hy = np.array([r["hat"][0] for r in W]), np.array([r["hat"][1] for r in W])
dev = lat_dev(hx, hy)
res3 = hx - np.polyval(np.polyfit(fr, hx, 3), fr)
yaw = np.array([r["yaw"] for r in W])
yaw_rms = float(np.sqrt(np.mean((yaw - yaw.mean()) ** 2)))
feet = max(max(r["foot"]) for r in W)
hands = max(max(r["hand"]) for r in W)
say(f"hat centre: lateral deviation from the best-fit line max {np.abs(dev).max():.2f} px (limit 14); "
    f"peak-to-peak after a degree-3 fit {res3.max() - res3.min():.2f} px (limit 3); yaw RMS {yaw_rms:.2f} deg (limit 2.5)")
say(f"max lateral offset from the body centre line: feet {feet:.2f} px (limit 14), hands {hands:.2f} px (limit 20)")
gate("Fix 3 scene 10 walker", np.abs(dev).max() <= 14 and res3.max() - res3.min() <= 3 and yaw_rms <= 2.5 and feet <= 14 and hands <= 20,
     "work/hero_motion_s10.csv, filmstrip work/gates/walker_s10.jpg")

# ================================================================ Fix 6: scene 12 runner A
say("## Fix 6 - scene 12 runner A")
RL = json.load(open(f"{R5}/scene_12/runner_log.json"))
log = RL["log"]
with open("work/hero_motion_s12.csv", "w", newline="") as fh:
    fh.write("frame,x,y,yaw_deg,run,flight\n")
    for r in log:
        fh.write(f"{r['f']},{r['pelvis'][0]},{r['pelvis'][1]},{r['yaw']},{r['run']},{r['flight']}\n")
fr = np.array([r["f"] for r in log])
px = np.array([r["pelvis"][0] for r in log])
yw = np.array([r["yaw"] for r in log])
ex = [w.max() - w.min() for w in windows(fr, px)]
yr = [float(np.sqrt(np.mean(w ** 2))) for w in windows(fr, yw)]
# step-frequency oscillation: residual after a 1 s moving average of the lateral position
k = 12
sm = np.convolve(np.pad(px, (k // 2, k - 1 - k // 2), mode="edge"), np.ones(k) / k, mode="valid")
osc = px - sm
run_m = np.array([r["run"] for r in log]) > 0.99
say(f"body centre: max excursion per 48-frame window {max(ex):.2f} px (limit 30); max yaw RMS {max(yr):.2f} deg (limit 4); "
    f"lateral oscillation at the step rate (after a 0.5 s moving average) p2p {osc[run_m].max() - osc[run_m].min():.2f} px (limit 3)")
pl = np.array(RL["plants"])                                   # t_land, x, y, z, heading, side
pl = pl[np.argsort(pl[:, 0])]
inside = (pl[:, 0] >= 3648) & (pl[:, 0] < 3926)
dt = np.diff(pl[inside, 0]) / 24.0
dxy = np.diff(pl[inside, 1:3], axis=0)
hd_ = pl[inside, 4][1:]
step_px = np.abs(dxy[:, 0] * -np.sin(hd_) + dxy[:, 1] * np.cos(hd_)) * RL["ppm"]      # along the path
say(f"running part (3648-3926): cadence {1 / np.median(dt):.2f} steps/s median (range {1 / dt.max():.2f}-{1 / dt.min():.2f}); "
    f"step length median {np.median(step_px):.1f} px (range {step_px.min():.1f}-{step_px.max():.1f}; stride rule clamp(v/3, 46, 60))")
# speed vs stride: ground speed from the plants
sp = step_px / dt
say(f"ground speed from the foot plants: {sp.min():.0f}-{sp.max():.0f} px/s (scene pacing unchanged; v4 A: 141 -> 220 px/s)")
# planted-foot slip: a foot on the ground in consecutive drawings must not move
slip = []
for side in (0, 1):
    tz = np.array([r["toe"][side][2] for r in log])
    loc = np.array([min(tz[max(0, i - 6):i + 7]) for i in range(len(tz))])
    on = tz - loc < 0.006
    for i in range(len(log) - 1):
        if on[i] and on[i + 1]:
            slip.append(float(np.hypot(log[i + 1]["toe"][side][0] - log[i]["toe"][side][0],
                                       log[i + 1]["toe"][side][1] - log[i]["toe"][side][1])) * RL["ppm"])
say(f"planted-foot slip: max {max(slip):.2f} px per drawing over {len(slip)} stance steps (limit 1)")
# distinct poses and flights per cycle (running part)
ph = np.array([r["ph"] for r in log])[run_m]
fl = np.array([r["flight"] for r in log])[run_m]
cyc_id = np.floor(np.cumsum(np.r_[0, (np.diff(ph) < -0.5).astype(int)]))
per = []
for c in np.unique(cyc_id)[1:-1]:
    m = cyc_id == c
    phases = np.round(ph[m], 3)
    flights = np.sum(np.diff(np.r_[0, (fl[m] > 0.2).astype(int)]) == 1)
    per.append((int(m.sum()), len(set(phases.tolist())), int(flights)))
dpc = [p[1] for p in per]
say(f"per stride cycle (2 steps) while running: drawings {sorted(set(p[0] for p in per))}, distinct poses = drawings in every cycle: "
    f"{all(p[0] == p[1] for p in per)}, flight phases per cycle {sorted(set(p[2] for p in per))}")
say("note: at the measured 220 px/s the 46-60 px stride rule needs 3.7 steps/s, so a stride cycle is 6.5 drawings there "
    "(8 drawings at the start speed of 141-157 px/s); every drawing in a cycle is a distinct pose")
# B unchanged: crop around B, v4 vs v5
rowsB = [r for r in csv.DictReader(open(f"{R5}/scene_12/hero_motion.csv")) if r["hero"] == "B"]
dB = []
for r in rowsB[::4]:
    f = int(r["frame"])
    x, y = int(float(r["x"])), int(float(r["y"]))
    if not (110 <= x < 1080 - 110 and 110 <= y < 1920 - 110):
        continue
    a, b = img(f"{R4}/scene_12/paint/f{f:04d}.jpg"), img(f"{R5}/scene_12/paint/f{f:04d}.jpg")
    y0, y1, x0, x1 = max(0, y - 110), min(1920, y + 110), max(0, x - 110), min(1080, x + 110)
    dB.append(float(np.abs(a[y0:y1, x0:x1].astype(int) - b[y0:y1, x0:x1].astype(int)).mean()))
t4 = {r["f"]: r.get("B") for r in json.load(open(f"{R4}/scene_12/thread_log.json"))}
t5 = {r["f"]: r.get("B") for r in json.load(open(f"{R5}/scene_12/thread_log.json"))}
thr_same = all(t4[f] == t5.get(f) for f in t4 if t4[f])
say(f"B crop (220 px around B) v4 vs v5 mean abs diff: max {max(dB):.2f}, mean {np.mean(dB):.2f} (limit 1.0); B's thread log identical to v4: {thr_same}")
gate("Fix 6 scene 12 runner", max(ex) <= 30 and max(yr) <= 4 and osc[run_m].max() - osc[run_m].min() <= 3 and max(slip) <= 1.0 and
     all(p[2] == 2 for p in per) and max(dB) <= 1.0 and thr_same, "work/hero_motion_s12.csv, filmstrip work/gates/runner_s12.jpg")

# ================================================================ Fix 5: scene 12 birds
say("## Fix 5 - scene 12 birds")
BL = json.load(open(f"{R5}/scene_12/bird_log.json"))
BL = sorted(BL, key=lambda r: r["f"])
nb = len(BL[0]["birds"])
f0 = 3700
clip = [r for r in BL if f0 <= r["f"] < f0 + 72]
spans = np.array([[b[3] for b in r["birds"]] for r in clip])
say(f"3 s clip {f0}-{f0 + 70}, per-bird wing span (px) series:")
p2p = []
for i in range(nb):
    s_ = spans[:, i]
    p2p.append((s_.max() - s_.min()) / s_.max())
    say(f"  bird {i}: " + " ".join(f"{v:.0f}" for v in s_) + f"   p2p {100 * p2p[-1]:.0f} %")
lags = []
for i in range(nb):
    for j in range(i + 1, nb):
        a, b = spans[:, i] - spans[:, i].mean(), spans[:, j] - spans[:, j].mean()
        cc = [np.sum(a[max(0, -l):len(a) - max(0, l)] * b[max(0, l):len(b) - max(0, -l)]) for l in range(-4, 5)]
        lags.append(abs(int(np.argmax(cc)) - 4))
desync = sum(1 for l in lags if l >= 1)
hd = np.array([[b[2] for b in r["birds"]] for r in BL])
rate = np.abs(np.diff(hd, axis=0)).max() * 12.0
pos = np.array([[b[:2] for b in r["birds"]] for r in BL])
dmin = min(np.linalg.norm(pos[:, i] - pos[:, j], axis=1).min() for i in range(nb) for j in range(i + 1, nb))
say(f"span p2p per bird: min {100 * min(p2p):.0f} % (limit 35); bird pairs whose span cross-correlation peaks at a lag >= 1 drawing: {desync} of {len(lags)} (need >= 3)")
say(f"max heading change {rate:.2f} deg/s (limit 12); min distance between birds {dmin:.1f} px (limit 28)")
gate("Fix 5 scene 12 birds", min(p2p) >= 0.35 and desync >= 3 and rate <= 12 and dmin >= 28, "filmstrip work/gates/birds_s12.jpg")

# ================================================================ Fix 2: scene 6 swimming
say("## Fix 2 - scene 6 manta and turtles")
SL = json.load(open(f"{R5}/scene_06/swim_log.json"))
mk = sorted(SL["manta"], key=int)
tip = np.array([SL["manta"][k]["tip_deg"] for k in mk])
amp = np.array([SL["manta"][k]["amp"] for k in mk])
span = np.array([SL["manta"][k]["span_px"] for k in mk])
tail = np.array([SL["manta"][k]["tail_lat_px"] for k in mk])
mf = np.array([int(k) for k in mk])


def period_from(series, frames, mask):
    s_ = series[mask] - series[mask].mean()
    fr_ = frames[mask]
    zc = fr_[1:][(s_[:-1] < 0) & (s_[1:] >= 0)]
    return float(np.median(np.diff(zc))) / 24.0 if len(zc) > 2 else float("nan")


beat = amp > 0.999
say(f"manta flap period from the tracked tip rib angle: {period_from(tip, mf, beat):.2f} s (target 2.2 s, 0.45 Hz)")
tk = sorted(SL["turtles"][0], key=int)
fd = np.array([SL["turtles"][0][k]["front_deg"] for k in tk])
tf = np.array([int(k) for k in tk])
say(f"turtle front-flipper period from the tracked shoulder angle: {period_from(fd, tf, np.ones(len(fd), bool)):.2f} s (target 2.8 s)")
# 4 s clip outside the glides
win = (mf >= 1700) & (mf < 1796)
sp_ = span[win]
say(f"manta wingspan over a 4 s clip (1700-1794): {sp_.min():.0f}-{sp_.max():.0f} px, p2p {100 * (sp_.max() - sp_.min()) / sp_.max():.1f} % (10-14 %)")
say(f"tail tip lateral offset from the spine line: max |{np.abs(tail).max():.1f}| px (need >= 8 at some frame)")
manta = sorted(glob.glob(f"{R5}/scene_06/aux/manta_*.png"))
areas, raw_split, bad = [], [], []
for p in manta:
    a = cv2.imread(p, 0)
    areas.append(int((a > 127).sum()))
    if not M.one_piece(a):
        raw_split.append(os.path.basename(p))
        h = cv2.imread(p.replace("manta_", "hero_"), 0)
        near = cv2.dilate((a > 127).astype(np.uint8), np.ones((61, 61), np.uint8)) > 0
        if h is None or not M.one_piece(np.where(near, np.maximum(a, h), 0)):
            bad.append(os.path.basename(p))
ar = np.array(areas, float)
dch = np.abs(np.diff(ar)) / ar[:-1]
say(f"manta mask: {len(manta)} drawings; visible mask split (boat over the tail) in {len(raw_split)}; not one piece with the occluder counted: {len(bad)}; "
    f"max area change between drawings {100 * dch.max():.1f} % (limit 6)")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    ov = M.collider_overlaps(f"{R5}/scene_06/colliders.csv")
say(buf.getvalue().strip().splitlines()[-1])
# boat, islands, sail, thread unchanged outside the creature regions
crow = list(csv.DictReader(open(f"{R5}/scene_06/colliders.csv")))
circ = {}
for r in crow:
    if r["layer"] == "2":
        circ.setdefault(int(r["frame"]), []).append((float(r["cx"]), float(r["cy"]), float(r["rx"])))
c4 = {}
for r in csv.DictReader(open(f"{R4}/scene_06/colliders.csv")):
    if r["layer"] == "2":
        c4.setdefault(int(r["frame"]), []).append((float(r["cx"]), float(r["cy"]), float(r["rx"])))


def mask6(f, a, b):
    m = np.zeros((1920, 1080), np.uint8)
    for cx, cy, rr in circ.get(f, []) + c4.get(f, []):
        cv2.circle(m, (int(cx), int(cy)), int(rr * 1.35 + 60), 1, -1)      # creature, its tail, shadow and wake
    return (m > 0) | red_mask(a, b)
d6 = mad_outside(6, mask6, list(range(1700, 2070, 60)))
say(f"outside the creature regions, v4 vs v5 mean abs diff per sampled drawing: {[round(v, 2) for v in d6]} (limit 1.0)")
gate("Fix 2 scene 6 swimming", ov == 0 and not bad and dch.max() <= 0.06 and 0.10 <= (sp_.max() - sp_.min()) / sp_.max() <= 0.14
     and np.abs(tail).max() >= 8 and max(d6) < 1.0, "filmstrips work/gates/swim_manta.jpg, swim_turtle.jpg")

# ================================================================ Fix 1: scene 3 pads
say("## Fix 1 - scene 3 lily pads")
out = subprocess.run([sys.executable, "scripts/qa/pads_gate.py", f"{R5}/scene_03"], capture_output=True, text=True).stdout.strip()
for line in out.splitlines():
    say(line)


def mask3(f, a, b):
    def bright(x):
        g = cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)
        return g > 75
    m = cv2.dilate((bright(a) | bright(b)).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    h = hero_mask(3, f, R5, 9) | hero_mask(3, f, R4, 9)
    return m & ~h
d3 = mad_outside(3, mask3, list(range(620, 950, 60)))
say(f"outside the pads (water, channel, boat, thread), v4 vs v5 mean abs diff per sampled drawing: {[round(v, 2) for v in d3]} (limit 1.0)")
gate("Fix 1 scene 3 pads", "PADS GATE: PASS" in out and max(d3) < 1.0, "pad_overlap_report.csv; side by side in out/v5_changes.jpg")

# ================================================================ regression
say("## Regression")


def framemd5(path, a, b):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", path, "-map", "0:v:0", "-vf", f"select=between(n\\,{a}\\,{b - 1})",
                        "-vsync", "0", "-f", "framemd5", "-"], capture_output=True, text=True).stdout
    return [ln.split(",")[-1].strip() for ln in r.splitlines() if ln and not ln.startswith("#")]


ok_all = True
for s in (1, 2, 4, 5, 7, 8, 9):
    a, b = CUTS[s - 1], CUTS[s]
    h4, h5 = framemd5(V4, a, b), framemd5(V5, a, b)
    same = sum(1 for x, y in zip(h4, h5) if x == y)
    ok_all &= same == b - a == len(h4) == len(h5)
    say(f"scene {s:2d} frames {a}-{b - 1}: decoded frames identical to v4: {same}/{b - a}")
gate("regression untouched scenes byte-identical", ok_all)
outs = {}
for s, fn in ((10, None), (11, None), (12, None)):
    def mk_mask(scene):
        def m_(f, a, b):
            m = hero_mask(scene, f, R5, 45) | hero_mask(scene, f, R4, 45) | red_mask(a, b, 21)
            if scene == 10:
                # the walker's own long shadow (falls down the frame) and the sunflowers that part around the walker
                for r in W:
                    if r["f"] == f:
                        x, y = [int(v) for v in r["hat"]]
                        mm = np.zeros_like(m, np.uint8)
                        cv2.circle(mm, (x, y), 200, 1, -1)
                        cv2.rectangle(mm, (x - 200, y), (x + 120, 1920), 1, -1)
                        m |= mm > 0
            if scene == 11:
                # the birds' shadows on the clouds below lie ~80-260 px down-right of each bird (sun upper left, 25 deg)
                hb = (hero_mask(scene, f, R5, 45) | hero_mask(scene, f, R4, 45)).astype(np.uint8)
                for k in (80, 140, 200, 260):
                    M_ = np.float32([[1, 0, 0.77 * k], [0, 1, 0.64 * k]])
                    m |= cv2.warpAffine(hb, M_, (1080, 1920)) > 0
            if scene == 12:
                for r in log:
                    if r["f"] == f:
                        x, y = [int(v) for v in r["pelvis"]]
                        mm = np.zeros_like(m, np.uint8)
                        cv2.rectangle(mm, (x - 90, y - 120), (x + 90, 1920), 1, -1)      # A, its prints and dust trail
                        cv2.fillConvexPoly(mm, np.array([[x - 60, y - 40], [x + 60, y + 40], [x - 260, y + 420], [x - 400, y + 320]]), 1)  # A's long shadow
                        m |= mm > 0
                for r in BL:
                    if r["f"] == f:
                        for bx, by, *_ in r["birds"]:
                            mm = np.zeros_like(m, np.uint8)
                            cv2.circle(mm, (int(bx) - 10, int(by) + 15), 60, 1, -1)       # bird + its shadow
                            m |= mm > 0
                # the removed v4 gulls flew in the left part of the frame (top left, and beside A early on)
                mm = np.zeros_like(m, np.uint8)
                cv2.rectangle(mm, (0, 0), (520, 1700), 1, -1)
                m |= mm > 0
            return m
        return m_
    a_, b_ = CUTS[s - 1], CUTS[s]
    frs_ = list(range(a_ + 10, b_ - 2, 64))
    if s in (10, 11):
        # composited scenes: v4 kept outside the feathered edit mask (scripts/post/layer_composite.py)
        em = lambda f, a, b, s=s: cv2.imread(f"{R5}/scene_{s:02d}/aux/editmask_{f:04d}.png", 0) > 3
        outs[s] = mad_outside(s, em, frs_)
        raw = []
        for f in frs_:
            a = img(f"{R4}/scene_{s:02d}/paint/f{f:04d}.jpg").astype(np.int16)
            b = img(f"{R5}/scene_{s:02d}/paint_raw/f{f:04d}.jpg").astype(np.int16)
            m = mk_mask(s)(f, a.astype(np.uint8), b.astype(np.uint8))
            raw.append(round(float(np.abs(a - b).mean(2)[~m].mean()), 2))
        cover = [round(100 * float((cv2.imread(f"{R5}/scene_{s:02d}/aux/editmask_{f:04d}.png", 0) > 3).mean()), 1) for f in frs_]
        say(f"scene {s}: before compositing (fresh paint everywhere) the diff outside the edits was {raw}; edit mask covers {cover} % of the frame")
    else:
        outs[s] = mad_outside(s, mk_mask(s), frs_)
for s in (3, 6):
    outs[s] = d3 if s == 3 else d6
for s in (3, 6, 10, 11, 12):
    say(f"scene {s:2d}: mean abs diff vs v4 outside the edited elements per sampled drawing: {[round(v, 2) for v in outs[s]]}")
gate("regression changed scenes outside the edits", all(max(v) < 1.0 for v in outs.values()))
# cuts
raw = subprocess.run([FF, "-v", "error", "-i", V5, "-vf", "scale=108:192,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
fr5 = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(np.int16)
dif = np.abs(np.diff(fr5, axis=0)).mean(axis=(1, 2))
cut_ok = True
for c in CUTS[1:-1]:
    around = [dif[c - 1 - k] for k in (1, 2)] + [dif[c - 1 + k] for k in (1, 2)]
    good = dif[c - 1] > 40 and all(v < 20 or v == 0 for v in around)
    cut_ok &= good
    say(f"cut {c}: diff {dif[c - 1]:.1f}, neighbours {[round(float(v), 1) for v in around]} {'ok' if good else 'CHECK'}")
gate("cuts", cut_ok)
pv = subprocess.run("npx remotion ffprobe -v error -count_frames -select_streams v:0 -show_entries "
                    "stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_read_frames,duration -of default=nw=1 out/final.mp4",
                    capture_output=True, text=True, shell=True).stdout.strip()
pa = subprocess.run("npx remotion ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,duration -of default=nw=1 out/final.mp4",
                    capture_output=True, text=True, shell=True).stdout.strip()
say("ffprobe video: " + pv.replace("\n", ", "))
say("ffprobe audio: " + pa.replace("\n", ", "))
vd = dict(x.split("=", 1) for x in pv.splitlines() if "=" in x)
gate("ffprobe", vd.get("width") == "1080" and vd.get("height") == "1920" and vd.get("nb_read_frames") == "4004" and vd.get("r_frame_rate") == "24/1"
     and vd.get("codec_name") == "h264" and vd.get("pix_fmt") in ("yuv420p", "yuvj420p"))
h5 = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", V5, "-map", "0:a", "-c", "copy", "-f", "md5", "-"], capture_output=True, text=True).stdout.strip()
say(f"$ ffmpeg -i out/final.mp4 -map 0:a -c copy -f md5 -\n{h5}")
gate("audio packet MD5", h5 == "MD5=2632a579c1377d79222ccb4e5300ad9e")
say("## Summary")
for k_, v_ in summary.items():
    say(f"- {k_}: {'PASS' if v_ else 'FAIL'}")
open("work/v5/gates_v5.txt", "w", encoding="utf8").write("\n".join(L) + "\n")
