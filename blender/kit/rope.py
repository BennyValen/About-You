"""The red thread v3: a world-space rope (pure numpy, no bpy, so it can also be tuned offline).

  * >= 240 segments, total length about two screen heights, pinned at the owner (waist, harness, stern, bike frame,
    coupler); the free end lies far beyond the frame edge.
  * Inextensible via dynamic follow-the-leader (DFTL, Mueller et al. 2012) with velocity correction, plus a small
    bending stiffness (Laplacian smoothing) and damping.
  * Forces: gravity; drag toward a time-varying world wind/current field (curl noise + gusts); the owner's motion
    (gait sway, rowing surges, pendulum swing...) arrives through the anchor path, which is sampled every substep.
  * Environments:
      ground  - lies on a height field; contact friction kills sideways sliding (sand: strong, ice: weak); air drag on
                lifted parts. On sand it lies along the trail; on ice it slides and whips on direction changes.
      water   - floats at the surface; viscous drag toward the surface current (wake + curl-noise eddies).
      air     - low drag toward the relative wind; long sway, catenary sag under gravity.
All numbers are SI (m, s). Time t is in frames (float), converted to seconds internally.
"""
import numpy as np

FPS = 24.0
_G = np.array([0.0, 0.0, -9.81])

# ---------------------------------------------------------------- smooth noise (vectorized value noise)
_rng = np.random.RandomState(1234)
_PERM = np.concatenate([_rng.permutation(256)] * 2)
_VAL = _rng.uniform(-1.0, 1.0, 256)


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def vnoise3(x, y, z, seed=0):
    """smooth value noise in [-1,1], vectorized over x,y (z scalar or array)"""
    x = np.asarray(x, float) + seed * 17.13
    y = np.asarray(y, float) + seed * 31.71
    z = np.broadcast_to(np.asarray(z, float), x.shape)
    xi, yi, zi = np.floor(x).astype(int), np.floor(y).astype(int), np.floor(z).astype(int)
    xf, yf, zf = x - xi, y - yi, z - zi
    u, v, w = _fade(xf), _fade(yf), _fade(zf)
    xi &= 255
    yi &= 255
    zi &= 255

    def h(a, b, c):
        return _VAL[_PERM[_PERM[_PERM[a] + b] + c] & 255]

    x1, y1, z1 = (xi + 1) & 255, (yi + 1) & 255, (zi + 1) & 255
    c000, c100, c010, c110 = h(xi, yi, zi), h(x1, yi, zi), h(xi, y1, zi), h(x1, y1, zi)
    c001, c101, c011, c111 = h(xi, yi, z1), h(x1, yi, z1), h(xi, y1, z1), h(x1, y1, z1)
    a = c000 + u * (c100 - c000)
    b = c010 + u * (c110 - c010)
    c = c001 + u * (c101 - c001)
    d = c011 + u * (c111 - c011)
    e = a + v * (b - a)
    f = c + v * (d - c)
    return e + w * (f - e)


def fbm3(x, y, z, octaves=2, seed=0):
    s, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + amp * vnoise3(x * 2 ** o, y * 2 ** o, z * 1.7 ** o, seed + o * 7)
        tot += amp
        amp *= 0.5
    return s / tot


class Field:
    """World wind (or surface current) field: base vector + curl noise (divergence free) + gusts.

    base: (vx, vy) m/s.  curl: m/s amplitude of the eddies.  scale: eddy size in m.  evolve: noise time rate (1/s).
    gust: m/s amplitude of gusts along `gust_dir` (default: base direction, else +x).  gust_hz: gust rate.
    lateral: extra m/s amplitude of a slow side-to-side meander perpendicular to the base (long sway).
    """

    def __init__(self, base=(0.0, 0.0), curl=0.5, scale=6.0, evolve=0.15, gust=0.0, gust_hz=0.12, gust_dir=None,
                 lateral=0.0, lateral_hz=0.15, seed=0, vertical=0.0):
        self.base = np.array([base[0], base[1], 0.0], float)
        self.curl, self.scale, self.evolve = curl, scale, evolve
        self.gust, self.gust_hz = gust, gust_hz
        b = self.base[:2]
        gd = np.asarray(gust_dir if gust_dir is not None else (b if np.linalg.norm(b) > 1e-6 else (1.0, 0.0)), float)
        self.gust_dir = np.array([gd[0], gd[1], 0.0]) / (np.linalg.norm(gd) + 1e-9)
        self.perp = np.array([-self.gust_dir[1], self.gust_dir[0], 0.0])
        self.lateral, self.lateral_hz = lateral, lateral_hz
        self.seed = seed
        self.vertical = vertical

    def gust_at(self, ts):
        g = 0.5 + 0.5 * vnoise3(np.array([ts * self.gust_hz]), np.array([0.37]), 0.0, self.seed + 91)[0]
        return self.gust * g * g * 2.0

    def __call__(self, P, t_frames):
        ts = t_frames / FPS
        n = len(P)
        out = np.tile(self.base, (n, 1))
        if self.curl > 0:
            x, y = P[:, 0] / self.scale, P[:, 1] / self.scale
            zt = ts * self.evolve
            e = 0.05
            dpy = (fbm3(x, y + e, zt, 2, self.seed) - fbm3(x, y - e, zt, 2, self.seed)) / (2 * e)
            dpx = (fbm3(x + e, y, zt, 2, self.seed) - fbm3(x - e, y, zt, 2, self.seed)) / (2 * e)
            out[:, 0] += self.curl * dpy
            out[:, 1] += -self.curl * dpx
        if self.gust > 0:
            out += self.gust_dir * self.gust_at(ts)
        if self.lateral > 0:
            # a slow meander that travels along the base direction (so the rope shows travelling S-waves)
            along = (P[:, :2] @ self.gust_dir[:2]) / max(self.scale, 1e-3)
            ph = 2 * np.pi * self.lateral_hz * ts - along * 0.9
            amp = self.lateral * (0.75 + 0.25 * vnoise3(np.array([ts * 0.07]), np.array([3.1]), 0.0, self.seed + 5)[0])
            out += self.perp[None, :] * (amp * np.sin(ph))[:, None]
        if self.vertical:
            out[:, 2] += self.vertical
        return out


# ---------------------------------------------------------------- rope
class Rope:
    def __init__(self, n_seg=260, length=60.0, mode="ground", ground=None, water_level=0.0, friction=20.0,
                 air_drag=1.2, water_drag=6.0, wind=None, current=None, substeps=6, bend=0.02, damping=0.4,
                 radius=0.01, dftl=0.92, push=None, gravity=1.0, lift=0.0):
        """friction: 1/s decay rate of sideways velocity for points touching the ground (sand ~25, ice ~0.6),
        or a callable (x, y) -> rate.  air_drag / water_drag: 1/s relaxation rate toward the wind / current.
        damping: 1/s global velocity damping. bend: 0..1 Laplacian smoothing per substep.
        push(P, t) -> (n,3) extra acceleration (wakes, rotor wash...). lift: m/s^2 constant upward accel (kite-like)."""
        self.n = n_seg
        self.rest = length / n_seg
        self.length = length
        self.mode = mode
        self.ground = ground or (lambda x, y: np.zeros_like(x))
        self.wl = water_level
        self.mu = friction
        self.k_air = air_drag
        self.k_w = water_drag
        self.wind = wind
        self.current = current
        self.sub = substeps
        self.bend = bend
        self.damp = damping
        self.r = radius
        self.s_dftl = dftl
        self.push = push
        self.gscale = gravity
        self.lift = lift

    def _ftl(self, P, pin):
        """sequential follow-the-leader projection; returns corrections d_i applied to each point"""
        n, rest = self.n, self.rest
        d = np.zeros_like(P)
        P[0] = pin
        prev = P[0].copy()
        for i in range(1, n + 1):
            v = P[i] - prev
            L = np.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) + 1e-12
            q = prev + v * (rest / L)
            d[i] = q - P[i]
            P[i] = q
            prev = q
        return d

    def _env(self, P, V, t, dt):
        n = len(P)
        acc = np.tile(_G * self.gscale, (n, 1))
        if self.lift:
            acc[:, 2] += self.lift
        if self.push is not None:
            acc += self.push(P, t)
        V += acc * dt
        if self.mode == "water":
            cur = self.current(P, t) if self.current is not None else np.zeros_like(P)
            a = 1.0 - np.exp(-self.k_w * dt)
            V[:, :2] += (cur[:, :2] - V[:, :2]) * a
            V[:, 2] *= np.exp(-12.0 * dt)
        else:
            w = self.wind(P, t) if self.wind is not None else np.zeros_like(P)
            a = 1.0 - np.exp(-self.k_air * dt)
            V += (w - V) * a
        if self.damp:
            V *= np.exp(-self.damp * dt)
        return V

    def _touch(self, P):
        if self.mode == "water":
            return np.zeros(len(P))
        gz = self.ground(P[:, 0], P[:, 1]) + self.r
        return (P[:, 2] <= gz + 2e-3).astype(float)

    def _contact(self, P, V, dt):
        if self.mode == "water":
            P[:, 2] = self.wl + self.r
            V[:, 2] = 0.0
            return
        gz = self.ground(P[:, 0], P[:, 1]) + self.r
        low = P[:, 2] <= gz + 1e-4
        if low.any():
            P[low, 2] = gz[low]
            V[low, 2] = np.maximum(V[low, 2], 0.0)
            mu = self.mu(P[low, 0], P[low, 1]) if callable(self.mu) else self.mu
            k = np.exp(-np.asarray(mu) * dt)
            if np.ndim(k):
                k = k[:, None]
            V[low, :2] *= k

    def run(self, frames, anchor, trail_dir, warm=120, init=None):
        """frames: sorted frames to record. anchor(t) -> xyz (t = float frame). trail_dir: xy direction the rope
        initially trails toward from the anchor (it is laid along the anchor's past path when init='path').
        Returns {f: (n+1,3) array}."""
        f0 = frames[0]
        dt = 1.0 / FPS / self.sub
        # lay the rope along the anchor's past path (extrapolated backward), so it starts as a settled trail
        s = np.arange(self.n + 1) * self.rest
        a0 = np.asarray(anchor(f0 - warm), float)
        td = np.array([trail_dir[0], trail_dir[1], 0.0], float)
        td /= np.linalg.norm(td) + 1e-9
        P = a0[None, :] + td[None, :] * s[:, None]
        if self.mode == "water":
            P[:, 2] = self.wl + self.r
        else:
            P[:, 2] = np.maximum(P[:, 2], self.ground(P[:, 0], P[:, 1]) + self.r)
        V = np.zeros_like(P)
        out = {}
        want = set(frames)
        last = frames[-1]
        lap_w = self.bend * 0.5
        for fi in range(f0 - warm, last + 1):
            for k in range(self.sub):
                t = fi + (k + 1) / self.sub
                pin = np.asarray(anchor(t), float)
                V = self._env(P, V, t, dt)
                Q = P + V * dt
                if lap_w > 0:
                    # small bending stiffness; points held by ground friction keep their laid shape
                    wv = lap_w * (1.0 - 0.9 * self._touch(Q))[1:-1, None]
                    Q[1:-1] += wv * (Q[:-2] + Q[2:] - 2 * Q[1:-1])
                d = self._ftl(Q, pin)
                self._contact(Q, V, dt)
                # DFTL velocity with correction from the next point (removes the artificial damping of FTL)
                Vn = (Q - P) / dt
                Vn[:-1] -= self.s_dftl * d[1:] / dt
                Vn[0] = 0.0
                P, V = Q, Vn
                self._contact(P, V, dt)
            if fi in want:
                out[fi] = P.copy()
        return out


def screen_points(rig_xy, ppm, cam_h, P, W=1080, H=1920):
    """project world points with the top-down camera (same model as kit.core.Rig): returns (n,2) px, (n,) ppm_at"""
    k = ppm * cam_h / np.maximum(cam_h - P[:, 2], 1e-3)
    sx = (P[:, 0] - rig_xy[0]) * k + W / 2
    sy = H / 2 - (P[:, 1] - rig_xy[1]) * k
    return np.stack([sx, sy], 1), k


def chord_stats(S, H=1920, W=1080):
    """same measurement as scripts/analysis_thread_stats.py, on projected points from the owner to the frame exit.
    S: (n,2) screen points from the owner outward. Returns dict or None."""
    inside = (S[:, 0] >= 0) & (S[:, 0] < W) & (S[:, 1] >= 0) & (S[:, 1] < H)
    if not inside[0]:
        return None
    out = np.nonzero(~inside)[0]
    m = out[0] if len(out) else len(S)
    Q = S[:m]
    if len(Q) < 5:
        return None
    # resample by rows (like the trace), only valid while the thread is monotonic-ish in y
    y = Q[:, 1]
    order = np.argsort(y)
    yu = np.arange(int(np.ceil(y.min())), int(np.floor(y.max())) + 1)
    if len(yu) < 30:
        return None
    xu = np.interp(yu, y[order], Q[order, 0])
    a = np.array([xu[0], yu[0]], float)
    b = np.array([xu[-1], yu[-1]], float)
    dvec = b - a
    L = np.linalg.norm(dvec) + 1e-6
    nrm = np.array([-dvec[1], dvec[0]]) / L
    PP = np.stack([xu, yu], 1)
    dev = (PP - a) @ nrm
    tt = ((PP - a) @ dvec) / L ** 2

    def at(q):
        return float(dev[np.argmin(np.abs(tt - q))])
    return dict(rms=float(np.sqrt(np.mean(dev ** 2))), maxdev=float(np.abs(dev).max()), length_px=float(L),
                dev_mid=at(0.5), dev_34=at(0.75), angle_deg=float(np.degrees(np.arctan2(dvec[0], dvec[1]))))
