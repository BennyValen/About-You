p = "blender/kit/core.py"
s = open(p).read()
a = '''def render_frames(frames, out_dir, update, label=""):
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    t_all = time.time()
    done = 0
    for f in frames:
        path = os.path.join(out_dir, f"f{f:04d}.png")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        t = time.time()
        sc.frame_set(f)
        update(f)
        t1 = time.time()
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done += 1
        print(f"RENDER {label} f{f} {time.time() - t:.2f}s (update {t1 - t:.2f}s)", flush=True)
    print(f"RENDER {label} done {done} frames in {time.time() - t_all:.1f}s", flush=True)'''
b = '''def camera_record():
    """camera position and ground-plane scale of the current frame (for the 2D post: stroke anchoring, thread)"""
    cam = bpy.context.scene.camera
    x, y, h = cam.matrix_world.translation
    cd = cam.data
    vis_h = h * cd.sensor_height / cd.lens
    return {"x": round(float(x), 5), "y": round(float(y), 5), "h": round(float(h), 4), "ppm": round(H / vis_h, 5)}


def render_frames(frames, out_dir, update, label="", fmt="JPEG"):
    """v3: drawings -> out_dir/clean/fNNNN.jpg, aux passes -> out_dir/aux, camera per drawing -> out_dir/meta.json"""
    from . import look
    clean = os.path.join(out_dir, "clean")
    aux = os.path.join(out_dir, "aux")
    os.makedirs(clean, exist_ok=True)
    os.makedirs(aux, exist_ok=True)
    look.set_aux_dir(aux)
    sc = bpy.context.scene
    if fmt == "JPEG":
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 95
        ext = "jpg"
    else:
        ext = "png"
    meta_p = os.path.join(out_dir, "meta.json")
    meta = json.load(open(meta_p)) if os.path.exists(meta_p) else {}
    cams = meta.setdefault("cams", {})
    t_all = time.time()
    done = 0
    for f in frames:
        path = os.path.join(clean, f"f{f:04d}.{ext}")
        if os.path.exists(path) and os.path.getsize(path) > 0 and str(f) in cams:
            continue
        t = time.time()
        sc.frame_set(f)
        update(f)
        cams[str(f)] = camera_record()
        t1 = time.time()
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done += 1
        print(f"RENDER {label} f{f} {time.time() - t:.2f}s (update {t1 - t:.2f}s)", flush=True)
        if done % 10 == 0:
            json.dump(meta, open(meta_p, "w"))
    json.dump(meta, open(meta_p, "w"))
    print(f"RENDER {label} done {done} frames in {time.time() - t_all:.1f}s", flush=True)
    return meta'''
assert a in s
s = s.replace(a, b)
open(p, "w").write(s)

p = "blender/run.py"
s = open(p).read()
a = '''out = opt.out or os.path.join(core.ROOT, "render", f"scene_{opt.scene:02d}" + ("" if opt.scale == 1.0 else f"_s{int(opt.scale * 100)}"))'''
b = '''out = opt.out or os.path.join(core.ROOT, "render", "v3", f"scene_{opt.scene:02d}" + ("" if opt.scale == 1.0 else f"_s{int(opt.scale * 100)}"))
os.makedirs(out, exist_ok=True)
# post-process parameters chosen by the scene (scripts/post/paint.py reads them from meta.json)
mp = os.path.join(out, "meta.json")
meta = json.load(open(mp)) if os.path.exists(mp) else {}
meta["post"] = dict(getattr(mod, "POST", {}), **getattr(run, "post", {}))
meta["scene"] = opt.scene
meta["scale"] = opt.scale
json.dump(meta, open(mp, "w"))'''
assert a in s
s = s.replace(a, b)
open(p, "w").write(s)
print("patched core.render_frames and run.py")
