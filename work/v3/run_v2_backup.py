"""Render one scene headless, resumable.

  blender -b --factory-startup -P blender/run.py -- --scene 12 [--scale 0.5] [--look cel|photo]
          [--frames 3648-4003] [--only 3700,3800] [--out render/scene_12] [--every 2]

Frames are drawings on twos (the original is fully on twos): every even frame of the scene is rendered;
the encoder holds each drawing for two frames. Existing PNGs are skipped (resume after a crash).
"""
import sys, os, argparse, importlib, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kit import core, look  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--scene", type=int, required=True)
ap.add_argument("--scale", type=float, default=1.0)
ap.add_argument("--look", default="cel")
ap.add_argument("--frames", default="")
ap.add_argument("--only", default="")
ap.add_argument("--out", default="")
ap.add_argument("--every", type=int, default=2)
ap.add_argument("--samples", type=int, default=8)
ap.add_argument("--save_blend", action="store_true")
opt = ap.parse_args(argv)

t0 = time.time()
mod = importlib.import_module(f"scenes.s{opt.scene:02d}")
run = mod.build(opt)
print(f"BUILD scene {opt.scene} in {time.time() - t0:.1f}s", flush=True)
look.set_look(opt.look)
start, end = core.span(opt.scene)
if opt.only:
    frames = [int(x) for x in opt.only.split(",")]
else:
    a, b = start, end
    if opt.frames:
        a, b = [int(x) for x in opt.frames.split("-")]
        b += 1
    frames = [f for f in core.drawing_frames(start, end, opt.every) if a <= f < b]
out = opt.out or os.path.join(core.ROOT, "render", f"scene_{opt.scene:02d}" + ("" if opt.scale == 1.0 else f"_s{int(opt.scale * 100)}"))
if opt.save_blend:
    import bpy
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(core.ROOT, "work", f"scene_{opt.scene:02d}.blend"))
core.render_frames(frames, out, run.update, label=f"s{opt.scene}")
if hasattr(run, "finish"):
    run.finish(out)
