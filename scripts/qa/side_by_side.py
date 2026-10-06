# Side-by-side sheets (original left, render right) for given frames + optional 1:1 crops around a point.
#   python scripts/qa/side_by_side.py <render_dir> <name> f1 f2 ... [--crop x,y]
import sys, os, subprocess
from PIL import Image, ImageDraw
FF = "./tools/ffmpeg.exe"
rd, name = sys.argv[1], sys.argv[2]
args = [a for a in sys.argv[3:] if not a.startswith("--")]
crop = None
for a in sys.argv[3:]:
    if a.startswith("--crop"):
        crop = [int(v) for v in a.split("=")[1].split(",")]
frames = [int(a) for a in args]
os.makedirs("work/refcache_full", exist_ok=True)
need = [f for f in frames if not os.path.exists(f"work/refcache_full/r{f:04d}.png")]
if need:
    sel = "+".join(f"eq(n\,{f})" for f in need)
    subprocess.run([FF, "-v", "error", "-y", "-i", "source/original.mp4", "-vf", f"select='{sel}'", "-vsync", "0", "work/refcache_full/tmp_%04d.png"], check=True)
    for i, f in enumerate(sorted(need)):
        os.replace(f"work/refcache_full/tmp_{i + 1:04d}.png", f"work/refcache_full/r{f:04d}.png")
W, H = 360, 640
cols = []
for f in frames:
    ref = Image.open(f"work/refcache_full/r{f:04d}.png").convert("RGB")
    p = os.path.join(rd, f"f{f - f % 2:04d}.png")
    mine = Image.open(p).convert("RGB").resize((1080, 1920)) if os.path.exists(p) else Image.new("RGB", (1080, 1920), (80, 0, 0))
    col = Image.new("RGB", (W * 2, H + (420 if crop else 0) + 18), (0, 0, 0))
    col.paste(ref.resize((W, H)), (0, 18))
    col.paste(mine.resize((W, H)), (W, 18))
    ImageDraw.Draw(col).text((4, 3), f"f{f}  original | render", fill=(255, 255, 0))
    if crop:
        x, y = crop
        box = (x - 180, y - 210, x + 180, y + 210)
        col.paste(ref.crop(box), (0, H + 18))
        col.paste(mine.crop(box), (W, H + 18))
    cols.append(col)
sheet = Image.new("RGB", (sum(c.width for c in cols), cols[0].height))
x = 0
for c in cols:
    sheet.paste(c, (x, 0))
    x += c.width
os.makedirs("work/compare", exist_ok=True)
sheet.save(f"work/compare/{name}.jpg", quality=88)
print(f"work/compare/{name}.jpg")
