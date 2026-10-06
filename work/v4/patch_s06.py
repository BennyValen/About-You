p = "blender/scenes/s06.py"
s = open(p).read()


def rep(a, b):
    global s
    assert a in s, a[:90]
    s = s.replace(a, b)


rep('''CHANNELS = [([(-9.0, 17.5), (-6.0, 18.6), (-3.33, 19.7), (-1.11, 21.7), (1.55, 23.3), (6.0, 24.8), (9.0, 25.4)], 0.95),
            ([(-9.0, 6.6), (-6.0, 6.17), (-2.89, 5.86), (0.22, 4.17), (2.89, 1.51), (6.0, -1.6), (9.0, -4.2)], 1.15)]''',
    '''CHANNELS = [([(-9.0, 17.5), (-6.0, 18.6), (-3.33, 19.7), (-1.11, 21.7), (1.55, 23.3), (6.0, 24.8), (9.0, 25.4)], 0.95),
            ([(-9.0, 6.6), (-6.0, 6.17), (-2.89, 5.86), (0.22, 4.17), (2.89, 1.51), (6.0, -1.6), (9.0, -4.2)], 1.15),
            # v4: the deep turquoise channel the boat sails along (straight course)
            ([(0.15, -14.0), (0.25, 0.0), (0.1, 12.0), (0.2, 24.0), (0.15, 36.0)], 0.9)]
BOAT_X = (555 - 540) / 90.0
LAYER = dict(floor=0, coral=1, creature=2, surface=3, boat=4, land=5)''')

# islands pushed clear of the boat's course (hull + 50 px on the left; hull + sail + 50 px on the right) and of each other
rep('''def speed_profile():''', '''def islands_v4(ylo=-8.0, yhi=26.0):
    out = []
    for cx, cy, r in CORALS:
        R = r * 1.45
        if ylo - R < cy < yhi + R:
            left = BOAT_X - (R + 0.7 + 0.56 + 0.15)
            right = BOAT_X + (R + 2.6 + 0.56 + 0.15)
            if left < cx < right:
                cx = left if cx < BOAT_X + 0.5 else right
        out.append([cx, cy, r])
    for _ in range(30):                                   # resolve island-island overlaps (rims at 1.45 r)
        moved = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                (xi, yi, ri), (xj, yj, rj) = out[i], out[j]
                dd = math.hypot(xi - xj, yi - yj)
                need = 1.45 * (ri + rj) + 0.1
                if dd < need:
                    k = max(0.6, dd / need)
                    out[i][2] *= k
                    out[j][2] *= k
                    moved = True
        if not moved:
            break
    return [tuple(v) for v in out]


def speed_profile():''')
rep('''    rng = np.random.default_rng(606)
    pts, scl, var, tint = [], [], [], []
    for cx, cy, r in CORALS:''', '''    rng = np.random.default_rng(606)
    ISL = islands_v4()
    pts, scl, var, tint = [], [], [], []
    for cx, cy, r in ISL:''')
rep('''    small = geo.poisson(rng, 60, x0, y0, x1, y1, 1.8, accept=lambda x, y: depth(x, y) < 0.9)
    for x, y in small:
        s = rng.uniform(0.18, 0.42)''', '''    def coral_ok(x, y):
        if depth(x, y) >= 0.9:
            return False
        if BOAT_X - (0.7 + 0.56 + 0.5) < x < BOAT_X + (2.6 + 0.56 + 0.5):     # clear of the course (hull + sail + 50 px)
            return False
        return all(math.hypot(x - cx, y - cy) > 1.45 * r + 0.6 for cx, cy, r in ISL)
    small = geo.poisson(rng, 60, x0, y0, x1, y1, 1.8, accept=coral_ok)
    CORAL_HEADS = []
    for x, y in small:
        s = rng.uniform(0.18, 0.42)
        CORAL_HEADS.append((x, y, s * 1.08))''')
rep('''    hp = np.array([(cx, cy, -float(depth(cx, cy)) + 0.015) for cx, cy, r in CORALS])
    hr = np.array([r * 1.45 for cx, cy, r in CORALS])''', '''    hp = np.array([(cx, cy, -float(depth(cx, cy)) + 0.015) for cx, cy, r in ISL])
    hr = np.array([r * 1.45 for cx, cy, r in ISL])''')
rep('''    pp = []
    for cx, cy, r in CORALS:''', '''    pp = []
    for cx, cy, r in ISL:''')
# manta: mask AOV, shallower wing wave
rep('''    manta = creatures.Manta("manta", look.cel("manta", core.hexc("#45586a"), shadow=(0.55, 0.6, 0.78, 1), high=(1.15, 1.15, 1.15, 1), paint=0.03,
                                              base_node=manta_base, soft=0.22, rim=0.3, hero=True), span=4.0, coll=ink)''',
    '''    manta_m = look.cel("manta", core.hexc("#45586a"), shadow=(0.55, 0.6, 0.78, 1), high=(1.15, 1.15, 1.15, 1), paint=0.03,
                       base_node=manta_base, soft=0.22, rim=0.3, hero=True)
    look.add_mask_aov(manta_m, "manta")
    manta = creatures.Manta("manta", manta_m, span=4.0, coll=ink)''')
# steering + colliders: inserted before the compositor
rep('''    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.99, 1.0, 1.01), gain=(1.02, 1.01, 0.99),
                         vignette=0.22, ink=0.4), res_scale=opt.scale)''', '''    # ---------------------------------------------------------------- v4: creatures steer around everything
    # creatures (layer 2) as conservative circles: manta (wings incl.), 3 turtles, 3 fish schools
    obstacles = [(cx, cy, 1.45 * r) for cx, cy, r in ISL] + list(CORAL_HEADS)
    BOAT_R = 1.9                                           # hull circle (the sail is above the water: not an obstacle below)
    cre = []
    mp0 = manta_path(start)
    cre.append(dict(id="manta", R=2.05, p=np.array([mp0[0], mp0[1]]), v=np.zeros(2), vmax=0.03, goal=lambda t: np.array(manta_path(t)[:2])))
    for i, (tx, ty, vx, vy) in enumerate(((3.6, 14.0, -0.004, 0.012), (-3.4, 3.0, 0.005, 0.016), (4.2, 26.0, -0.006, 0.01))):
        cre.append(dict(id=f"turtle{i}", R=0.62, p=np.array([tx, ty]), v=np.array([vx, vy]), vmax=0.022, base=np.array([vx, vy])))
    for k, (sx_, sy_, vx_, vy_) in enumerate(((-2.5, 9.0, 0.012, 0.02), (3.0, 20.0, -0.01, 0.014), (-1.0, 27.0, 0.008, 0.024))):
        cre.append(dict(id=f"school{k}", R=1.35, p=np.array([sx_, sy_]), v=np.array([vx_, vy_]), vmax=0.03, base=np.array([vx_, vy_])))
    traj = {c["id"]: {} for c in cre}
    head = {c["id"]: {} for c in cre}
    hd_state = {c["id"]: math.atan2(-c["v"][0], c["v"][1] + 1e-9) for c in cre}
    for fr in range(start - 30, end + 3):
        bp = np.array(boat_frame(fr)[:2])
        movers = [(c["p"][0], c["p"][1], c["R"]) for c in cre]
        for ci, c in enumerate(cre):
            if "goal" in c:
                want = np.clip((c["goal"](fr) - c["p"]) * 0.05, -c["vmax"], c["vmax"])
            else:
                want = c["base"]
            v = 0.9 * c["v"] + 0.1 * want
            obs = obstacles + [(bp[0], bp[1], BOAT_R)] + [m for j, m in enumerate(movers) if j != ci]
            for ox, oy, orr in obs:
                dvec = c["p"] - np.array([ox, oy])
                dist = math.hypot(*dvec) + 1e-6
                need = 1.2 * (c["R"] + orr)
                if dist < need * 1.5:
                    v = v + dvec / dist * (need * 1.5 - dist) / need * 0.03
            sp = math.hypot(*v)
            if sp > c["vmax"]:
                v = v / sp * c["vmax"]
            c["v"] = v
            c["p"] = c["p"] + v
            # hard projection: never overlap anything (touching tolerance 2 cm)
            for _ in range(3):
                for ox, oy, orr in obs:
                    dvec = c["p"] - np.array([ox, oy])
                    dist = math.hypot(*dvec) + 1e-9
                    if dist < c["R"] + orr + 0.02:
                        c["p"] = np.array([ox, oy]) + dvec / dist * (c["R"] + orr + 0.02)
            want_h = math.atan2(-c["v"][0], c["v"][1] + 1e-9)
            dh = (want_h - hd_state[c["id"]] + math.pi) % (2 * math.pi) - math.pi
            hd_state[c["id"]] += max(-0.02, min(0.02, dh))
            traj[c["id"]][fr] = c["p"].copy()
            head[c["id"]][fr] = hd_state[c["id"]]
    col_rows = []

    def log_colliders(f):
        ppm_ = rig.ppm
        def add(id_, layer, x, y, rx, ry, deg):
            sx_, sy_ = rig.world_to_screen(f, (x, y, 0.0))
            if -300 < sx_ < 1380 and -300 < sy_ < 2220:
                col_rows.append(f"{f},{id_},{layer},{sx_:.1f},{sy_:.1f},{rx * ppm_:.1f},{ry * ppm_:.1f},{deg:.1f}")
        for i, (cx, cy, r) in enumerate(ISL):
            add(f"island{i}", LAYER["land"], cx, cy, 1.45 * r, 1.45 * r, 0.0)
        for i, (cx, cy, r) in enumerate(CORAL_HEADS):
            add(f"coral{i}", LAYER["coral"], cx, cy, r, r, 0.0)
        for c in cre:
            q = traj[c["id"]][f]
            add(c["id"], LAYER["creature"], q[0], q[1], c["R"], c["R"], 0.0)
        bp = boat_frame(f)
        add("boat", LAYER["boat"], bp[0], bp[1], 0.68, 1.72, 0.0)

    look.compositor(dict(kuwahara=3, bloom=0.35, bloom_threshold=0.95, streak=0.06, lift=(0.99, 1.0, 1.01), gain=(1.02, 1.01, 0.99),
                         vignette=0.22, ink=0.4), res_scale=opt.scale)
    look.register_mask_output("manta")''')
rep('''        mp = manta_path(d)
        manta.obj.location = (mp[0], mp[1], -0.22)
        manta.obj.rotation_euler = (0, 0, 0.25 + 0.08 * math.sin(d / 40.0))
        manta.pose(d)
        for tt, tx, ty, vx, vy in turtles:
            t = d - start
            tt.shell.location = (tx + vx * t * 24 / 24, ty + vy * t, -float(depth(tx + vx * t, ty + vy * t)) + 0.35)
            tt.shell.rotation_euler = (0, 0, math.atan2(-vx, vy))
            tt.pose(t)''', '''        mq = traj["manta"][d]
        manta.obj.location = (mq[0], mq[1], -0.12)
        manta.obj.rotation_euler = (0, 0, head["manta"][d])
        manta.pose(d, amp=0.08)
        for i, (tt, tx, ty, vx, vy) in enumerate(turtles):
            t = d - start
            q = traj[f"turtle{i}"][d]
            tt.shell.location = (q[0], q[1], -float(depth(q[0], q[1])) + 0.35)
            tt.shell.rotation_euler = (0, 0, head[f"turtle{i}"][d])
            tt.pose(t)
        log_colliders(f)''')
rep('''        for ob_, sx_, sy_, vx_, vy_, offs, ph in schools:
            cx, cy = sx_ + vx_ * t_ + 0.4 * math.sin(t_ * 0.02), sy_ + vy_ * t_
            heading = math.atan2(-(vx_ + 0.008 * math.cos(t_ * 0.02)), vy_)''', '''        for k_, (ob_, sx_, sy_, vx_, vy_, offs, ph) in enumerate(schools):
            cx, cy = traj[f"school{k_}"][d]
            heading = head[f"school{k_}"][d]''')
rep('''    r.finish = lambda out: rope_io.export(out, [rope])
    return r''', '''    def finish(out):
        rope_io.export(out, [rope])
        with open(os.path.join(out, "colliders.csv"), "w") as fh:
            fh.write("frame,id,layer,cx,cy,rx,ry,deg\\n")
            for row in col_rows:
                fh.write(row + "\\n")
    r.finish = finish
    return r''')
# school fish stay within the school circle (offsets bounded)
rep('''        offs = rng.normal(0, 1, (NF, 2)) * np.array([0.55, 0.35])''', '''        offs = np.clip(rng.normal(0, 1, (NF, 2)) * np.array([0.5, 0.32]), -1.0, 1.0)''')
open(p, "w").write(s)
print("s06 patched")
