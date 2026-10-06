

class Runner:
    """v5: planted-foot run along a 2D path (top-down readable): per stride cycle (2 steps) contact-L, stance, toe-off,
    flight, contact-R, stance, toe-off, flight. Stance feet are fixed in world space (no slip); the body rises in flight
    (small lift so the shadow detaches a few px) and is drawn slightly larger; torso leans forward; bent arms pump along
    the path; shoulders counter-rotate; the body centre never moves sideways.
    run(t) in [0, 1] blends to an ordinary walk (duty 0.62, no flight, walking arms) for slowing down.
    ppm: ground px per metre (for the px-specified stride rule: stride = clamp(v / 3 steps/s, 46, 60) px)."""

    def __init__(self, path, heading, t0, t1, height=1.72, ground=None, ppm=130.0, run=None, foot_lat=0.064, toe_len=0.025,
                 lean_run=0.2, lean_walk=0.06, arm_in=0.12, dt=0.25, fps=24):
        self.path, self.heading, self.h, self.ppm = path, heading, height, ppm
        self.ground = ground or (lambda x, y: 0.0)
        self.run = run or (lambda t: 1.0)
        self.foot_lat, self.toe_len, self.lean_run, self.lean_walk, self.arm_in = foot_lat, toe_len, lean_run, lean_walk, arm_in
        k = height / 1.72
        self.ts = np.arange(t0 - 200, t1 + 200, dt)
        pts = np.array([path(x) for x in self.ts], float)
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        v = np.r_[seg, seg[-1]] / dt * fps                         # m/s
        r = np.array([self.run(x) for x in self.ts])
        run_step = np.clip(v * ppm / 3.0, 46.0, 60.0) / ppm        # metres per step while running
        walk_step = np.clip(0.42 + 0.18 * v, 0.5, 0.92) * k
        self.step = walk_step * (1 - r) + run_step * r
        self.phase = np.concatenate([[0.0], np.cumsum(seg / (2 * self.step[:-1]))])
        self.phase_inv = self.phase + np.arange(len(self.phase)) * 1e-7
        self.speed = v

    def cycles(self, t):
        return float(np.interp(t, self.ts, self.phase))

    def time_at_phase(self, c):
        return float(np.interp(c, self.phase_inv, self.ts))

    def duty(self, t):
        return 0.62 - 0.245 * self.run(t)                          # run: stance 3/8 of the cycle per foot -> 2 flights

    def _plant(self, ci, off, lat):
        t_start = self.time_at_phase(ci + off)
        tc = self.time_at_phase(ci + off + self.duty(t_start) / 2)
        pb = np.array(self.path(tc), float)
        hc = self.heading(tc)
        q = pb + (rot_z(hc) @ np.array([lat, 0.0, 0.0]))[:2]
        return np.array([q[0], q[1], self.ground(q[0], q[1])]), hc, t_start

    def _bob(self, ph, r, du, k):
        walk = -0.022 * math.cos(4 * math.pi * (ph - 0.31)) * k
        # run: highest in the middle of each flight (half-cycle offset du + (0.5 - du) / 2), lowest at mid-stance
        run = 0.006 * math.cos(4 * math.pi * (ph - (du + (0.5 - du) / 2))) * k
        return walk * (1 - r) + run * r

    def flight(self, t):
        """0..1 bump while both feet are off the ground (0 when walking)"""
        r = self.run(t)
        ph = self.cycles(t) % 1.0
        du = self.duty(t)
        out = 0.0
        w = 0.5 - du
        if w > 0:
            for off in (0.0, 0.5):
                p = (ph - off - du) % 1.0                          # time since that foot left the ground
                if p < w:
                    out = max(out, math.sin(math.pi * p / w))
        return out * r

    def pose(self, t):
        k = self.h / 1.72
        cphase = self.cycles(t)
        ph = cphase % 1.0
        r = self.run(t)
        du = self.duty(t)
        base = np.array(self.path(t), float)
        hd = self.heading(t)
        R = rot_z(hd)
        J = standing(self.h)
        fl = self.flight(t)
        bob = self._bob(ph, r, du, k)
        lean = self.lean_walk * (1 - r) + self.lean_run * r
        upper = ("pelvis", "spine", "chest", "neck", "head", "sho_l", "sho_r", "elb_l", "elb_r", "wri_l", "wri_r", "hnd_l",
                 "hnd_r", "hip_l", "hip_r", "hem_l", "hem_r", "hem_b")
        for n in upper:
            J[n] = J[n] + np.array([0.0, 0.0, bob])
        for n in upper:
            z = J[n][2] - J["pelvis"][2]
            if z > 0:
                J[n][1] += z * math.sin(lean)
        # flight: the figure is drawn up to 4 % larger (about the pelvis)
        s = 1.0 + 0.04 * fl
        for n in J:
            if n != "pelvis":
                J[n] = J["pelvis"] + (J[n] - J["pelvis"]) * s
        gz = self.ground(base[0], base[1])
        Jw = to_world(J, np.array([base[0], base[1], gz]), hd)
        for side, off in (("l", 0.0), ("r", 0.5)):
            p = (ph - off) % 1.0
            lat = (-self.foot_lat if side == "l" else self.foot_lat) * k
            ci = math.floor(cphase - off)
            if p < du:
                A, fwd, _ = self._plant(ci, off, lat)
                lift = 0.0
                push = max(0.0, (p - du * 0.6) / (du * 0.4))
                pitch = 0.0
            else:
                A0, h0, _ = self._plant(ci, off, lat)
                A1, h1, _ = self._plant(ci + 1, off, lat)
                u = (p - du) / (1 - du)
                ue = 0.5 - 0.5 * math.cos(math.pi * u)
                A = A0 * (1 - ue) + A1 * ue
                # walk: low arc; run: heel kicks up behind, then the foot reaches forward
                lift = (0.11 * (1 - r) + 0.24 * r) * math.sin(math.pi * u) ** (1.0 + 0.6 * r) * k
                push, pitch = 0.0, (0.5 + 0.5 * r) * math.sin(math.pi * u)
                fwd = h0 * (1 - ue) + h1 * ue
            toe_dir = rot_z(fwd) @ np.array([0.0, 1.0, 0.0])
            ank = A + np.array([0, 0, 0.08 * k + lift + 0.05 * k * push])
            toe = ank + toe_dir * self.toe_len * k * math.cos(pitch) + np.array([0, 0, -0.06 * k - self.toe_len * k * math.sin(pitch)])
            kne, ank = ik2(Jw[f"hip_{side}"], ank, L_THIGH * k * s, L_SHIN * k * s, R @ np.array([0, 1.0, 0.15]))
            Jw[f"kne_{side}"], Jw[f"ank_{side}"], Jw[f"toe_{side}"] = kne, ank, toe
        # shoulders counter-rotate against the hips (6 degrees running, 3 walking)
        Rs = rot_z(math.radians(3.0 + 3.0 * r) * math.cos(2 * math.pi * ph))
        for side in ("l", "r"):
            Jw[f"sho_{side}"] = Jw["chest"] + Rs @ (Jw[f"sho_{side}"] - Jw["chest"])
        # arms: running = elbows bent ~90 deg pumping along the path; walking = hanging swing
        for side, sx, sgn in (("l", -1, -1), ("r", 1, 1)):
            c = math.cos(2 * math.pi * ph) * sgn
            a_up = (0.30 * (1 - r) + 0.42 * r) * c                  # upper-arm swing (rad, + forward)
            bend = (0.22 * (1 - r) + 1.45 * r) + 0.2 * r * max(0.0, c)
            ua = np.array([sx * (0.03 - self.arm_in * r), math.sin(a_up), -math.cos(a_up)])
            fa = np.array([sx * (0.02 - 1.6 * self.arm_in * r), math.sin(a_up + bend), -math.cos(a_up + bend)])
            el = Jw[f"sho_{side}"] + R @ (ua / np.linalg.norm(ua) * L_UPPER * k * s)
            wr = el + R @ (fa / np.linalg.norm(fa) * L_FORE * k * s)
            Jw[f"elb_{side}"], Jw[f"wri_{side}"] = el, wr
            Jw[f"hnd_{side}"] = wr + R @ (fa / np.linalg.norm(fa) * L_HAND * k * s)
        return Jw, hd, ph

    def plants(self, t0, t1):
        """every foot plant (t_land, x, y, z, heading, side) between t0 and t1"""
        out = []
        k = self.h / 1.72
        c0, c1 = int(math.floor(self.cycles(t0))) - 1, int(math.ceil(self.cycles(t1))) + 1
        for ci in range(c0, c1 + 1):
            for off, side in ((0.0, -1.0), (0.5, 1.0)):
                p, hd, tl = self._plant(ci, off, side * self.foot_lat * k)
                out.append((tl, p[0], p[1], p[2], hd, side))
        return out

    def attach(self, t, back=0.12, up=0.04):
        """thread anchor on the lower back (hip yaw sways it ~4 px sideways at the stride rate)"""
        k = self.h / 1.72
        ph = self.cycles(t) % 1.0
        r = self.run(t)
        base = np.array(self.path(t), float)
        hd = self.heading(t)
        R = rot_z(hd)
        bob = self._bob(ph, r, self.duty(t), k)
        sway = 0.03 * r * math.sin(2 * math.pi * ph)
        gz = self.ground(base[0], base[1])
        return np.array([base[0], base[1], gz]) + R @ np.array([sway, -back * k, 0.98 * k + bob + up * k])
