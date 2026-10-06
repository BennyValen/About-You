import re


def patch(p, pairs):
    s = open(p).read()
    for a, b in pairs:
        assert a in s, (p, a[:70])
        s = s.replace(a, b)
    open(p, "w").write(s)
    print("patched", p)


# scene 3: boat travels straight (yaw from the old weave is zero now); log heading
patch("blender/scenes/s03.py", [
    ('''    rope = rope_io.Owner("A", SCENE, rig, stern, frames, trail=(0.0, -1.0), warm=150, cfg_motion=False)''',
     '''    rope = rope_io.Owner("A", SCENE, rig, stern, frames, trail=(0.0, -1.0), warm=150, cfg_motion=False,
                         heading_fn=lambda t: boat_matrix(t).to_euler().z)'''),
])
# scene 5: heading straight; log it
patch("blender/scenes/s05.py", [
    ('''    heading = lambda t: -0.25 * (mot(t + 1)[0] - mot(t - 1)[0]) * PPM / 2.88''', '''    heading = lambda t: 0.0'''),
    ('''    rope = rope_io.Owner("A", SCENE, rig, walk.cantle, frames, trail=(0.0, -1.0), ground_fn=hg, warm=150, cfg_motion=False)''',
     '''    rope = rope_io.Owner("A", SCENE, rig, walk.cantle, frames, trail=(0.0, -1.0), ground_fn=hg, warm=150, cfg_motion=False,
                         heading_fn=heading)'''),
])
# scene 6: steady course
patch("blender/scenes/s06.py", [
    ('''    rope = rope_io.Owner("A", SCENE, rig, stern, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False)''',
     '''    rope = rope_io.Owner("A", SCENE, rig, stern, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,
                         heading_fn=lambda t: boat_matrix(t).to_euler().z)'''),
])
# scene 7: pendulum swing fore and aft along the flight direction (~25 px), not sideways
patch("blender/scenes/s07.py", [
    ('''        swing = math.radians(2.5) * math.sin(2 * math.pi * t / 110.0)''', '''        swing = math.radians(5.0) * math.sin(2 * math.pi * t / 110.0)'''),
    ('''        return np.array([p[0] + math.sin(swing) * 6.0 + mot(t)[0], p[1] - 0.4, GLIDER_Z - 6.5])''',
     '''        return np.array([p[0] + mot(t)[0], p[1] - 0.4 - math.sin(swing) * 6.0, GLIDER_Z - 6.5])'''),
    ('''        Mc = Matrix.Translation((p[0] + mot(d)[0], p[1], GLIDER_Z)) @ Euler((0, swing, yaw)).to_matrix().to_4x4()''',
     '''        Mc = Matrix.Translation((p[0] + mot(d)[0], p[1], GLIDER_Z)) @ Euler((-swing, 0, yaw)).to_matrix().to_4x4()'''),
    ('''        M = Matrix.Translation(Vector(hp.tolist())) @ Euler((0, swing, yaw)).to_matrix().to_4x4()''',
     '''        M = Matrix.Translation(Vector(hp.tolist())) @ Euler((-swing, 0, yaw)).to_matrix().to_4x4()'''),
    ('''    rope = rope_io.Owner("A", SCENE, rig, harness_pt, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,''',
     '''    rope = rope_io.Owner("A", SCENE, rig, harness_pt, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,
                         heading_fn=lambda t: glider_world(t)[2],'''),
])
# scene 8: straight run with tiny corrections
patch("blender/scenes/s08.py", [
    ('''TURN_A, TURN_HZ = 0.55, 0.22         # S-turn half-width (m) and rate''',
     '''TURN_A, TURN_HZ = 0.04, 0.22         # v4: a straight run with only tiny corrections (half-width m, rate)'''),
    ('''    rope = rope_io.Owner("A", SCENE, rig, attach, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,''',
     '''    rope = rope_io.Owner("A", SCENE, rig, attach, list(range(start, end, 2)), trail=(0.0, -1.0), warm=150, cfg_motion=False,
                         heading_fn=heading,'''),
])
# scene 9: ride straight
patch("blender/scenes/s09.py", [
    ('''        wob = 0.02 * math.sin(d * 0.21) + 0.012 * math.sin(d * 0.53)''', '''        wob = 0.012 * math.sin(d * 0.21) + 0.006 * math.sin(d * 0.53)'''),
    ('''        bike["root"].rotation_euler = (0, wob, -0.25 * (mot(d + 1)[0] - mot(d - 1)[0]) * PPM / 4.17)''',
     '''        bike["root"].rotation_euler = (0, wob, 0.0)'''),
    ('''    rope = rope_io.Owner("A", SCENE, rig, attach, list(range(start, end, 2)), trail=(0.0, -1.0), ground_fn=lambda x, y: hg(x, y) + 0.01,''',
     '''    rope = rope_io.Owner("A", SCENE, rig, attach, list(range(start, end, 2)), trail=(0.0, -1.0), ground_fn=lambda x, y: hg(x, y) + 0.01,
                         heading_fn=lambda t: 0.0,'''),
])
# scene 12: log heading
patch("blender/scenes/s12.py", [
    ('''    rope_a = rope_io.Owner("A", SCENE, rig, anchor_of(wa), frames, trail=(0.0, -1.0), ground_fn=dh, warm=150, cfg_motion=False)''',
     '''    rope_a = rope_io.Owner("A", SCENE, rig, anchor_of(wa), frames, trail=(0.0, -1.0), ground_fn=dh, warm=150, cfg_motion=False,
                           heading_fn=pa.heading)'''),
    ('''    rope_b = rope_io.Owner("B", SCENE, rig, anchor_of(wb), b_frames, trail=(0.25, 1.0), ground_fn=dh, warm=120, seed_offset=5,''',
     '''    rope_b = rope_io.Owner("B", SCENE, rig, anchor_of(wb), b_frames, trail=(0.25, 1.0), ground_fn=dh, warm=120, seed_offset=5,
                           heading_fn=pb.heading,'''),
])
# walkers: the body centre does not sway sideways (hips bob vertically); scene 10 is not re-rendered
patch("blender/kit/human.py", [
    ('''        sway = 0.018 * math.sin(2 * math.pi * (ph - 0.31)) * k
        upper = (''', '''        sway = 0.004 * math.sin(2 * math.pi * (ph - 0.31)) * k
        upper = ('''),
    ('''    sway = 0.018 * math.sin(2 * math.pi * (ph - 0.31)) * k
    pel = np.array([-sway, 0.0, 0.98 * k + bob])''', '''    sway = 0.004 * math.sin(2 * math.pi * (ph - 0.31)) * k
    pel = np.array([-sway, 0.0, 0.98 * k + bob])'''),
])
