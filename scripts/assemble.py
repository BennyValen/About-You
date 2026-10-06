# Assemble the film from per-scene drawings (render/scene_XX/fNNNN.png on even frames) into a 4004-frame
# sequence on twos (each drawing held for two frames, via hard links), encode H.264 CRF 16 yuv420p, and mux
# the original audio stream untouched: renders are silent; the only mux is -map 0:v -map 1:a -c copy with the audio
# taken directly from source/original.mp4 (no intermediate file, no -shortest). After the mux the audio packet MD5
# (-c copy -f md5) of the output must equal the source's, otherwise the script fails.
#   python scripts/assemble.py [--src render] [--suffix ""] [--scale 1.0] [--out out/final.mp4] [--silent work/video_silent.mp4]
import argparse, os, shutil, subprocess, sys

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
TOTAL = 4004

ap = argparse.ArgumentParser()
ap.add_argument("--src", default="render/v4")
ap.add_argument("--suffix", default="")
ap.add_argument("--out", default="out/final.mp4")
ap.add_argument("--silent", default="work/video_silent.mp4")
ap.add_argument("--seq", default="work/seq")
ap.add_argument("--crf", default="16")
ap.add_argument("--size", default="1080x1920")
o = ap.parse_args()

if os.path.isdir(o.seq):
    shutil.rmtree(o.seq)
os.makedirs(o.seq)
missing = []
for s in range(12):
    a, b = CUTS[s], CUTS[s + 1]
    d = os.path.join(o.src, f"scene_{s + 1:02d}{o.suffix}", "paint")
    for f in range(a, b):
        drawing = f - ((f - a) % 2)              # on twos: each painted drawing is held for two frames (hard links)
        src = os.path.join(d, f"f{drawing:04d}.jpg")
        if not os.path.exists(src):
            missing.append(src)
            continue
        dst = os.path.join(o.seq, f"{f:05d}.jpg")
        try:
            os.link(src, dst)
        except OSError:
            shutil.copyfile(src, dst)
if missing:
    print(f"MISSING {len(missing)} drawings, first: {missing[:5]}")
    sys.exit(1)
w, h = o.size.split("x")
cmd = [FF, "-hide_banner", "-y", "-framerate", "24", "-i", os.path.join(o.seq, "%05d.jpg"), "-frames:v", str(TOTAL),
       "-vf", f"scale={w}:{h}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", o.crf,
       "-pix_fmt", "yuv420p", "-r", "24", "-an", o.silent]
print(" ".join(cmd))
subprocess.run(cmd, check=True)
os.makedirs(os.path.dirname(o.out) or ".", exist_ok=True)
mux = [FF, "-hide_banner", "-y", "-i", o.silent, "-i", "source/original.mp4", "-map", "0:v:0", "-map", "1:a:0", "-c", "copy",
       "-movflags", "+faststart", o.out]
print(" ".join(mux))
subprocess.run(mux, check=True)


def packet_md5(path):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", path, "-map", "0:a", "-c", "copy", "-f", "md5", "-"],
                       capture_output=True, text=True)
    return r.stdout.strip()


h_src, h_out = packet_md5("source/original.mp4"), packet_md5(o.out)
print(f"audio packet md5  source/original.mp4: {h_src}")
print(f"audio packet md5  {o.out}: {h_out}")
if h_src != h_out or not h_src.startswith("MD5="):
    print("AUDIO PACKET MD5 MISMATCH")
    sys.exit(2)
print("wrote", o.out)
