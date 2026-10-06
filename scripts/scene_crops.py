import subprocess, os, numpy as np
from PIL import Image, ImageDraw
FF="./tools/ffmpeg.exe"
CUTS=[0,294,608,954,1314,1674,2078,2492,2646,2982,3316,3648,4004]
# subject centre (x,y) at full res, refined after first look
SUBJ={1:(540,1240),2:(540,1300),3:(540,1240),4:(560,1160),5:(560,1180),6:(560,1180),7:(560,1180),8:(560,1180),9:(540,1180),10:(560,1200),11:(540,1220),12:(450,1260)}
for s in range(1,13):
    a,b=CUTS[s-1],CUTS[s]
    fl=[a+int((b-a)*p) for p in (0.1,0.5,0.9)]
    sel="+".join(f"eq(n\,{f})" for f in fl)
    subprocess.run([FF,"-v","error","-y","-i","source/original.mp4","-vf",f"select='{sel}'","-vsync","0","work/scene_notes/crops/tmp_%d.png"],check=True)
    ims=[Image.open(f"work/scene_notes/crops/tmp_{i+1}.png").convert("RGB") for i in range(3)]
    cx,cy=SUBJ[s]
    sheet=Image.new("RGB",(360*3+420*2,840),(0,0,0)); d=ImageDraw.Draw(sheet)
    for i,im in enumerate(ims):
        sheet.paste(im.resize((360,640)),(360*i,0)); d.text((360*i+4,644),f"f{fl[i]}",fill=(255,255,0))
    for i,idx in enumerate((1,2)):
        c=ims[idx].crop((cx-210,cy-210,cx+210,cy+210)); sheet.paste(c,(1080+420*i,0)); d.text((1080+420*i+4,424),f"1:1 f{fl[idx]} @({cx},{cy})",fill=(255,255,0))
    # palette
    q=ims[1].resize((270,480)).quantize(colors=12,method=Image.Quantize.MEDIANCUT)
    pal=q.getpalette()[:36]; cnt=sorted(q.getcolors(),reverse=True)
    hexes=[]
    for j,(n,ix) in enumerate(cnt):
        r,g,bb=pal[ix*3:ix*3+3]; hx=f"#{r:02x}{g:02x}{bb:02x}"; hexes.append(hx)
        d.rectangle([1080+j*70,440,1080+j*70+66,520],fill=(r,g,bb)); d.text((1080+j*70+2,524),hx,fill=(255,255,255))
    sheet.save(f"work/scene_notes/crops/s{s:02d}.jpg",quality=90)
    open(f"work/scene_notes/crops/s{s:02d}_palette.txt","w").write(" ".join(hexes))
    for i in range(3): os.remove(f"work/scene_notes/crops/tmp_{i+1}.png")
print("ok")
