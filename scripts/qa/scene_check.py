# Per-scene check of the painted drawings (before the full assembly): builds the scene on twos as a quick clip and
# reports speed ratio + dup fraction (brief metric) and the wiggle residual at three places vs. the original.
#   python scripts/qa/scene_check.py SCENE [--dir render/v3/scene_XX] [--paint paint]
import argparse, os, shutil, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import wiggle_gate as WG       # noqa: E402

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]


def gray_seq(path_or_pattern, n=None, start_frame=None, is_video=True):
    cmd = [FF, "-v", "error"]
    if is_video and start_frame is not None:
        cmd += ["-ss", f"{start_frame / 24:.4f}"]
    if not is_video:
        cmd += ["-framerate", "24"]
    cmd += ["-i", path_or_pattern]
    if n:
        cmd += ["-frames:v", str(n)]
    cmd += ["-vf", "scale=108:192,format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(np.int16)


def mad(a):
    return np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene", type=int)
    ap.add_argument("--dir", default="")
    ap.add_argument("--paint", default="paint")
    ap.add_argument("--nowiggle", action="store_true")
    ap.add_argument("--frames", default="", help="a-b window (even start)")
    o = ap.parse_args()
    s = o.scene
    sdir = o.dir or f"render/v3/scene_{s:02d}"
    a, b = CUTS[s - 1], CUTS[s]
    a0 = a
    if o.frames:
        a, b = [int(x) for x in o.frames.split("-")]
        b += 1
    seq = f"work/v3/check_s{s:02d}"
    shutil.rmtree(seq, ignore_errors=True)
    os.makedirs(seq)
    for i, f in enumerate(range(a, b)):
        d = f - ((f - a0) % 2)
        src = os.path.join(sdir, o.paint, f"f{d:04d}.jpg")
        os.link(src, os.path.join(seq, f"{i:05d}.jpg"))
    clip = f"work/v3/check_s{s:02d}.mp4"
    subprocess.run([FF, "-v", "error", "-y", "-framerate", "24", "-i", os.path.join(seq, "%05d.jpg"), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "16", "-pix_fmt", "yuv420p", clip], check=True)
    r = mad(gray_seq(clip))
    org = mad(gray_seq("source/original.mp4", n=b - a, start_frame=a))
    so, sr = org[: b - a - 1], r[: b - a - 1]
    dist = lambda x: x[x >= 0.05].mean() if (x >= 0.05).any() else 0
    dup = lambda x: (x < 0.05).mean()
    print(f"s{s:02d} speed ratio {dist(sr) / (dist(so) + 1e-6):.2f}  dup orig {dup(so):.2f} ours {dup(sr):.2f}  "
          f"(mean step orig {dist(so):.2f} ours {dist(sr):.2f})")
    if not o.nowiggle:
        wo, wr = [], []
        pl = WG.places(s) if not o.frames else [a + ((a - a0) % 2)]
        for f in pl:
            wo.append(WG.wiggle("source/original.mp4", f)[0])
            wr.append(WG.wiggle(clip, f - a)[0])
        ref = wo if s != 8 else [WG.wiggle("source/original.mp4", f)[0] for f in WG.places(4)]
        print(f"s{s:02d} wiggle orig {np.mean(ref):.2f} ours {np.mean(wr):.2f}  x{np.mean(wr) / max(np.mean(ref), 1e-6):.2f}  ({wr})")
    shutil.rmtree(seq, ignore_errors=True)


if __name__ == "__main__":
    main()
