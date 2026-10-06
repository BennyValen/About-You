# Scene 5 shadow connectivity gate: horse + rider cast a shadow on flat white ground, invisible to the camera,
# rendered at 12 gait phases (S5_SHADOW_GATE=1, see blender/scenes/s05.py); the shadow mask must be one piece.
import glob, subprocess, sys, os, shutil
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
out = "render/v4test/s5shadow"
if "--render" in sys.argv:
    shutil.rmtree(out, ignore_errors=True)
    env = dict(os.environ, S5_SHADOW_GATE="1")
    frames = ",".join(str(1420 + 4 * i) for i in range(12))
    subprocess.run(["./tools/blender/blender.exe", "-b", "--factory-startup", "-P", "blender/run.py", "--", "--scene", "5", "--scale", "0.5",
                    "--only", frames, "--out", os.path.abspath(out)], env=env, capture_output=True)
ok = True
for p in sorted(glob.glob(f"{out}/clean/*.jpg")):
    g = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2GRAY).astype(np.float32)
    m = (g < 0.75 * np.median(g)).astype(np.uint8)
    m = cv2.dilate(m, np.ones((3, 3), np.uint8))      # tolerate 1 px seams
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    big = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 20]
    piece = len(big) == 1
    ok &= piece
    print(os.path.basename(p), "shadow components:", len(big), "areas:", [int(st[i, cv2.CC_STAT_AREA]) for i in big], "one piece:", piece)
print("SCENE 5 SHADOW GATE:", "PASS" if ok else "FAIL")
