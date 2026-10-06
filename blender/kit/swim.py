"""v5 swimming bodies: a reusable travelling-wave hinge chain and two rigs built on it.

chain_angles(phase, n, amp, delay, bias): joint angles of an n-hinge chain with a wave travelling from root to tip
(phase in cycles, delay = cycles per hinge) -- used for the manta's wing ribs, the turtle's flipper joints (and the
same idea drives the scene 12 gulls' 3-segment wings).

MantaRig  : the approved manta planform (same mesh layout, colours and size) made deformable: 6 wing ribs per side with
            a 0.12-cycle delay (span foreshortening, tip lag, trailing-edge ripple, tilt shading attribute "tilt"),
            banking, head-leads body bend, curling cephalic fins, an 8-segment tapering whip tail, glide windows.
TurtleRig : rigid domed shell, head + neck (bob), two 3-joint front flippers (power 45 % / feathered recovery 55 %),
            two hind paddles (+-12 deg, half a cycle out of phase), short tail; draw order by height.
All poses are pure functions of time (frames) and the heading history, so they are deterministic on twos."""
import math
import numpy as np
import bpy
from . import geo


def chain_angles(phase, n, amp, delay, bias=0.0):
    """angles (rad) of n hinges: amp * sin(2 pi (phase - delay * i)) + bias"""
    i = np.arange(n)
    return amp * np.sin(2 * np.pi * (phase - delay * i)) + bias


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def poly_mesh(name, V, F, coll, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], [list(q) for q in F])
    me.update()
    ob = bpy.data.objects.new(name, me)
    me.materials.append(mat)
    coll.objects.link(ob)
    return ob


def set_verts(ob, V):
    ob.data.vertices.foreach_set("co", np.asarray(V, np.float32).ravel())
    ob.data.update()


# ---------------------------------------------------------------- manta
class MantaRig:
    FREQ = 0.45                     # Hz: one beat = 2.2 s = 26.7 drawings on twos

    def __init__(self, name, mat, span=4.0, coll=None, ppm=90.0, glides=()):
        S = span / 2
        self.S, self.ppm = S, ppm
        self.glides = list(glides)                    # (start_frame, frames) windows of gliding
        nu, nv = 41, 14
        V, F, UV = [], [], []
        for i in range(nu):
            u = -1 + 2 * i / (nu - 1)
            au = abs(u)
            centre = 0.12 * S - 0.36 * S * au ** 1.8
            half = 0.42 * S * max(0.0, 1 - au ** 1.5) ** 0.7 + 0.008 * S
            lead = centre + half
            trail = centre - half * (0.75 + 0.25 * au)
            for j in range(nv):
                v = j / (nv - 1)
                y = lead * (1 - v) + trail * v
                th = 0.12 * S * (1 - au) ** 2 * math.sin(math.pi * v)
                V.append((u * S, y, th))
                UV.append((u, v))
        for i in range(nu - 1):
            for j in range(nv - 1):
                a, b, c, d = i * nv + j, (i + 1) * nv + j, (i + 1) * nv + j + 1, i * nv + j + 1
                F.append((a, b, c, d))
        self.rest = np.array(V, float)
        self.uv = np.array(UV, float)
        self.obj = poly_mesh(name, self.rest, F, coll, mat)
        self.obj.data.polygons.foreach_set("use_smooth", np.ones(len(F), bool))
        self.tilt = self.obj.data.attributes.new("tilt", "FLOAT", "POINT")
        # cephalic fins (rest geometry from the approved model), re-posed per drawing (curl in / out)
        fins, ff = [], []
        self.fin_root = []
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
            self.fin_root.append((s, np.array([s * 0.12 * S, 0.5 * S, 0.0])))
        self.fin_rest = np.array(fins, float)
        self.fins = poly_mesh(name + "_fins", self.fin_rest, ff, coll, mat)
        self.fins.parent = self.obj
        # whip tail: 8 segments (9 joints), ribbon tapering 5 px -> 1.5 px
        self.NT = 8
        self.tail_len = 1.1 * S
        tv = np.zeros((2 * (self.NT + 1), 3))
        tf = [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(self.NT)]
        self.tail = poly_mesh(name + "_tail", tv, tf, coll, mat)
        self.tail.parent = self.obj
        self.log = {}

    def amp_env(self, t):
        """1 while beating, 0 while gliding (0.3 s ramp down, 0.5 s ramp up)"""
        a = 1.0
        for g0, gl in self.glides:
            down = smooth((t - g0) / 18.0)                 # 0.75 s ramps keep the span change per drawing small
            up = smooth((t - (g0 + gl)) / 18.0)
            a = min(a, 1.0 - down + up)
        return float(np.clip(a, 0.0, 1.0))

    def pose(self, t, heading_fn, turn_rate):
        """t: frame (drawing time); heading_fn(t) -> world heading (rad) of the trajectory; turn_rate: rad/s (+ = left).
        Returns the object yaw to apply (the body lags the head by 0.17 s)."""
        S = self.S
        ph = self.FREQ * t / 24.0
        A = self.amp_env(t)
        u, v = self.uv[:, 0], self.uv[:, 1]
        a = np.abs(u)
        side = np.sign(u)
        # wing ribs: 6 hinges between |u| = 0.25 (wing root) and the tip, wave delay 0.12 cycle per rib
        R0, NR = 0.25, 6
        dr = (1.0 - R0) / NR
        beta = chain_angles(ph, NR, 0.2 * A, 0.12, bias=-0.06 * A + 0.045 * (1 - A))        # glide: held slightly up
        bank = float(np.clip(turn_rate * 0.4, -0.12, 0.12))
        cols = np.linspace(R0, 1.0, 60)
        th_cols = np.zeros_like(cols)
        for i in range(NR):
            th_cols += beta[i] * np.clip((cols - (R0 + i * dr)) / dr, 0.0, 1.0)
        x_cols = R0 + np.concatenate([[0.0], np.cumsum(np.cos(th_cols[:-1]) * np.diff(cols))])
        z_cols = np.concatenate([[0.0], np.cumsum(np.sin(th_cols[:-1]) * np.diff(cols))])
        P = self.rest.copy()
        wing = a > R0
        th_v = np.interp(a, cols, th_cols) - side * bank * smooth((a - R0) / 0.75)      # inside wing lowered
        # recompute the cumulative projection with the bank added (bank is a uniform rotation about the root)
        xa = np.interp(a, cols, x_cols)
        za = np.interp(a, cols, z_cols)
        cb, sb = np.cos(-side * bank * smooth((a - R0) / 0.75)), np.sin(-side * bank * smooth((a - R0) / 0.75))
        rx, rz = (xa - R0), za
        xb = R0 + rx * cb - rz * sb
        zb = rx * sb + rz * cb
        P[wing, 0] = side[wing] * xb[wing] * S
        # the planform foreshortens with the full wing angles, but the wing tip may rise at most ~8 cm (soft cap) so it
        # never breaks the water surface (the manta swims 12 cm down); downward travel is halved
        zd = zb * S
        P[wing, 2] += np.where(zd > 0, 0.08 * np.tanh(zd / 0.08), 0.5 * zd)[wing]
        # tip trails the root by 8-14 px, breathing with the beat; trailing-edge ripple 5-8 px travelling to the tip
        lag_px = 8.0 + 6.0 * (0.5 + 0.5 * math.sin(2 * math.pi * (ph - 0.72))) * A + 2.0 * (1 - A)
        P[:, 1] -= (lag_px / self.ppm) * smooth((a - R0) / 0.75) ** 1.5
        rip = np.clip((v - 0.55) / 0.45, 0.0, 1.0) ** 2 * smooth((a - 0.15) / 0.5)
        P[:, 1] += (6.5 / self.ppm) * rip * np.sin(2 * np.pi * (2 * ph - 2.2 * a)) * (0.3 + 0.7 * A)
        # body: yaw sway 2.5 deg at the beat; the head leads turns (head now, body 0.17 s later)
        sway = math.radians(2.5) * math.sin(2 * math.pi * ph) * A
        h_now, h_body = heading_fn(t), heading_fn(t - 4.0)
        lead = (h_now - h_body + math.pi) % (2 * math.pi) - math.pi
        yfac = smooth((P[:, 1] / S + 0.1) / 0.6)                 # front half turns with the head
        ang = sway * (P[:, 1] / S) + lead * yfac
        c_, s_ = np.cos(ang), np.sin(ang)
        x0, y0 = P[:, 0].copy(), P[:, 1].copy()
        P[:, 0], P[:, 1] = x0 * c_ - y0 * s_, x0 * s_ + y0 * c_
        set_verts(self.obj, P)
        # tilt shading: wing up -> up to 8 % lighter, down -> up to 6 % darker
        tv_ = np.where(th_v > 0, 0.08 * np.clip(th_v / 0.45, 0, 1), 0.06 * np.clip(th_v / 0.45, -1, 0)) * wing
        self.tilt.data.foreach_set("value", tv_.astype(np.float32))
        # cephalic fins curl in and out (0.2 Hz, +-10 deg) about their roots
        curl = math.radians(10.0) * math.sin(2 * math.pi * 0.2 * t / 24.0)
        Fv = self.fin_rest.copy()
        for k, (s, root) in enumerate(self.fin_root):
            idx = slice(12 * k, 12 * (k + 1))
            q = Fv[idx] - root
            ca, sa = math.cos(-s * curl), math.sin(-s * curl)
            Fv[idx, 0] = root[0] + q[:, 0] * ca - q[:, 1] * sa
            Fv[idx, 1] = root[1] + q[:, 0] * sa + q[:, 1] * ca
            hl = (h_now - h_body + math.pi) % (2 * math.pi) - math.pi
            ch, sh = math.cos(hl), math.sin(hl)
            x1, y1 = Fv[idx, 0].copy(), Fv[idx, 1].copy()
            Fv[idx, 0], Fv[idx, 1] = x1 * ch - y1 * sh, x1 * sh + y1 * ch
        set_verts(self.fins, Fv)
        # whip tail: each segment trails the previous (turn history + a travelling sway), tip lag 12-18 px, sway +-8 px
        J = [np.array([0.0, -0.12 * S])]
        seg = self.tail_len / self.NT
        ang_t = 0.0
        tail_sway = math.radians(6.0) * math.sin(2 * math.pi * (ph - 0.25))
        for k in range(1, self.NT + 1):
            hk = heading_fn(t - 4.0 - 2.5 * k)
            follow = (hk - h_body + math.pi) % (2 * math.pi) - math.pi
            ang_t = 0.55 * ang_t + 0.45 * (follow + tail_sway * (k / self.NT) * 1.6 * math.cos(0.45 * k) + math.radians(1.2))
            d = np.array([-math.sin(ang_t), -math.cos(ang_t)])
            J.append(J[-1] + d * seg)
        J = np.array(J)
        Tv = np.zeros((2 * (self.NT + 1), 3))
        for k in range(self.NT + 1):
            w = (5.0 - 3.5 * k / self.NT) / self.ppm / 2
            nxt = J[min(k + 1, self.NT)] - J[max(k - 1, 0)]
            nrm = np.array([-nxt[1], nxt[0]]) / (np.linalg.norm(nxt) + 1e-9)
            Tv[2 * k, :2], Tv[2 * k + 1, :2] = J[k] - nrm * w, J[k] + nrm * w
            Tv[2 * k:2 * k + 2, 2] = 0.004
        set_verts(self.tail, Tv)
        # gate log: tip dihedral, projected span, tail-tip lateral offset from the spine line (px)
        span = (P[:, 0].max() - P[:, 0].min()) * self.ppm
        self.log[int(t)] = dict(tip_deg=round(math.degrees(float(th_cols[-1])), 3), span_px=round(float(span), 2),
                                tail_lat_px=round(float(J[-1][0]) * self.ppm, 2), amp=round(A, 3), bank=round(bank, 4))
        return h_body


# ---------------------------------------------------------------- turtle
class TurtleRig:
    PERIOD = 2.8 * 24.0             # frames per front-flipper stroke (67.2 frames = 33.6 drawings)

    def __init__(self, name, mat_shell, mat_skin, length=0.95, coll=None, ppm=90.0, phase0=0.0):
        import bmesh
        L = length
        self.L, self.ppm, self.phase0 = L, ppm, phase0
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1.0)
        bmesh.ops.scale(bm, vec=(0.36 * L, 0.48 * L, 0.14 * L), verts=bm.verts)
        self.shell = geo.bm_to_object(bm, name, mat_shell, coll)
        # head + neck, front flippers, hind paddles, tail: one skin mesh re-posed each drawing, parented to the shell
        self.parts = poly_mesh(name + "_skin", np.zeros((4, 3)), [(0, 1, 2, 3)], coll, mat_skin)
        self.parts.parent = self.shell
        self.log = {}

    def _paddle(self, root, angles, lengths, widths, z):
        """a flat jointed paddle: joint chain from root with absolute angles (rad, 0 = +x side direction, + = forward);
        returns outline vertices (left edge then right edge) and the joint list"""
        J = [np.array(root[:2], float)]
        for a, l in zip(angles, lengths):
            J.append(J[-1] + l * np.array([math.cos(a), math.sin(a)]))
        J = np.array(J)
        Lft, Rgt = [], []
        for k in range(len(J)):
            dvec = J[min(k + 1, len(J) - 1)] - J[max(k - 1, 0)]
            n = np.array([-dvec[1], dvec[0]]) / (np.linalg.norm(dvec) + 1e-9)
            w = widths[k] / 2
            Lft.append(np.r_[J[k] + n * w, z])
            Rgt.append(np.r_[J[k] - n * w, z])
        return Lft, Rgt, J

    def pose(self, t, turn_rate):
        """t: frame; turn_rate rad/s (+ = left turn). Returns (shell_yaw_offset, along_track_offset_m)."""
        L = self.L
        cyc = (t / self.PERIOD + self.phase0) % 1.0
        # front stroke angle: power 45 % (forward +5 deg -> swept back -70 deg), recovery 55 % (back to +5, feathered)
        if cyc < 0.45:
            u = smooth(cyc / 0.45)
            sweep = math.radians(5.0) + (math.radians(-70.0) - math.radians(5.0)) * u
            feather = 1.0
        else:
            u = smooth((cyc - 0.45) / 0.55)
            sweep = math.radians(-70.0) + (math.radians(5.0) - math.radians(-70.0)) * u
            feather = 0.4 + 0.6 * (1 - math.sin(math.pi * u)) ** 3
        outer = float(np.clip(turn_rate * 1.5, -1, 1))       # + = turning left: the right flipper strokes harder
        V, F = [], []

        def add_strip(Lft, Rgt):
            i0 = len(V)
            n = len(Lft)
            V.extend(Lft)
            V.extend(Rgt)
            for k in range(n - 1):
                F.append((i0 + k, i0 + k + 1, i0 + n + k + 1, i0 + n + k))
        joint_log = {}
        for s in (-1, 1):
            amp = 1.0 + (0.2 if s * outer > 0 else -0.3) * abs(outer)
            sw = math.radians(5.0) + (sweep - math.radians(5.0)) * amp
            cyc_s = (cyc + (0.05 if s > 0 else 0.0)) % 1.0       # slight asymmetry between the two sides
            elbow = -math.radians(18.0) * math.sin(2 * math.pi * cyc_s)
            tipb = -math.radians(14.0) * math.sin(2 * math.pi * (cyc_s - 0.1))
            base = 0.0 if s > 0 else math.pi
            a0 = base + s * sw
            angs = [a0, a0 + s * elbow, a0 + s * (elbow + tipb)]
            W = np.array([0.16, 0.15, 0.11, 0.03]) * L
            W[:3] *= feather
            Lf, Rg, J = self._paddle((s * 0.3 * L, 0.24 * L), angs, [0.16 * L, 0.16 * L, 0.12 * L], W, -0.03)
            add_strip(Rg, Lf)                                     # wound so the normals face up
            joint_log[s] = math.degrees(sw)
            # hind paddles: +-12 deg, half a cycle out of phase
            ha = (math.pi if s < 0 else 0.0) + s * (-0.6 + math.radians(12.0) * math.sin(2 * math.pi * (cyc + 0.5)))
            Lf, Rg, _ = self._paddle((s * 0.24 * L, -0.36 * L), [ha, ha - s * 0.2], [0.09 * L, 0.07 * L],
                                     np.array([0.1, 0.085, 0.02]) * L, -0.03)
            add_strip(Rg, Lf)
        # neck + head over the shell edge, bobbing 4 px forward/back lagged 0.15 cycle
        bob = (4.0 / self.ppm) * math.sin(2 * math.pi * (cyc - 0.15))
        hy = 0.5 * L + bob
        Lh = [np.array([-0.06 * L, 0.38 * L, 0.03]), np.array([-0.08 * L, hy, 0.04]), np.array([-0.05 * L, hy + 0.12 * L, 0.04]),
              np.array([0.0, hy + 0.17 * L, 0.04])]
        Rh = [np.array([0.06 * L, 0.38 * L, 0.03]), np.array([0.08 * L, hy, 0.04]), np.array([0.05 * L, hy + 0.12 * L, 0.04]),
              np.array([0.0, hy + 0.17 * L, 0.04])]
        add_strip(Rh, Lh)
        # short tail
        add_strip([np.array([-0.03 * L, -0.42 * L, -0.02]), np.array([0.0, -0.55 * L, -0.02])],
                  [np.array([0.03 * L, -0.42 * L, -0.02]), np.array([0.0, -0.55 * L, -0.02])])
        me = self.parts.data
        if len(me.vertices) != len(V):
            me.clear_geometry()
            me.from_pydata([tuple(map(float, q)) for q in V], [], [list(q) for q in F])
        else:
            set_verts(self.parts, V)
        me.update()
        yaw = math.radians(3.0) * math.sin(2 * math.pi * cyc)
        # forward speed pulses: peak at the end of the power stroke, down to 55 % before the next (mean unchanged)
        along_amp = 0.45 / (2 * math.pi / self.PERIOD)            # frames x (fraction of the mean speed per frame)
        along = along_amp * math.sin(2 * math.pi * (cyc - 0.45 + 0.25))
        self.log[int(t)] = dict(front_deg=round(joint_log[1], 3), front_deg_l=round(joint_log[-1], 3), feather=round(feather, 3),
                                cyc=round(cyc, 4))
        return yaw, along
