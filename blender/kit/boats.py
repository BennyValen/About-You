"""Boats: a lofted wooden rowboat (outer + inner hull, gunwale, thwarts, ribs, floorboards, transom,
oarlocks), oars, and the rowing stroke solver (catch -> drive -> release -> recovery).

Boat-local frame: +Y bow, +X starboard (right), +Z up, z = 0 at the waterline.
"""
import math
import numpy as np
import bpy
import bmesh
from mathutils import Matrix, Vector
from . import geo
from .human import standing, ik2, rot_z, L_UPPER, L_FORE, L_HAND, L_THIGH, L_SHIN


def _hull_section(L, B, D, u, transom=0.5):
    """half-width, keel depth (below gunwale) and gunwale height at u in [-1 (stern), 1 (bow)]"""
    if u >= 0:
        w = B / 2 * (1 - u ** 2.2) ** 0.75
    else:
        w = B / 2 * (transom + (1 - transom) * (1 - (-u) ** 2.6) ** 0.6)
    sheer = 0.36 + 0.12 * max(u, 0) ** 2 + 0.03 * max(-u, 0) ** 2
    keel = D * (1 - 0.35 * max(u, 0) ** 3)
    return max(w, 0.004), keel, sheer


def rowboat(name, mats, L=3.6, B=1.25, D=0.42, coll=None, n_u=48, n_v=18, transom=0.5):
    """mats: dict(hull, inner, trim, seat, metal). Returns (root empty, dict of parts)."""
    coll = coll or bpy.context.scene.collection
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    parts = {}
    us = np.linspace(-1, 1, n_u)
    def surf(scale, zoff):
        verts = []
        for u in us:
            w, k, sh = _hull_section(L, B, D, u, transom)
            w *= scale
            for j in range(n_v):
                th = -math.pi / 2 + math.pi * j / (n_v - 1)
                x = w * math.sin(th)
                z = sh - k * scale * (math.cos(th) ** 0.55) + zoff
                verts.append((x, u * L / 2, z))
        return verts
    vo = surf(1.0, 0.0)
    vi = surf(0.9, 0.04)
    faces_o, faces_i = [], []
    for i in range(n_u - 1):
        for j in range(n_v - 1):
            a, b, c, d = i * n_v + j, (i + 1) * n_v + j, (i + 1) * n_v + j + 1, i * n_v + j + 1
            faces_o.append((a, d, c, b))
            faces_i.append((a, b, c, d))
    hull = geo.mesh_from_arrays(f"{name}_hull", vo, faces_o, coll, True, mats["hull"])
    inner = geo.mesh_from_arrays(f"{name}_inner", vi, faces_i, coll, True, mats["inner"])
    # gunwale rail: thin strip joining outer and inner rims
    rv, rf = [], []
    for i, u in enumerate(us):
        for jj, src in ((0, vo), (1, vi)):
            for side in (0, n_v - 1):
                p = src[i * n_v + side]
                rv.append((p[0], p[1], p[2] + 0.012))
    for i in range(n_u - 1):
        for s in range(2):
            a = i * 4 + s
            b = i * 4 + 2 + s
            c = (i + 1) * 4 + 2 + s
            d = (i + 1) * 4 + s
            rf.append((a, d, c, b))
    rim = geo.mesh_from_arrays(f"{name}_rim", rv, rf, coll, False, mats["trim"])
    # transom board at the stern
    w, k, sh = _hull_section(L, B, D, -1.0, transom)
    bm = bmesh.new()
    pts = []
    for j in range(n_v):
        th = -math.pi / 2 + math.pi * j / (n_v - 1)
        pts.append(bm.verts.new((w * math.sin(th), -L / 2 + 0.005, sh - k * (math.cos(th) ** 0.55))))
    bm.faces.new(pts)
    tr = geo.bm_to_object(bm, f"{name}_transom", mats["trim"], coll, smooth=False)
    # thwarts (seats), ribs and floorboards
    def box(nm, size, loc, mat, rot=0.0):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=size, verts=bm.verts)
        if rot:
            bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(rot, 3, "Z"))
        bmesh.ops.translate(bm, vec=loc, verts=bm.verts)
        o = geo.bm_to_object(bm, nm, mat, coll, smooth=False)
        return o
    seats = []
    for i, yy in enumerate((0.95, 0.05, -1.05)):
        u = yy / (L / 2)
        w, k, sh = _hull_section(L, B, D, u, transom)
        seats.append(box(f"{name}_thwart{i}", (2 * w * 0.9, 0.24, 0.035), (0, yy, sh - 0.1), mats["seat"]))
    ribs = []
    for i, yy in enumerate(np.linspace(-1.35, 1.25, 9)):
        u = yy / (L / 2)
        w, k, sh = _hull_section(L, B, D, u, transom)
        ribs.append(box(f"{name}_rib{i}", (2 * w * 0.82, 0.045, 0.02), (0, yy, sh - k * 0.82 + 0.05), mats["trim"]))
    floor = []
    for i, xx in enumerate((-0.22, -0.08, 0.08, 0.22)):
        floor.append(box(f"{name}_floor{i}", (0.11, 2.3, 0.015), (xx, -0.1, 0.36 - D * 0.9 + 0.075), mats["seat"]))
    locks = []
    for side in (-1, 1):
        yy = -0.28
        u = yy / (L / 2)
        w, k, sh = _hull_section(L, B, D, u, transom)
        locks.append(box(f"{name}_lock{side}", (0.05, 0.05, 0.08), (side * w * 0.97, yy, sh + 0.04), mats["metal"]))
    for o in [hull, inner, rim, tr] + seats + ribs + floor + locks:
        o.parent = root
    parts.update(hull=hull, inner=inner, rim=rim, transom=tr, seats=seats, ribs=ribs, floor=floor, locks=locks)
    parts["oarlock_pos"] = [Vector(l.location) for l in [locks[0], locks[1]]]
    parts["dims"] = (L, B, D)
    return root, parts


def oar(name, mats, length=2.7, coll=None):
    """oar along local +X from the handle (x=0) to the blade tip (x=length)"""
    coll = coll or bpy.context.scene.collection
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.022, radius2=0.02, depth=length * 0.78)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    bmesh.ops.translate(bm, vec=(length * 0.39 + 0.1, 0, 0), verts=bm.verts)
    shaft = geo.bm_to_object(bm, f"{name}_shaft", mats["shaft"], coll)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=1.0)
    bmesh.ops.scale(bm, vec=(0.3, 0.085, 0.018), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(length - 0.28, 0, 0), verts=bm.verts)
    blade = geo.bm_to_object(bm, f"{name}_blade", mats["blade"], coll)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.026, radius2=0.026, depth=0.2)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    bmesh.ops.translate(bm, vec=(0.1, 0, 0), verts=bm.verts)
    grip = geo.bm_to_object(bm, f"{name}_grip", mats["grip"], coll)
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    for o in (shaft, blade, grip):
        o.parent = root
    return root, [shaft, blade, grip]


def stroke_angles(psi, catch_deg=52.0, finish_deg=-34.0, drive=0.4, release=0.08):
    """oar yaw (deg, + = blade toward the bow), blade height (m) and feather for stroke phase psi in [0,1)."""
    def ease(x):
        return 0.5 - 0.5 * math.cos(math.pi * min(max(x, 0.0), 1.0))
    if psi < drive:                                   # drive: blade buried, sweeps from bow to stern
        u = psi / drive
        yaw = catch_deg + (finish_deg - catch_deg) * (u * 0.6 + 0.4 * ease(u))
        h, feather, inwater = -0.06, 0.0, True
    elif psi < drive + release:                       # release: lift and feather
        u = (psi - drive) / release
        yaw = finish_deg - 2 * u
        h, feather, inwater = -0.06 + 0.34 * ease(u), ease(u), False
    else:                                             # recovery: blade high, back toward the bow
        u = (psi - drive - release) / (1 - drive - release)
        yaw = (finish_deg - 2) + (catch_deg - finish_deg + 2) * ease(u)
        h, feather, inwater = 0.28 - 0.3 * ease(max(0.0, (u - 0.82) / 0.18)), 1.0 - ease(max(0.0, (u - 0.75) / 0.25)), False
    return yaw, h, feather, inwater


def row_pose(psi, seat, lock_l, lock_r, inboard=0.78, height=1.72, drive=0.4):
    """Rower facing the stern (-Y) on a thwart. Returns (joints dict in boat space, handle/blade info)."""
    k = height / 1.72
    yaw, bh, feather, inwater = stroke_angles(psi, drive=drive)
    # torso lean (radians, + = toward the stern) : forward at the catch, back at the finish
    if psi < drive:
        u = psi / drive
        lean = 0.42 - 0.75 * (0.5 - 0.5 * math.cos(math.pi * u))
    elif psi < drive + 0.08:
        lean = -0.33
    else:
        u = (psi - drive - 0.08) / (1 - drive - 0.08)
        lean = -0.33 + 0.75 * (0.5 - 0.5 * math.cos(math.pi * u))
    J = {}
    pel = np.array(seat, float) + np.array([0, 0.02, 0.06 * k])
    J["pelvis"] = pel
    # spine leaning toward -Y (stern) by `lean`
    def up(lz, fy=0.0):
        return pel + np.array([0, -math.sin(lean) * lz + fy, math.cos(lean) * lz])
    J["spine"], J["chest"], J["neck"] = up(0.18 * k), up(0.38 * k), up(0.54 * k)
    J["head"] = up(0.65 * k, -0.03)
    for s, sx in (("l", -1), ("r", 1)):
        J[f"sho_{s}"] = J["chest"] + np.array([sx * 0.19 * k, 0.0, 0.06 * k])
        J[f"hip_{s}"] = pel + np.array([sx * 0.1 * k, 0, -0.04 * k])
    info = {}
    for s, sx, lock in (("l", -1, lock_l), ("r", 1, lock_r)):
        a = math.radians(yaw)
        outward = np.array([sx * math.cos(a), math.sin(a), 0.0])     # from the lock toward the blade
        drop = (bh - 0.0) / 2.0
        dirv = outward + np.array([0, 0, drop])
        dirv /= np.linalg.norm(dirv)
        handle = np.array(lock, float) - dirv * inboard
        blade = np.array(lock, float) + dirv * 1.9
        info[s] = dict(handle=handle, blade=blade, dir=dirv, yaw=yaw, feather=feather, inwater=inwater)
        sh = J[f"sho_{s}"]
        el, wr = ik2(sh, handle, L_UPPER * k, L_FORE * k, np.array([sx * 0.8, 0.3, -0.6]))
        J[f"elb_{s}"], J[f"wri_{s}"] = el, wr
        J[f"hnd_{s}"] = wr + (handle - sh) / (np.linalg.norm(handle - sh) + 1e-9) * L_HAND * k * 0.6
        # legs: feet braced on the stretcher toward the stern, knees up
        foot = pel + np.array([sx * 0.13 * k, -0.62 * k, -0.24 * k])
        kne, ank = ik2(J[f"hip_{s}"], foot, L_THIGH * k, L_SHIN * k, np.array([0, -0.2, 1.0]))
        J[f"kne_{s}"], J[f"ank_{s}"] = kne, ank
        J[f"toe_{s}"] = ank + np.array([0, -0.15 * k, -0.04 * k])
    J["hem_l"] = J["pelvis"] + np.array([-0.16, 0.0, -0.1])
    J["hem_r"] = J["pelvis"] + np.array([0.16, 0.0, -0.1])
    J["hem_b"] = J["pelvis"] + np.array([0, 0.1, -0.1])
    return J, info


def place_oar(root, lock, info, side):
    """orient an oar root (local +X handle->blade) along the stroke direction"""
    d = Vector(info["dir"].tolist())
    h = Vector(info["handle"].tolist())
    rot = Vector((1, 0, 0)).rotation_difference(d).to_matrix().to_4x4()
    feather = Matrix.Rotation(info["feather"] * math.pi / 2 * (1 if side == "r" else -1), 4, "X")
    root.matrix_local = Matrix.Translation(h) @ rot @ feather
