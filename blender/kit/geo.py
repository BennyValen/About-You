"""Geometry helpers: numpy-built meshes, terrain grids, geometry-nodes instancing with per-instance
attributes (scale, rotation, variant, tint read by the shader as an INSTANCER attribute), seeded scatter."""
import math
import numpy as np
import bpy
import bmesh


def mesh_from_arrays(name, verts, faces, coll=None, smooth=True, mat=None):
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, np.float32)
    faces = np.asarray(faces, np.int32)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    nl = faces.shape[1]
    me.loops.add(faces.size)
    me.loops.foreach_set("vertex_index", faces.ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", np.arange(0, faces.size, nl, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(faces), nl, np.int32))
    me.update(calc_edges=True)
    me.validate()
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def grid(name, x0, y0, x1, y1, nx, ny, height=None, coll=None, mat=None, uv=True):
    xs = np.linspace(x0, x1, nx)
    ys = np.linspace(y0, y1, ny)
    X, Y = np.meshgrid(xs, ys)
    Z = height(X, Y) if height is not None else np.zeros_like(X)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    i = np.arange(nx * ny).reshape(ny, nx)
    faces = np.stack([i[:-1, :-1].ravel(), i[:-1, 1:].ravel(), i[1:, 1:].ravel(), i[1:, :-1].ravel()], 1)
    ob = mesh_from_arrays(name, verts, faces, coll, True, mat)
    if uv:
        me = ob.data
        uvl = me.uv_layers.new(name="UVMap")
        uvs = np.stack([(X.ravel() - x0) / (x1 - x0), (Y.ravel() - y0) / (y1 - y0)], 1)
        loops_v = np.zeros(len(me.loops), np.int32)
        me.loops.foreach_get("vertex_index", loops_v)
        uvl.data.foreach_set("uv", uvs[loops_v].astype(np.float32).ravel())
    return ob


def proto_collection(name):
    """hidden collection holding instance prototypes"""
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    lc = bpy.context.view_layer.layer_collection.children[c.name]
    lc.exclude = True
    return c


def _gn_instancer(protos):
    ng = bpy.data.node_groups.new("instancer", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes
    L = ng.links.new
    gi = N.new("NodeGroupInput")
    go = N.new("NodeGroupOutput")
    ci = N.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = protos
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True
    ci.transform_space = "ORIGINAL"
    iop = N.new("GeometryNodeInstanceOnPoints")
    iop.inputs["Pick Instance"].default_value = True
    def attr(name, dtype):
        a = N.new("GeometryNodeInputNamedAttribute")
        a.data_type = dtype
        a.inputs["Name"].default_value = name
        return a.outputs["Attribute"]
    L(gi.outputs[0], iop.inputs["Points"])
    L(ci.outputs[0], iop.inputs["Instance"])
    L(attr("variant", "INT"), iop.inputs["Instance Index"])
    L(attr("rot", "FLOAT_VECTOR"), iop.inputs["Rotation"])
    L(attr("scl", "FLOAT_VECTOR"), iop.inputs["Scale"])
    L(iop.outputs[0], go.inputs[0])
    return ng


def instances(name, protos, pos, rot=None, scl=None, variant=None, tint=None, coll=None, extra=None):
    """Instance prototypes (objects in collection `protos`, alphabetical order = variant index) on points."""
    n = len(pos)
    me = bpy.data.meshes.new(name)
    me.vertices.add(n)
    me.vertices.foreach_set("co", np.asarray(pos, np.float32).ravel())
    def put(nm, typ, arr):
        a = me.attributes.new(nm, typ, "POINT")
        if typ == "FLOAT_VECTOR":
            a.data.foreach_set("vector", np.asarray(arr, np.float32).ravel())
        else:
            a.data.foreach_set("value", np.asarray(arr).ravel())
    put("rot", "FLOAT_VECTOR", rot if rot is not None else np.zeros((n, 3)))
    put("scl", "FLOAT_VECTOR", scl if scl is not None else np.ones((n, 3)))
    put("variant", "INT", np.asarray(variant if variant is not None else np.zeros(n), np.int32))
    put("tint", "FLOAT", np.asarray(tint if tint is not None else np.zeros(n), np.float32))
    for k, v in (extra or {}).items():
        put(k, "FLOAT", np.asarray(v, np.float32))
    me.update()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    md = ob.modifiers.new("inst", "NODES")
    md.node_group = _gn_instancer(protos)
    return ob


def update_points(ob, pos, rot=None, scl=None):
    me = ob.data
    n = len(pos)
    if len(me.vertices) != n:
        raise ValueError("point count changed")
    me.vertices.foreach_set("co", np.asarray(pos, np.float32).ravel())
    if rot is not None:
        me.attributes["rot"].data.foreach_set("vector", np.asarray(rot, np.float32).ravel())
    if scl is not None:
        me.attributes["scl"].data.foreach_set("vector", np.asarray(scl, np.float32).ravel())
    me.update()


def poisson(rng, n, x0, y0, x1, y1, rmin, accept=None, tries=40):
    """dart-throwing scatter with a minimum spacing (seeded numpy Generator)"""
    cell = rmin / math.sqrt(2)
    gw, gh = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
    gridm = -np.ones((gh, gw), np.int64)
    pts = []
    att = 0
    while len(pts) < n and att < n * tries:
        att += 1
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if accept is not None and not accept(x, y):
            continue
        gx, gy = int((x - x0) / cell), int((y - y0) / cell)
        ok = True
        for j in range(max(0, gy - 2), min(gh, gy + 3)):
            for i in range(max(0, gx - 2), min(gw, gx + 3)):
                k = gridm[j, i]
                if k >= 0 and (pts[k][0] - x) ** 2 + (pts[k][1] - y) ** 2 < rmin * rmin:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            gridm[gy, gx] = len(pts)
            pts.append((x, y))
    return np.array(pts).reshape(-1, 2)


def bm_to_object(bm, name, mat=None, coll=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def value_noise2(x, y, seed=0):
    """smooth value noise in numpy (deterministic), for terrain shaping on the CPU side"""
    def h(ix, iy):
        v = np.sin(ix * 127.1 + iy * 311.7 + seed * 74.7) * 43758.5453
        return v - np.floor(v)
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b, c, d = h(ix, iy), h(ix + 1, iy), h(ix, iy + 1), h(ix + 1, iy + 1)
    return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy


def fbm2(x, y, octaves=4, seed=0):
    s, amp, f = 0.0, 0.5, 1.0
    for o in range(octaves):
        s = s + amp * (value_noise2(x * f, y * f, seed + o * 13) * 2 - 1)
        amp *= 0.5
        f *= 2.03
    return s


def knobbly(name, mat, coll, seed=0, subdiv=3, knob=0.35, flat=0.55, lumps=6):
    """organic lumpy blob (coral head / bush / rock): icosphere with baked fbm and lump displacement"""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    V = np.array([v.co[:] for v in bm.verts])
    N = V / np.linalg.norm(V, axis=1)[:, None]
    disp = np.zeros(len(V))
    for _ in range(lumps):
        c = rng.normal(size=3)
        c /= np.linalg.norm(c)
        disp += rng.uniform(0.2, 0.45) * np.exp(-((N - c) ** 2).sum(1) / rng.uniform(0.15, 0.4))
    disp += knob * 0.5 * (fbm2(N[:, 0] * 3 + N[:, 2] * 2.1, N[:, 1] * 3 - N[:, 2] * 1.7, 4, seed) )
    V = N * (0.75 + disp)[:, None]
    V[:, 2] = np.where(V[:, 2] < 0, V[:, 2] * 0.15, V[:, 2] * flat)
    for v, p in zip(bm.verts, V):
        v.co = p
    return bm_to_object(bm, name, mat, coll)


class Wake:
    """Stateless (closed-form) foam particles behind a moving hull. Particles are emitted at regular times
    from points along the hull with an outward velocity that decays exponentially; every particle's
    position at time t is computed directly, so any frame can be rendered independently."""

    def __init__(self, hull_frame, t0, t1, rate=6, life=60.0, spread=0.35, decay=0.04, seed=0,
                 emit_points=((0.0, -1.7, 0.0),), jitter=0.12):
        self.hf = hull_frame          # hull_frame(t) -> (origin xy, forward unit xy, right unit xy, speed m/frame)
        self.rng = np.random.default_rng(seed)
        self.t0, self.t1 = t0 - life, t1
        self.rate, self.life, self.spread, self.decay = rate, life, spread, decay
        self.emit_points = emit_points
        self.jitter = jitter
        self.parts = []
        ts = np.arange(self.t0, self.t1, 1.0 / rate)
        for te in ts:
            o, fw, rt, sp = hull_frame(te)
            for (ex, ey, side) in emit_points:
                p = np.array(o) + np.array(rt) * ex + np.array(fw) * ey
                p = p + self.rng.normal(0, jitter, 2)
                out = np.array(rt) * side * spread * (0.6 + 0.8 * self.rng.random())
                back = -np.array(fw) * sp * 0.25
                v = (out + back) * 0.05
                self.parts.append((te, p[0], p[1], v[0], v[1], self.rng.uniform(0.5, 1.0), self.rng.uniform(0, 6.28)))
        self.parts = np.array(self.parts)

    def at(self, t, max_n):
        P = self.parts
        age = t - P[:, 0]
        m = (age >= 0) & (age < self.life)
        P, age = P[m], age[m]
        k = self.decay
        disp = (1 - np.exp(-k * age)) / k
        x = P[:, 1] + P[:, 3] * disp
        y = P[:, 2] + P[:, 4] * disp
        life_u = age / self.life
        size = P[:, 5] * (0.25 + 0.9 * np.sqrt(life_u)) * (1 - life_u ** 2)
        out = np.zeros((max_n, 5))
        n = min(len(x), max_n)
        out[:n] = np.c_[x, y, size, P[:, 6], life_u][-n:] if n else out[:0]
        return out


def spiky(name, mat, coll, seed=0, subdiv=4, spikes=220, sharp=22.0, amp=0.55, flat=0.8):
    """fluffy foliage clump: radial tufts of pointed leaf-spikes (reads as foliage from above)"""
    rng = np.random.default_rng(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    V = np.array([v.co[:] for v in bm.verts])
    N = V / np.linalg.norm(V, axis=1)[:, None]
    D = rng.normal(size=(spikes, 3))
    D /= np.linalg.norm(D, axis=1)[:, None]
    m = np.zeros(len(N))
    for c in np.array_split(D, max(1, spikes // 40)):
        m = np.maximum(m, (np.clip(N @ c.T, 0, 1) ** sharp).max(1))
    r = 0.72 + amp * m + 0.06 * fbm2(N[:, 0] * 4, N[:, 1] * 4 + N[:, 2], 3, seed)
    V = N * r[:, None]
    V[:, 2] *= flat
    for v, p in zip(bm.verts, V):
        v.co = p
    return bm_to_object(bm, name, mat, coll)


def merge_objects(objs, name, coll):
    """merge objects into one mesh (world transforms applied, material slots kept) without operators"""
    mats = []
    bm = bmesh.new()
    for o in objs:
        me = o.data
        tmp = bmesh.new()
        tmp.from_mesh(me)
        tmp.transform(o.matrix_world)
        remap = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        for f in tmp.faces:
            f.material_index = remap[f.material_index] if remap else 0
        tm = bpy.data.meshes.new("tmp")
        tmp.to_mesh(tm)
        tmp.free()
        bm.from_mesh(tm)
        bpy.data.meshes.remove(tm)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    for o in objs:
        bpy.data.objects.remove(o)
    return ob


def mesh_from_faces(name, verts, faces, coll=None, smooth=True, mat=None):
    """mesh from a vertex array and a list of faces of any size (tris + quads mixed)"""
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.asarray(verts, float).tolist(), [], [tuple(int(i) for i in f) for f in faces])
    me.update(calc_edges=True)
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    ob = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


class HeightGrid:
    """bake an expensive height function h(X, Y) on a regular grid once; fast bilinear lookups (scalar or arrays)"""

    def __init__(self, fn, x0, y0, x1, y1, step=0.05):
        self.x0, self.y0, self.step = x0, y0, step
        self.nx, self.ny = int((x1 - x0) / step) + 2, int((y1 - y0) / step) + 2
        X, Y = np.meshgrid(x0 + np.arange(self.nx) * step, y0 + np.arange(self.ny) * step)
        self.Z = np.asarray(fn(X, Y), float)

    def __call__(self, x, y):
        scalar = np.isscalar(x) and np.isscalar(y)
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        fx = np.clip((x - self.x0) / self.step, 0, self.nx - 1.001)
        fy = np.clip((y - self.y0) / self.step, 0, self.ny - 1.001)
        ix, iy = np.floor(fx).astype(int), np.floor(fy).astype(int)
        tx, ty = fx - ix, fy - iy
        Z = self.Z
        z = (Z[iy, ix] * (1 - tx) * (1 - ty) + Z[iy, ix + 1] * tx * (1 - ty) + Z[iy + 1, ix] * (1 - tx) * ty + Z[iy + 1, ix + 1] * tx * ty)
        return float(z) if scalar else z
