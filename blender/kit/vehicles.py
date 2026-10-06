"""Vehicles: bicycle (wheels with spokes, frame, saddle, handlebar, basket) with wheel spin from ground
speed (omega = v / R) and cranks geared to the wheels; the pedalling rider follows the pedals by IK.
Train cars live in the train scenes. Bike-local frame: +Y forward, +Z up, origin on the ground under the
bottom bracket."""
import math
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector
from . import geo
from .human import ik2, L_UPPER, L_FORE, L_HAND, L_THIGH, L_SHIN

WHEEL_R = 0.34
WHEELBASE = 1.05
GEAR = 2.6            # wheel revolutions per crank revolution
CRANK = 0.17


def _tube(bm, a, b, r, seg=8):
    va, vb = Vector(a), Vector(b)
    L = (vb - va).length
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=L)
    rot = Vector((0, 0, 1)).rotation_difference(vb - va).to_matrix()
    bmesh.ops.rotate(bm, verts=res["verts"], cent=(0, 0, 0), matrix=rot)
    bmesh.ops.translate(bm, vec=(va + vb) / 2, verts=res["verts"])


def bicycle(name, mats, coll):
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    wheels = []
    for i, y in enumerate((-WHEELBASE * 0.45, WHEELBASE * 0.55)):
        bm = bmesh.new()
        tor = bmesh.ops.create_circle(bm, cap_ends=False, segments=40, radius=WHEEL_R)
        bmesh.ops.rotate(bm, verts=tor["verts"], cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
        bm.free()
        bm = bmesh.new()
        # tyre as a thin torus
        for k in range(40):
            a0, a1 = 2 * math.pi * k / 40, 2 * math.pi * (k + 1) / 40
            _tube(bm, (0, WHEEL_R * math.cos(a0), WHEEL_R * math.sin(a0)), (0, WHEEL_R * math.cos(a1), WHEEL_R * math.sin(a1)), 0.022, 6)
        tyre = geo.bm_to_object(bm, f"{name}_tyre{i}", mats["tyre"], coll)
        bm = bmesh.new()
        for k in range(16):
            a = 2 * math.pi * k / 16
            _tube(bm, (0, 0, 0), (0, WHEEL_R * 0.95 * math.cos(a), WHEEL_R * 0.95 * math.sin(a)), 0.004, 4)
        _tube(bm, (-0.03, 0, 0), (0.03, 0, 0), 0.025, 8)
        spokes = geo.bm_to_object(bm, f"{name}_spokes{i}", mats["metal"], coll, smooth=False)
        hub = bpy.data.objects.new(f"{name}_wheel{i}", None)
        coll.objects.link(hub)
        hub.parent = root
        hub.location = (0, y, WHEEL_R)
        tyre.parent = hub
        spokes.parent = hub
        wheels.append(hub)
    rear, front = (0, -WHEELBASE * 0.45, WHEEL_R), (0, WHEELBASE * 0.55, WHEEL_R)
    bb = (0, 0.0, 0.3)
    seat = (0, -0.18, 0.86)
    head = (0, 0.42, 0.9)
    bm = bmesh.new()
    for a, b in ((rear, bb), (bb, seat), (seat, rear), (bb, head), (head, front), (seat, (0, 0.38, 0.84))):
        _tube(bm, a, b, 0.02)
    _tube(bm, head, (0, 0.38, 1.02), 0.018)
    _tube(bm, (-0.26, 0.36, 1.02), (0.26, 0.36, 1.02), 0.014)
    frame = geo.bm_to_object(bm, f"{name}_frame", mats["frame"], coll)
    frame.parent = root
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.08, 0.14, 0.03), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, -0.2, 0.9), verts=bm.verts)
    saddle = geo.bm_to_object(bm, f"{name}_saddle", mats["saddle"], coll)
    saddle.parent = root
    # straw basket on the handlebar
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.15, radius2=0.18, depth=0.22)
    bmesh.ops.scale(bm, vec=(1.0, 0.85, 1.0), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0.6, 0.98), verts=bm.verts)
    basket = geo.bm_to_object(bm, f"{name}_basket", mats["basket"], coll)
    basket.parent = root
    crank = bpy.data.objects.new(f"{name}_crank", None)
    coll.objects.link(crank)
    crank.parent = root
    crank.location = bb
    bm = bmesh.new()
    _tube(bm, (-0.06, 0, 0), (-0.06, 0, -CRANK), 0.012)
    _tube(bm, (0.06, 0, 0), (0.06, 0, CRANK), 0.012)
    cr = geo.bm_to_object(bm, f"{name}_cranks", mats["metal"], coll)
    cr.parent = crank
    return dict(root=root, wheels=wheels, crank=crank, bb=np.array(bb), seat=np.array(seat), bar=(np.array((-0.24, 0.36, 1.02)), np.array((0.24, 0.36, 1.02))))


def ride_pose(distance, bike, height=1.72):
    """rider joints in bike space for a ground distance travelled (m); returns (J, wheel_angle, crank_angle)"""
    k = height / 1.72
    wheel = distance / WHEEL_R
    crank = wheel / GEAR
    J = {}
    seat = bike["seat"]
    pel = seat + np.array([0, 0.02, 0.06])
    J["pelvis"] = pel
    lean = 0.42
    def up(l, fy=0.0):
        return pel + np.array([0, math.sin(lean) * l + fy, math.cos(lean) * l])
    J["spine"], J["chest"], J["neck"], J["head"] = up(0.18 * k), up(0.38 * k), up(0.54 * k), up(0.66 * k, 0.03)
    for s, sx, off in (("l", -1, math.pi), ("r", 1, 0.0)):
        J[f"sho_{s}"] = J["chest"] + np.array([sx * 0.18 * k, 0, 0.05 * k])
        J[f"hip_{s}"] = pel + np.array([sx * 0.1 * k, 0, -0.05 * k])
        a = crank + off
        pedal = bike["bb"] + np.array([sx * 0.11, CRANK * math.sin(a), CRANK * math.cos(a)])
        ank = pedal + np.array([0, -0.04, 0.07])
        kne, ank = ik2(J[f"hip_{s}"], ank, L_THIGH * k, L_SHIN * k, np.array([0, 1.0, 0.4]))
        J[f"kne_{s}"], J[f"ank_{s}"], J[f"toe_{s}"] = kne, ank, ank + np.array([0, 0.14, -0.05])
        grip = bike["bar"][0 if s == "l" else 1]
        el, wr = ik2(J[f"sho_{s}"], grip, L_UPPER * k, L_FORE * k, np.array([sx * 0.6, 0, -0.8]))
        J[f"elb_{s}"], J[f"wri_{s}"], J[f"hnd_{s}"] = el, wr, grip + np.array([0, 0.04, 0])
    J["hem_l"] = J["hem_r"] = J["hem_b"] = pel
    return J, wheel, crank


def train_car(name, mats, coll, length=7.6, width=1.9, height=2.2, nose=False, fans=3, windows=True, modern=False):
    """passenger car along +Y: rounded-roof body, window strips (emissive material slot), roof fans or
    equipment boxes, bogies, gangway. Origin at the car's rear end on the rail head."""
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    bm = bmesh.new()
    nseg = 14
    prof = []
    for i in range(nseg + 1):
        a = math.pi * i / nseg
        x = -math.cos(a) * width / 2
        z = 0.55 + (height - 0.55) * (0.78 + 0.22 * math.sin(a)) if 0 < i < nseg else 0.55
        prof.append((x, z))
    prof = [(-width / 2, 0.55)] + [(x, max(z, 0.55)) for x, z in prof[1:-1]] + [(width / 2, 0.55)]
    def ring(y, shrink=1.0, lift=0.0):
        return [bm.verts.new((x * shrink, y, 0.55 + (z - 0.55) * shrink + lift)) for x, z in prof]
    ys = list(np.linspace(0.0, length, 16))
    rings = []
    for y in ys:
        s = 1.0
        if nose and y > length - 1.8:
            u = (y - (length - 1.8)) / 1.8
            s = max(0.12, math.cos(u * math.pi / 2) ** 0.7)
        rings.append(ring(y, s))
    for r0, r1 in zip(rings[:-1], rings[1:]):
        for k in range(len(prof) - 1):
            bm.faces.new((r0[k], r0[k + 1], r1[k + 1], r1[k]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    body = geo.bm_to_object(bm, name + "_body", mats["body"], coll)
    body.parent = root
    parts = [body]
    if windows:
        bm = bmesh.new()
        for side in (-1, 1):
            for y0 in np.arange(0.6, length - (2.0 if nose else 0.6), 0.9):
                r = bmesh.ops.create_cube(bm, size=1.0)
                bmesh.ops.scale(bm, vec=(0.04, 0.62, 0.42), verts=r["verts"])
                bmesh.ops.translate(bm, vec=(side * (width / 2 + 0.01), y0 + 0.35, 1.45), verts=r["verts"])
        win = geo.bm_to_object(bm, name + "_win", mats["window"], coll, smooth=False)
        win.parent = root
        parts.append(win)
    bm = bmesh.new()
    for i in range(fans):
        y = length * (i + 0.5) / fans
        if modern:
            r = bmesh.ops.create_cube(bm, size=1.0)
            bmesh.ops.scale(bm, vec=(0.8, 1.2, 0.18), verts=r["verts"])
            bmesh.ops.translate(bm, vec=(0, y, height + 0.06), verts=r["verts"])
            for dy in (-0.3, 0.3):
                c = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.24, radius2=0.24, depth=0.05)
                bmesh.ops.translate(bm, vec=(0, y + dy, height + 0.17), verts=c["verts"])
        else:
            c = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.3, radius2=0.26, depth=0.1)
            bmesh.ops.translate(bm, vec=(0, y, height + 0.02), verts=c["verts"])
    roof = geo.bm_to_object(bm, name + "_roof", mats["roof"], coll)
    roof.parent = root
    parts.append(roof)
    bm = bmesh.new()
    for y in (1.3, length - 1.3):
        r = bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(width * 0.8, 2.0, 0.5), verts=r["verts"])
        bmesh.ops.translate(bm, vec=(0, y, 0.35), verts=r["verts"])
    bog = geo.bm_to_object(bm, name + "_bogies", mats["under"], coll, smooth=False)
    bog.parent = root
    parts.append(bog)
    return root, parts
