p = "blender/scenes/s12.py"
s = open(p).read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


# ---------------------------------------------------------------- A: runner (dark shoes, smaller feet)
rep('''    A = human.Human("A", mats("A", "#4d55a6", "#757a99", "#2e2220"), hair="short", height=1.95, coll=ink,
                    bulk={"top": 1.45, "legs": 1.15, "hands": 1.25})''',
    '''    A = human.Human("A", mats("A", "#4d55a6", "#757a99", "#2e2220", shoes="#2a2630"), hair="short", height=1.95, coll=ink,
                    bulk={"top": 1.45, "legs": 1.15, "hands": 1.25, "shoes": 0.65})''')
rep('''    wa = human.Walker(pa_pos, pa.heading, start - 140, end + 20, height=1.95, ground=gnd, arm_swing=0.5)''',
    '''    # v5: A runs (stride = clamp(speed / 3 steps/s, 46, 60) px, two flight phases per cycle) until the meeting point,
    # then slows to a walk over 1 s (3930 -> 3954) and is still walking when the film ends
    RUN_END0, RUN_END1 = 3930, 3954

    def run_amt(t):
        u = min(max((t - RUN_END0) / (RUN_END1 - RUN_END0), 0.0), 1.0)
        return 1.0 - u * u * (3 - 2 * u)
    wa = human.Runner(pa_pos, pa.heading, start - 140, end + 20, height=1.95, ground=gnd, ppm=PPM, run=run_amt)''')
# footprints: A's own small prints (10 x 6 px, 25 %, fading after 6 s) in their own object; B's unchanged
rep('''    prints = plants_of(wa, start - 140, end) + [p for p in plants_of(wb, B_START - 30, end) if p[0] >= B_START - 30]''',
    '''    prints = [p for p in plants_of(wb, B_START - 30, end) if p[0] >= B_START - 30]''')
rep('''    fp_obj = geo.instances("footprints", fprotos, np.tile(far, (nfp, 1)), rot=np.c_[np.zeros(nfp), np.zeros(nfp), prints[:, 4]],
                           variant=np.zeros(nfp, int), coll=env)''',
    '''    fp_obj = geo.instances("footprints", fprotos, np.tile(far, (nfp, 1)), rot=np.c_[np.zeros(nfp), np.zeros(nfp), prints[:, 4]],
                           variant=np.zeros(nfp, int), coll=env)
    fpa_mat = look.cel("footprint_a", core.hexc("#8a74a2"), shadow=(0.7, 0.62, 0.82, 1), paint=0.0, soft=0.3, alpha=0.5, ao=0.0)
    ga_ = [n for n in fpa_mat.node_tree.nodes if n.type == "GROUP"][0]
    ia_ = _n(fpa_mat.node_tree, "ShaderNodeAttribute", (-400, -500), attribute_type="INSTANCER", attribute_name="tint")
    _l(fpa_mat.node_tree, _math(fpa_mat.node_tree, "MULTIPLY", fp_alpha(fpa_mat.node_tree), ia_.outputs["Fac"], (0, -400)), ga_.inputs["Alpha"])
    fpa_protos = geo.proto_collection("P_foot_a")
    fpa = footprint_proto("fpa", fpa_mat, fpa_protos)
    for v_ in fpa.data.vertices:                     # 0.06 x 0.078 m -> about 8 x 10 px
        v_.co.x *= 0.6
        v_.co.y *= 0.31
    a_prints = np.array(wa.plants(start - 140, end))
    nfa = len(a_prints)
    fpa_obj = geo.instances("footprints_a", fpa_protos, np.tile(far, (nfa, 1)),
                            rot=np.c_[np.zeros(nfa), np.zeros(nfa), a_prints[:, 4]], tint=np.zeros(nfa), coll=env)
    # dust at every foot strike: 4 sand-coloured specks, 40 % opacity, 0.4 s, spreading 4 -> 10 px
    dust_m = look.cel("dust", core.hexc("#ecd8c4"), paint=0.0, soft=0.4, alpha=0.5, ao=0.0)
    gd_ = [n for n in dust_m.node_tree.nodes if n.type == "GROUP"][0]
    id_ = _n(dust_m.node_tree, "ShaderNodeAttribute", (-400, -300), attribute_type="INSTANCER", attribute_name="tint")
    _l(dust_m.node_tree, id_.outputs["Fac"], gd_.inputs["Alpha"])
    dprot = geo.proto_collection("P_dust")
    import bmesh as _bm
    bm_ = _bm.new()
    _bm.ops.create_icosphere(bm_, subdivisions=1, radius=0.012)
    geo.bm_to_object(bm_, "speck", dust_m, dprot)
    ND = 4
    nd = nfa * ND
    drng = np.random.default_rng(1203)
    d_ang = drng.uniform(0, 2 * math.pi, nd)
    d_rad = drng.uniform(0.7, 1.0, nd)
    dust_obj = geo.instances("dust", dprot, np.tile(far, (nd, 1)), tint=np.zeros(nd), coll=env)
    for o_ in (fpa_obj, dust_obj):
        o_.visible_shadow = False''')
rep('''        pos[on] = prints[on, 1:4] + np.array([0, 0, 0.004])
        geo.update_points(fp_obj, pos)''', '''        pos[on] = prints[on, 1:4] + np.array([0, 0, 0.004])
        geo.update_points(fp_obj, pos)
        # A's prints: appear at the landing, 25 % opacity, fade out over 1 s after 6 s
        age = (d - a_prints[:, 0]) / 24.0
        on = age >= 0
        pa_ = np.tile(far, (nfa, 1))
        pa_[on] = a_prints[on, 1:4] + np.array([0, 0, 0.004])
        ta_ = np.where(on, 0.25 * np.clip(7.0 - age, 0.0, 1.0), 0.0)
        me_ = fpa_obj.data
        me_.vertices.foreach_set("co", pa_.astype(np.float32).ravel())
        me_.attributes["tint"].data.foreach_set("value", ta_.astype(np.float32))
        me_.update()
        # dust
        ag = np.repeat(age, ND)
        live = (ag >= 0) & (ag < 0.4)
        u_ = np.clip(ag / 0.4, 0, 1)
        r_px = (4.0 + 6.0 * u_) * d_rad
        P_ = np.tile(far, (nd, 1))
        base_ = np.repeat(a_prints[:, 1:4], ND, axis=0)
        P_[live] = base_[live] + np.c_[np.cos(d_ang[live]) * r_px[live] / PPM, np.sin(d_ang[live]) * r_px[live] / PPM,
                                       0.02 + 0.03 * u_[live]]
        T_ = np.where(live, 0.4 * (1 - u_), 0.0)
        me_ = dust_obj.data
        me_.vertices.foreach_set("co", P_.astype(np.float32).ravel())
        me_.attributes["tint"].data.foreach_set("value", T_.astype(np.float32))
        me_.update()''')
# thread A: calmer sideways wind on the first ~120 px so the cord streams straight behind the runner
rep('''    rope_a = rope_io.Owner("A", SCENE, rig, anchor_of(wa), frames, trail=(0.0, -1.0), ground_fn=dh, warm=150, cfg_motion=False,
                           heading_fn=pa.heading)''', '''    def calm_near_runner(wind):
        def w(P, t):
            out = wind(P, t)
            dist = np.linalg.norm(P[:, :2] - P[0, :2], axis=1)
            k_ = np.clip(dist / 0.92, 0.0, 1.0) * 0.6 + 0.4          # 0.4 at the anchor -> 1.0 beyond ~120 px
            out[:, 0] *= k_
            return out
        return w
    rope_a = rope_io.Owner("A", SCENE, rig, anchor_of(wa), frames, trail=(0.0, -1.0), ground_fn=dh, warm=150, cfg_motion=False,
                           heading_fn=pa.heading, wind_wrap=calm_near_runner)''')

# ---------------------------------------------------------------- birds: six small gulls with flapping wing chains
i0 = s.index("    # ---------------------------------------------------------------- gulls")
i1 = s.index("    st = look.freestyle(ink")
s = s[:i0] + '''    # ---------------------------------------------------------------- birds (v5)
    # six small pale gulls in a loose group at the top left, present from the first drawing, flying up and a little left
    # at 55-80 px/s over the ground (the camera outruns them, so they drift down the left side and leave by the edge).
    # Each bird is one mesh: body, tail, and two 3-segment wing chains posed per drawing from a stylised 1.5 Hz beat
    # (8 drawings per cycle, desynchronised, +-6 %), flap-and-glide (4-6 beats, then 0.8-1.4 s gliding), bob, speed pulse.
    # Steering: slow wander, separation >= 28 px, cohesion, avoidance of A, B, threads and shrubs in screen space,
    # turn rate <= 12 deg/s. Shadows: a draped copy of the same pose, 17 px along the light direction, 25 %.
    gw = look.cel("gull", core.hexc("#f6f3ef"), shadow=(0.72, 0.68, 0.84, 1), paint=0.0, soft=0.2, hero=True)
    gt = look.cel("gull_tip", core.hexc("#55505e"), paint=0.0, hero=True)
    gshadow = look.emissive("gull_shadow", core.hexc("#6c5884"), 1.0, alpha=0.25)
    NB, BZ = 6, 2.2
    ppm_b = float(rig.ppm_at(BZ))
    ring = 16
    th_ = np.linspace(0, 2 * math.pi, ring, endpoint=False)
    body_xy = np.c_[0.022 * np.cos(th_), 0.05 * np.sin(th_)]
    body_xy[:, 1] *= np.where(body_xy[:, 1] > 0, 1.12, 1.0)
    tail_xy = np.array([(-0.007, -0.047), (0.007, -0.047), (0.015, -0.08), (-0.015, -0.08)])
    faces = [(0, 1 + i, 1 + (i + 1) % ring) for i in range(ring)] + [(20, 19, 18, 17)]
    for w0, flip in ((21, False), (28, True)):                   # all faces wound so the normals point up
        fw = [(w0, w0 + 1, w0 + 5, w0 + 4), (w0 + 1, w0 + 2, w0 + 6, w0 + 5), (w0 + 2, w0 + 3, w0 + 6)]
        faces += [tuple(reversed(q)) for q in fw] if flip else fw
    WL = (0.05, 0.045, 0.032)
    CH = (0.034, 0.03, 0.02)

    def bird_local(phi, g):
        """local vertices (35 x 3) for wing phase phi and glide blend g (0 flapping .. 1 gliding)"""
        th = np.array([0.75 * math.sin(phi), 0.45 * math.sin(phi - 0.7), 0.35 * math.sin(phi - 1.2)])
        sw = 0.35 * max(0.0, math.cos(phi)) * np.array([0.0, 0.6, 1.0])     # upstroke: outer wing swept back, folded
        th = th * (1 - g) + np.array([0.1, 0.04, -0.03]) * g
        sw = sw * (1 - g) + np.array([0.0, 0.03, 0.06]) * g
        V = np.zeros((35, 3))
        V[0] = (0, 0, 0.012)
        V[1:17, :2] = body_xy
        V[1:17, 2] = 0.01
        V[17:21, :2] = tail_xy
        V[17:21, 2] = 0.008
        for side, w0 in ((-1, 21), (1, 28)):
            J = np.array([side * 0.018, 0.012, 0.008])
            cum = 0.0
            pts = [J.copy()]
            for i in range(3):
                cum += th[i]
                d = np.array([side * math.cos(cum) * math.cos(sw[i]), -math.sin(sw[i]) * math.cos(cum), math.sin(cum)])
                J = J + d * WL[i]
                pts.append(J.copy())
            for i in range(4):
                V[w0 + i] = pts[i]
            for i in range(3):
                V[w0 + 4 + i] = pts[i] + np.array([0.0, -CH[i], 0.0])
        return V
    birds = []
    for i in range(NB):
        ob = geo.mesh_from_arrays(f"bird{i}", bird_local(0.0, 0.0), faces, ink, False, gw)
        ob.data.materials.append(gt)
        mi = np.zeros(len(faces), np.int32)
        mi[[ring + 1 + 2, ring + 1 + 5]] = 1                               # the tip feathers are dark
        ob.data.polygons.foreach_set("material_index", mi)
        ob.visible_shadow = False
        sh = geo.mesh_from_arrays(f"bird{i}_shadow", bird_local(0.0, 0.0), faces, env, False, gshadow)
        sh.visible_shadow = False
        birds.append((ob, sh))
    # flight simulation (world metres at the bird height; screen px via the rig)
    brng = np.random.default_rng(1207)
    START_PX = [(185, 205), (295, 150), (255, 305), (385, 245), (150, 370), (335, 400)]
    v_px = brng.uniform(66, 78, NB)                        # mean ground speed px/s
    hd_off = np.radians(brng.uniform(-12, 12, NB))
    f_hz = 1.5 * brng.uniform(0.94, 1.06, NB)
    ph0 = brng.uniform(0, 2 * math.pi, NB)
    wander_ph = brng.uniform(0, 2 * math.pi, (NB, 2))
    BASE_HD = math.radians(15.0)                           # up the frame and a little left
    LIGHT = np.array([-0.552, 0.834])                      # screen direction of the shadows (down-left)
    sim_frames = list(range(start - 72, end + 2))
    # obstacles in screen space
    shrub_xyz = shrub_pos.copy()
    shrub_r_px = np.full(len(shrub_pos), 1.0 * PPM)

    def scr(f, p):
        return np.array(rig.world_to_screen(max(f, start), p))
    pos = np.array([rig.screen_to_world(start, x, y, BZ)[:2] for x, y in START_PX])
    hd = BASE_HD + hd_off
    vel_m = v_px / 24.0 / PPM
    pos = pos - 72 * np.c_[-np.sin(hd), np.cos(hd)] * vel_m[:, None]   # fly in from where they were 3 s earlier
    phi = ph0.copy()
    # flap-and-glide schedule per bird
    state = ["flap"] * NB
    beats_left = brng.integers(4, 7, NB).astype(float)
    glide_left = np.zeros(NB)
    gblend = np.zeros(NB)
    btrack = {}
    for f in sim_frames:
        P_scr = np.array([scr(f, np.array([pos[i][0], pos[i][1], BZ])) for i in range(NB)])
        obs = []
        if f >= start:
            obs.append((scr(f, np.array(list(pa_pos(f)) + [1.0])), 70.0))
            if f >= B_START:
                obs.append((scr(f, np.array(list(pb_pos(f)) + [1.0])), 70.0))
            for q, rr in zip(shrub_xyz, shrub_r_px):
                obs.append((scr(f, q + np.array([0, 0, 1.0])), rr + 30.0))
            for rope_ in (rope_a, rope_b):
                fk = f - (f - start) % 2
                if fk in rope_.sim:
                    for q in rope_.sim[fk][::8]:
                        obs.append((scr(f, q), 28.0))
        for i in range(NB):
            t = f / 24.0
            want = BASE_HD + hd_off[i] + math.radians(8.0) * (math.sin(2 * math.pi * t / 7.3 + wander_ph[i, 0]) +
                                                               0.5 * math.sin(2 * math.pi * t / 11.0 + wander_ph[i, 1]))
            steer = np.zeros(2)
            for j in range(NB):
                if j != i:
                    dv = P_scr[i] - P_scr[j]
                    dd = np.linalg.norm(dv) + 1e-6
                    if dd < 60:
                        steer += dv / dd * (60 - dd) / 60 * 2.0
            cen = P_scr.mean(0)
            dc = np.linalg.norm(P_scr[i] - cen)
            if dc > 140:
                steer += (cen - P_scr[i]) / dc * min((dc - 140) / 110, 1.0)
            for q, rr in obs:
                dv = P_scr[i] - q
                dd = np.linalg.norm(dv) + 1e-6
                if dd < rr + 40:
                    steer += dv / dd * (rr + 40 - dd) / 40 * 3.0
            if np.linalg.norm(steer) > 1e-6:
                # screen -> world direction (screen y is down), then fold into the wanted heading
                sw_ = np.array([steer[0], -steer[1]])
                cur = np.array([-math.sin(hd[i]), math.cos(hd[i])])
                side = cur[0] * sw_[1] - cur[1] * sw_[0]
                want += math.radians(25.0) * math.tanh(side)
            dh_ = (want - hd[i] + math.pi) % (2 * math.pi) - math.pi
            hd[i] += max(-math.radians(0.5), min(math.radians(0.5), dh_))       # <= 12 deg/s
            # flap-and-glide
            if state[i] == "flap":
                before = phi[i]
                phi[i] += 2 * math.pi * f_hz[i] / 24.0
                if math.floor(phi[i] / (2 * math.pi)) > math.floor(before / (2 * math.pi)):
                    beats_left[i] -= 1
                    if beats_left[i] <= 0:
                        state[i] = "glide"
                        glide_left[i] = brng.uniform(0.8, 1.4) * 24
                gblend[i] = max(0.0, gblend[i] - 1 / 4.0)
            else:
                glide_left[i] -= 1
                gblend[i] = min(1.0, gblend[i] + 1 / 4.0)
                if glide_left[i] <= 0:
                    state[i] = "flap"
                    beats_left[i] = brng.integers(4, 7)
            pulse = 1.0 + 0.08 * math.sin(phi[i] - math.pi) * (1 - gblend[i])
            pos[i] = pos[i] + np.array([-math.sin(hd[i]), math.cos(hd[i])]) * vel_m[i] * pulse
        btrack[f] = (pos.copy(), hd.copy(), phi.copy(), gblend.copy())
    bird_log = []

    def pose_birds(f):
        P, H, PH, G = btrack[f]
        rec = []
        for i, (ob, sh) in enumerate(birds):
            V = bird_local(PH[i], G[i])
            bobs = 1.0 + 0.03 * math.cos(PH[i] - 1.5 * math.pi - 0.3) * (1 - G[i])
            c, s_ = math.cos(H[i]), math.sin(H[i])
            R2 = np.array([[c, -s_], [s_, c]])
            W = np.zeros_like(V)
            W[:, :2] = (V[:, :2] * bobs) @ R2.T + P[i]
            W[:, 2] = BZ + V[:, 2] * bobs + 0.02 * (bobs - 1.0) / 0.03
            ob.data.vertices.foreach_set("co", W.astype(np.float32).ravel())
            ob.data.update()
            # shadow: the same pose, 17 px down-left along the light on screen, draped on the dune
            Sx = np.array([scr(f, w) for w in W])
            Sx = Sx + LIGHT * (17.0 + 1.5 * (bobs - 1.0) / 0.03)
            SW = np.array([rig.screen_to_world(f, x, y, 0.0)[:2] for x, y in Sx])
            Z = dh(SW[:, 0], SW[:, 1]) + 0.006
            sh.data.vertices.foreach_set("co", np.c_[SW, Z].astype(np.float32).ravel())
            sh.data.update()
            tips = Sx - LIGHT * (17.0 + 1.5 * (bobs - 1.0) / 0.03)
            span = float(np.linalg.norm(tips[24] - tips[31]))
            ctr = scr(f, np.array([P[i][0], P[i][1], BZ]))
            rec.append([round(float(ctr[0]), 2), round(float(ctr[1]), 2), round(math.degrees(H[i]), 3), round(span, 2), round(float(G[i]), 2)])
        bird_log.append(dict(f=int(f), birds=rec))

''' + s[i1:]
rep('''        for g in gulls:
            t = d - start
            if g["early"]:
                cx, cy = 230 + g["off"][0] + 70 * math.sin(t * 0.02 * g["r"] + g["ph"]), 1350 + g["off"][1] + 40 * math.cos(t * 0.025 + g["ph"])
                cx -= t * 0.6
                cy += t * 1.2
            else:
                cx, cy = 150 + g["off"][0] + 50 * math.sin(t * 0.02 + g["ph"]), 150 + g["off"][1] + 30 * math.cos(t * 0.03 * g["r"])
            p = rig.screen_to_world(f, cx, cy, 2.2)
            heading = math.atan2(-1.0, 0.4) + 0.4 * math.sin(t * 0.03 + g["ph"])
            g["body"].location = (p[0], p[1], 2.2)
            g["body"].rotation_euler = (0, 0, heading)
            flap = 0.55 * math.sin(d * 0.55 + g["ph"])
            for w, side in zip(g["wings"], (-1, 1)):
                w.rotation_euler = (0, -side * flap, 0)
            vis = (t < 150) if g["early"] else (t > 120)
            for o in [g["body"]] + g["wings"]:
                o.hide_render = not vis''', '''        pose_birds(d)''')
# runner log for the gates
rep('''        for Hm, wk in ((A, wa), (B, wb)):
            Jw, hd, _ = wk.pose(d)
            Hm.set_world(Jw, hd)''', '''        for Hm, wk in ((A, wa), (B, wb)):
            Jw, hd, ph_ = wk.pose(d)
            Hm.set_world(Jw, hd)
            if wk is wa:
                sc_ = lambda q: np.array(rig.world_to_screen(d, q))
                fw_ = np.array([-math.sin(hd), -math.cos(hd)])
                c_ = sc_(Jw["pelvis"])
                lat_ = lambda q: float(fw_[0] * (sc_(q) - c_)[1] - fw_[1] * (sc_(q) - c_)[0])
                run_log.append(dict(f=int(d), pelvis=c_.round(2).tolist(), yaw=round(math.degrees(hd), 3), ph=round(ph_, 4),
                                    run=round(wa.run(d), 3), flight=round(wa.flight(d), 3),
                                    toe=[np.round(Jw["toe_l"], 4).tolist(), np.round(Jw["toe_r"], 4).tolist()],
                                    foot_lat=[round(lat_(Jw["toe_l"]), 2), round(lat_(Jw["toe_r"]), 2)],
                                    hand_lat=[round(lat_(Jw["hnd_l"]), 2), round(lat_(Jw["hnd_r"]), 2)],
                                    hand_fwd=[round(float(-(fw_ @ (sc_(Jw["hnd_l"]) - c_))), 2), round(float(-(fw_ @ (sc_(Jw["hnd_r"]) - c_))), 2)]))''')
rep('''    def update(f):
        rig.apply(f)''', '''    run_log = []

    def update(f):
        rig.apply(f)''')
rep('''    def finish(out):
        rope_io.export(out, [rope_a, rope_b])''', '''    def finish(out):
        rope_io.export(out, [rope_a, rope_b])
        json.dump(dict(log=run_log, plants=[[round(float(x), 4) for x in p_] for p_ in a_prints], ppm=PPM),
                  open(os.path.join(out, "runner_log.json"), "w"))
        json.dump(bird_log, open(os.path.join(out, "bird_log.json"), "w"))''')
open(p, "w").write(s)
print("s12 patched")
