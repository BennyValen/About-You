# v4 deliverable media: flipbooks (original | v3 | v4, 12 drawings, 540 wide each), contact sheet (original, v3, v4 for
# scenes 1, 5, 6, 8, 11 + 1:1 hero crops) and the 1:1 look crops (out/look/v4_sXX.jpg).
#   python scripts/qa/v4_media.py [flip] [sheet] [look]
import csv, os, subprocess, sys
import numpy as np, cv2

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
VID = {"original": "source/original.mp4", "v3": "source/v3.mp4", "v4": "out/final.mp4"}
FLIP = {1: 140, 5: 1480, 9: 3140, 11: 3470}               # start frame (even) of the 12 drawings
SHEET = {1: 146, 5: 1500, 6: 1880, 8: 2570, 11: 3482}


def frame(path, n):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{n / 24:.4f}", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3).copy()


def hero_xy(scene, n):
    best = None
    for r in csv.DictReader(open("work/hero_motion.csv")):
        if int(r["scene"]) == scene and r["hero"] == "A":
            d = abs(int(r["frame"]) - n)
            if best is None or d < best[0]:
                best = (d, float(r["x"]), float(r["y"]))
    return (540, 1100) if best is None else (best[1], best[2])


def flipbooks():
    for s, f0 in FLIP.items():
        out = f"out/flipbook_s{s:02d}.mp4"
        ins = []
        for k in ("original", "v3", "v4"):
            ins += ["-ss", f"{f0 / 24:.4f}", "-t", f"{24 / 24:.4f}", "-i", VID[k]]
        lab = lambda i, t: (f"[{i}:v]scale=540:960,setpts=PTS-STARTPTS,drawtext=text='{t}':x=16:y=16:fontsize=28:fontcolor=white:"
                            f"box=1:boxcolor=black@0.5[v{i}]")
        flt = ";".join([lab(0, "original"), lab(1, "v3"), lab(2, f"v4  scene {s}  frames {f0}-{f0 + 23}")]) + \
            ";[v0][v1][v2]hstack=3,loop=loop=2:size=24:start=0[o]"
        cmd = [FF, "-hide_banner", "-y"] + ins + ["-filter_complex", flt, "-map", "[o]", "-an", "-c:v", "libx264", "-crf", "16",
                                                   "-pix_fmt", "yuv420p", "-r", "24", out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            # drawtext needs a font on Windows; fall back to unlabeled panels
            flt = ";".join([f"[{i}:v]scale=540:960,setpts=PTS-STARTPTS[v{i}]" for i in range(3)]) + \
                ";[v0][v1][v2]hstack=3,loop=loop=2:size=24:start=0[o]"
            cmd = [FF, "-hide_banner", "-y"] + ins + ["-filter_complex", flt, "-map", "[o]", "-an", "-c:v", "libx264", "-crf", "16",
                                                       "-pix_fmt", "yuv420p", "-r", "24", out]
            r = subprocess.run(cmd, capture_output=True, text=True)
        print(out, "ok" if r.returncode == 0 else r.stderr[-400:])


def put(img, text, y=28):
    cv2.putText(img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1, cv2.LINE_AA)


def sheet():
    rows = []
    for s, n in SHEET.items():
        hx, hy = hero_xy(s, n)
        c = 240
        x0, y0 = int(min(max(hx - c // 2, 0), 1080 - c)), int(min(max(hy - c // 2, 0), 1920 - c))
        thumbs, crops = [], []
        for k in ("original", "v3", "v4"):
            im = frame(VID[k], n)
            t = cv2.resize(im, (270, 480), interpolation=cv2.INTER_AREA)
            put(t, f"{k} s{s} f{n}")
            cv2.rectangle(t, (x0 // 4, y0 // 4), ((x0 + c) // 4, (y0 + c) // 4), (255, 255, 255), 1)
            thumbs.append(t)
            cr = im[y0:y0 + c, x0:x0 + c].copy()
            put(cr, f"{k} 1:1", 22)
            crops.append(cr)
        crop_col = np.vstack([np.hstack(crops[:2]), np.hstack([crops[2], np.zeros((c, c, 3), np.uint8)])])
        rows.append(np.hstack(thumbs + [crop_col]))
    out = np.vstack(rows)
    cv2.imwrite("out/contact_sheet.jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print("out/contact_sheet.jpg", out.shape)


def look():
    os.makedirs("out/look", exist_ok=True)
    for s, n in SHEET.items():
        hx, hy = hero_xy(s, n)
        boxes = [f"{int(hx)},{int(hy)},400", "300,500,400"]
        r = subprocess.run([sys.executable, "scripts/qa/look_crops.py", str(n)] + boxes + ["--ours_video", "out/final.mp4", "--out",
                            f"out/look/v4_s{s:02d}.jpg", "--full", "400"], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr[-300:])


if __name__ == "__main__":
    what = sys.argv[1:] or ["flip", "sheet", "look"]
    if "flip" in what:
        flipbooks()
    if "sheet" in what:
        sheet()
    if "look" in what:
        look()
