# Contact sheet: one frame per scene, original (top row) vs recreation (bottom row).
# usage: python scripts/contact_sheet.py <recreation.mp4 | stills-dir> <out.jpg>
import subprocess, sys, os
from PIL import Image, ImageDraw
F = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
frames = [(CUTS[i] + CUTS[i + 1]) // 2 for i in range(12)]
src, out = sys.argv[1], sys.argv[2]
W, H = 270, 480

def grab(video, fl, tag):
    os.makedirs("work/sheetcache", exist_ok=True)
    sel = "+".join(f"eq(n\,{f})" for f in fl)
    pat = f"work/sheetcache/{tag}_%02d.png"
    subprocess.run([F, "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-vf",
                    f"select='{sel}',scale={W}:{H}", "-vsync", "0", pat], check=True)
    return [Image.open(f"work/sheetcache/{tag}_{i + 1:02d}.png").convert("RGB") for i in range(len(fl))]

refs = grab("source/original.mp4", frames, "ref")
if os.path.isdir(src):
    mine = [Image.open(os.path.join(src, f"f{f:04d}.png")).convert("RGB").resize((W, H)) for f in frames]
else:
    mine = grab(src, frames, "new")
pad = 26
sheet = Image.new("RGB", (W * 12, H * 2 + pad * 2), (12, 12, 14))
d = ImageDraw.Draw(sheet)
for i in range(12):
    sheet.paste(refs[i], (i * W, pad))
    sheet.paste(mine[i], (i * W, pad * 2 + H))
    d.text((i * W + 6, 6), f"{i + 1:02d} original f{frames[i]}", fill=(230, 230, 230))
    d.text((i * W + 6, pad + H + 6), f"{i + 1:02d} recreation f{frames[i]}", fill=(230, 230, 230))
sheet.save(out, quality=90)
print(out, frames)
