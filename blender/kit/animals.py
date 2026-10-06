"""Horse (with rider seat) built from a joint skeleton dressed with skin-modifier parts, like kit.human.

Body-local frame: +Y forward, +X right, +Z up, metres. Withers ~1.55 m, nose to tail ~2.5 m.
Gait: four-beat walk, lateral sequence LH -> LF -> RH -> RF (phase offsets 0, 0.25, 0.5, 0.75), duty 0.62;
stance hooves are planted in world space (no sliding), swing hooves arc between consecutive plants.
Head and neck nod twice per stride, the tail swishes, the barrel bobs and sways with the footfalls.
"""
import math
import numpy as np
import bpy
from mathutils import Matrix, Vector
from .human import ik2, rot_z

# rest skeleton (body-local)
J0 = dict(
    croup=(0, -0.62, 1.48), back=(0, -0.15, 1.42), withers=(0, 0.34, 1.56), chest=(0, 0.62, 1.22), belly=(0, 0.0, 1.05),
    neck0=(0, 0.6, 1.5), neck1=(0, 0.86, 1.74), poll=(0, 1.06, 1.9), muzzle=(0, 1.46, 1.58),
    dock=(0, -0.8, 1.42), tail1=(0, -0.98, 1.12), tail2=(0, -1.04, 0.78),
    sho_l=(-0.17, 0.5, 1.22), sho_r=(0.17, 0.5, 1.22), hip_l=(-0.19, -0.58, 1.3), hip_r=(0.19, -0.58, 1.3),
)
LEGS = {  # leg: (top joint, lateral, forward offset of the hoof at mid-stance, upper len, lower len, pole sign, phase offset)
    "lh": ("hip_l", -0.15, -0.6, 0.78, 0.42, -1.0, 0.0),
    "lf": ("sho_l", -0.14, 0.5, 0.74, 0.4, 1.0, 0.25),
    "rh": ("hip_r", 0.15, -0.6, 0.78, 0.42, -1.0, 0.5),
    "rf": ("sho_r", 0.14, 0.5, 0.74, 0.4, 1.0, 0.75),
}
PASTERN = 0.17


def _skin(name, verts, edges, radii, mat, coll, levels=2):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(0, 0, 0)] * len(verts), edges, [])
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    coll.objects.link(ob)
    sk = ob.modifiers.new("skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.7
    sv = me.skin_vertices[0].data
    for i, r in enumerate(radii):
        sv[i].radius = r
    sv[0].use_root = True
    ss = ob.modifiers.new("subd", "SUBSURF")
    ss.levels = 1
    ss.render_levels = levels
    ob["joints"] = verts
    return ob


class Horse:
    """v4: ONE connected skin-modifier mesh for the whole animal (spine, neck, head, ears, tail and four 3-segment legs
    joined in a single skeleton graph), so there are no gaps in any pose. The mane is a thin overlapping strip on the neck."""

    NAMES = ["croup", "back", "withers", "chest", "belly", "neck0", "neck1", "poll", "muzzle", "dock", "tail1", "tail2",
             "ear_l", "ear_r"]
    EDGES = [("croup", "back"), ("back", "withers"), ("withers", "chest"), ("back", "belly"), ("withers", "neck0"), ("neck0", "neck1"),
             ("neck1", "poll"), ("poll", "muzzle"), ("croup", "dock"), ("dock", "tail1"), ("tail1", "tail2"), ("poll", "ear_l"), ("poll", "ear_r")]
    RADII = dict(croup=(0.27, 0.25), back=(0.29, 0.29), withers=(0.25, 0.27), chest=(0.23, 0.26), belly=(0.24, 0.22), neck0=(0.18, 0.21),
                 neck1=(0.13, 0.16), poll=(0.1, 0.11), muzzle=(0.075, 0.085), dock=(0.07, 0.06), tail1=(0.08, 0.05), tail2=(0.05, 0.03),
                 ear_l=(0.022, 0.02), ear_r=(0.022, 0.02))

    def __init__(self, name, mats, coll, scale=1.0):
        self.k = scale
        names = list(self.NAMES)
        edges = list(self.EDGES)
        radii = dict(self.RADII)
        for leg, (top, *_rest) in LEGS.items():
            for seg, r in (("top", (0.12, 0.14)), ("mid", (0.065, 0.07)), ("fet", (0.05, 0.05)), ("hoof", (0.058, 0.058))):
                names.append(f"{leg}_{seg}")
                radii[f"{leg}_{seg}"] = r
            # the upper leg starts inside the torso (shoulder under the withers/chest, hip under the croup)
            edges += [("chest" if leg.endswith("f") else "croup", f"{leg}_top"), (f"{leg}_top", f"{leg}_mid"), (f"{leg}_mid", f"{leg}_fet"),
                      (f"{leg}_fet", f"{leg}_hoof")]
        idx = {n: i for i, n in enumerate(names)}
        me = bpy.data.meshes.new(name)
        me.from_pydata([(0, 0, 0)] * len(names), [(idx[a], idx[b]) for a, b in edges], [])
        ob = bpy.data.objects.new(name, me)
        ob.data.materials.append(mats["coat"])
        coll.objects.link(ob)
        sk = ob.modifiers.new("skin", "SKIN")
        sk.use_smooth_shade = True
        sk.branch_smoothing = 0.8
        sv = me.skin_vertices[0].data
        for n, i in idx.items():
            sv[i].radius = radii[n]
        sv[idx["back"]].use_root = True
        ss = ob.modifiers.new("subd", "SUBSURF")
        ss.levels = 1
        ss.render_levels = 2
        self.body = ob
        self.names = names
        self.mane = _skin(f"{name}_mane", ["mane0", "mane1", "mane2"], [(0, 1), (1, 2)],
                          [(0.045, 0.06), (0.04, 0.055), (0.03, 0.04)], mats["mane"], coll)
        # legacy attributes used by the walk solver
        self.parts = {"body": ob, "mane": self.mane}
        self.legs = {}
        self.ears = []

    def all_objects(self):
        return [self.body, self.mane]


class HorseWalk:
    """Planted-hoof walk along a 2D path. path(t)->(x,y) body centre on the ground, heading(t)->angle (0 = +Y)."""

    def __init__(self, horse, path, heading, t0, t1, stride=1.25, duty=0.62, ground=None, dt=0.25, fps=24):
        self.h, self.path, self.heading = horse, path, heading
        self.stride, self.duty = stride, duty
        self.ground = ground or (lambda x, y: 0.0)
        self.ts = np.arange(t0 - 120, t1 + 120, dt)
        pts = np.array([path(x) for x in self.ts], float)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        self.phase = np.concatenate([[0.0], np.cumsum(seg / stride)])
        self.phase_inv = self.phase + np.arange(len(self.phase)) * 1e-7

    def cycles(self, t):
        return float(np.interp(t, self.ts, self.phase))

    def time_at_phase(self, c):
        return float(np.interp(c, self.phase_inv, self.ts))

    def plant(self, leg, ci):
        top, lat, fwd, l1, l2, pole, off = LEGS[leg]
        tc = self.time_at_phase(ci + off + self.duty / 2)
        b = np.array(self.path(tc), float)
        hd = self.heading(tc)
        q = b + (rot_z(hd) @ np.array([lat, fwd, 0.0]))[:2]
        return np.array([q[0], q[1], self.ground(q[0], q[1])]), hd

    def hoof(self, leg, t):
        """hoof world position, lift height, in_stance"""
        off = LEGS[leg][6]
        c = self.cycles(t)
        p = (c - off) % 1.0
        ci = math.floor(c - off)
        if p < self.duty:
            P, _ = self.plant(leg, ci)
            return P, 0.0, True, p / self.duty
        A, _ = self.plant(leg, ci)
        B, _ = self.plant(leg, ci + 1)
        u = (p - self.duty) / (1 - self.duty)
        ue = 0.5 - 0.5 * math.cos(math.pi * u)
        lift = math.sin(math.pi * u) * 0.16
        return A * (1 - ue) + B * ue + np.array([0, 0, lift]), lift, False, u

    def body_frame(self, t):
        c = self.cycles(t)
        b = np.array(self.path(t), float)
        hd = self.heading(t)
        bob = 0.03 * math.cos(4 * math.pi * c)
        sway = 0.025 * math.sin(2 * math.pi * c)
        gz = self.ground(b[0], b[1])
        R = rot_z(hd)
        origin = np.array([b[0], b[1], gz]) + R @ np.array([sway, 0.0, bob])
        return origin, R, hd, c

    def pose(self, t, tail_t=None):
        hz = self.h
        k = hz.k
        origin, R, hd, c = self.body_frame(t)
        W = lambda v: origin + R @ (np.asarray(v, float) * k)
        J = {n: W(v) for n, v in J0.items()}
        # head nod (twice per stride) and slight lateral swing of the head
        nod = 0.05 * math.sin(4 * math.pi * c + 0.6)
        lat = 0.03 * math.sin(2 * math.pi * c + 0.3)
        for n, w in (("neck1", 0.4), ("poll", 0.8), ("muzzle", 1.0)):
            J[n] = J[n] + R @ np.array([lat * w, 0.0, -nod * w]) * k
        # mane along the top of the neck
        J["mane0"] = J["withers"] + R @ np.array([0, 0.18, 0.06]) * k
        J["mane1"] = (J["neck0"] + J["neck1"]) * 0.5 + R @ np.array([0, -0.04, 0.16]) * k
        J["mane2"] = J["poll"] + R @ np.array([0, -0.08, 0.08]) * k
        # tail swish
        tt = (t if tail_t is None else tail_t) / 24.0
        sw = 0.16 * math.sin(2 * math.pi * 0.42 * tt) + 0.05 * math.sin(2 * math.pi * 1.1 * tt + 1.0)
        J["tail1"] = J["tail1"] + R @ np.array([sw * 0.5, 0, 0]) * k
        J["tail2"] = J["tail2"] + R @ np.array([sw, -0.03, 0.02]) * k
        events = {}
        for leg in LEGS:
            top, la, fw, l1, l2, pole, off = LEGS[leg]
            hp, lift, stance, u = self.hoof(leg, t)
            fet = hp + np.array([0, 0, PASTERN * k]) + R @ np.array([0, -0.03 if pole > 0 else 0.03, 0]) * k
            mid, fet = ik2(J[top], fet, l1 * k, l2 * k, R @ np.array([0, pole, 0.0]))
            J[f"{leg}_top"], J[f"{leg}_mid"], J[f"{leg}_fet"], J[f"{leg}_hoof"] = J[top], mid, fet, hp + np.array([0, 0, 0.03 * k])
            events[leg] = (hp, stance, u)
        for side, sx in (("l", -1), ("r", 1)):
            J[f"ear_{side}"] = J["poll"] + R @ np.array([0.06 * sx, 0.01, 0.15]) * k
        co = np.array([J[n] for n in hz.names], np.float32).ravel()
        hz.body.data.vertices.foreach_set("co", co)
        hz.body.data.update()
        mco = np.array([J[n] for n in hz.mane["joints"]], np.float32).ravel()
        hz.mane.data.vertices.foreach_set("co", mco)
        hz.mane.data.update()
        self.J = J
        self.R = R
        return J, R, hd, events

    def saddle(self, t):
        """saddle seat point and frame (for the rider and the thread attach)"""
        origin, R, hd, c = self.body_frame(t)
        k = self.h.k
        return origin + R @ np.array([0, 0.08, 1.62]) * k, R, hd

    def cantle(self, t):
        origin, R, hd, c = self.body_frame(t)
        k = self.h.k
        return origin + R @ np.array([0, -0.22, 1.6]) * k


def rider_joints(seat, R, t, k=1.0, cycles=0.0):
    """seated rider joint dict (kit.human names) on a saddle seat; hands forward to the reins"""
    bob = 0.015 * math.cos(4 * math.pi * cycles + 0.5)
    sway = -0.012 * math.sin(2 * math.pi * cycles)
    W = lambda v: seat + R @ (np.asarray(v, float) * k)
    J = {}
    J["pelvis"] = W((sway, -0.02, 0.06 + bob))
    J["spine"] = W((sway * 1.2, 0.0, 0.25 + bob))
    J["chest"] = W((sway * 1.4, 0.03, 0.45 + bob))
    J["neck"] = W((sway * 1.5, 0.05, 0.62 + bob))
    J["head"] = W((sway * 1.5, 0.07, 0.74 + bob))
    for s, sx in (("l", -1), ("r", 1)):
        J[f"sho_{s}"] = W((sx * 0.19 + sway, 0.03, 0.55 + bob))
        J[f"elb_{s}"] = W((sx * 0.22 + sway, 0.2, 0.33 + bob))
        J[f"wri_{s}"] = W((sx * 0.1, 0.42, 0.28 + bob * 0.5))
        J[f"hnd_{s}"] = W((sx * 0.07, 0.5, 0.27))
        J[f"hip_{s}"] = W((sx * 0.1, 0.0, 0.02))
        J[f"kne_{s}"] = W((sx * 0.3, 0.2, -0.28))
        J[f"ank_{s}"] = W((sx * 0.3, 0.06, -0.7))
        J[f"toe_{s}"] = W((sx * 0.3, 0.2, -0.72))
    J["hem_l"] = J["hem_r"] = J["hem_b"] = J["pelvis"]
    return J
