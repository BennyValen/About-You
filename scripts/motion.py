import subprocess, numpy as np
F = "./tools/ffmpeg.exe"
W, H = 270, 480
p = subprocess.Popen([F, "-hide_banner", "-loglevel", "error", "-i", "source/original.mp4",
                      "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
frames = []
while True:
    b = p.stdout.read(W*H)
    if len(b) < W*H: break
    frames.append(np.frombuffer(b, np.uint8).reshape(H, W).astype(np.float32))
def pc(a, b):
    win = np.outer(np.hanning(H), np.hanning(W))
    A = np.fft.fft2((a-a.mean())*win); B = np.fft.fft2((b-b.mean())*win)
    R = A*np.conj(B); R /= np.abs(R)+1e-6
    r = np.fft.ifft2(R).real
    y, x = np.unravel_index(np.argmax(r), r.shape)
    if y > H/2: y -= H
    if x > W/2: x -= W
    return y, x
cuts = [0,294,608,954,1314,1674,2078,2492,2646,2982,3316,3648,4004]
for s in range(12):
    a, b = cuts[s], cuts[s+1]
    res = []
    for n in range(a+2, b-12, 24):
        dy, dx = pc(frames[n+8], frames[n])  # shift over 8 frames
        res.append((n-a, dy, dx))
    dys = [r[1] for r in res]; dxs = [r[2] for r in res]
    # convert to 1080 px per frame: *4 /8
    print(f"scene {s+1}: dy/frame(1080px) median {np.median(dys)*4/8:.2f}  dx {np.median(dxs)*4/8:.2f}   series dy:", [round(r[1]*0.5,1) for r in res][::2])
