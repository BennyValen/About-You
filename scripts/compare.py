# Side-by-side comparison: reference frame (left) vs recreation still (right).
# usage: python scripts/compare.py name frame1 frame2 ...   (stills read from work/stills/fNNNN.png)
import subprocess, sys, os
from PIL import Image, ImageDraw
F = "./tools/ffmpeg.exe"
name = sys.argv[1]
frames = [int(x) for x in sys.argv[2:]]
os.makedirs("work/refcache", exist_ok=True)
os.makedirs("work/compare", exist_ok=True)
need = [f for f in frames if not os.path.exists(f"work/refcache/r{f:04d}.png")]
if need:
    sel = "+".join(f"eq(n\,{min(f, 4003)})" for f in need)
    tmp = "work/refcache/tmp_%04d.png"
    subprocess.run([F, "-hide_banner", "-loglevel", "error", "-y", "-i", "source/original.mp4",
                    "-vf", f"select='{sel}',scale=540:960", "-vsync", "0", tmp], check=True)
    for i, f in enumerate(sorted(need)):
        os.replace(f"work/refcache/tmp_{i+1:04d}.png", f"work/refcache/r{f:04d}.png")
W, H = 540, 960
sheet = Image.new("RGB", (W * 2 * len(frames), H), (0, 0, 0))
for i, f in enumerate(frames):
    ref = Image.open(f"work/refcache/r{f:04d}.png").convert("RGB").resize((W, H))
    p = f"work/stills/f{f:04d}.png"
    mine = Image.open(p).convert("RGB").resize((W, H)) if os.path.exists(p) else Image.new("RGB", (W, H), (60, 0, 0))
    sheet.paste(ref, (i * 2 * W, 0))
    sheet.paste(mine, (i * 2 * W + W, 0))
out = f"work/compare/{name}.jpg"
sheet.save(out, quality=90)
print(out)
