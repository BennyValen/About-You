"""Procedural human: a joint skeleton dressed with skin-modifier body parts (shirt, trousers, shoes,
hands, neck), sphere head + hair. Poses are computed per drawing (on twos) from activity solvers with
analytic two-bone IK; the walk keeps stance feet planted in world space (no sliding).

Body-local frame: +Y forward (facing), +X right, +Z up. Units: metres. Default height ~1.72 m.
"""
import math
import numpy as np
import bpy
from mathutils import Vector, Matrix

JOINTS = ["pelvis", "spine", "chest", "neck", "head", "sho_l", "elb_l", "wri_l", "hnd_l", "sho_r", "elb_r",
          "wri_r", "hnd_r", "hip_l", "kne_l", "ank_l", "toe_l", "hip_r", "kne_r", "ank_r", "toe_r", "hem_l", "hem_r", "hem_b"]

# part: list of (joint chain) edges; radii per joint
PARTS = {
    "top": dict(edges=[("pelvis", "spine"), ("spine", "chest"), ("chest", "neck"), ("chest", "sho_l"), ("sho_l", "elb_l"),
                       ("elb_l", "wri_l"), ("chest", "sho_r"), ("sho_r", "elb_r"), ("elb_r", "wri_r")],
                radius=dict(pelvis=(0.135, 0.11), spine=(0.13, 0.1), chest=(0.15, 0.11), neck=(0.06, 0.06), sho_l=(0.068, 0.068),
                            elb_l=(0.052, 0.052), wri_l=(0.042, 0.042), sho_r=(0.068, 0.068), elb_r=(0.052, 0.052), wri_r=(0.042, 0.042))),
    "legs": dict(edges=[("pelvis", "hip_l"), ("hip_l", "kne_l"), ("kne_l", "ank_l"), ("pelvis", "hip_r"), ("hip_r", "kne_r"), ("kne_r", "ank_r")],
                 radius=dict(pelvis=(0.13, 0.1), hip_l=(0.088, 0.088), kne_l=(0.06, 0.06), ank_l=(0.046, 0.046),
                             hip_r=(0.088, 0.088), kne_r=(0.06, 0.06), ank_r=(0.046, 0.046))),
    "shoes": dict(edges=[("ank_l", "toe_l"), ("ank_r", "toe_r")],
                  radius=dict(ank_l=(0.05, 0.05), toe_l=(0.042, 0.03), ank_r=(0.05, 0.05), toe_r=(0.042, 0.03))),
    "hands": dict(edges=[("wri_l", "hnd_l"), ("wri_r", "hnd_r")],
                  radius=dict(wri_l=(0.036, 0.03), hnd_l=(0.034, 0.022), wri_r=(0.036, 0.03), hnd_r=(0.034, 0.022))),
    "coat": dict(edges=[("pelvis", "hem_l"), ("pelvis", "hem_r"), ("pelvis", "hem_b")],
                 radius=dict(pelvis=(0.15, 0.12), hem_l=(0.1, 0.06), hem_r=(0.1, 0.06), hem_b=(0.12, 0.06))),
}

L_UPPER, L_FORE, L_HAND = 0.29, 0.26, 0.09
L_THIGH, L_SHIN = 0.445, 0.44


def ik2(a, c, l1, l2, pole):
    """two-bone IK: root a, target c, bone lengths, pole direction -> middle joint b (numpy)"""
    d = c - a
    dist = np.linalg.norm(d)
    dist_c = min(max(dist, 1e-4), l1 + l2 - 1e-4)
    u = d / (dist + 1e-9)
    if dist > l1 + l2 - 1e-4:
        c = a + u * dist_c
    x = (l1 * l1 - l2 * l2 + dist_c * dist_c) / (2 * dist_c)
    hgt = math.sqrt(max(l1 * l1 - x * x, 0.0))
    p = pole - np.dot(pole, u) * u
    pn = np.linalg.norm(p)
    p = p / pn if pn > 1e-6 else np.array([0.0, 0.0, 1.0])
    return a + u * x + p * hgt, c


def rot_z(h):
    c, s = math.cos(h), math.sin(h)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def standing(height=1.72):
    k = height / 1.72
    J = dict(pelvis=(0, 0, 0.98), spine=(0, -0.01, 1.16), chest=(0, 0, 1.36), neck=(0, 0.01, 1.52), head=(0, 0.03, 1.63),
             sho_l=(-0.19, 0, 1.44), sho_r=(0.19, 0, 1.44), hip_l=(-0.095, 0, 0.93), hip_r=(0.095, 0, 0.93),
             hem_l=(-0.16, 0.02, 0.62), hem_r=(0.16, 0.02, 0.62), hem_b=(0, -0.08, 0.6))
    J = {n: np.array(v, float) * k for n, v in J.items()}
    for s, sx in (("l", -1), ("r", 1)):
        J[f"elb_{s}"] = J[f"sho_{s}"] + np.array([sx * 0.03, 0, -L_UPPER]) * k
        J[f"wri_{s}"] = J[f"elb_{s}"] + np.array([0, 0.03, -L_FORE]) * k
        J[f"hnd_{s}"] = J[f"wri_{s}"] + np.array([0, 0.01, -L_HAND]) * k
        J[f"kne_{s}"] = J[f"hip_{s}"] + np.array([0, 0.01, -L_THIGH]) * k
        J[f"ank_{s}"] = np.array([J[f"hip_{s}"][0], 0, 0.08 * k])
        J[f"toe_{s}"] = J[f"ank_{s}"] + np.array([0, 0.16, -0.05]) * k
    return J


class Human:
    def __init__(self, name, colors, hair="short", height=1.72, coll=None, mats=None, ink=True, bulk=None):
        """colors: dict of material objects: top, legs, shoes, skin, hair (bpy materials).
        bulk: per-part radius multipliers, e.g. {"top": 1.35} for a puffy jacket (v3: chunkier painted figures)."""
        self.name, self.height, self.hair_style = name, height, hair
        self.coll = coll or bpy.context.scene.collection
        self.objs = {}
        self.parts = {}
        for part, spec in PARTS.items():
            k = (bulk or {}).get(part, 1.0)
            self.parts[part] = dict(edges=spec["edges"], radius={j: (r[0] * k, r[1] * k) for j, r in spec["radius"].items()})
        if hair != "coat" and "coat" in colors and colors.get("coat") is None:
            pass
        for part, spec in self.parts.items():
            if part == "coat" and "coat" not in colors:
                continue
            self.objs[part] = self._skin_part(f"{name}_{part}", spec, colors[part if part != "coat" else "coat"])
        # head + hair
        hm = bpy.data.meshes.new(f"{name}_head")
        self._uv_sphere(hm, 1.0, 24, 16)
        self.head = bpy.data.objects.new(f"{name}_head", hm)
        self.head.data.materials.append(colors["skin"])
        self.coll.objects.link(self.head)
        hr = bpy.data.meshes.new(f"{name}_hair")
        self._uv_sphere(hr, 1.0, 24, 16)
        self.hair = bpy.data.objects.new(f"{name}_hair", hr)
        self.hair.data.materials.append(colors["hair"])
        self.coll.objects.link(self.hair)
        for o in (self.head, self.hair):
            for p in o.data.polygons:
                p.use_smooth = True
        self.tail = None
        if hair == "long":
            tm = bpy.data.meshes.new(f"{name}_hairtail")
            tm.from_pydata([(0, 0, 0), (0, -0.1, -0.12), (0, -0.14, -0.3)], [(0, 1), (1, 2)], [])
            self.tail = bpy.data.objects.new(f"{name}_hairtail", tm)
            self.tail.data.materials.append(colors["hair"])
            self._add_skin(self.tail, [(0.085, 0.06), (0.09, 0.05), (0.07, 0.03)])
            self.coll.objects.link(self.tail)
        self.J = standing(height)

    # -------------------------------------------------------------- building
    @staticmethod
    def _uv_sphere(me, r, seg, ring):
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=r)
        bm.to_mesh(me)
        bm.free()

    def _add_skin(self, ob, radii):
        me = ob.data
        sk = ob.modifiers.new("skin", "SKIN")
        sk.use_smooth_shade = True
        sk.branch_smoothing = 0.6
        sv = me.skin_vertices[0].data
        for i, r in enumerate(radii):
            sv[i].radius = r
        sv[0].use_root = True
        ss = ob.modifiers.new("subd", "SUBSURF")
        ss.levels = 1
        ss.render_levels = 2

    def _skin_part(self, name, spec, mat):
        verts = []
        for a, b in spec["edges"]:
            for j in (a, b):
                if j not in verts:
                    verts.append(j)
        idx = {j: i for i, j in enumerate(verts)}
        me = bpy.data.meshes.new(name)
        me.from_pydata([(0, 0, 0)] * len(verts), [(idx[a], idx[b]) for a, b in spec["edges"]], [])
        ob = bpy.data.objects.new(name, me)
        ob.data.materials.append(mat)
        self.coll.objects.link(ob)
        radii = [spec["radius"].get(j, (0.05, 0.05)) for j in verts]
        self._add_skin(ob, radii)
        # one root per connected component
        sv = me.skin_vertices[0].data
        comp = list(range(len(verts)))
        def find(i):
            while comp[i] != i:
                comp[i] = comp[comp[i]]
                i = comp[i]
            return i
        for a, b in spec["edges"]:
            comp[find(idx[a])] = find(idx[b])
        seen = set()
        for i in range(len(verts)):
            r = find(i)
            sv[i].use_root = r not in seen
            seen.add(r)
        ob["joints"] = verts
        return ob

    # -------------------------------------------------------------- posing
    def set_world(self, Jw, heading):
        """Jw: dict joint -> world xyz (numpy). heading: facing angle (radians, 0 = +Y)."""
        for part, ob in self.objs.items():
            names = ob["joints"]
            co = np.array([Jw[n] for n in names], np.float32).ravel()
            ob.data.vertices.foreach_set("co", co)
            ob.data.update()
        k = self.height / 1.72
        hd = Jw["head"]
        up = Jw["head"] - Jw["neck"]
        up = up / (np.linalg.norm(up) + 1e-9)
        R = Matrix(rot_z(heading).tolist()).to_4x4()
        tilt = Vector((0, 0, 1)).rotation_difference(Vector(up.tolist())).to_matrix().to_4x4()
        self.head.matrix_world = Matrix.Translation(Vector(hd.tolist())) @ tilt @ R @ Matrix.Diagonal((0.088 * k, 0.1 * k, 0.11 * k, 1))
        off = rot_z(heading) @ np.array([0, -0.018, 0.028]) * k
        hk = getattr(self, "hair_scale", 1.0)
        self.hair.matrix_world = Matrix.Translation(Vector((hd + off).tolist())) @ tilt @ R @ Matrix.Diagonal((0.096 * k * hk, 0.108 * k * hk, 0.1 * k, 1))
        if self.tail is not None:
            self.tail.matrix_world = Matrix.Translation(Vector((hd + rot_z(heading) @ np.array([0, -0.03, 0.02]) * k).tolist())) @ R
            self.tail.data.update()

    def all_objects(self):
        out = list(self.objs.values()) + [self.head, self.hair]
        if self.tail is not None:
            out.append(self.tail)
        return out


def to_world(Jl, base, heading):
    R = rot_z(heading)
    return {n: base + R @ v for n, v in Jl.items()}


# ---------------------------------------------------------------- activities
class Walker:
    """Planted-foot walk along a 2D path.
    path(t) -> (x, y) ground position under the pelvis at time t (frames, float); heading(t) -> facing angle.
    Feet: stance (duty ~0.62) keeps the foot fixed in world space; swing arcs between consecutive plants.
    Arc length is tabulated once over [t0, t1] so poses are cheap."""

    def __init__(self, path, heading, t0, t1, step_len=None, duty=0.62, height=1.72, ground=None, arm_swing=0.42,
                 lean=0.06, dt=0.25, fps=24):
        """step_len: metres per step, or None for speed-dependent steps (longer strides when faster)."""
        self.path, self.heading = path, heading
        self.duty, self.h, self.arm, self.lean = duty, height, arm_swing, lean
        self.ground = ground or (lambda x, y: 0.0)
        self.ts = np.arange(t0 - 200, t1 + 200, dt)
        pts = np.array([path(x) for x in self.ts], float)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        v = seg / dt * fps                                   # m/s
        k = height / 1.72
        if step_len is None:
            step = np.clip(0.42 + 0.18 * v, 0.5, 0.92) * k
        else:
            step = np.full_like(v, step_len)
        # gait phase (cycles) = integral of distance / stride, stride = 2 steps
        self.phase = np.concatenate([[0.0], np.cumsum(seg / (2 * step))])
        self.phase_inv = self.phase + np.arange(len(self.phase)) * 1e-7

    def cycles(self, t):
        return float(np.interp(t, self.ts, self.phase))

    def time_at_phase(self, c):
        return float(np.interp(c, self.phase_inv, self.ts))

    def _plant(self, ci, off, lat):
        tc = self.time_at_phase(ci + off + self.duty / 2)
        pb = np.array(self.path(tc), float)
        hc = self.heading(tc)
        q = pb + (rot_z(hc) @ np.array([lat, 0.0, 0.0]))[:2]
        return np.array([q[0], q[1], self.ground(q[0], q[1])]), hc

    def pose(self, t):
        k = self.h / 1.72
        cphase = self.cycles(t)
        ph = cphase % 1.0
        base = np.array(self.path(t), float)
        hd = self.heading(t)
        R = rot_z(hd)
        J = standing(self.h)
        bob = -0.022 * math.cos(4 * math.pi * (ph - 0.31)) * k
        sway = 0.004 * math.sin(2 * math.pi * (ph - 0.31)) * k
        upper = ("pelvis", "spine", "chest", "neck", "head", "sho_l", "sho_r", "elb_l", "elb_r", "wri_l", "wri_r", "hnd_l",
                 "hnd_r", "hip_l", "hip_r", "hem_l", "hem_r", "hem_b")
        for n in upper:
            J[n] = J[n] + np.array([-sway, 0, bob])
        for n in upper:
            z = J[n][2] - J["pelvis"][2]
            if z > 0:
                J[n][1] += z * self.lean
        gz = self.ground(base[0], base[1])
        Jw = to_world(J, np.array([base[0], base[1], gz]), hd)
        for side, off in (("l", 0.0), ("r", 0.5)):
            p = (ph - off) % 1.0
            lat = (-0.1 if side == "l" else 0.1) * k
            ci = math.floor(cphase - off)
            if p < self.duty:
                A, fwd = self._plant(ci, off, lat)
                lift, push = 0.0, max(0.0, (p - self.duty * 0.6) / (self.duty * 0.4))
            else:
                A0, h0 = self._plant(ci, off, lat)
                A1, h1 = self._plant(ci + 1, off, lat)
                u = (p - self.duty) / (1 - self.duty)
                ue = 0.5 - 0.5 * math.cos(math.pi * u)
                A = A0 * (1 - ue) + A1 * ue
                lift, push = math.sin(math.pi * u) * 0.11 * k, 0.0
                fwd = h0 * (1 - ue) + h1 * ue
            toe_dir = rot_z(fwd) @ np.array([0.0, 1.0, 0.0])
            ank = A + np.array([0, 0, 0.08 * k + lift + 0.06 * k * push])
            toe = ank + toe_dir * 0.155 * k + np.array([0, 0, -0.065 * k - 0.04 * k * push])
            kne, ank = ik2(Jw[f"hip_{side}"], ank, L_THIGH * k, L_SHIN * k, R @ np.array([0, 1.0, 0.1]))
            Jw[f"kne_{side}"], Jw[f"ank_{side}"], Jw[f"toe_{side}"] = kne, ank, toe
        # arms swing opposite to the legs: right arm forward when the left foot strikes (ph = 0)
        for side, sx, sgn in (("l", -1, -1), ("r", 1, 1)):
            a = self.arm * math.cos(2 * math.pi * ph) * sgn
            bend = 0.22 + 0.45 * max(0.0, a) / max(self.arm, 1e-3)
            ua = np.array([sx * 0.06, math.sin(a), -math.cos(a)])
            fa = np.array([sx * 0.03, math.sin(a + bend), -math.cos(a + bend)])
            el = Jw[f"sho_{side}"] + R @ (ua / np.linalg.norm(ua) * L_UPPER * k)
            wr = el + R @ (fa / np.linalg.norm(fa) * L_FORE * k)
            Jw[f"elb_{side}"], Jw[f"wri_{side}"] = el, wr
            Jw[f"hnd_{side}"] = wr + R @ (fa / np.linalg.norm(fa) * L_HAND * k)
        return Jw, hd, ph

    def waist_back(self, Jw, heading):
        """attach point of a trailing thread: the lower back"""
        return Jw["pelvis"] + rot_z(heading) @ np.array([0, -0.12, 0.04]) * (self.h / 1.72)


def _walker_attach(self, t, back=0.12, up=0.04):
    """cheap thread attach point (lower back) at time t: same pelvis as pose(), without the legs/arms/IK"""
    k = self.h / 1.72
    ph = self.cycles(t) % 1.0
    base = np.array(self.path(t), float)
    hd = self.heading(t)
    R = rot_z(hd)
    bob = -0.022 * math.cos(4 * math.pi * (ph - 0.31)) * k
    sway = 0.004 * math.sin(2 * math.pi * (ph - 0.31)) * k
    pel = np.array([-sway, 0.0, 0.98 * k + bob])
    gz = self.ground(base[0], base[1])
    return np.array([base[0], base[1], gz]) + R @ (pel + np.array([0.0, -back, up]) * k)


Walker.attach = _walker_attach
