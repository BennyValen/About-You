# Section 7 gate 4 (speed parity per distinct step) and gate 3 (on-twos dup fraction), as given in the brief.
#   python scripts/qa/speed_parity.py [render.mp4]
import subprocess, sys, numpy as np
FF = "./tools/ffmpeg.exe"
def load(p):
    raw = subprocess.run([FF,"-v","error","-i",p,"-vf","scale=108:192,format=gray",
                          "-f","rawvideo","-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1,192,108).astype(np.int16)
def mad(a): return np.abs(np.diff(a, axis=0)).mean(axis=(1,2))
cuts=[0,294,608,954,1314,1674,2078,2492,2646,2982,3316,3648,4004]
if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out/final.mp4"
    o, r = mad(load("source/original.mp4")), mad(load(out))
    for i in range(12):
        a,b = cuts[i], cuts[i+1]-1
        so, sr = o[a:b], r[a:b]
        dist = lambda x: x[x>=0.05].mean() if (x>=0.05).any() else 0
        dup  = lambda x: (x<0.05).mean()
        print(i+1, "speed ratio", round(dist(sr)/(dist(so)+1e-6),2), "dup orig/new", round(dup(so),2), round(dup(sr),2),
              "| median odd-pair diff new", round(float(np.median(sr[1::2] if (a%2==0) else sr[0::2])),3))
