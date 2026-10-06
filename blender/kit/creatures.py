"""Creatures with physically-motivated motion: koi (travelling body wave), manta ray (travelling wave
along the wings), sea turtle (flipper strokes), birds (flap cycle). Meshes are built procedurally;
deformations are written per drawing."""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Matrix, Vector
from . import geo


class Koi:
    """Fish along local +Y (head at +Y). length in metres."""

    def __init__(self, name, mat, mat_fin, length=1.3, coll=None, seed=0):
        self.L = length
        n_u, n_v = 26, 12
        verts, faces = [], []
        us = np.linspace(0, 1, n_u)              # 0 head, 1 tail root
        for u in us:
            w = 0.11 * math.sin(math.pi * min(1.0, u * 0.95 + 0.03)) ** 0.7 * (1 - 0.55 * u)
            hgt = w * 0.75
            y = (0.5 - u) * length * 0.82
            for j in range(n_v):
                th = 2 * math.pi * j / n_v
                verts.append((w * length * math.cos(th), y, hgt * length * math.sin(th)))
        for i in range(n_u - 1):
            for j in range(n_v):
                a, b = i * n_v + j, i * n_v + (j + 1) % n_v
                c, d = (i + 1) * n_v + (j + 1) % n_v, (i + 1) * n_v + j
                faces.append((a, b, c, d))
        body = geo.mesh_from_arrays(name, verts, faces, coll, True, mat)
        # tail fin + pectoral fins (flat, double-sided)
        ty = (0.5 - 1.0) * length * 0.82
        tail = [(0, ty + 0.02 * length, 0), (0.12 * length, ty - 0.2 * length, 0), (0.05 * length, ty - 0.15 * length, 0),
                (0, ty - 0.1 * length, 0), (-0.05 * length, ty - 0.15 * length, 0), (-0.12 * length, ty - 0.2 * length, 0)]
        pecs = []
        for s in (-1, 1):
            py = 0.2 * length
            pecs += [(s * 0.06 * length, py, 0), (s * 0.17 * length, py - 0.06 * length, 0), (s * 0.12 * length, py - 0.13 * length, 0),
                     (s * 0.05 * length, py - 0.07 * length, 0)]
        fv = tail + pecs
        ff = [(0, 1, 2, 3), (0, 3, 4, 5), (6, 7, 8, 9), (10, 11, 12, 13)]
        self.fins = geo.mesh_from_arrays(name + "_fins", fv, ff, coll, False, mat_fin)
        self.fins.parent = body
        self.body = body
        self.rest = np.array(verts, np.float32)
        self.rest_f = np.array(fv, np.float32)
        self.seed = seed

    def pose(self, t, amp=0.07, waves=1.1, freq=0.035):
        """travelling body wave: lateral offset grows toward the tail"""
        L = self.L
        def wave(P):
            u = np.clip(0.5 - P[:, 1] / (L * 0.82), 0, 1.25)
            a = amp * L * (0.15 + u ** 1.6)
            return P[:, 0] + a * np.sin(2 * math.pi * (waves * u - freq * t) + self.seed)
        P = self.rest.copy()
        P[:, 0] = wave(P)
        self.body.data.vertices.foreach_set("co", P.ravel())
        self.body.data.update()
        F = self.rest_f.copy()
        F[:, 0] = wave(F)
        self.fins.data.vertices.foreach_set("co", F.ravel())
        self.fins.data.update()


class Manta:
    """Manta ray along local +Y. Wings undulate with a travelling wave from the leading to the trailing edge."""

    def __init__(self, name, mat, mat_belly=None, span=4.0, coll=None):
        S = span / 2
        nu, nv = 41, 14
        verts, faces = [], []
        for i in range(nu):
            u = -1 + 2 * i / (nu - 1)
            au = abs(u)
            # planform: chord centre line swept back toward pointed tips, chord shrinking to the tip
            centre = 0.12 * S - 0.36 * S * au ** 1.8
            half = 0.42 * S * max(0.0, 1 - au ** 1.5) ** 0.7 + 0.008 * S
            lead = centre + half                                              # leading edge (front, +y)
            trail = centre - half * (0.75 + 0.25 * au)                        # trailing edge (back)
            for j in range(nv):
                v = j / (nv - 1)
                y = lead * (1 - v) + trail * v
                th = 0.12 * S * (1 - au) ** 2 * math.sin(math.pi * v)       # body thickness at the centre
                verts.append((u * S, y, th))
        for i in range(nu - 1):
            for j in range(nv - 1):
                a, b, c, d = i * nv + j, (i + 1) * nv + j, (i + 1) * nv + j + 1, i * nv + j + 1
                faces.append((a, b, c, d))
        self.obj = geo.mesh_from_arrays(name, verts, faces, coll, True, mat)
        self.rest = np.array(verts, np.float32)
        self.S = S
        # cephalic fins and tail
        # cephalic fins: two rolled, forward-curling lobes either side of the mouth; long thin tail
        fins, ff = [], []
        for s in (-1, 1):
            i0 = len(fins)
            for k in range(6):
                t = k / 5
                ang = 0.6 * math.pi * t
                cx = s * (0.12 + 0.05 * math.sin(ang)) * S
                cy = (0.5 + 0.2 * t) * S
                rr = 0.035 * S * (1 - 0.5 * t)
                fins += [(cx - rr, cy, 0.03 * S * math.cos(ang)), (cx + rr, cy, 0.03 * S * math.cos(ang) + 0.01 * S)]
            for k in range(5):
                a_ = i0 + 2 * k
                ff.append((a_, a_ + 1, a_ + 3, a_ + 2))
        i0 = len(fins)
        # the tail root sits inside the body (trailing edge at the centre is about -0.19 S), so the silhouette is one piece
        fins += [(-0.016 * S, -0.12 * S, 0.0), (0.016 * S, -0.12 * S, 0.0), (0.004 * S, -1.35 * S, 0.0), (-0.004 * S, -1.35 * S, 0.0)]
        ff.append((i0, i0 + 1, i0 + 2, i0 + 3))
        self.fins = geo.mesh_from_arrays(name + "_fins", fins, ff, coll, False, mat)
        self.fins.parent = self.obj

    def pose(self, t, amp=0.22, period=70.0, wavelength=1.6):
        P = self.rest.copy()
        u = np.abs(P[:, 0]) / self.S
        ph = 2 * math.pi * (t / period) - 2 * math.pi * (P[:, 1] / (self.S * wavelength))
        P[:, 2] += amp * self.S * u ** 1.5 * np.sin(ph)
        # flapping wings foreshorten slightly from above
        P[:, 0] *= 1 - 0.06 * u ** 2 * (1 - np.cos(ph)) / 2
        self.obj.data.vertices.foreach_set("co", P.ravel())
        self.obj.data.update()


class Turtle:
    """Sea turtle: domed shell, head, four flippers (front flippers stroke, rear flippers steer)."""

    def __init__(self, name, mat_shell, mat_skin, length=0.9, coll=None):
        L = length
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)
        bmesh.ops.scale(bm, vec=(0.36 * L, 0.48 * L, 0.14 * L), verts=bm.verts)
        self.shell = geo.bm_to_object(bm, name, mat_shell, coll)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0)
        bmesh.ops.scale(bm, vec=(0.1 * L, 0.13 * L, 0.07 * L), verts=bm.verts)
        bmesh.ops.translate(bm, vec=(0, 0.55 * L, 0.0), verts=bm.verts)
        self.head = geo.bm_to_object(bm, name + "_head", mat_skin, coll)
        self.head.parent = self.shell
        self.flips = []
        for fx, fy, sx, sy in ((0.3, 0.25, 0.34, 0.1), (-0.3, 0.25, 0.34, 0.1), (0.24, -0.38, 0.16, 0.08), (-0.24, -0.38, 0.16, 0.08)):
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=6, radius=1.0)
            bmesh.ops.scale(bm, vec=(sx * L, sy * L, 0.025 * L), verts=bm.verts)
            bmesh.ops.translate(bm, vec=(math.copysign(sx * L * 0.9, fx), 0, 0), verts=bm.verts)
            o = geo.bm_to_object(bm, f"{name}_flip", mat_skin, coll)
            o.parent = self.shell
            o.location = (fx * L, fy * L, 0)
            self.flips.append((o, fx))

    def pose(self, t, period=48.0):
        ph = 2 * math.pi * t / period
        for i, (o, fx) in enumerate(self.flips):
            s = math.copysign(1, fx)
            if i < 2:
                o.rotation_euler = (0, s * 0.35 * math.sin(ph), -s * (0.5 * math.sin(ph) + 0.15))
            else:
                o.rotation_euler = (0, 0, s * 0.25 * math.sin(ph + 1.2) - s * 0.6)


class Crane:
    """White crane seen from above: body, black neck and head, trailing legs, two-segment wings with
    black fingered primaries, short tail. Flap: inner wing leads, outer wing lags."""

    def __init__(self, name, m_white, m_black, m_leg, span=2.2, coll=None):
        k = span / 2.2
        self.k = k
        def ell(nm, sc, loc, mat):
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.0)
            bmesh.ops.scale(bm, vec=sc, verts=bm.verts)
            bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
            return geo.bm_to_object(bm, nm, mat, coll)
        self.body = ell(name, (0.12 * k, 0.42 * k, 0.11 * k), (0, 0, 0), m_white)
        neck_pts = [(0, 0.36 * k, 0.03 * k), (0, 0.6 * k, 0.07 * k), (0, 0.85 * k, 0.06 * k)]
        bm = bmesh.new()
        for (a, b) in zip(neck_pts[:-1], neck_pts[1:]):
            va, vb = Vector(a), Vector(b)
            mid = (va + vb) / 2
            L = (vb - va).length
            cone = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.035 * k, radius2=0.028 * k, depth=L)
            rot = Vector((0, 0, 1)).rotation_difference(vb - va).to_matrix()
            bmesh.ops.rotate(bm, verts=cone["verts"], cent=(0, 0, 0), matrix=rot)
            bmesh.ops.translate(bm, vec=mid, verts=cone["verts"])
        self.neck = geo.bm_to_object(bm, name + "_neck", m_black, coll)
        self.head = ell(name + "_head", (0.045 * k, 0.07 * k, 0.04 * k), (0, 0.9 * k, 0.06 * k), m_black)
        self.beak = ell(name + "_beak", (0.012 * k, 0.07 * k, 0.012 * k), (0, 1.0 * k, 0.055 * k), m_leg)
        self.tail = ell(name + "_tail", (0.09 * k, 0.14 * k, 0.02 * k), (0, -0.46 * k, 0.0), m_white)
        legs = []
        for s in (-1, 1):
            legs.append(ell(name + f"_leg{s}", (0.012 * k, 0.36 * k, 0.012 * k), (s * 0.04 * k, -0.72 * k, -0.02 * k), m_leg))
        for o in [self.neck, self.head, self.beak, self.tail] + legs:
            o.parent = self.body
        self.wings = []
        for s in (-1, 1):
            root = bpy.data.objects.new(f"{name}_wroot{s}", None)
            coll.objects.link(root)
            root.parent = self.body
            root.location = (s * 0.08 * k, 0.1 * k, 0.04 * k)
            inner = self._poly(f"{name}_win{s}", [(0, 0.17, 0), (0.55, 0.16, 0), (0.55, -0.2, 0), (0, -0.24, 0)], s, k, m_white, coll)
            inner.parent = root
            hroot = bpy.data.objects.new(f"{name}_hroot{s}", None)
            coll.objects.link(hroot)
            hroot.parent = root
            hroot.location = (s * 0.55 * k, 0, 0)
            hand = self._poly(f"{name}_whd{s}", [(0, 0.16, 0), (0.32, 0.12, 0), (0.36, -0.12, 0), (0, -0.2, 0)], s, k, m_white, coll)
            hand.parent = hroot
            feathers = []
            for i in range(5):
                y0 = 0.1 - i * 0.065
                fe = self._poly(f"{name}_pf{s}_{i}", [(0.3, y0 + 0.025, 0), (0.62 - i * 0.03, y0 + 0.01 - i * 0.02, 0),
                                                      (0.6 - i * 0.03, y0 - 0.03 - i * 0.02, 0), (0.28, y0 - 0.03, 0)], s, k, m_black, coll)
                fe.parent = hroot
                feathers.append(fe)
            self.wings.append((root, hroot, s))

    @staticmethod
    def _poly(nm, pts, s, k, mat, coll):
        bm = bmesh.new()
        vs = [bm.verts.new((s * x * k, y * k, z * k)) for x, y, z in pts]
        bm.faces.new(vs if s > 0 else vs[::-1])
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.012 * k)
        return geo.bm_to_object(bm, nm, mat, coll, smooth=False)

    def pose(self, t, period=26.0, amp=0.55, phase=0.0):
        ph = 2 * math.pi * t / period + phase
        a1 = amp * math.sin(ph) + 0.08
        a2 = amp * 1.25 * math.sin(ph - 0.7) + 0.05
        for root, hroot, s in self.wings:
            root.rotation_euler = (0, -s * a1, 0)
            hroot.rotation_euler = (0, -s * (a2 - a1) * 0.8, 0.12 * s * math.sin(ph))
