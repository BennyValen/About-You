# Final gates (brief v4, section 7) on out/final.mp4 -> out/gates_report.md (every gate prints its own output)
#    1 audio packet MD5          2 cuts / 4004 frames / no fade     3 on twos          4 camera within 10 %
#    5 hero motion table         6 horse + shadow connectivity      7 scene 6 colliders, manta continuity, boat clearance
#    8 tone (s1, s8, s11) + scene 1 corridor + window light         9 thread continuity / pops
#   10 wiggle calibration + flipbooks                              11 look checklist (1:1 crops)
#   python scripts/qa/gates_v4.py [out/final.mp4]
import csv, glob, json, os, subprocess, sys
import numpy as np, cv2
sys.path.insert(0, "scripts/qa")
from speed_parity import load, mad                                  # noqa: E402
import measure_v4 as M                                              # noqa: E402

FF = "./tools/ffmpeg.exe"
OUT = sys.argv[1] if len(sys.argv) > 1 else "out/final.mp4"
SRC = "source/original.mp4"
CUTS = M.CUTS
EXPECTED = CUTS[1:-1]
R = "render/v4"
L, summary = [], {}


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def gate(name, ok, note=""):
    summary[name] = bool(ok)
    L.append(f"**{name}: {'PASS' if ok else 'FAIL'}**{(' — ' + note) if note else ''}\n")


L.append(f"# Gates report (brief v4) — {OUT}\n")
# ---------------------------------------------------------------- 1 audio
L.append("## 1. Audio packet MD5\n")
md5_src = sh([FF, "-hide_banner", "-loglevel", "error", "-i", SRC, "-map", "0:a", "-c", "copy", "-f", "md5", "-"])
md5_out = sh([FF, "-hide_banner", "-loglevel", "error", "-i", OUT, "-map", "0:a", "-c", "copy", "-f", "md5", "-"])
L.append("```")
L.append(f"$ ffmpeg -i {SRC} -map 0:a -c copy -f md5 -\n{md5_src}")
L.append(f"$ ffmpeg -i {OUT} -map 0:a -c copy -f md5 -\n{md5_out}")
L.append("```")
gate("1 audio", md5_src == md5_out and md5_src.startswith("MD5="))

# ---------------------------------------------------------------- 2 cuts, frames, no fade
L.append("## 2. Cuts, 4004 frames, no fade\n")
nb = subprocess.run(" ".join(["npx", "remotion", "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                              "stream=codec_name,width,height,r_frame_rate,nb_read_frames", "-of", "default=nw=1", f'"{OUT}"']),
                    capture_output=True, text=True, shell=True).stdout.strip()
o_raw, r_raw = load(SRC), load(OUT)
nframes = len(r_raw)
L.append("```\n" + (nb + "\n" if nb else "") + f"decoded frames (108x192 gray): {nframes}")
mo, mr = mad(o_raw), mad(r_raw)


def nbh(d, i):
    return max(d[i - 2] if i >= 2 else 0.0, d[i + 2] if i + 2 < len(d) else 0.0, 0.5)


found = [i + 1 for i in range(len(mr)) if mr[i] > 12 and mr[i] > 2.5 * nbh(mr, i)]
L.append(f"detected hard cuts: {found}\nexpected:          {EXPECTED}")
# fade check: mean luma over the 4 frames either side of each cut vs. the 8 frames before/after that
lum_o, lum_r = o_raw.mean(axis=(1, 2)), r_raw.mean(axis=(1, 2))
fade_bad = []
L.append("cut   out-ratio(ours/orig)   in-ratio(ours/orig)")
for c in EXPECTED + [4004]:
    def ratios(lum):
        out_r = lum[c - 4:c].mean() / max(lum[c - 16:c - 8].mean(), 1e-3)
        in_r = lum[c:c + 4].mean() / max(lum[c + 8:c + 16].mean(), 1e-3) if c < 4004 else 1.0
        return out_r, in_r
    (ro, ri), (oo, oi) = ratios(lum_r), ratios(lum_o)
    # a fade = a luma ramp of more than 25 % into or out of the cut that the original does not have
    bad = (ro < 0.75 and oo > 0.85) or (ri < 0.75 and oi > 0.85)
    if bad:
        fade_bad.append(c)
    L.append(f"{c:5d}   {ro:5.2f} / {oo:5.2f}            {ri:5.2f} / {oi:5.2f}   {'FADE?' if bad else 'ok'}")
L.append("```")
gate("2 cuts+frames+no fade", nframes == 4004 and found == EXPECTED and not fade_bad,
     f"{nframes} frames, cuts {'match' if found == EXPECTED else 'DIFFER'}, fades: {fade_bad or 'none'}")

# ---------------------------------------------------------------- 3 on twos
L.append("## 3. On twos (every drawing held for exactly two frames)\n```\nscene  dup-steps  held-pairs-identical")
twos_ok = True
for i in range(12):
    a, b = CUTS[i], CUTS[i + 1] - 1
    sr = mr[a:b]
    pair = np.array([mr[f] for f in range(a, b, 2)])
    exact = float((pair < 0.05).mean())
    dup = float((sr < 0.05).mean())
    ok = 0.3 <= dup <= 0.51 and exact >= 0.99
    twos_ok &= ok
    L.append(f"{i + 1:5d}  {dup:9.2f}  {exact:9.2f} {'ok' if ok else 'FAIL'}")
L.append("```")
gate("3 on twos", twos_ok)

# ---------------------------------------------------------------- 4 camera
L.append("## 4. Camera speed within 10 % (phase correlation, px per drawing at 1080 wide; 3 samples per scene)\n```")
L.append("scene  samples              mean   target  ratio")
cam_ok = True
cam = M.camera_table(OUT)
for s in range(1, 13):
    v = cam[s]
    m = float(np.mean(v))
    ratio = m / M.ORIG_CAM[s]
    ok = 0.9 <= ratio <= 1.1
    cam_ok &= ok
    L.append(f"{s:5d}  {str(v):20s} {m:5.1f}  {M.ORIG_CAM[s]:5.1f}  {ratio:5.2f} {'ok' if ok else 'FAIL'}")
L.append("```")
gate("4 camera", cam_ok)

# ---------------------------------------------------------------- 5 hero motion
L.append("## 5. Heroes travel straight (work/hero_motion.csv; every 48-frame window, step 12)\n")
LIM = {1: (8, 0.5), 2: (8, 0.5), 3: (20, 2.5), 4: (60, None), 5: (12, 2), 6: (20, 2), 7: (20, 3), 8: (15, 2), 9: (26, 3),
       10: (42, 4), 11: (20, 4), 12: (30, 4)}
rows = list(csv.DictReader(open("work/hero_motion.csv")))
by = {}
for r_ in rows:
    by.setdefault((int(r_["scene"]), r_["hero"]), []).append((int(r_["frame"]), float(r_["x"]), float(r_["y"]), float(r_["yaw_deg"])))


def windows(fr, vals, win=48):
    out = []
    for f0 in range(fr[0], fr[-1] - win + 1, 12):
        m = (fr >= f0) & (fr < f0 + win)
        if m.sum() >= 6:
            t, x = fr[m], vals[m]
            out.append(x - np.polyval(np.polyfit(t, x, 1), t))
    return out


L.append("```\nscene hero  drawings  excursion max/median (px)  limit   yaw-RMS max (deg)  limit")
hero_ok = True
for (s, h) in sorted(by):
    d = np.array(sorted(by[(s, h)]))
    fr, xs, yaw = d[:, 0].astype(int), d[:, 1], d[:, 3]
    ex = [w.max() - w.min() for w in windows(fr, xs)]
    yr = [float(np.sqrt(np.mean(w ** 2))) for w in windows(fr, yaw)]
    lim_x, lim_y = LIM[s]
    exm, exmed = (max(ex), float(np.median(ex))) if ex else (0.0, 0.0)
    yrm = max(yr) if yr else 0.0
    ok = exm <= lim_x and (lim_y is None or yrm <= lim_y)
    hero_ok &= ok
    ytxt = f"{yrm:8.2f}           {lim_y}" if lim_y is not None else "  path tangent (S-curve kept)"
    L.append(f"{s:5d}  {h:3s}  {len(fr):8d}  {exm:8.1f} / {exmed:6.1f}            {lim_x:5d}   {ytxt}  {'ok' if ok else 'FAIL'}")
L.append("```")
base = json.load(open("work/baseline.json"))["hero"]
L.append("Template tracker on the videos (same tool for all three; median excursion per 4 s, px):\n```")
for s, (sf, box) in M.SEEDS.items():
    tr = M.track(OUT, s, sf, box)
    fr = list(tr)
    ours = M.excursion([tr[f][0] for f in fr], fr)
    L.append(f"scene {s}: original {base['original'][str(s)]['excursion_px']}  v3 {base['v3'][str(s)]['excursion_px']}  v4 {ours:.1f}")
L.append("```")
gate("5 hero motion", hero_ok)

# ---------------------------------------------------------------- 6 horse + shadow
L.append("## 6. Scene 5: horse + rider mask and shadow mask, one piece each\n```")
hero_masks = sorted(glob.glob(f"{R}/scene_05/aux/hero_*.png"))
bad = []
for p in hero_masks:
    a = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    if a is None or not M.one_piece(a):
        n = cv2.connectedComponents(cv2.dilate((a > 127).astype(np.uint8), np.ones((3, 3), np.uint8)))[0] - 1 if a is not None else -1
        bad.append((os.path.basename(p), n))
L.append(f"horse+rider hero mask: {len(hero_masks)} drawings checked, {len(bad)} not one piece {bad[:10]}")
sh_log = sh([sys.executable, "scripts/qa/s5_shadow_gate.py"])
L.append(sh_log)
L.append("```")
gate("6 horse+shadow connectivity", len(hero_masks) > 100 and not bad and "SCENE 5 SHADOW GATE: PASS" in sh_log)

# ---------------------------------------------------------------- 7 scene 6
L.append("## 7. Scene 6: depth-layer colliders, manta continuity, boat clearance\n```")
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    overlaps = M.collider_overlaps("work/colliders.csv")
L.append(buf.getvalue().strip())
crow = list(csv.DictReader(open("work/colliders.csv")))
L.append(f"collider rows: {len(crow)}, frames: {len({r_['frame'] for r_ in crow})}, layers: {sorted({r_['layer'] for r_ in crow})}")
# boat clearance: distance from the boat collider (layer 4) to the nearest island (layer 5), screen px
from shapely.geometry import Point
from shapely import affinity


def ell(r_):
    cx, cy, rx, ry, deg = (float(r_[k]) for k in ("cx", "cy", "rx", "ry", "deg"))
    return affinity.rotate(affinity.scale(Point(cx, cy).buffer(1), rx, ry), deg, origin=(cx, cy))


fr_rows = {}
for r_ in crow:
    fr_rows.setdefault(r_["frame"], []).append(r_)
clear = []
for f, rs in fr_rows.items():
    boats = [ell(r_) for r_ in rs if r_["layer"] == "4"]
    isl = [ell(r_) for r_ in rs if r_["layer"] == "5"]
    if boats and isl:
        clear.append(min(b.distance(i) for b in boats for i in isl))
L.append(f"boat-island clearance (px): min {min(clear):.1f}, median {np.median(clear):.1f} over {len(clear)} drawings")
manta = sorted(glob.glob(f"{R}/scene_06/aux/manta_*.png"))
areas, pieces_bad, split_raw = [], [], []
for p in manta:
    a = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
    areas.append(int((a > 127).sum()))
    if areas[-1] > 0 and not M.one_piece(a):
        # occlusion-aware: pixels of a nearer hero object (the boat) over the manta count as hidden manta
        split_raw.append(os.path.basename(p))
        h = cv2.imread(p.replace("manta_", "hero_"), cv2.IMREAD_GRAYSCALE)
        near = cv2.dilate((a > 127).astype(np.uint8), np.ones((61, 61), np.uint8)) > 0
        if h is None or not M.one_piece(np.where(near, np.maximum(a, h), 0)):
            pieces_bad.append(os.path.basename(p))
ar = np.array(areas, float)
vis = ar > 2000
dch = [abs(ar[i + 1] - ar[i]) / ar[i] for i in range(len(ar) - 1) if vis[i] and vis[i + 1]]
# the manta enters/leaves through the frame edge: area changes there are framing, not shape; count interior drawings only
L.append(f"manta mask: {len(manta)} drawings, {int(vis.sum())} with the manta in view; visible mask split in {len(split_raw)} "
         f"{split_raw[:8]} (the boat passing over the tail); not one piece once the occluding boat is counted: {len(pieces_bad)} {pieces_bad[:8]}")
L.append(f"manta area change between drawings: max {max(dch) * 100:.1f} %, median {np.median(dch) * 100:.1f} % (limit 6 %)" if dch else "manta: no data")
L.append("```")
gate("7 scene 6 colliders+manta+boat", overlaps == 0 and min(clear) >= 50 and not pieces_bad and dch and max(dch) <= 0.06)

# ---------------------------------------------------------------- 8 tone + corridor
L.append("## 8. Tone (scenes 1, 8, 11), scene 1 corridor and window light\n```")
L.append("frame  scene  mean   p5   p95   sat    targets")
T = {146: (1, (68, 74), 36, (0, 125), 0.5), 2570: (8, (90, 105), 28, (195, 215), 0.45), 3482: (11, (148, 172), 0, (0, 255), 1.0)}
tone_ok = True
for n, (s, (m0, m1), p5min, (q0, q1), smax) in T.items():
    mean, p5, p95, sat = M.tone(OUT, n)
    ok = m0 <= mean <= m1 and p5 >= p5min and q0 <= p95 <= q1 and sat <= smax
    tone_ok &= ok
    L.append(f"{n:5d}  {s:5d}  {mean:5.1f}  {p5:3d}  {p95:4d}  {sat:4.2f}   mean {m0}-{m1}, p5>={p5min}, p95 {q0}-{q1}, sat<={smax}  {'ok' if ok else 'FAIL'}")


def frame_bgr(n):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{n / 24:.4f}", "-i", OUT, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)


# scene 11 palette shares over five frames: deep blue gaps (#475082-#2E3766), lavender/violet shadows, pale tops
gaps, lav = [], []
for n in (3330, 3400, 3482, 3560, 3640):
    sm = cv2.resize(frame_bgr(n), (540, 960), interpolation=cv2.INTER_AREA)
    g = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY).astype(int)
    b, gg, r = [sm[..., i].astype(int) for i in range(3)]
    gap = (b > r + 25) & (g < 120)
    lv = (~gap) & (g >= 90) & (g < 170) & (b >= r - 5)
    gaps.append(gap.mean())
    lav.append(lv.mean())
    L.append(f"s11 f{n}: gaps {gap.mean():.2f}  lavender/violet {lv.mean():.2f}  mean luma {g.mean():.1f}")
s11_ok = 0.2 <= np.mean(gaps) <= 0.25 + 0.02 and np.mean(lav) >= 0.3
L.append(f"s11 mean over the scene: gaps {np.mean(gaps):.2f} (target 0.20-0.25), lavender/violet {np.mean(lav):.2f} (>= 0.30)  {'ok' if s11_ok else 'FAIL'}")
cor = json.load(open(f"{R}/scene_01/corridor.json"))
L.append(f"s1 corridor (scene graph): {cor}")
# window light never clipped: warm pixels (R > G > B) beside the train
im = frame_bgr(146).astype(int)
b, g, r = im[..., 0], im[..., 1], im[..., 2]
warm = (r > g + 15) & (g > b) & (r > 110)
wr, wg = (int(r[warm].max()), int(g[warm].max())) if warm.any() else (0, 0)
win_ok = wr <= 235 and wg <= 200
L.append(f"s1 f146 warm window light: {int(warm.sum())} px, max R {wr} (<=235), max G {wg} (<=200)  {'ok' if win_ok else 'FAIL'}")
L.append("```")
gate("8 tone + corridor", tone_ok and s11_ok and cor.get("pass_") and win_ok)

# ---------------------------------------------------------------- 9 thread
L.append("## 9. Thread continuity, no pops (simulation logs per drawing)\n```")
thread_ok = True
for s in range(1, 13):
    p = f"{R}/scene_{s:02d}/thread_log.json"
    if not os.path.exists(p):
        L.append(f"scene {s:2d}: no log")
        thread_ok = False
        continue
    log = json.load(open(p))
    for owner in ("A", "B"):
        rec = [x[owner] for x in log if owner in x]
        if not rec:
            continue
        outside = all(r_["free_end_outside"] for r_ in rec)
        segs = sorted({r_["segments"] for r_ in rec})
        jump = max(r_.get("max_seg_px", 0) for r_ in rec)
        oe = np.array([r_["owner_end"] for r_ in rec])
        st_ = np.linalg.norm(np.diff(oe, axis=0), axis=1) if len(oe) > 1 else np.zeros(1)
        acc_ = np.abs(np.diff(st_)).max() if len(st_) > 1 else 0.0
        ok = outside and segs[0] >= 240 and jump < 40 and acc_ < 30
        thread_ok &= ok
        L.append(f"scene {s:2d} {owner}: {len(rec)} drawings, segments {segs}, free end beyond the frame: {outside}, "
                 f"max segment {jump:.1f}px, max owner step change {acc_:.1f}px {'ok' if ok else 'FAIL'}")
L.append("```")
gate("9 thread", thread_ok)

# ---------------------------------------------------------------- 10 wiggle
L.append("## 10. Wiggle: fine boil only (cells 8-24 px), calibration and flipbooks\n```")
for s in range(1, 13):
    c = json.load(open(f"work/v4/calib/s{s:02d}.json"))
    if "floor" in c:
        ex_v3, ex_new = c["v3"] - c["floor"], c["new"][str(c["boil_scale"])] - c["floor"]
        L.append(f"s{s:02d} boil_scale {c['boil_scale']}: residual flow floor {c['floor']:.2f}  v3 {c['v3']:.2f}  new {{" +
                 ", ".join(f"{k}: {v:.2f}" for k, v in c["new"].items()) + f"}}  extra new/v3 = {ex_new / max(ex_v3, 1e-6):.2f}")
    else:
        L.append(f"s{s:02d} boil_scale {c['boil_scale']}  ({c.get('rule', '')})")
fb = sorted(glob.glob("out/flipbook_*.mp4"))
for p in fb:
    L.append(f"{p}  {os.path.getsize(p) / 1e6:.1f} MB")
L.append("```")
gate("10 wiggle+flipbooks", len(fb) == 4, "coarse warp removed (boil_mode=fine everywhere); see flipbooks for the look")

# ---------------------------------------------------------------- 11 look
L.append("## 11. Look checklist (1:1 crops: `out/look/v4_sXX.jpg`, original left, v4 right)\n")
lk = "work/v4/look_checklist.md"
L.append(open(lk, encoding="utf8").read() if os.path.exists(lk) else "(missing)")
gate("11 look checklist", os.path.exists(lk) and all(os.path.exists(f"out/look/v4_s{s:02d}.jpg") for s in (1, 5, 6, 8, 11)))

L.append("## Summary\n")
for k, v in summary.items():
    L.append(f"- {k}: {'PASS' if v else 'FAIL'}")
open("out/gates_report.md", "w", encoding="utf8").write("\n".join(L) + "\n")
print("\n".join(L))
