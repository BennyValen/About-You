from PIL import Image, ImageDraw
import os
CUTS=[0,294,608,954,1314,1674,2078,2492,2646,2982,3316,3648,4004]
for s in range(12):
    a,b=CUTS[s],CUTS[s+1]
    fl=[f for f in range(0,4004,6) if a<=f<b][::2]   # 2 per second for the sheet
    cols=10; tw,th=135,240
    rows=(len(fl)+cols-1)//cols
    sh=Image.new("RGB",(cols*tw,rows*(th+14)),(0,0,0)); d=ImageDraw.Draw(sh)
    for i,f in enumerate(fl):
        im=Image.open(f"work/ref4/f{f:04d}.jpg").resize((tw,th))
        x,y=(i%cols)*tw,(i//cols)*(th+14)
        sh.paste(im,(x,y+14)); d.text((x+2,y+1),f"{f} {f/24:.1f}s",fill=(255,255,0))
    sh.save(f"work/ref4/sheets/scene{s+1:02d}.jpg",quality=85)
print("ok")
