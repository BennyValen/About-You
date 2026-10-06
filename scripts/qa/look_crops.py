# Side-by-side 1:1 crops (original left, ours right) for the look checklist.
#   python scripts/qa/look_crops.py SCENE FRAME x,y[,size] [x,y ...] --ours path/to/frame.jpg --out file.jpg
import sys, subprocess, numpy as np, cv2, argparse
FF = "./tools/ffmpeg.exe"
def frame(path, f):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{f/24:.4f}", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)
ap = argparse.ArgumentParser()
ap.add_argument("frame", type=int); ap.add_argument("boxes", nargs="*")
ap.add_argument("--ours", default=""); ap.add_argument("--ours_video", default=""); ap.add_argument("--out", required=True)
ap.add_argument("--full", type=int, default=480)
o = ap.parse_args()
orig = frame("source/original.mp4", o.frame)
ours = cv2.imread(o.ours) if o.ours else (frame(o.ours_video, o.frame) if o.ours_video else None)
if ours is not None and ours.shape[:2] != (1920, 1080):
    ours = cv2.resize(ours, (1080, 1920))
rows = []
h = o.full * 1920 // 1080
fulls = [cv2.resize(orig, (o.full, h), interpolation=cv2.INTER_AREA)]
if ours is not None: fulls.append(cv2.resize(ours, (o.full, h), interpolation=cv2.INTER_AREA))
top = np.hstack(fulls)
crops = []
for b in o.boxes:
    v = [int(x) for x in b.split(",")]
    x, y = v[0], v[1]; s = v[2] if len(v) > 2 else 400
    x = min(max(0, x - s // 2), 1080 - s); y = min(max(0, y - s // 2), 1920 - s)
    pair = [orig[y:y+s, x:x+s]] + ([ours[y:y+s, x:x+s]] if ours is not None else [])
    crops.append(np.hstack(pair))
W = max([top.shape[1]] + [c.shape[1] for c in crops])
pad = lambda im: np.hstack([im, np.zeros((im.shape[0], W - im.shape[1], 3), np.uint8)]) if im.shape[1] < W else im
out = np.vstack([pad(top)] + [pad(c) for c in crops])
cv2.imwrite(o.out, out, [cv2.IMWRITE_JPEG_QUALITY, 90])
print(o.out, out.shape)
