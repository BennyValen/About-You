"""The red thread: a 200-segment Verlet cord, simulated deterministically per scene.

Environments:
  'ground' : gravity, lies on the ground (height function), Coulomb-like friction -> drags and sags.
  'water'  : floats at the surface (buoyancy spring + water drag), follows a surface flow field (wakes).
  'air'    : gravity + quadratic-ish air drag against a wind field; hangs and trails from a flier,
             and drapes onto the ground far below if it reaches it.
One end is pinned to its owner (waist, harness, stern, coupler); the other end is free and lies beyond
the frame edge. The whole cord is one curve object for its whole life.
"""
import numpy as np
import bpy

G = np.array([0.0, 0.0, -9.81])


class Cord:
    def __init__(self, n_seg=200, length=30.0, mode="ground", ground=None, water_level=0.0,
                 friction=0.85, air_drag=1.6, water_drag=6.0, wind=None, flow=None, substeps=6, iters=24,
                 bend=0.08, damping=0.995, thickness_rest=0.004, push=None):
        self.n = n_seg
        self.rest = length / n_seg
        self.mode = mode
        self.ground = ground or (lambda x, y: np.zeros_like(x))
        self.wl = water_level
        self.mu = friction
        self.cd_air = air_drag
        self.cd_w = water_drag
        self.wind = wind
        self.flow = flow
        self.sub = substeps
        self.iters = iters
        self.bend = bend
        self.damp = damping
        self.z_off = thickness_rest
        self.push = push

    def _constrain(self, P, pin):
        n = self.n
        idx = np.arange(n)
        w = np.ones(n + 1)
        w[0] = 0.0
        for _ in range(self.iters):
            P[0] = pin
            for par in (0, 1):
                i = idx[par::2]
                d = P[i + 1] - P[i]
                L = np.linalg.norm(d, axis=1)[:, None] + 1e-9
                wa, wb = w[i][:, None], w[i + 1][:, None]
                corr = (L - self.rest) / L * d / (wa + wb)
                P[i] += corr * wa
                P[i + 1] -= corr * wb
            if self.bend > 0:
                j = np.arange(n - 1)
                d = P[j + 2] - P[j]
                L = np.linalg.norm(d, axis=1)[:, None] + 1e-9
                r2 = 2 * self.rest * 0.97
                short = (L < r2)
                wa, wb = w[j][:, None], w[j + 2][:, None]
                corr = (L - r2) / L * d / (wa + wb) * self.bend * short
                P[j] += corr * wa
                P[j + 2] -= corr * wb
        P[0] = pin

    def run(self, frames, anchor, trail_dir, warm=72, fps=24):
        """frames: sorted list of frames to record. anchor(f) -> xyz (float frame allowed).
        trail_dir: unit xy vector the cord initially trails toward. Returns {f: (n+1,3) array}."""
        f0 = frames[0]
        a0 = np.asarray(anchor(f0 - warm), float)
        td = np.array([trail_dir[0], trail_dir[1], 0.0])
        td /= np.linalg.norm(td) + 1e-9
        s = np.arange(self.n + 1)[:, None] * self.rest
        P = a0[None, :] + td[None, :] * s
        gz = self.ground(P[:, 0], P[:, 1])
        if self.mode == "water":
            P[:, 2] = self.wl + self.z_off
        else:
            P[:, 2] = np.maximum(P[:, 2], gz + self.z_off)
        Pp = P.copy()
        dt = 1.0 / fps / self.sub
        out = {}
        want = set(frames)
        last = frames[-1]
        for fi in range(f0 - warm, last + 1):
            for k in range(self.sub):
                t = fi + (k + 1) / self.sub
                pin = np.asarray(anchor(t), float)
                vel = (P - Pp) * self.damp
                Pp = P.copy()
                acc = np.tile(G, (self.n + 1, 1))
                if self.mode == "water":
                    v = vel / dt
                    fl = np.zeros_like(P)
                    if self.flow is not None:
                        fx, fy = self.flow(P[:, 0], P[:, 1], t)
                        fl[:, 0], fl[:, 1] = fx, fy
                    under = P[:, 2] < self.wl + self.z_off
                    acc[:, 2] += np.where(under, 9.81 + 400.0 * (self.wl + self.z_off - P[:, 2]), 0.0)
                    acc[:, :2] += -self.cd_w * (v[:, :2] - fl[:, :2]) * under[:, None]
                    acc[:, 2] += -self.cd_w * 2 * v[:, 2] * under
                elif self.mode == "air":
                    v = vel / dt
                    wv = np.zeros_like(P)
                    if self.wind is not None:
                        wx, wy, wz = self.wind(P[:, 0], P[:, 1], P[:, 2], t)
                        wv[:, 0], wv[:, 1], wv[:, 2] = wx, wy, wz
                    rel = v - wv
                    sp = np.linalg.norm(rel, axis=1)[:, None]
                    acc += -self.cd_air * rel * (0.4 + sp * 0.25)
                if self.push is not None:
                    px, py = self.push(P[:, 0], P[:, 1], t)
                    acc[:, 0] += px
                    acc[:, 1] += py
                P = P + vel + acc * dt * dt
                self._constrain(P, pin)
                if self.mode != "water":
                    gz = self.ground(P[:, 0], P[:, 1]) + self.z_off
                    low = P[:, 2] <= gz + 1e-4
                    if low.any():
                        P[low, 2] = gz[low]
                        # friction: kill most tangential velocity of points in contact (mu may vary by surface)
                        mu = self.mu(P[low, 0], P[low, 1])[:, None] if callable(self.mu) else self.mu
                        Pp[low, :2] = P[low, :2] - (P[low, :2] - Pp[low, :2]) * (1.0 - mu)
                        Pp[low, 2] = P[low, 2]
            if fi in want:
                out[fi] = P.copy()
        return out


class CordCurve:
    """Renderable curve for a Cord: constant screen thickness (per-point radius from camera distance)."""

    def __init__(self, name, n_pts, material, rig, px=3.6, coll=None):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions = "3D"
        cu.bevel_mode = "ROUND"
        cu.bevel_depth = 1.0
        cu.bevel_resolution = 2
        cu.use_fill_caps = True
        sp = cu.splines.new("POLY")
        sp.points.add(n_pts - 1)
        self.sp = sp
        self.obj = bpy.data.objects.new(name, cu)
        self.obj.data.materials.append(material)
        (coll or bpy.context.scene.collection).objects.link(self.obj)
        self.rig = rig
        self.px = px

    def set(self, P):
        n = len(P)
        co = np.c_[P, np.ones(n)].astype(np.float32).ravel()
        self.sp.points.foreach_set("co", co)
        k = self.rig.ppm_at(P[:, 2])
        rad = (self.px * 0.5 / k).astype(np.float32)
        self.sp.points.foreach_set("radius", rad)
        self.obj.data.update_tag()


def endpoint_record(rig, f, P, owner_xy=None):
    """Screen-space endpoints for the per-frame thread log, plus whether any of the cord is in frame."""
    a = rig.world_to_screen(f, P[0])
    b = rig.world_to_screen(f, P[-1])
    S = np.array([rig.world_to_screen(f, p) for p in P])
    inside = (S[:, 0] >= 0) & (S[:, 0] <= 1080) & (S[:, 1] >= 0) & (S[:, 1] <= 1920)
    seg = np.linalg.norm(np.diff(S, axis=0), axis=1)
    vis_len = float(seg[inside[1:] & inside[:-1]].sum())
    return {"f": int(f), "owner_end": [round(a[0], 1), round(a[1], 1)], "free_end": [round(b[0], 1), round(b[1], 1)],
            "free_end_outside": bool(b[0] < -2 or b[0] > 1082 or b[1] < -2 or b[1] > 1922), "visible": bool(vis_len > 30.0),
            "visible_px": round(vis_len, 1),
            "segments": int(len(P) - 1)}
