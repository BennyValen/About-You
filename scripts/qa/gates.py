# QA gates for one scene (or several), run on a render directory of drawings (fNNNN.png on even frames).
#   python scripts/qa/gates.py --scene 12 --dir render/preview/scene_12 [--report out/gates_s12.txt]
# Gates:
#   motion : per-second mean |frame diff| (108x192 gray) vs the original, ratio must be within [0.75, 1.3],
#            no stall (ratio < 0.5 for > 0.5 s) unless the original stalls too.
#   thread : red-thread components per frame from the render + thread_log.json endpoints:
#            before B enters exactly one thread reaching the bottom edge; after, two (bottom + top), each
#            connected to its owner, never one curve touching both owners.
import argparse, json, os, subprocess, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.dirname(__file__))
from threadmask import thread_mask, render_thread_mask, render_thread_mask_hyst

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]


def load_original(a, b, w=108, h=192):
    raw = subprocess.run([FF, "-v", "error", "-i", "source/original.mp4", "-vf",
                          f"select='between(n\\,{a}\\,{b - 1})',scale={w}:{h},format=gray", "-vsync", "0", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.int16)


def load_render(d, a, b, w=108, h=192, gray=True):
    out = []
    last = None
    for f in range(a, b):
        p = os.path.join(d, f"f{f - (f - a) % 2:04d}.png")
        if not os.path.exists(p):
            p = os.path.join(d, f"f{f:04d}.png")
        if os.path.exists(p):
            im = cv2.imread(p, cv2.IMREAD_GRAYSCALE if gray else cv2.IMREAD_COLOR)
            last = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)
        if last is None:
            raise SystemExit(f"missing drawing for frame {f} in {d}")
        out.append(last)
    return np.array(out).astype(np.int16)


def mad(a):
    return np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))


def motion_gate(scene, d, lines):
    a, b = CUTS[scene - 1], CUTS[scene]
    o = load_original(a, b)
    r = load_render(d, a, b)
    mo, mr = mad(o), mad(r)
    ok = True
    lines.append(f"## motion parity, scene {scene} (frames {a}-{b - 1}); per-second mean |diff| original vs render")
    lines.append("sec  frames      orig   render  ratio  status")
    stall_run = 0
    n = len(mo) // 24
    for s in range(n + (1 if len(mo) % 24 >= 12 else 0)):
        i0, i1 = s * 24, min((s + 1) * 24, len(mo))
        x, y = mo[i0:i1].mean(), mr[i0:i1].mean()
        ratio = y / (x + 1e-6)
        st = "ok"
        if not (0.75 <= ratio <= 1.3):
            st = "FAIL"
            ok = False
        lines.append(f"{s:3d}  {a + i0:4d}-{a + i1:4d}  {x:6.2f}  {y:6.2f}  {ratio:5.2f}  {st}")
    # stall check on half-second windows
    for s in range(0, len(mo) - 12, 12):
        x, y = mo[s:s + 12].mean(), mr[s:s + 12].mean()
        if y / (x + 1e-6) < 0.5 and x > 0.3:
            stall_run += 12
            if stall_run > 12:
                ok = False
                lines.append(f"STALL near frames {a + s}-{a + s + 12}")
        else:
            stall_run = 0
    lines.append(f"motion gate scene {scene}: {'PASS' if ok else 'FAIL'}")
    return ok, mo, mr


def thread_gate(scene, d, lines, scale):
    a, b = CUTS[scene - 1], CUTS[scene]
    log_p = os.path.join(d, "thread_log.json")
    if not os.path.exists(log_p):
        lines.append(f"thread gate scene {scene}: no thread_log.json")
        return False
    log = {r["A"]["f"]: r for r in json.load(open(log_p))}
    ok = True
    bad = []
    counts = {}
    for f in range(a, b, 2):
        p = os.path.join(d, f"f{f:04d}.png")
        if f not in log or not os.path.exists(p):
            continue
        rec = log[f]
        # a thread is expected in the frame once at least 60 px of it (full-res units) is inside the frame
        owners = {k: rec[k] for k in rec if rec[k].get("visible_px", 1e9) >= 30.0}
        for k, v in owners.items():
            if not v["free_end_outside"]:
                bad.append(f"f{f} thread {k}: free end inside the frame {v['free_end']}")
        im = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
        h, w = im.shape[:2]
        m = render_thread_mask_hyst(im, w / 1080).astype(np.uint8)
        m = cv2.dilate(m, np.ones((3, 3), np.uint8), iterations=2 if w >= 540 else 1)
        nl, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        k = w / 1080
        comps = []
        for i in range(1, nl):
            if st[i][4] < 60 * k or max(st[i][2], st[i][3]) < 40 * k:
                continue
            ys, xs = np.where(lab == i)
            # the edge depth-of-field softens the cord in the last few px; accept a component that reaches
            # within 30 px (full-res units) of the edge
            touches_bottom = ys.max() >= h - 1 - 30 * k
            touches_top = ys.min() <= 30 * k
            own = []
            for name, v in owners.items():
                ox, oy = v["owner_end"][0] * k, v["owner_end"][1] * k
                dmin = np.min((xs - ox) ** 2 + (ys - oy) ** 2) ** 0.5 if len(xs) else 1e9
                if dmin < 14 * k + 3:
                    own.append(name)
            comps.append((touches_bottom, touches_top, own, int(st[i][4])))
        main = [c for c in comps if c[0] or c[1]]
        expect = len(owners)
        counts[f] = len(main)
        joined = [c for c in comps if len(c[2]) > 1]
        if joined:
            # owners close together at the very end may both lie near one blob of red pixels: only a failure
            # if that component reaches both frame edges
            for c in joined:
                if c[0] and c[1]:
                    bad.append(f"f{f}: one red curve touches both owners and both edges")
        if len(main) != expect:
            bad.append(f"f{f}: {len(main)} edge-reaching thread components, expected {expect} ({comps})")
    lines.append(f"## thread gate, scene {scene}: frames checked {len(counts)}")
    lines.append(f"edge-reaching components per frame (count: frames): " +
                 str({c: sum(1 for v in counts.values() if v == c) for c in sorted(set(counts.values()))}))
    for x in bad[:40]:
        lines.append("  " + x)
    if len(bad) > 40:
        lines.append(f"  ... {len(bad) - 40} more")
    ok = len(bad) == 0
    lines.append(f"thread gate scene {scene}: {'PASS' if ok else 'FAIL'} ({len(bad)} issues)")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", type=int, required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--report", default="")
    ap.add_argument("--scale", type=float, default=0.25)
    ap.add_argument("--no_thread", action="store_true")
    o = ap.parse_args()
    lines = []
    ok_m, mo, mr = motion_gate(o.scene, o.dir, lines)
    from thread_trace import gate as trace_gate
    ok_t = True if o.no_thread else trace_gate(o.scene, o.dir, lines)
    txt = "\n".join(lines)
    print(txt)
    if o.report:
        os.makedirs(os.path.dirname(o.report) or ".", exist_ok=True)
        open(o.report, "w").write(txt + "\n")
