"""v3 painting post-process (brief section 3.4 + 3b), applied to each distinct drawing (even frame) only.

  clean render  ->  stroke layer (oriented brush dabs anchored to surfaces, re-laid with jitter every drawing)
                ->  boil (smooth displacement field reseeded every drawing; heroes get a fraction)
                ->  red thread (world-space rope projected, tapered, AA, highlight, cast shadow, glow)
                ->  screen-fixed canvas weave + impasto (never boils)  ->  grain  ->  luminance lock

Inputs per scene dir (render/v3/scene_XX):  clean/fNNNN.jpg|png, aux/hero_NNNN.png (8/16-bit), aux/pos_NNNN.png
(16-bit, fract(world/period) encoded, half res), meta.json (camera per drawing, post params), thread.npz.
Output: paint/fNNNN.jpg

  python scripts/post/paint.py --scene 3 [--dir render/v3/scene_03] [--frames a-b] [--jobs 12] [--force]
"""
import argparse, json, os, sys, time, glob
import numpy as np
import cv2

W, H = 1080, 1920
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
POS_PERIOD = (256.0, 256.0, 128.0)
POS_ZOFF = 32.0

DEFAULT = dict(
    stroke_px=12.0,           # coarse stroke cell (px at ground scale)
    fine_px=5.5,              # fine strokes where the coarse painting loses detail
    edge_sigma=0.11,          # colour distance where a dab stops painting over (edge-aware strokes)
    fine_err=0.035,           # mean abs error (0..1) that triggers fine strokes
    elong=2.0,                # stroke elongation in coherent (oriented) areas
    repaint=0.55,             # how much of a background pixel takes the stroke's flat colour
    repaint_hero=0.10,
    value_static=5.0,         # persistent per-stroke value offset (levels)
    value_jitter=3.5,         # per-drawing value jitter (levels)  (v4: 3-4; v3 used 8)
    angle_jitter=2.0,         # per-drawing angle jitter (deg)
    pos_jitter=1.0,           # per-drawing position jitter (px)   (v4: 0.5-1.5)
    bristle=0.035,            # bristle stripe contrast
    flow_deg=90.0,            # default stroke direction where the picture has no orientation (screen deg, 0 = +x)
    boil_mode="fine",         # v4: fine-scale boil only (patches 8-24 px); "coarse" reproduces v3 (patches 32-88 px)
    boil_scale=1.0,           # v4 per-scene strength: textured 0.8 px, flat 0.4 px mean (x boil_scale); heroes/outlines <= 0.3 px
    boil_mean=2.0,            # px at 1080 wide, mean |displacement| of the background boil (coarse/v3 mode only)
    boil_hero=0.35,           # fraction for heroes
    wobble=0.55,              # px, fine edge wobble
    canvas=0.0035,            # canvas weave strength (faint: a stronger fixed texture captures the rigid alignment of gate 8)
    impasto=0.0035,           # fixed impasto relief strength (faint, same reason)
    grain=2.0,                # levels
    light_deg=135.0,          # screen direction the light comes FROM (0 = +x right, 90 = up)
    thread_rgb=(196, 44, 50),
    thread_w0=4.0, thread_w1=2.5,
    thread_shadow_px=2.2,     # shadow offset for rope lying on the surface
    thread_shadow_per_m=0.0,  # extra offset per metre of height above the surface
    thread_shadow_alpha=0.42,
    thread_glow=0.0,
    thread_glints=0,          # ice-crystal glints along the thread (count per drawing)
    lum_lock=True,
    seed=0,
)


# ---------------------------------------------------------------- helpers
def h32(*arrs):
    """vectorized integer hash -> uint32"""
    h = np.uint32(2166136261) * np.ones(np.broadcast(*arrs).shape, np.uint32)
    for a in arrs:
        x = np.asarray(a).astype(np.int64).astype(np.uint32)
        h ^= x * np.uint32(0x9E3779B1)
        h = (h ^ (h >> np.uint32(15))) * np.uint32(0x85EBCA77)
        h ^= h >> np.uint32(13)
    return h


def u01(h):
    return (h & np.uint32(0xFFFFFF)).astype(np.float32) / np.float32(0xFFFFFF)


def smooth_noise(h, w, cell, rng):
    gh, gw = int(np.ceil(h / cell)) + 3, int(np.ceil(w / cell)) + 3
    g = rng.standard_normal((gh, gw)).astype(np.float32)
    up = cv2.resize(g, (int(gw * cell), int(gh * cell)), interpolation=cv2.INTER_CUBIC)
    oy, ox = rng.integers(0, max(1, int(cell)), 2)
    return up[oy:oy + h, ox:ox + w]


def boil_field(h, w, rng, mean_px, wobble_px):
    dx = np.zeros((h, w), np.float32)
    dy = np.zeros((h, w), np.float32)
    for cell, a in ((88, 1.0), (54, 0.75), (32, 0.5)):
        dx += a * smooth_noise(h, w, cell, rng)
        dy += a * smooth_noise(h, w, cell, rng)
    mag = np.sqrt(dx * dx + dy * dy).mean() + 1e-6
    dx *= mean_px / mag
    dy *= mean_px / mag
    if wobble_px > 0:
        fx, fy = smooth_noise(h, w, 9, rng), smooth_noise(h, w, 9, rng)
        m = np.sqrt(fx * fx + fy * fy).mean() + 1e-6
        dx += fx * wobble_px / m
        dy += fy * wobble_px / m
    return dx, dy


def boil_field_fine(h, w, rng, img_gray, hero, scale):
    """v4 boil: displacement patches 8-24 px only (no coarse warp: big shapes hold still). Amplitude map: 0.8 px mean in
    textured regions, 0.4 px in flat regions (x scale); heroes and hard outlines at most 0.3 px; edge wobble <= 0.5 px."""
    dx = np.zeros((h, w), np.float32)
    dy = np.zeros((h, w), np.float32)
    for cell, a in ((24, 1.0), (14, 0.8), (8, 0.6)):
        dx += a * smooth_noise(h, w, cell, rng)
        dy += a * smooth_noise(h, w, cell, rng)
    mag = np.sqrt(dx * dx + dy * dy).mean() + 1e-6
    dx /= mag
    dy /= mag
    g = cv2.GaussianBlur(img_gray, (0, 0), 1.2)
    gm = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3))
    tex = cv2.blur(gm, (11, 11))
    tex = np.clip(tex / (np.percentile(tex, 90) + 1e-6), 0, 1)
    amp = (0.4 + 0.4 * tex) * scale
    edges = cv2.dilate((gm > np.percentile(gm, 97)).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    cap = np.maximum(edges, hero)
    amp = amp * (1 - cap) + np.minimum(amp, 0.3) * cap
    amp = np.minimum(amp, 2.0)            # peak guard
    return dx * amp, dy * amp


_CANVAS = {}


def canvas_tex(light_deg, seed=7):
    key = (round(light_deg), seed)
    if key in _CANVAS:
        return _CANVAS[key]
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    # woven canvas: two slightly irregular gratings (warp/weft), ~3.6 px pitch
    wx = smooth_noise(H, W, 40, rng) * 1.2
    wy = smooth_noise(H, W, 40, rng) * 1.2
    weave = (np.sin((xx + wx) * 2 * np.pi / 3.6) * np.sin((yy + wy) * 2 * np.pi / 3.7))
    weave += 0.35 * smooth_noise(H, W, 2.2, rng)
    weave = weave / (np.abs(weave).max() + 1e-6)
    # impasto relief: a fixed field of short strokes (height map), lit by the scene light (emboss)
    hmap = np.zeros((H, W), np.float32)
    n = 26000
    xs, ys = rng.uniform(0, W, n), rng.uniform(0, H, n)
    ang = rng.uniform(0, 180, n)
    ln, wd = rng.uniform(6, 16, n), rng.uniform(2.0, 4.5, n)
    hv = rng.uniform(0.3, 1.0, n)
    for i in range(n):
        cv2.ellipse(hmap, (int(xs[i]), int(ys[i])), (int(ln[i]), int(wd[i])), float(ang[i]), 0, 360, float(hv[i]), -1)
    hmap = cv2.GaussianBlur(hmap, (0, 0), 1.6)
    gx = cv2.Sobel(hmap, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(hmap, cv2.CV_32F, 0, 1, ksize=3)
    la = np.radians(light_deg)
    lx, ly = np.cos(la), -np.sin(la)        # screen y down
    imp = -(gx * lx + gy * ly)
    imp = imp / (np.percentile(np.abs(imp), 99) + 1e-6)
    _CANVAS[key] = (weave.astype(np.float32), np.clip(imp, -1.5, 1.5).astype(np.float32))
    return _CANVAS[key]


# ---------------------------------------------------------------- strokes
def orientation(gray):
    g = cv2.GaussianBlur(gray, (0, 0), 1.6)
    ix = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    iy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    jxx = cv2.GaussianBlur(ix * ix, (0, 0), 5)
    jxy = cv2.GaussianBlur(ix * iy, (0, 0), 5)
    jyy = cv2.GaussianBlur(iy * iy, (0, 0), 5)
    return jxx, jxy, jyy


def surface_coords(pos16, cam_xy, ppm):
    """decode the position pass -> continuous world x, y, z (m) near the camera"""
    p = cv2.resize(pos16, (W, H), interpolation=cv2.INTER_NEAREST).astype(np.float32) / 65535.0
    # cv2 loads BGR: channel 2 = X, 1 = Y, 0 = Z
    x = p[..., 2] * POS_PERIOD[0]
    y = p[..., 1] * POS_PERIOD[1]
    z = p[..., 0] * POS_PERIOD[2] - POS_ZOFF
    cx, cy = cam_xy
    x = ((x - cx + POS_PERIOD[0] / 2) % POS_PERIOD[0]) - POS_PERIOD[0] / 2 + cx
    y = ((y - cy + POS_PERIOD[1] / 2) % POS_PERIOD[1]) - POS_PERIOD[1] / 2 + cy
    return x, y, z


def ground_coords(cam_xy, ppm):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return cam_xy[0] + (xx - W / 2) / ppm, cam_xy[1] - (yy - H / 2) / ppm, np.zeros((H, W), np.float32)


def paint_layer(img, wx, wy, wz, ppm, cell_px, P, drawing, hero, J, select=None, layer_seed=0, fine=False):
    """one stroke layer. Returns (painted image, coverage mask) where coverage = pixels that received a stroke."""
    cell = cell_px / ppm
    gx = np.floor(wx / cell).astype(np.int64)
    gy = np.floor(wy / cell).astype(np.int64)
    gz = np.floor(wz / (cell * 3.0)).astype(np.int64)
    lx, ly, lz = gx - gx.min(), gy - gy.min(), gz - gz.min()
    nx, ny = int(lx.max()) + 1, int(ly.max()) + 1
    lid = ((lz * ny + ly) * nx + lx).ravel()
    uid, inv = np.unique(lid, return_inverse=True)
    n = len(uid)
    yy, xx = np.mgrid[0:H, 0:W]
    cnt = np.bincount(inv, minlength=n).astype(np.float32)
    sx = np.bincount(inv, xx.ravel(), n) / cnt
    sy = np.bincount(inv, yy.ravel(), n) / cnt
    # stroke colour: the (lightly blurred) picture at the stroke centre, not the cell mean (no mixing across edges)
    imgb = cv2.GaussianBlur(img, (0, 0), 1.2)
    col = imgb[np.clip(sy.astype(int), 0, H - 1), np.clip(sx.astype(int), 0, W - 1)].astype(np.float32)
    jxx = np.bincount(inv, J[0].ravel(), n) / cnt
    jxy = np.bincount(inv, J[1].ravel(), n) / cnt
    jyy = np.bincount(inv, J[2].ravel(), n) / cnt
    herof = np.bincount(inv, hero.ravel(), n) / cnt
    # global cell coordinates of each stroke (for persistent randoms)
    rep = np.zeros(n, np.int64)
    rep[inv] = np.arange(len(inv))
    cgx, cgy, cgz = gx.ravel()[rep], gy.ravel()[rep], gz.ravel()[rep]
    hs = h32(cgx, cgy, cgz, np.int64(P["seed"] * 7 + layer_seed))
    hd = h32(cgx, cgy, cgz, np.int64(drawing * 31 + 5 + layer_seed))
    r1, r2, r3, r4 = u01(hs), u01(h32(hs, 1)), u01(h32(hs, 2)), u01(h32(hs, 3))
    d1, d2, d3, d4 = u01(hd), u01(h32(hd, 1)), u01(h32(hd, 2)), u01(h32(hd, 3))
    # orientation along edges (structure tensor), coherence -> elongation
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2
    lam = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2)
    coh = np.clip(lam / (jxx + jyy + 1e-9), 0, 1) ** 1.2
    strength = np.clip((jxx + jyy) / 0.0006, 0, 1)
    w_or = np.clip(coh * strength * 1.6, 0, 1)
    flow = np.radians(P["flow_deg"]) + (r4 - 0.5) * 0.9
    # blend angles on the doubled-angle circle
    c2 = w_or * np.cos(2 * theta) + (1 - w_or) * np.cos(2 * flow)
    s2 = w_or * np.sin(2 * theta) + (1 - w_or) * np.sin(2 * flow)
    ang = 0.5 * np.arctan2(s2, c2) + np.radians(P["angle_jitter"]) * (d1 - 0.5) * 2
    el = 1.0 + (P["elong"] - 1.0) * (0.35 + 0.65 * w_or)
    L = cell_px * (0.62 + 0.3 * r1) * np.sqrt(el)
    Wd = cell_px * (0.62 + 0.3 * r2) / np.sqrt(el) * 0.82
    if fine:
        L *= 1.05
    jx = sx + (d2 - 0.5) * 2 * P["pos_jitter"] * (1 - 0.7 * herof)
    jy = sy + (d3 - 0.5) * 2 * P["pos_jitter"] * (1 - 0.7 * herof)
    vstat = (r3 - 0.5) * 2 * P["value_static"] / 255.0
    vjit = (d4 - 0.5) * 2 * P["value_jitter"] / 255.0
    keep = cnt > (0.08 * cell_px * cell_px if not fine else 0.2 * cell_px * cell_px)
    if select is not None:
        keep &= select(sx, sy, inv, cnt)
    idmap = np.zeros((H, W), np.float32)
    order = np.nonzero(keep)[0]
    order = order[np.argsort(u01(h32(cgx[order], cgy[order], 99 + layer_seed)))]
    sh = 4
    for i in order:
        cv2.ellipse(idmap, (int(jx[i] * 16), int(jy[i] * 16)), (max(1, int(L[i] * 8)), max(1, int(Wd[i] * 8))),
                    float(np.degrees(-ang[i])), 0, 360, float(i + 1), -1, cv2.LINE_8, sh)
    sid = idmap.astype(np.int64) - 1
    cov = sid >= 0
    s = np.where(cov, sid, 0)
    # stroke-local coordinates -> bristle stripes, soft ends
    ca, sa = np.cos(-ang[s]), np.sin(-ang[s])
    du, dv = xx - jx[s], yy - jy[s]
    u = (du * ca + dv * sa) / np.maximum(L[s], 1)
    v = (-du * sa + dv * ca) / np.maximum(Wd[s], 1)
    nb = 3.0 + 3.0 * r1[s]
    bri = np.sin(v * np.pi * nb + r2[s] * 6.28) * (0.6 + 0.4 * np.cos(u * 2.1 + r3[s] * 6.28))
    rr = np.clip(u * u + v * v, 0, 1)
    scol = col[s] * (1.0 + (vstat[s] + vjit[s])[..., None]) + (P["bristle"] * bri * (1 - 0.6 * rr))[..., None]
    # edge-aware: a dab does not paint over a region of a different colour (keeps silhouettes and edges clean)
    diff = np.abs(img - col[s]).mean(2)
    ea = np.exp(-(diff / P["edge_sigma"]) ** 2)
    a = np.where(cov, (P["repaint"] * (1 - hero) + P["repaint_hero"] * hero) * (1 - 0.35 * rr) * ea, 0.0)[..., None]
    out = img * (1 - a) + scol * a
    # value jitter shows even where the repaint is light (strokes visibly re-lay)
    vj = np.where(cov, (vjit[s] + vstat[s]) * (1 - 0.75 * hero) * (0.4 + 0.6 * ea), 0.0)[..., None]
    out = out + img * vj * (1 - a)
    return out.astype(np.float32), cov


# ---------------------------------------------------------------- thread
def draw_thread(img, pts, hgt, P, hero_mask, rng, light_deg):
    """pts: (n,2) screen points from the owner outward; hgt: (n,) metres above the surface below."""
    if pts is None or len(pts) < 2:
        return img
    inside = (pts[:, 0] > -40) & (pts[:, 0] < W + 40) & (pts[:, 1] > -40) & (pts[:, 1] < H + 40)
    if not inside.any():
        return img
    last = np.nonzero(inside)[0].max()
    Q = pts[: min(len(pts), last + 3)].astype(np.float32).copy()
    hz = hgt[: len(Q)]
    # tiny per-drawing wobble (hand-drawn line): smooth along the length
    k = len(Q)
    wob = np.cumsum(rng.standard_normal((k, 2)) * 0.12, 0)
    wob -= np.linspace(0, 1, k)[:, None] * wob[-1]
    wob = cv2.GaussianBlur(wob.astype(np.float32).reshape(k, 1, 2), (1, 0), 6).reshape(k, 2) if k > 3 else wob
    Q += np.clip(wob, -0.6, 0.6)
    seg = np.linalg.norm(np.diff(Q, axis=0), axis=1)
    sarc = np.concatenate([[0], np.cumsum(seg)])
    vis_len = max(sarc[min(last, len(sarc) - 1)], 1.0)
    width = P["thread_w0"] + (P["thread_w1"] - P["thread_w0"]) * np.clip(sarc / vis_len, 0, 1)
    la = np.radians(light_deg)
    ldir = np.array([np.cos(la), -np.sin(la)], np.float32)      # toward the light, screen coords
    sh_off = -ldir * (P["thread_shadow_px"] + P["thread_shadow_per_m"] * hz[:, None])
    x0 = int(max(0, np.floor(min(Q[:, 0].min(), (Q + sh_off)[:, 0].min()) - 8)))
    x1 = int(min(W, np.ceil(max(Q[:, 0].max(), (Q + sh_off)[:, 0].max()) + 8)))
    y0 = int(max(0, np.floor(min(Q[:, 1].min(), (Q + sh_off)[:, 1].min()) - 8)))
    y1 = int(min(H, np.ceil(max(Q[:, 1].max(), (Q + sh_off)[:, 1].max()) + 8)))
    if x1 <= x0 or y1 <= y0:
        return img
    bw, bh = x1 - x0, y1 - y0

    def coverage(points, widths):
        """AA coverage of a tapered polyline (union of capsules) in the bbox"""
        cov = np.zeros((bh, bw), np.float32)
        for i in range(len(points) - 1):
            a, b = points[i], points[i + 1]
            r = 0.5 * (widths[i] + widths[i + 1]) * 0.5
            lo_x = int(max(x0, min(a[0], b[0]) - r - 2)) - x0
            hi_x = int(min(x1, max(a[0], b[0]) + r + 3)) - x0
            lo_y = int(max(y0, min(a[1], b[1]) - r - 2)) - y0
            hi_y = int(min(y1, max(a[1], b[1]) + r + 3)) - y0
            if hi_x <= lo_x or hi_y <= lo_y:
                continue
            yy, xx = np.mgrid[lo_y:hi_y, lo_x:hi_x].astype(np.float32)
            px, py = xx + x0 + 0.5, yy + y0 + 0.5
            ab = b - a
            t = np.clip(((px - a[0]) * ab[0] + (py - a[1]) * ab[1]) / (ab @ ab + 1e-9), 0, 1)
            d = np.hypot(px - (a[0] + t * ab[0]), py - (a[1] + t * ab[1]))
            c = np.clip(r - d + 0.5, 0, 1)
            sub = cov[lo_y:hi_y, lo_x:hi_x]
            np.maximum(sub, c, out=sub)
        return cov

    body = coverage(Q, width)
    shadow = cv2.GaussianBlur(coverage(Q + sh_off, width * 1.1), (0, 0), 1.3)
    hl = coverage(Q + ldir * (width[:, None] * 0.22), width * 0.32)
    vis = 1.0 - hero_mask[y0:y1, x0:x1]
    roi = img[y0:y1, x0:x1].copy()
    a_sh = (shadow * P["thread_shadow_alpha"] * vis)[..., None]
    roi = roi * (1 - a_sh * 0.55)
    if P["thread_glow"] > 0:
        glow = cv2.GaussianBlur(body, (0, 0), 6.0) * P["thread_glow"] * vis
        roi = roi + glow[..., None] * np.array([0.85, 0.12, 0.10], np.float32)
    col = np.array(P["thread_rgb"], np.float32) / 255.0
    # shade along the body: slightly darker rim
    a_b = (body * vis)[..., None]
    roi = roi * (1 - a_b) + col * a_b
    a_h = (hl * vis * 0.38)[..., None]
    roi = roi * (1 - a_h) + np.array([1.0, 0.62, 0.55], np.float32) * a_h
    if P.get("thread_glints", 0) > 0:
        # tiny star-like glints at random points along the visible thread, re-picked every drawing
        k = int(P["thread_glints"])
        lim = max(2, min(len(Q) - 1, last))
        for _ in range(k):
            i = int(rng.integers(0, lim))
            gx_, gy_ = Q[i] + rng.normal(0, 2.0, 2)
            ix, iy = int(gx_) - x0, int(gy_) - y0
            if 2 <= ix < bw - 3 and 2 <= iy < bh - 3 and vis[iy, ix] > 0.5:
                a_ = rng.uniform(0.5, 1.0)
                roi[iy, ix - 2:ix + 3] = roi[iy, ix - 2:ix + 3] * (1 - 0.5 * a_) + 0.5 * a_ * np.array([0.9, 0.95, 1.0], np.float32)
                roi[iy - 2:iy + 3, ix] = roi[iy - 2:iy + 3, ix] * (1 - 0.5 * a_) + 0.5 * a_ * np.array([0.9, 0.95, 1.0], np.float32)
                roi[iy, ix] = np.array([1.0, 1.0, 1.0], np.float32)
    img[y0:y1, x0:x1] = roi
    return img


# ---------------------------------------------------------------- per drawing
def process(job):
    sdir, f, drawing, first, P, meta, out_path = job
    t0 = time.time()
    rng = np.random.default_rng((P["seed"] + 1) * 100003 + drawing * 7919)
    cp = None
    for ext in ("jpg", "png"):
        q = os.path.join(sdir, "clean", f"f{f:04d}.{ext}")
        if os.path.exists(q):
            cp = q
            break
    if cp is None:
        q = os.path.join(sdir, f"f{f:04d}.png")
        cp = q if os.path.exists(q) else None
    if cp is None:
        return f, "missing"
    bgr = cv2.imread(cp, cv2.IMREAD_COLOR)
    img = bgr[..., ::-1].astype(np.float32) / 255.0
    if img.shape[:2] != (H, W):
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_CUBIC)
    # hero mask
    hp = os.path.join(sdir, "aux", f"hero_{f:04d}.png")
    if os.path.exists(hp):
        hm = cv2.imread(hp, cv2.IMREAD_UNCHANGED).astype(np.float32)
        hm = hm[..., 0] if hm.ndim == 3 else hm
        hm = cv2.resize(hm / (65535.0 if hm.max() > 255 else 255.0), (W, H), interpolation=cv2.INTER_LINEAR)
        hard = (hm > 0.5).astype(np.float32)
    else:
        hard = np.zeros((H, W), np.float32)
    hero = cv2.GaussianBlur(cv2.dilate(hard, np.ones((7, 7), np.uint8)), (0, 0), 3.0)
    cam = meta["cams"].get(str(f), meta["cams"].get(f))
    ppm = cam["ppm"]
    pp = os.path.join(sdir, "aux", f"pos_{f:04d}.png")
    if os.path.exists(pp):
        wx, wy, wz = surface_coords(cv2.imread(pp, cv2.IMREAD_UNCHANGED), (cam["x"], cam["y"]), ppm)
    else:
        wx, wy, wz = ground_coords((cam["x"], cam["y"]), ppm)
    lum0 = float((img @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean())
    gray = img @ np.array([0.299, 0.587, 0.114], np.float32)
    J = orientation(gray)
    # coarse strokes
    out, cov = paint_layer(img, wx, wy, wz, ppm, P["stroke_px"], P, drawing, hero, J, layer_seed=0)
    # fine strokes where the coarse painting lost detail (Hertzmann-style error threshold)
    err = cv2.blur(np.abs(out - img).mean(2), (9, 9))

    def sel(sx, sy, inv, cnt):
        e = np.bincount(inv, err.ravel(), len(cnt)) / cnt
        return e > P["fine_err"]
    out2, cov2 = paint_layer(out, wx, wy, wz, ppm, P["fine_px"], dict(P, repaint=min(0.85, P["repaint"] + 0.15)), drawing,
                             hero, J, select=sel, layer_seed=1, fine=True)
    # fine strokes repaint from the source colours (not from the coarse layer)
    blend = cov2[..., None].astype(np.float32)
    out = out * (1 - blend) + out2 * blend
    # boil
    amp = 0.0 if first else P["boil_mean"]
    fine = P.get("boil_mode", "fine") == "fine"
    if (fine and not first and P["boil_scale"] > 0) or (not fine and (amp > 0 or P["wobble"] > 0)):
        if fine:
            dx, dy = boil_field_fine(H, W, rng, out.mean(2), hero, P["boil_scale"])
        else:
            dx, dy = boil_field(H, W, rng, amp, P["wobble"] if not first else 0.0)
            k = 1.0 - (1.0 - P["boil_hero"]) * hero
            dx *= k
            dy *= k
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        mx, my = xx + dx, yy + dy
        out = cv2.remap(out, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        hard_w = cv2.remap(hard, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    else:
        hard_w = hard
    # thread(s)
    th = meta.get("_thread")
    if th is not None:
        for owner in th:
            idx = owner["index"].get(f)
            if idx is None:
                continue
            pts = owner["pts"][idx]
            hgt = owner["hgt"][idx]
            occl = cv2.GaussianBlur(hard_w, (0, 0), 0.7)
            out = draw_thread(out, pts, hgt, P, occl, rng, P["light_deg"])
    # canvas + impasto (screen-fixed) and grain
    weave, imp = canvas_tex(P["light_deg"])
    out = out * (1.0 + P["canvas"] * weave[..., None] + P["impasto"] * imp[..., None])
    if P["grain"] > 0:
        g = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
        g = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR) * (P["grain"] / 255.0)
        out = out + g[..., None]
    if P["lum_lock"]:
        lum1 = float((np.clip(out, 0, 1) @ np.array([0.2126, 0.7152, 0.0722], np.float32)).mean())
        out = out * (lum0 / max(lum1, 1e-4))
    res = np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8)[..., ::-1]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, res, [cv2.IMWRITE_JPEG_QUALITY, 96, cv2.IMWRITE_JPEG_SAMPLING_FACTOR, cv2.IMWRITE_JPEG_SAMPLING_FACTOR_444])
    return f, round(time.time() - t0, 2)


_META = None


def _init(meta):
    global _META
    _META = meta


def _run(job):
    sdir, f, drawing, first, P, out_path = job
    return process((sdir, f, drawing, first, P, _META, out_path))


def load_meta(sdir, scene, P):
    mp = os.path.join(sdir, "meta.json")
    meta = json.load(open(mp)) if os.path.exists(mp) else {}
    if "cams" not in meta:
        # fallback (v2 renders): camera from the measured speed profile and the scene ppm
        sys.path.insert(0, "blender")
        from kit import rope_cfg as C
        prof = json.load(open("work/cam_profile.json"))[str(scene)]
        a, b = CUTS[scene - 1], CUTS[scene]
        ppm = C.PPM[scene]
        ys = np.concatenate([[0.0], np.cumsum([prof[min(i, len(prof) - 1)] for i in range(b - a + 1)])]) / ppm
        meta["cams"] = {str(f): dict(x=0.0, y=float(ys[f - a]), ppm=ppm) for f in range(a, b)}
    tp = os.path.join(sdir, "thread.npz")
    if os.path.exists(tp):
        z = np.load(tp, allow_pickle=True)
        owners = []
        for name in z["owners"]:
            fr = z[f"{name}_frames"]
            owners.append(dict(name=str(name), index={int(x): i for i, x in enumerate(fr)}, pts=z[f"{name}_pts"], hgt=z[f"{name}_hgt"]))
        meta["_thread"] = owners
    post = dict(DEFAULT)
    post.update(meta.get("post", {}))
    post.update(P)
    return meta, post


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", type=int, required=True)
    ap.add_argument("--dir", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--frames", default="")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--set", default="", help="k=v,k=v post overrides")
    o = ap.parse_args()
    s = o.scene
    sdir = o.dir or f"render/v4/scene_{s:02d}"
    odir = o.out or os.path.join(sdir, "paint")
    over = {}
    for kv in filter(None, o.set.split(",")):
        k, v = kv.split("=")
        if isinstance(DEFAULT[k], str):
            over[k] = v
        else:
            over[k] = type(DEFAULT[k])(float(v)) if not isinstance(DEFAULT[k], tuple) else tuple(float(x) for x in v.split("/"))
    meta, P = load_meta(sdir, s, over)
    a, b = CUTS[s - 1], CUTS[s]
    lo, hi = a, b
    if o.frames:
        lo, hi = [int(x) for x in o.frames.split("-")]
        hi += 1
    jobs = []
    for f in range(a, b, 2):
        if not (lo <= f < hi):
            continue
        op = os.path.join(odir, f"f{f:04d}.jpg")
        if os.path.exists(op) and not o.force:
            continue
        jobs.append((sdir, f, (f - a) // 2 + s * 1000, f == a, P, op))
    t0 = time.time()
    canvas_tex(P["light_deg"])
    if o.jobs <= 1 or len(jobs) <= 1:
        _init(meta)
        for j in jobs:
            print(_run(j), flush=True)
    else:
        from multiprocessing import Pool
        with Pool(o.jobs, initializer=_init, initargs=(meta,)) as pool:
            for r in pool.imap_unordered(_run, jobs, chunksize=2):
                pass
    print(f"POST scene {s}: {len(jobs)} drawings in {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
