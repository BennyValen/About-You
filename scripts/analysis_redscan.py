import subprocess, sys, numpy as np, cv2
sys.path.insert(0, "scripts/qa")
from threadmask import thread_mask
FF="./tools/ffmpeg.exe"; W,H=540,960
raw=subprocess.run([FF,"-v","error","-i","source/original.mp4","-vf",f"scale={W}:{H}","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True).stdout
fr=np.frombuffer(raw,np.uint8).reshape(-1,H,W,3)
top=[];bot=[];tot=[]
for n in range(len(fr)):
    m=thread_mask(fr[n],0.5)
    top.append(int(m[:24].sum())); bot.append(int(m[-24:].sum())); tot.append(int(m.sum()))
top=np.array(top); bot=np.array(bot); tot=np.array(tot)
np.save("work/redscan.npy", np.stack([top,bot,tot]))
CUTS=[0,294,608,954,1314,1674,2078,2492,2646,2982,3316,3648,4004]
for s in range(12):
    a,b=CUTS[s],CUTS[s+1]
    print(f"scene {s+1:2d}: thread px/frame median {np.median(tot[a:b]):5.0f}  touches bottom {np.mean(bot[a:b]>0)*100:3.0f}%  touches top {np.mean(top[a:b]>0)*100:3.0f}%")
first=[n for n in range(len(top)) if top[n]>0]
print("frames touching top edge:", first[:40], "... total", len(first))
