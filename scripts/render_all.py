# v3 final render driver (resumable): Blender renders each scene's drawings (even frames) to render/v3/scene_XX
# (clean JPEG + aux passes + meta + thread.npz); the painting post-process for that scene starts right away in the
# background (CPU) while the next scene renders (GPU). Per-scene timings go to work/final_render_v3.log.
#   python scripts/render_all.py [scene ...] [--tag=A] [--jobs=6]
import os, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
BL = os.path.join(ROOT, "tools", "blender", "blender.exe")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
order = [int(x) for x in args] or [12, 5, 4, 3, 9, 10, 6, 7, 2, 1, 11, 8]
tag = opts.get("tag", "")
jobs = opts.get("jobs", "6")
extra = []
if "samples" in opts:
    extra += ["--samples", opts["samples"]]
log = open(os.path.join(ROOT, "work", f"final_render_v3{tag}.log"), "a", buffering=1)


def say(msg):
    log.write(time.strftime("%H:%M:%S ") + msg + "\n")


posts = []
t_all = time.time()
for s in order:
    out = os.path.join(ROOT, "render", opts.get("root", "v4"), f"scene_{s:02d}")
    say(f"scene {s}: start")
    t = time.time()
    for attempt in range(3):
        r = subprocess.run([BL, "-b", "--factory-startup", "-P", os.path.join(ROOT, "blender", "run.py"), "--", "--scene", str(s), "--out", out] + extra,
                           capture_output=True, text=True)
        lines = (r.stdout + r.stderr).splitlines()
        renders = [l for l in lines if l.startswith("RENDER s") and " f" in l and "done" not in l]
        tail = [l for l in lines if l.startswith(("BUILD", "Traceback", "RENDER s")) and ("done" in l or not l.startswith("RENDER")) or "Error:" in l][-4:]
        say(f"scene {s}: blender exit {r.returncode} " + " | ".join(tail))
        if r.returncode == 0 and os.path.exists(os.path.join(out, "thread.npz")):
            break
    secs = [float(l.split()[3].rstrip("s")) for l in renders if len(l.split()) > 3]
    say(f"scene {s}: rendered in {time.time() - t:.0f}s ({len(secs)} drawings, median {sorted(secs)[len(secs) // 2] if secs else 0:.2f}s/drawing)")
    cal = os.path.join(ROOT, "work", "v4", "calib", f"s{s:02d}.json")
    post_cmd = ([sys.executable, "scripts/post/repost.py", str(s), f"--jobs={jobs}", f"--root={opts.get('root', 'v4')}"] if os.path.exists(cal) else
                [sys.executable, "scripts/post/paint.py", "--scene", str(s), "--dir", out, "--jobs", jobs])
    posts.append((s, subprocess.Popen(post_cmd,
                                      stdout=open(os.path.join(ROOT, "work", f"post_s{s:02d}.log"), "w"), stderr=subprocess.STDOUT)))
for s, p in posts:
    p.wait()
    say(f"scene {s}: post exit {p.returncode}")
say(f"all done in {time.time() - t_all:.0f}s")
