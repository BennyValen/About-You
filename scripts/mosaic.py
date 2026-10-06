# Reference-only world mosaic of a scene: frames stitched with the measured camera offsets (for placing
# environment features by eye). Never used in the output.
import sys, json, subprocess, numpy as np
from PIL import Image
FF = "./tools/ffmpeg.exe"
scene = int(sys.argv[1]); step = int(sys.argv[2]) if len(sys.argv) > 2 else 12
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
a, b = CUTS[scene - 1], CUTS[scene]
prof = json.load(open("work/cam_profile.json"))[str(scene)]   # per-frame dy px/f at 1080, local index
cum = np.concatenate([[0], np.cumsum(prof)])
W, H = 270, 480
raw = subprocess.run([FF, "-v", "error", "-i", "source/original.mp4", "-vf", f"select='between(n\,{a}\,{b-1})*not(mod(n-{a}\,{step}))',scale={W}:{H}",
                      "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
k = W / 1080
total = cum[b - a - 1] * k
canvas = np.zeros((int(total) + H + 4, W, 3), np.uint8)
for j, f in enumerate(range(a, b, step)):
    if j >= len(fr): break
    y = int(round(total - cum[f - a] * k))
    canvas[y:y + H] = fr[j]
Image.fromarray(canvas).save(f"work/compare/mosaic_s{scene:02d}.jpg", quality=88)
print("mosaic", canvas.shape, "travel px@1080", cum[-1])
