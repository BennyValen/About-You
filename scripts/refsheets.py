from PIL import Image, ImageDraw
import os
cuts = [0,294,608,954,1314,1674,2078,2492,2646,2982,3316,3648,4004]
os.makedirs("work/ref/sheets", exist_ok=True)
for s in range(12):
    a, b = cuts[s], cuts[s+1]
    fr = [f for f in range(0, 4004, 24) if a <= f < b]
    if len(fr) > 8:
        fr = [fr[round(i*(len(fr)-1)/7)] for i in range(8)]
    tw, th = 270, 480
    sheet = Image.new("RGB", (tw*len(fr), th+20), (0,0,0))
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(fr):
        im = Image.open(f"work/ref/f{f:04d}.jpg").resize((tw, th))
        sheet.paste(im, (i*tw, 20))
        d.text((i*tw+4, 4), f"f={f} (+{f-a})", fill=(255,255,0))
    sheet.save(f"work/ref/sheets/scene{s+1:02d}.jpg", quality=88)
print("ok")
