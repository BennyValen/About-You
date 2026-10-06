p = "blender/scenes/s06.py"
s = open(p).read()


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:90])
    s = s.replace(a, b)


rep('''from kit import core, look, geo, human, boats, creatures, plants, rope_io''',
    '''from kit import core, look, geo, human, boats, creatures, plants, rope_io, swim''')
# manta: tilt shading attribute multiplies the approved colours (lighter when a wing is up, darker when down)
rep('''        return _mixrgb(nt, "MIX", edge.outputs["Result"], core.hexc("#3c4f63"), core.hexc("#6e8494"), (-200, 0))
    manta_m''', '''        col = _mixrgb(nt, "MIX", edge.outputs["Result"], core.hexc("#3c4f63"), core.hexc("#6e8494"), (-200, 0))
        tl = _n(nt, "ShaderNodeAttribute", (-400, -400), attribute_type="GEOMETRY", attribute_name="tilt")
        return look.mul_color(nt, col, _math(nt, "ADD", tl.outputs["Fac"], 1.0, (-250, -400)), (-100, 0))
    manta_m''')
rep('''    manta = creatures.Manta("manta", manta_m, span=4.0, coll=ink)''',
    '''    # v5: a swimming rig (same planform, size and colours): wing ribs flap at 0.45 Hz, two 1.2 s glides
    manta = swim.MantaRig("manta", manta_m, span=4.0, coll=ink, ppm=float(rig.ppm_at(-0.12)),
                          glides=[(start + int(5.5 * 24), 29), (start + int(15.0 * 24), 29)])''')
rep('''        tt = creatures.Turtle(f"turtle{i}", tm_shell, tm_skin, length=0.95, coll=ink)''',
    '''        tt = swim.TurtleRig(f"turtle{i}", tm_shell, tm_skin, length=0.95, coll=ink, ppm=float(rig.ppm), phase0=(0.0, 0.37, 0.71)[i])''')
# manta turns at most 18 deg/s (heading only; positions and every other creature path are unchanged)
rep('''            hd_state[c["id"]] += max(-0.02, min(0.02, dh))''', '''            lim = 0.0131 if c["id"] == "manta" else 0.02
            hd_state[c["id"]] += max(-lim, min(lim, dh))''')
# swim offsets along the track (speed pulses), heading lag for the turtles, wake dashes
rep('''    col_rows = []

    def log_colliders(f):''', '''    # v5: speed pulses as small offsets along the track (the steering paths stay the approved ones), turtle heading
    # following the velocity with a 0.3 s lag, and the manta / turtle positions actually drawn (logged as colliders)
    def hfun_of(cid):
        fr_ = np.array(sorted(head[cid]))
        hv = np.unwrap(np.array([head[cid][k] for k in fr_]))
        return lambda t: float(np.interp(t, fr_, hv))
    hfun = {c["id"]: hfun_of(c["id"]) for c in cre}
    adj = {}
    for c in cre:
        cid = c["id"]
        if not (cid == "manta" or cid.startswith("turtle")):
            continue
        adj[cid], lagged = {}, {}
        hl = None
        for fr in sorted(traj[cid]):
            h = hfun[cid](fr)
            hl = h if hl is None else hl + (h - hl) * (1 - math.exp(-1 / 7.2))
            lagged[fr] = hl
            prev = traj[cid].get(fr - 1, traj[cid][fr])
            vfr = float(np.linalg.norm(traj[cid][fr] - prev))
            if cid == "manta":
                ph = swim.MantaRig.FREQ * fr / 24.0
                off = 0.10 * vfr / (2 * math.pi * swim.MantaRig.FREQ / 24.0) * math.sin(2 * math.pi * (ph - 0.1)) * manta.amp_env(fr)
            else:
                k_ = int(cid[-1])
                cyc = (fr / swim.TurtleRig.PERIOD + (0.0, 0.37, 0.71)[k_]) % 1.0
                off = 0.45 * vfr / (2 * math.pi / swim.TurtleRig.PERIOD) * math.sin(2 * math.pi * (cyc - 0.2))
            fw = np.array([-math.sin(h), math.cos(h)])
            adj[cid][fr] = traj[cid][fr] + fw * off
        if cid.startswith("turtle"):
            head[cid + "_lag"] = lagged
    # turtle wake: 3 faint ripple dashes on the water behind each turtle at every stroke, fading over 1 s
    dash_m = look.emissive("turtle_wake", core.hexc("#eaf6f4"), 1.0, alpha=0.5)
    dprot = geo.proto_collection("P_dash")
    bm_ = bmesh.new()
    bmesh.ops.create_circle(bm_, cap_ends=True, segments=10, radius=1.0)
    bmesh.ops.scale(bm_, vec=(0.09, 0.025, 1.0), verts=bm_.verts)
    geo.bm_to_object(bm_, "dash", dash_m, dprot)
    for o_ in dprot.objects:
        o_.data.materials.clear()
        o_.data.materials.append(dash_m)
    dash_ev = []
    for i in range(len(turtles)):
        cid = f"turtle{i}"
        ph0 = (0.0, 0.37, 0.71)[i]
        k0 = math.floor((start - 40) / swim.TurtleRig.PERIOD + ph0)
        while True:
            t0 = (k0 - ph0) * swim.TurtleRig.PERIOD + 0.45 * swim.TurtleRig.PERIOD    # end of the power stroke
            if t0 > end:
                break
            fr0 = int(round(t0))
            if fr0 in adj[cid]:
                h = hfun[cid](fr0)
                fw = np.array([-math.sin(h), math.cos(h)])
                sd = np.array([fw[1], -fw[0]])
                for j, (bk, lt) in enumerate(((0.45, 0.06), (0.62, -0.05), (0.8, 0.03))):
                    q = adj[cid][fr0] - fw * bk + sd * lt
                    dash_ev.append((t0 + 2 * j, q[0], q[1], h))
            k0 += 1
    dash_ev = np.array(dash_ev)
    ND = len(dash_ev)
    dash_obj = geo.instances("turtle_wake", dprot, np.tile([0.0, -1e4, -50.0], (ND, 1)),
                             rot=np.c_[np.zeros(ND), np.zeros(ND), dash_ev[:, 3]], tint=np.zeros(ND), coll=env)
    dash_obj.visible_shadow = False
    dg_ = [n for n in dash_m.node_tree.nodes if n.type == "MIX_SHADER"]
    if dg_:
        ia_ = _n(dash_m.node_tree, "ShaderNodeAttribute", (-200, -300), attribute_type="INSTANCER", attribute_name="tint")
        _l(dash_m.node_tree, ia_.outputs["Fac"], dg_[0].inputs[0])
    col_rows = []

    def log_colliders(f):''')
rep('''        for c in cre:
            q = traj[c["id"]][f]
            add(c["id"], LAYER["creature"], q[0], q[1], c["R"], c["R"], 0.0)''', '''        for c in cre:
            q = adj[c["id"]][f] if c["id"] in adj else traj[c["id"]][f]
            add(c["id"], LAYER["creature"], q[0], q[1], c["R"], c["R"], 0.0)''')
rep('''        mq = traj["manta"][d]
        manta.obj.location = (mq[0], mq[1], -0.12)
        manta.obj.rotation_euler = (0, 0, head["manta"][d])
        manta.pose(d, amp=0.08)
        for i, (tt, tx, ty, vx, vy) in enumerate(turtles):
            t = d - start
            q = traj[f"turtle{i}"][d]
            tt.shell.location = (q[0], q[1], -float(depth(q[0], q[1])) + 0.35)
            tt.shell.rotation_euler = (0, 0, head[f"turtle{i}"][d])
            tt.pose(t)''', '''        mq = adj["manta"][d]
        turn = (hfun["manta"](d) - hfun["manta"](d - 2)) * 12.0
        hb = manta.pose(d, hfun["manta"], turn)
        manta.obj.location = (mq[0], mq[1], -0.12)
        manta.obj.rotation_euler = (0, 0, hb)
        for i, (tt, tx, ty, vx, vy) in enumerate(turtles):
            cid = f"turtle{i}"
            q = adj[cid][d]
            tr_ = (head[cid + "_lag"][d] - head[cid + "_lag"].get(d - 2, head[cid + "_lag"][d])) * 12.0
            yaw_off, _ = tt.pose(d, tr_)
            tt.shell.location = (q[0], q[1], -float(depth(q[0], q[1])) + 0.35)
            tt.shell.rotation_euler = (0, 0, head[cid + "_lag"][d] + yaw_off)
        age = (d - dash_ev[:, 0]) / 24.0
        live = (age >= 0) & (age < 1.0)
        Pd = np.tile([0.0, -1e4, -50.0], (ND, 1))
        Pd[live] = np.c_[dash_ev[live, 1], dash_ev[live, 2], np.full(int(live.sum()), 0.013)]
        Td = np.where(live, 0.18 * (1 - age), 0.0)
        Sd = np.repeat((1.0 + 0.6 * np.clip(age, 0, 1))[:, None], 3, 1)
        me_ = dash_obj.data
        me_.vertices.foreach_set("co", Pd.astype(np.float32).ravel())
        me_.attributes["tint"].data.foreach_set("value", Td.astype(np.float32))
        if "scl" in me_.attributes:
            me_.attributes["scl"].data.foreach_set("vector", Sd.astype(np.float32).ravel())
        me_.update()''')
rep('''        with open(os.path.join(out, "colliders.csv"), "w") as fh:
            fh.write("frame,id,layer,cx,cy,rx,ry,deg\\n")
            for row in col_rows:
                fh.write(row + "\\n")''', '''        with open(os.path.join(out, "colliders.csv"), "w") as fh:
            fh.write("frame,id,layer,cx,cy,rx,ry,deg\\n")
            for row in col_rows:
                fh.write(row + "\\n")
        json.dump(dict(manta=manta.log, turtles=[tt.log for tt, *_ in turtles]), open(os.path.join(out, "swim_log.json"), "w"))''')
open(p, "w").write(s)
print("s06 patched")
