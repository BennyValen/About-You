import subprocess, numpy as np, sys
F = "./tools/ffmpeg.exe"
W, H = 72, 128
p = subprocess.Popen([F, "-hide_banner", "-loglevel", "error", "-i", "source/original.mp4",
                      "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     stdout=subprocess.PIPE)
frames = []
while True:
    b = p.stdout.read(W*H*3)
    if len(b) < W*H*3: break
    frames.append(np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32))
print("decoded frames:", len(frames))
d = [0.0] + [float(np.mean(np.abs(frames[i]-frames[i-1]))) for i in range(1, len(frames))]
d = np.array(d)
np.save("work/framediff.npy", d)
means = np.array([f.mean(axis=(0,1)) for f in frames])
np.save("work/framemeans.npy", means)
med = np.median(d)
idx = np.argsort(d)[::-1][:30]
for i in sorted(idx):
    print(i, round(i/24,3), round(d[i],2), "ratio", round(d[i]/max(1e-3, np.median(d[max(0,i-12):i+12])),1))
