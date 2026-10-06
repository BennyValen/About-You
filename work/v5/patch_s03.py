p = "blender/scenes/s03.py"
s = open(p).read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


# keep handles to the flower instancers so they can ride on their pads
rep('''    geo.instances("lilies", fprotos, fl_pos, rot=np.c_[np.zeros(34), np.zeros(34), rng.uniform(0, 6.28, 34)],
                  scl=np.repeat(rng.uniform(0.8, 1.3, 34)[:, None], 3, 1), variant=fl_var, tint=rng.random(34), coll=env)
    geo.instances("lily_centres", fprotos, fl_pos[:24] + np.array([0, 0, 0.0]), variant=np.full(24, 4), coll=env)''',
    '''    lilies_obj = geo.instances("lilies", fprotos, fl_pos, rot=np.c_[np.zeros(34), np.zeros(34), rng.uniform(0, 6.28, 34)],
                               scl=np.repeat(rng.uniform(0.8, 1.3, 34)[:, None], 3, 1), variant=fl_var, tint=rng.random(34), coll=env)
    centres_obj = geo.instances("lily_centres", fprotos, fl_pos[:24] + np.array([0, 0, 0.0]), variant=np.full(24, 4), coll=env)''')

# after the boat and its oars exist: relax the pads, assign the stacking order, plan their (rigid) motion
rep('''    st = look.freestyle(ink, thickness=1.8, res_scale=opt.scale)''', '''    # ---------------------------------------------------------------- v5: lily pads never phase through each other
    # 1) deterministic position-based relaxation (no RNG; the scene RNG sequence is untouched): overlap depth at most
    #    22 % of the smaller pad's radius; pads kept clear of the boat's swept corridor (hull + 40 px each side) and of
    #    every oar-blade position of the shot. 2) a fixed integer layer index per pad (seeded permutation) turned into
    #    stacking levels so an upper pad always sits higher (4.8 cm per level -> a 4 px cast contact shadow at this sun).
    # 3) pads are fixed in the world apart from a shared 1 px/s water drift and a tiny bob (yaw <= 0.8 deg, <= 0.5 px,
    #    a spatially smooth phase so overlapping neighbours move together); no per-pad pushes or tilts.
    boat_x = rig.screen_to_world(start, *BOAT_SCREEN, 0.0)[0]
    HALF_CORR = 1.25 / 2 + 40.0 / PPM
    blade_pts = []
    for t_ in range(start - 30, end + 2, 2):
        M_ = boat_matrix(t_)
        _, inf_ = boats.row_pose(psi_of(t_), seat_pos, lock_l, lock_r)
        for s_ in ("l", "r"):
            q_ = M_ @ Vector(inf_[s_]["blade"].tolist())
            blade_pts.append((q_.x, q_.y))
    blade_pts = np.array(blade_pts)
    BLADE_R = 0.22
    XY = P[:, :2].copy()
    Rr = P[:, 2].copy()
    for it in range(240):
        d_ = XY[:, None, :] - XY[None, :, :]
        dist = np.sqrt((d_ ** 2).sum(-1)) + np.eye(len(XY)) * 1e9
        allow = 0.22 * np.minimum(Rr[:, None], Rr[None, :])
        excess = (Rr[:, None] + Rr[None, :] - dist) - allow
        mov = np.zeros_like(XY)
        m_ = excess > 1e-4
        if m_.any():
            w_ = np.where(m_, excess / 2.0 / dist, 0.0)
            mov += (d_ * w_[..., None]).sum(1)
        # boat corridor (the boat runs straight up the frame at boat_x) and oar blades
        gap = np.abs(XY[:, 0] - boat_x) - (HALF_CORR + Rr)
        out_ = gap < 0
        mov[out_, 0] += np.sign(XY[out_, 0] - boat_x + 1e-9) * (-gap[out_])
        db = XY[:, None, :] - blade_pts[None, :, :]
        dd = np.sqrt((db ** 2).sum(-1)) + 1e-9
        pen = (Rr[:, None] + BLADE_R) - dd
        pm = pen > 0
        if pm.any():
            k_ = np.argmax(np.where(pm, pen, -1), axis=1)
            sel = pm.any(1)
            dv = db[sel, k_[sel]] / dd[sel, k_[sel]][:, None]
            mov[sel] += dv * pen[sel, k_[sel]][:, None]
        XY += mov * (1.0 if it < 200 else 1.05)
        if it >= 60 and not m_.any() and not out_.any() and not pm.any():
            break
    pad_iters = it + 1
    lr_ = np.random.default_rng(3031)
    pad_layer = lr_.permutation(len(XY))                    # fixed integer z-order index per pad
    d_ = XY[:, None, :] - XY[None, :, :]
    dist = np.sqrt((d_ ** 2).sum(-1)) + np.eye(len(XY)) * 1e9
    ovl = (Rr[:, None] + Rr[None, :] - dist) > 0
    level = np.zeros(len(XY), int)
    for j in np.argsort(pad_layer):
        below = np.nonzero(ovl[j] & (pad_layer < pad_layer[j]))[0]
        if len(below):
            level[j] = level[below].max() + 1
    DZ = 0.048
    pad_z = 0.01 + level * DZ
    pad_bob_ph = 2 * math.pi * (0.021 * XY[:, 0] + 0.017 * XY[:, 1])     # neighbours ~2 m apart differ by < 15 deg
    DRIFT = np.array([0.0, -1.0 / 24.0 / PPM])                           # shared water drift, 1 px/s down the frame
    BOB_DIR = np.array([0.6, 0.8])

    def pad_state(d):
        t_ = d - start
        ph = 2 * math.pi * t_ / 150.0 + pad_bob_ph
        xy = XY + DRIFT * t_ + np.outer(np.sin(ph), BOB_DIR) * (0.5 / PPM)
        z = pad_z + 0.004 * np.sin(ph + 0.7)
        yaw = pad_rot[:, 2] + math.radians(0.8) * np.sin(ph + 1.9)
        return xy, z, yaw
    # flowers ride on their pads (same offset, on top of that pad's level)
    fl_off = fl_pos[:, :2] - P[picks, :2]
    fl_off *= np.minimum(1.0, 0.55 / (np.linalg.norm(fl_off, axis=1) / P[picks, 2] + 1e-9))[:, None]
    PAD_LOG = dict(n=int(len(XY)), iters=int(pad_iters), x=XY[:, 0].round(4).tolist(), y=XY[:, 1].round(4).tolist(),
                   r=Rr.round(4).tolist(), layer=pad_layer.tolist(), level=level.tolist(), z=pad_z.round(4).tolist(),
                   ph=pad_bob_ph.round(5).tolist(), ppm=PPM, start=start, end=end)

    st = look.freestyle(ink, thickness=1.8, res_scale=opt.scale)''')
rep('''        # pads near the boat are pushed aside by the bow wave and bob in the wake, then drift back
        bo = boat.matrix_world.translation
        dy = P[:, 1] - bo.y
        dx = P[:, 0] - bo.x
        env_ = np.exp(-np.maximum(dy - 1.2, 0) ** 2 / 0.6) * np.exp(-np.maximum(-dy - 1.0, 0) / 3.5) * (dy > -12)
        prox = np.exp(-np.maximum(np.abs(dx) - 0.9 - P[:, 2], 0) / 0.5)
        push = 0.28 * env_ * prox
        pos = np.c_[P[:, 0] + np.sign(dx) * push, P[:, 1] - 0.05 * push, P[:, 3] + 0.012 * env_ * prox * np.sin(d * 0.35 + pad_ph)]
        rot = pad_rot.copy()
        rot[:, 0] = 0.03 * env_ * prox * np.sin(d * 0.3 + pad_ph)
        rot[:, 1] = 0.03 * env_ * prox * np.cos(d * 0.27 + pad_ph)
        geo.update_points(pads_obj, pos, rot=rot)''', '''        # v5: pads rigid in the world (shared drift + tiny coherent bob), fixed stacking levels
        pxy, pz, pyaw = pad_state(d)
        rot = pad_rot.copy()
        rot[:, 2] = pyaw
        geo.update_points(pads_obj, np.c_[pxy, pz], rot=rot)
        fxy = pxy[picks] + fl_off
        fz = pz[picks] + 0.09
        geo.update_points(lilies_obj, np.c_[fxy, fz])
        geo.update_points(centres_obj, np.c_[fxy[:24], fz[:24]])''')
rep('''    log = []

    def update(f):''', '''    log = []

    def update(f):''')
# write the pad table for the gate
i0 = s.rindex("    r.finish")
line_end = s.index("\n", i0)
fin_line = s[i0:line_end]
s = s[:i0] + '''    _fin0 = ''' + fin_line.split("=", 1)[1].strip() + '''

    def finish(out):
        _fin0(out)
        json.dump(PAD_LOG, open(os.path.join(out, "pads.json"), "w"))
    r.finish = finish''' + s[line_end:]
open(p, "w").write(s)
print("s03 patched")
