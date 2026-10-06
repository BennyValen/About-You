import subprocess, numpy as np, cv2
FF="./tools/ffmpeg.exe"; W,H=540,960
raw=subprocess.run([FF,"-v","error","-i","source/original.mp4","-vf",f"scale={W}:{H},format=gray","-f","rawvideo","-"],capture_output=True).stdout
fr=np.frombuffer(raw,np.uint8).reshape(-1,H,W)
np.save("work/gray540.npy", fr)
CUTS=[0,294,608,954,1314,1674,2078,2492,2646,2982,3316,3648,4004]
win=cv2.createHanningWindow((W,H),cv2.CV_32F)
for s in range(12):
    a,b=CUTS[s],CUTS[s+1]
    res=[]
    for k in (2,4,8,16,24,48):
        vals=[]
        for n in range(a+4,b-k-2,24):
            (sx,sy),r=cv2.phaseCorrelate(fr[n].astype(np.float32),fr[n+k].astype(np.float32),win)
            vals.append(sy*2/k)
        res.append(f"k{k}:{np.median(vals):5.2f}")
    print(f"scene {s+1:2d} dy px/f(1080) by span:", " ".join(res))
