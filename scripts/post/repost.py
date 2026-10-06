# Re-run the painting post (v4 fine boil) for scenes with their calibrated boil_scale (work/v4/calib/sXX.json).
#   python scripts/post/repost.py SCENE [SCENE ...] [--jobs=4]
import json, os, subprocess, sys
jobs = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--jobs=")), "4")
root = next((a.split("=")[1] for a in sys.argv[1:] if a.startswith("--root=")), "v4")
for s in [int(a) for a in sys.argv[1:] if not a.startswith("--")]:
    c = json.load(open(f"work/v4/calib/s{s:02d}.json"))
    over = f"boil_mode=fine,boil_scale={c['boil_scale']}"
    print(f"scene {s}: {over}", flush=True)
    subprocess.run([sys.executable, "scripts/post/paint.py", "--scene", str(s), "--dir", f"render/{root}/scene_{s:02d}", "--jobs", jobs, "--force",
                    "--set", over], check=True)
