# Final gates (brief v3, section 7) on out/final.mp4 -> out/gates_report.md
#   1 audio packet MD5 (+ ffprobe fields)   2 video stream / cuts   3 on twos (dup fraction per scene)
#   4 speed parity per distinct step        5 thread (continuity, pops, RMS deviation, sway vs. the original)
#   6 look checklist (1:1 crops, see out/look/)   7 stalls   8 painting wiggle (residual flow vs. the original)
import json, os, subprocess, sys
import numpy as np
sys.path.insert(0, "scripts/qa")
sys.path.insert(0, "scripts")
from speed_parity import load, mad, cuts as CUTS          # noqa: E402
import wiggle_gate as WG                                   # noqa: E402

FF = "./tools/ffmpeg.exe"
OUT = sys.argv[1] if len(sys.argv) > 1 else "out/final.mp4"
SRC = "source/original.mp4"
EXPECTED = CUTS[1:-1]
L = []
summary = {}


def sh(cmd, shell=False):
    r = subprocess.run(cmd, capture_output=True, text=True, shell=shell)
    return (r.stdout + r.stderr).strip()


def probe(path, entries, sel):
    return sh(" ".join(["npx", "remotion", "ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", entries, "-of", "default=nw=1", f'"{path}"']), shell=True)


L.append(f"# Gates report — {OUT}\n")
# ---------------------------------------------------------------- 1 audio
L.append("## 1. Audio (packet MD5 must equal the original's)\n")
# packet MD5 (-c copy) compares the compressed AAC packets, so any re-encode fails even if it decodes similarly
md5_src = sh([FF, "-hide_banner", "-loglevel", "error", "-i", SRC, "-map", "0:a", "-c", "copy", "-f", "md5", "-"])
md5_out = sh([FF, "-hide_banner", "-loglevel", "error", "-i", OUT, "-map", "0:a", "-c", "copy", "-f", "md5", "-"])
L.append("```")
L.append(f"$ ffmpeg -i source/original.mp4 -map 0:a -c copy -f md5 -\n{md5_src}")
L.append(f"$ ffmpeg -i {OUT} -map 0:a -c copy -f md5 -\n{md5_out}")
L.append("```")
ent = "stream=codec_name,profile,sample_rate,channels,channel_layout,bit_rate,duration,nb_frames"
a_src, a_out = probe(SRC, ent, "a:0"), probe(OUT, ent, "a:0")
L.append(f"```\nffprobe audio, source:\n{a_src}\n\nffprobe audio, final:\n{a_out}\n```")
summary["1 audio"] = md5_src == md5_out and md5_src.startswith("MD5=") and a_src == a_out
L.append(f"**Audio gate: {'PASS' if summary['1 audio'] else 'FAIL'}**\n")

# ---------------------------------------------------------------- 2 video + cuts
L.append("## 2. Video stream and cuts\n")
v_out = sh(" ".join(["npx", "remotion", "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                     "stream=codec_name,width,height,r_frame_rate,pix_fmt,nb_read_frames,duration", "-of", "default=nw=1", f'"{OUT}"']), shell=True)
L.append("```\n" + v_out + "\n```")
vd = dict(x.split("=", 1) for x in v_out.splitlines() if "=" in x)
video_ok = vd.get("width") == "1080" and vd.get("height") == "1920" and vd.get("r_frame_rate") == "24/1" and vd.get("nb_read_frames") == "4004"
o_raw, r_raw = load(SRC), load(OUT)
mo, mr = mad(o_raw), mad(r_raw)
d = mr


def nb(i):
    return max(d[i - 2] if i >= 2 else 0.0, d[i + 2] if i + 2 < len(d) else 0.0, 0.5)


found = [i + 1 for i in range(len(d)) if d[i] > 12 and d[i] > 2.5 * nb(i)]
L.append(f"```\ndetected hard cuts: {found}\nexpected:          {EXPECTED}\n```")
summary["2 video+cuts"] = video_ok and found == EXPECTED
L.append(f"**Video/cut gate: {'PASS' if summary['2 video+cuts'] else 'FAIL'}** (1080x1920, 24/1, 4004 frames; cuts on the expected frames)\n")

# ---------------------------------------------------------------- 3 on twos + 4 speed parity
L.append("## 3–4. On twos and speed parity (brief script: 108x192 gray mean |diff|, near-identical < 0.05)\n")
L.append("```\nscene  speed-ratio  dup-orig  dup-ours  exact-pairs(ours)")
twos_ok, speed_ok = True, True
for i in range(12):
    a, b = CUTS[i], CUTS[i + 1] - 1
    so, sr = mo[a:b], mr[a:b]
    dist = lambda x: x[x >= 0.05].mean() if (x >= 0.05).any() else 0
    dup = lambda x: (x < 0.05).mean()
    ratio = dist(sr) / (dist(so) + 1e-6)
    held = sr[0::2] if (a % 2 == 0) else sr[1::2]       # second frame of each drawing pair
    # pairs (f, f+1) with f-a even are the same drawing: their diff must be ~0
    pair = np.array([mr[f] for f in range(a, b, 2)])
    exact = float((pair < 0.05).mean())
    s_ok = (0.9 <= ratio <= 1.1) or i + 1 == 8
    # on twos gives one near-identical step per drawing: 50% of the steps, slightly above when a scene has an odd number
    # of frames (147 held pairs in 293 steps = 50.2%); the exact-pairs column checks that every held pair is a duplicate
    t_ok = 0.3 <= dup(sr) <= 0.51 and exact >= 0.99
    twos_ok &= t_ok
    speed_ok &= s_ok
    L.append(f"{i + 1:5d}  {ratio:10.2f}{'' if s_ok else ' !'}  {dup(so):8.2f}  {dup(sr):8.2f}{'' if t_ok else ' !'}  {exact:8.2f}")
L.append("```\n(scene 8 is exempt from speed parity: it was replaced)")
summary["3 on twos"] = twos_ok
summary["4 speed parity"] = speed_ok
L.append(f"**On-twos gate: {'PASS' if twos_ok else 'FAIL'}** · **Speed gate: {'PASS' if speed_ok else 'FAIL'}**\n")

# ---------------------------------------------------------------- 5 thread
L.append("## 5. Thread\n")
thread_ok = True
L.append("Continuity / pops / free end (simulation logs, per drawing):\n```")
for s in range(1, 13):
    p = f"render/v3/scene_{s:02d}/thread_log.json"
    if not os.path.exists(p):
        L.append(f"scene {s:2d}: no log")
        thread_ok = False
        continue
    log = json.load(open(p))
    for owner in ("A", "B"):
        rec = [x[owner] for x in log if owner in x]
        if not rec:
            continue
        outside = all(r["free_end_outside"] for r in rec)
        segs = sorted({r["segments"] for r in rec})
        jump = max(r.get("max_seg_px", 0) for r in rec)
        # pops: the owner end must move smoothly between drawings
        # pops: the thread end at the owner must follow the owner smoothly; a pop is a step far above the neighbouring
        # steps (B walks onto the screen fast in scene 12, which is real motion, not a pop)
        oe = np.array([r["owner_end"] for r in rec])
        st_ = np.linalg.norm(np.diff(oe, axis=0), axis=1) if len(oe) > 1 else np.zeros(1)
        step = st_.max()
        acc_ = np.abs(np.diff(st_)).max() if len(st_) > 1 else 0.0
        ok = outside and segs[0] >= 240 and jump < 40 and acc_ < 30
        thread_ok &= ok
        L.append(f"scene {s:2d} {owner}: {len(rec)} drawings, segments {segs}, free end beyond the frame: {outside}, "
                 f"max segment {jump:.1f}px, max owner step {step:.1f}px, max step change {acc_:.1f}px {'ok' if ok else 'FAIL'}")
L.append("```")
if os.path.exists("work/thread_stats_final.json"):
    o_st = json.load(open("work/thread_stats.json"))["scenes"]
    r_st = json.load(open("work/thread_stats_final.json"))["scenes"]
    good = [o_st[str(k)] for k in range(1, 13) if o_st[str(k)].get("used", 0) >= 30]
    med = dict(rms_dev_px=float(np.median([g["rms_dev_px"] for g in good])), sway_mid_centroid_hz=float(np.median([g["sway_mid_centroid_hz"] for g in good])))
    L.append("Shape vs. the original (same measurement, `scripts/analysis_thread_stats.py` on both videos):\n```")
    L.append("scene  rms-orig  rms-ours  ratio   sway-orig  sway-ours  ratio  sway-std-ours")
    for s in range(1, 13):
        o, r = o_st[str(s)], r_st[str(s)]
        if not r.get("used"):
            L.append(f"{s:5d}  thread not traced in our video")
            thread_ok = False
            continue
        ob = o if o.get("used", 0) >= 30 else med
        rr = r["rms_dev_px"] / max(ob["rms_dev_px"], 1e-6)
        fr = r["sway_mid_centroid_hz"] / max(ob["sway_mid_centroid_hz"], 1e-6)
        ok = 0.6 <= rr <= 1.4 and 0.6 <= fr <= 1.4 and r["sway_mid_std_px"] > 1.0
        thread_ok &= ok
        L.append(f"{s:5d}  {ob['rms_dev_px']:8.2f}  {r['rms_dev_px']:8.2f}  {rr:5.2f}   {ob['sway_mid_centroid_hz']:9.2f}  {r['sway_mid_centroid_hz']:9.2f}  "
                 f"{fr:5.2f}  {r['sway_mid_std_px']:6.1f} {'ok' if ok else 'FAIL'}{'  (film-median target)' if ob is med else ''}")
    L.append("```")
summary["5 thread"] = thread_ok
L.append(f"**Thread gate: {'PASS' if thread_ok else 'FAIL'}**\n")

# ---------------------------------------------------------------- 6 look
L.append("## 6. Look checklist (1:1 crops, original left, ours right: `out/look/sXX.jpg`)\n")
look_md = "work/v3/look_checklist.md"
L.append(open(look_md, encoding="utf8").read() if os.path.exists(look_md) else "(see out/look/)")
L.append("")

# ---------------------------------------------------------------- 7 stalls
L.append("## 7. Stalls (no second with motion below 50% of the original's)\n")
stall = []
n = min(len(mo), len(mr))
for s0 in range(0, n - 24, 12):
    rng_ = [i for i in range(s0, s0 + 24) if (i + 1) not in set(EXPECTED)]
    x, y = mo[rng_].mean(), mr[rng_].mean()
    if x > 0.3 and y / x < 0.5:
        stall.append(round(s0 / 24, 1))
summary["7 stalls"] = not stall
L.append(f"stall windows (start second): {stall if stall else 'none'}")
L.append(f"**Stall gate: {'PASS' if not stall else 'FAIL'}**\n")

# ---------------------------------------------------------------- 8 wiggle
L.append("## 8. Painting wiggle (brief script; residual flow after rigid alignment, px at 1080 wide)\n```")
wig_ok = True
for s, f0 in [(2, 400), (3, 700), (5, 1500), (7, 2300)]:
    L.append(f"reference s{s} f{f0}: original {WG.wiggle(SRC, f0)}  ours {WG.wiggle(OUT, f0)}")
L.append("scene  orig  ours  ratio")
for s in range(1, 13):
    o = float(np.mean([WG.wiggle(SRC, f)[0] for f in WG.places(s)]))
    r = float(np.mean([WG.wiggle(OUT, f)[0] for f in WG.places(s)]))
    if s == 8:
        o = float(np.mean([WG.wiggle(SRC, f)[0] for f in WG.places(4)]))     # replaced scene: compare with scene 4's paint motion
    ratio = r / max(o, 1e-6)
    ok = 0.6 <= ratio <= 1.4
    wig_ok &= ok
    L.append(f"{s:5d}  {o:4.2f}  {r:4.2f}  {ratio:5.2f} {'ok' if ok else 'FAIL'}{'  (vs. scene 4: scene 8 was replaced)' if s == 8 else ''}")
L.append("```")
summary["8 wiggle"] = wig_ok
L.append(f"**Wiggle gate: {'PASS' if wig_ok else 'FAIL'}**\n")

L.append("## Summary\n")
for k, v in summary.items():
    L.append(f"- {k}: {'PASS' if v else 'FAIL'}")
open("out/gates_report.md", "w", encoding="utf8").write("\n".join(L) + "\n")
print("\n".join(L))
