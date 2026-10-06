"""Run the v3 rope for a scene's owner(s) and export what the post-process draws.

thread.npz      per owner: frames, screen points (n_draw, n+1, 2) float32, height above the surface below (m) float16
thread_log.json per drawing endpoint log (owner end, free end, free end outside the frame, visible length, segments)
"""
import json, os
import numpy as np
from . import rope as R
from . import rope_cfg as C


class Owner:
    def __init__(self, name, scene, rig, anchor, frames, trail=(0.0, -1.0), ground_fn=None, surface_fn=None, push=None,
                 warm=150, seed_offset=0, cfg_motion=True, heading_fn=None):
        """anchor(t) -> xyz of the owner's attach point WITHOUT the rope_cfg owner motion (added here when cfg_motion).
        surface_fn(x, y) -> height of the surface below (for the shadow offset); defaults to ground_fn or 0."""
        self.name, self.scene, self.rig = name, scene, rig
        mot = C.owner_motion(scene) if cfg_motion else (lambda t: (0.0, 0.0, 0.0))
        self.motion = mot

        def anc(t):
            p = np.asarray(anchor(t), float)
            d = mot(t)
            return np.array([p[0] + d[0], p[1] + d[1], p[2] + d[2]])
        self.anchor = anc
        self.rope = C.make_rope(scene, ground_fn=ground_fn, push=push, seed_offset=seed_offset)
        self.surface = surface_fn or ground_fn or (lambda x, y: np.zeros_like(x))
        self.frames = list(frames)
        self.heading_fn = heading_fn
        self.sim = self.rope.run(self.frames, anc, trail, warm=warm)

    def points(self, f):
        return self.sim.get(f)

    def screen(self, f):
        P = self.sim[f]
        S = np.array([self.rig.world_to_screen(f, p) for p in P], np.float32)
        hgt = (P[:, 2] - self.surface(P[:, 0], P[:, 1])).astype(np.float32)
        return S, hgt


def owner_offset(scene, f):
    """the rope_cfg owner motion at frame f (so scenes can move the hero body with its own attach point)"""
    return C.owner_motion(scene)(f)


def export(out_dir, owners, frames=None):
    os.makedirs(out_dir, exist_ok=True)
    data = {"owners": np.array([o.name for o in owners])}
    log = {}
    for o in owners:
        fr = [f for f in (frames or o.frames) if f in o.sim]
        pts, hg = [], []
        for f in fr:
            S, h = o.screen(f)
            pts.append(S)
            hg.append(h)
            log.setdefault(f, {"f": int(f)})[o.name] = endpoint(S, len(S) - 1)
        data[f"{o.name}_frames"] = np.array(fr, np.int32)
        data[f"{o.name}_pts"] = np.array(pts, np.float32)
        data[f"{o.name}_hgt"] = np.array(hg, np.float16)
    np.savez_compressed(os.path.join(out_dir, "thread.npz"), **data)
    # hero motion log (v4 gate): where the thread leaves the traveller, in screen px (camera motion removed), and yaw
    rows = []
    for o in owners:
        fr = [f for f in (frames or o.frames) if f in o.sim]
        xy = np.array([o.screen(f)[0][0] for f in fr])
        if o.heading_fn is not None:
            yaw = [float(np.degrees(o.heading_fn(f))) for f in fr]
        else:
            d = np.gradient(xy, axis=0)
            yaw = list(np.degrees(np.arctan2(d[:, 0], -d[:, 1] + 1e-9)))
        for f, (x, y), yw in zip(fr, xy, yaw):
            rows.append(f"{f},{o.scene},{o.name},{x:.2f},{y:.2f},{yw:.3f}")
    with open(os.path.join(out_dir, "hero_motion.csv"), "w") as fh:
        fh.write("frame,scene,hero,x,y,yaw_deg\n")
        for row in rows:
            fh.write(row + "\n")
    json.dump([log[f] for f in sorted(log)], open(os.path.join(out_dir, "thread_log.json"), "w"))


def endpoint(S, nseg):
    a, b = S[0], S[-1]
    inside = (S[:, 0] >= 0) & (S[:, 0] <= 1080) & (S[:, 1] >= 0) & (S[:, 1] <= 1920)
    seg = np.linalg.norm(np.diff(S, axis=0), axis=1)
    vis_len = float(seg[inside[1:] & inside[:-1]].sum())
    jump = float(seg.max())
    return {"owner_end": [round(float(a[0]), 1), round(float(a[1]), 1)], "free_end": [round(float(b[0]), 1), round(float(b[1]), 1)],
            "free_end_outside": bool(b[0] < -2 or b[0] > 1082 or b[1] < -2 or b[1] > 1922), "visible": bool(vis_len > 30.0),
            "visible_px": round(vis_len, 1), "max_seg_px": round(jump, 2), "segments": int(nseg)}
