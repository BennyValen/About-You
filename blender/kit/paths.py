"""Smooth ground paths from keyframes, with linear extrapolation and a heading from the velocity."""
import math
import numpy as np


class KeyPath:
    def __init__(self, keys, t_min, t_max, sigma=4.0, min_speed=1e-3, heading_override=None, hold_heading=True):
        """keys: list of (t, x, y). Dense per-frame samples on [t_min, t_max] (step 0.5), Gaussian-smoothed."""
        k = np.array(sorted(keys), float)
        self.t = np.arange(t_min, t_max + 1e-9, 0.5)
        x = np.interp(self.t, k[:, 0], k[:, 1])
        y = np.interp(self.t, k[:, 0], k[:, 2])
        # linear extrapolation outside the keyed range
        if len(k) >= 2:
            v0 = (k[1, 1:] - k[0, 1:]) / max(k[1, 0] - k[0, 0], 1e-6)
            v1 = (k[-1, 1:] - k[-2, 1:]) / max(k[-1, 0] - k[-2, 0], 1e-6)
            lo = self.t < k[0, 0]
            hi = self.t > k[-1, 0]
            x[lo] = k[0, 1] + v0[0] * (self.t[lo] - k[0, 0])
            y[lo] = k[0, 2] + v0[1] * (self.t[lo] - k[0, 0])
            x[hi] = k[-1, 1] + v1[0] * (self.t[hi] - k[-1, 0])
            y[hi] = k[-1, 2] + v1[1] * (self.t[hi] - k[-1, 0])
        if sigma > 0:
            r = int(sigma * 2 * 3)
            g = np.exp(-0.5 * (np.arange(-r, r + 1) / (sigma * 2)) ** 2)
            g /= g.sum()
            pad = lambda a: np.concatenate([2 * a[0] - a[r:0:-1], a, 2 * a[-1] - a[-2:-r - 2:-1]])
            x = np.convolve(pad(x), g, "valid")
            y = np.convolve(pad(y), g, "valid")
        self.x, self.y = x, y
        vx, vy = np.gradient(x), np.gradient(y)
        sp = np.hypot(vx, vy)
        hd = np.arctan2(-vx, vy)                         # 0 = facing +Y, positive = turning left (CCW)
        if hold_heading:
            for i in range(1, len(hd)):
                if sp[i] < min_speed:
                    hd[i] = hd[i - 1]
        self.hd = np.unwrap(hd)
        if heading_override is not None:
            self.hd = np.array([heading_override(tt, h) for tt, h in zip(self.t, self.hd)])
        if sigma > 0:
            r = int(sigma * 2 * 3)
            g = np.exp(-0.5 * (np.arange(-r, r + 1) / (sigma * 2)) ** 2)
            g /= g.sum()
            self.hd = np.convolve(np.concatenate([np.full(r, self.hd[0]), self.hd, np.full(r, self.hd[-1])]), g, "valid")

    def pos(self, t):
        return float(np.interp(t, self.t, self.x)), float(np.interp(t, self.t, self.y))

    def heading(self, t):
        return float(np.interp(t, self.t, self.hd))

    def velocity(self, t, dt=1.0):
        a, b = self.pos(t - dt / 2), self.pos(t + dt / 2)
        return (b[0] - a[0]) / dt, (b[1] - a[1]) / dt
