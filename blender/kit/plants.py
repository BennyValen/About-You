"""Vegetation prototypes built from small constructed parts (numpy meshes), for geometry-nodes instancing.

shrub      leafless branching shrub (recursive branches as tapered tubes) -> long branching shadows at low sun
grass_tuft dry grass: 14-30 curved, tapered blades leaning outward
leaf_clump tree crown clump made of individual leaf cards (oriented, varied)
"""
import math
import numpy as np
from . import geo


def _tube(points, radii, sides=5):
    """tapered tube along a polyline -> verts, faces"""
    P = np.asarray(points, float)
    n = len(P)
    V, F = [], []
    for i in range(n):
        if i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = P[i + 1] - P[i - 1]
        t = t / (np.linalg.norm(t) + 1e-9)
        a = np.array([0.0, 0.0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(t, a)
        u /= np.linalg.norm(u) + 1e-9
        w = np.cross(t, u)
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            V.append(P[i] + radii[i] * (math.cos(ang) * u + math.sin(ang) * w))
    for i in range(n - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            c, d = (i + 1) * sides + (k + 1) % sides, (i + 1) * sides + k
            F.append((a, b, c, d))
    # tip cap
    tip = len(V)
    V.append(P[-1] + (P[-1] - P[-2]) * 0.05)
    for k in range(sides):
        F.append(((n - 1) * sides + k, (n - 1) * sides + (k + 1) % sides, tip))
    return np.array(V), F


def _merge(parts):
    V, F, off = [], [], 0
    for v, f in parts:
        V.append(v)
        F.extend([tuple(i + off for i in face) for face in f])
        off += len(v)
    return np.concatenate(V), F


def shrub(name, mat, coll, seed=0, height=0.55, depth=4, spread=0.9, twig_r=0.004, base_r=0.012):
    rng = np.random.default_rng(seed)
    parts = []

    def branch(p, d, length, r, lvl):
        steps = 4
        pts, rad = [p], [r]
        q = p.copy()
        dd = d.copy()
        for s in range(steps):
            dd = dd + rng.normal(0, 0.18, 3) * np.array([1, 1, 0.5])
            dd[2] = max(dd[2], -0.2)
            dd /= np.linalg.norm(dd)
            q = q + dd * length / steps
            pts.append(q.copy())
            rad.append(max(twig_r, r * (1 - 0.6 * (s + 1) / steps)))
        parts.append(_tube(pts, rad, 5 if lvl < 2 else 4))
        if lvl >= depth:
            return
        nchild = rng.integers(2, 4)
        for c in range(nchild):
            k = rng.integers(2, steps + 1)
            base = pts[k]
            ang = rng.uniform(0, 2 * math.pi)
            tilt = rng.uniform(0.35, 0.9) * spread
            nd = d * math.cos(tilt) + np.array([math.cos(ang), math.sin(ang), 0.0]) * math.sin(tilt)
            nd[2] = abs(nd[2]) * 0.8 + 0.15
            nd /= np.linalg.norm(nd)
            branch(base, nd, length * rng.uniform(0.55, 0.75), rad[k] * 0.7, lvl + 1)

    nstem = rng.integers(3, 6)
    for s in range(nstem):
        ang = rng.uniform(0, 2 * math.pi)
        d = np.array([math.cos(ang) * 0.35, math.sin(ang) * 0.35, 1.0])
        d /= np.linalg.norm(d)
        branch(np.array([rng.normal(0, 0.02), rng.normal(0, 0.02), 0.0]), d, height * rng.uniform(0.4, 0.55), base_r, 1)
    V, F = _merge(parts)
    return geo.mesh_from_faces(name, V, F, coll, smooth=True, mat=mat)


def grass_tuft(name, mat, coll, seed=0, n=(14, 30), height=0.28, lean=0.55):
    rng = np.random.default_rng(seed)
    V, F = [], []
    nb = int(rng.integers(*n))
    for b in range(nb):
        ang = rng.uniform(0, 2 * math.pi)
        h = height * rng.uniform(0.55, 1.15)
        lw = rng.uniform(0.004, 0.008)
        lean_b = lean * rng.uniform(0.4, 1.2)
        base = np.array([rng.normal(0, 0.02), rng.normal(0, 0.02), 0.0])
        dirh = np.array([math.cos(ang), math.sin(ang), 0.0])
        side = np.array([-math.sin(ang), math.cos(ang), 0.0])
        segs = 4
        i0 = len(V)
        for s in range(segs + 1):
            t = s / segs
            p = base + dirh * (lean_b * h * t * t) + np.array([0, 0, h * (t - 0.35 * lean_b * t * t)])
            w = lw * (1 - t) + 0.0005
            V.append(p - side * w)
            V.append(p + side * w)
        for s in range(segs):
            a = i0 + 2 * s
            F.append((a, a + 1, a + 3, a + 2))
    return geo.mesh_from_arrays(name, np.array(V), F, coll, smooth=True, mat=mat)


def leaf_clump(name, mat, coll, seed=0, radius=0.5, n_leaves=60, leaf=0.09, flat=0.65):
    """a clump of individual leaf cards on a squashed sphere shell, facing outward/up (tree crown building block)"""
    rng = np.random.default_rng(seed)
    V, F = [], []
    for i in range(n_leaves):
        u = rng.normal(0, 1, 3)
        u[2] = abs(u[2]) * 1.2 + 0.2
        u /= np.linalg.norm(u)
        c = u * radius * rng.uniform(0.7, 1.0) * np.array([1, 1, flat])
        nrm = u + np.array([0, 0, 0.6])
        nrm /= np.linalg.norm(nrm)
        a = np.array([1.0, 0, 0]) if abs(nrm[0]) < 0.9 else np.array([0, 1.0, 0])
        t1 = np.cross(nrm, a)
        t1 /= np.linalg.norm(t1)
        t2 = np.cross(nrm, t1)
        r = rng.uniform(0, 2 * math.pi)
        t1, t2 = t1 * math.cos(r) + t2 * math.sin(r), -t1 * math.sin(r) + t2 * math.cos(r)
        L = leaf * rng.uniform(0.7, 1.3)
        Wd = L * rng.uniform(0.35, 0.5)
        i0 = len(V)
        # leaf: 4-vertex diamond with a slight fold
        V += [c - t1 * L * 0.5, c + t2 * Wd * 0.5 + nrm * L * 0.06, c + t1 * L * 0.5, c - t2 * Wd * 0.5 + nrm * L * 0.06]
        F.append((i0, i0 + 1, i0 + 2, i0 + 3))
    return geo.mesh_from_arrays(name, np.array(V), F, coll, smooth=False, mat=mat)


def crown(name, mat, coll, seed=0, radius=2.0, height=None, n_clumps=34, leaves=70, leaf=0.16, flat=0.62, core=False, clump_attr=False):
    """tree crown seen from above: clumps of individual leaf cards arranged on a domed shell; each leaf gets a
    random value 'lv' (geometry attribute) for light/dark variation in the shader. Origin at the crown base."""
    rng = np.random.default_rng(seed)
    H = height if height is not None else radius * 1.25
    V, F, LV, CL = [], [], [], []
    centres = []
    for i in range(n_clumps):
        u = rng.normal(0, 1, 3)
        u[2] = abs(u[2]) * 0.9 + 0.15
        u /= np.linalg.norm(u)
        c = np.array([u[0] * radius * 0.82, u[1] * radius * 0.82, H * 0.55 + u[2] * H * 0.45 * flat / 0.62])
        centres.append((c, rng.uniform(0.55, 0.9) * radius * 0.4))
    for c, cr in centres:
        base_v = rng.uniform(-0.25, 0.25)
        clv = rng.random()
        for k in range(leaves):
            u = rng.normal(0, 1, 3)
            u[2] = abs(u[2]) * 1.1 + 0.25
            u /= np.linalg.norm(u)
            p = c + u * cr * rng.uniform(0.6, 1.0) * np.array([1, 1, 0.75])
            nrm = u + np.array([0, 0, 0.8])
            nrm /= np.linalg.norm(nrm)
            a = np.array([1.0, 0, 0]) if abs(nrm[0]) < 0.9 else np.array([0, 1.0, 0])
            t1 = np.cross(nrm, a)
            t1 /= np.linalg.norm(t1)
            t2 = np.cross(nrm, t1)
            r = rng.uniform(0, 2 * math.pi)
            t1, t2 = t1 * math.cos(r) + t2 * math.sin(r), -t1 * math.sin(r) + t2 * math.cos(r)
            L = leaf * rng.uniform(0.7, 1.35)
            Wd = L * rng.uniform(0.4, 0.55)
            i0 = len(V)
            V += [p - t1 * L * 0.5, p + t2 * Wd * 0.5 + nrm * L * 0.08, p + t1 * L * 0.5, p - t2 * Wd * 0.5 + nrm * L * 0.08]
            F.append((i0, i0 + 1, i0 + 2, i0 + 3))
            # value: top/outer leaves lighter, plus per-clump and per-leaf variation
            v = 0.5 + 0.35 * (p[2] / (H * 1.1) - 0.5) + base_v + rng.normal(0, 0.12)
            LV += [v] * 4
            CL += [clv] * 4
    if core:
        # dark inner foliage mass so gaps between leaf clumps read as deep leaves, not ground
        nu, nv = 16, 8
        i0 = len(V)
        for j in range(nv + 1):
            th = math.pi * 0.5 * j / nv
            for i in range(nu):
                ph = 2 * math.pi * i / nu
                V.append(np.array([math.cos(ph) * math.cos(th) * radius * 0.85, math.sin(ph) * math.cos(th) * radius * 0.85,
                                   H * 0.35 + math.sin(th) * H * 0.55]))
                LV.append(0.12)
                CL.append(0.5)
        for j in range(nv):
            for i in range(nu):
                a_, b_ = i0 + j * nu + i, i0 + j * nu + (i + 1) % nu
                F.append((a_, b_, b_ + nu, a_ + nu))
    ob = geo.mesh_from_arrays(name, np.array(V), F, coll, smooth=False, mat=mat)
    a = ob.data.attributes.new("lv", "FLOAT", "POINT")
    a.data.foreach_set("value", np.clip(np.array(LV, np.float32), 0, 1))
    if clump_attr:
        c_ = ob.data.attributes.new("cl", "FLOAT", "POINT")
        c_.data.foreach_set("value", np.array(CL, np.float32))
    # trunk stub (hinted at the centre)
    return ob


def leaf_card(name, mat, coll, size=0.07):
    V = np.array([(-size * 0.5, 0, 0), (0, size * 0.22, 0.004), (size * 0.5, 0, 0), (0, -size * 0.22, 0.004)])
    return geo.mesh_from_arrays(name, V, [(0, 1, 2, 3)], coll, smooth=False, mat=mat)
