"""Scene setup, colour helpers, the top-down camera rig and the resumable render loop.

World convention: metres, +X right (east), +Y up the frame (north), +Z up toward the camera.
Each scene picks `ppm`, the screen pixels per metre on the ground plane (z = 0) at 1080x1920.
"""
import bpy, math, os, json, time
import numpy as np
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FPS, W, H = 24, 1080, 1920
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]


def span(scene):
    return CUTS[scene - 1], CUTS[scene]


# ---------------------------------------------------------------- colour
def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexc(h, a=1.0, mul=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return (srgb_to_linear(r) * mul, srgb_to_linear(g) * mul, srgb_to_linear(b) * mul, a)


def mixc(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(4))


def scalec(c, k, alpha=None):
    return (c[0] * k[0], c[1] * k[1], c[2] * k[2], c[3] if alpha is None else alpha) if isinstance(k, tuple) else (c[0] * k, c[1] * k, c[2] * k, c[3])


# ---------------------------------------------------------------- scene
def reset(res_scale=1.0, samples=16):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = int(round(res_scale * 100))
    sc.render.fps = FPS
    sc.render.film_transparent = False
    sc.render.filter_size = 1.2
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"
    sc.eevee.taa_render_samples = samples
    sc.eevee.use_shadows = True
    sc.eevee.shadow_ray_count = 2
    sc.eevee.shadow_step_count = 8
    sc.eevee.use_raytracing = False
    sc.eevee.volumetric_tile_size = "8"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.render.compositor_device = "GPU"
    w = bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    return sc


def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def world_ambient(color, strength):
    w = bpy.context.scene.world
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = color
    bg.inputs[1].default_value = strength


def sun(direction_to_sun, irradiance, color=(1, 1, 1, 1), angle_deg=2.0, name="sun"):
    """direction_to_sun: vector pointing from the ground toward the sun (x east, y north, z up)."""
    d = Vector(direction_to_sun).normalized()
    li = bpy.data.lights.new(name, "SUN")
    li.energy = irradiance
    li.color = color[:3]
    li.angle = math.radians(angle_deg)
    li.use_shadow = True
    ob = link(bpy.data.objects.new(name, li))
    # a sun light shines along its local -Z
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return ob


def sun_irradiance_for(ground_level, d, ambient):
    """Irradiance so a horizontal white diffuse surface reads `ground_level` (display value)."""
    s = Vector(d).normalized().z
    return max(0.01, (ground_level - ambient) * math.pi / max(s, 0.05))


# ---------------------------------------------------------------- camera rig
class Rig:
    """Top-down perspective camera. `speed(f)` = background flow in px/frame at 1080 wide (camera moves +Y)."""

    def __init__(self, scene, ppm, speed, lens=60.0, sensor=24.0, x0=0.0, y0=0.0, drift_x=None, roll=0.0):
        self.scene, self.ppm, self.lens, self.sensor = scene, ppm, lens, sensor
        self.start, self.end = span(scene)
        self.n = self.end - self.start
        vis_h = H / ppm                       # metres of ground visible vertically
        self.h = vis_h * lens / sensor          # camera height
        v = np.array([speed(i) for i in range(self.n + 2)], float)
        self.ys = y0 + np.concatenate([[0.0], np.cumsum(v)])[: self.n + 2] / ppm
        dx = np.array([(drift_x(i) if drift_x else 0.0) for i in range(self.n + 2)], float)
        self.xs = x0 + np.concatenate([[0.0], np.cumsum(dx)])[: self.n + 2] / ppm
        cd = bpy.data.cameras.new("cam")
        cd.lens, cd.sensor_fit, cd.sensor_height = lens, "VERTICAL", sensor
        cd.clip_start, cd.clip_end = 0.5, self.h * 3
        self.obj = link(bpy.data.objects.new("cam", cd))
        bpy.context.scene.camera = self.obj
        self.roll = roll

    def local(self, f):
        return int(min(max(f - self.start, 0), self.n))

    def pos(self, f):
        i = self.local(f)
        return float(self.xs[i]), float(self.ys[i])

    def apply(self, f):
        x, y = self.pos(f)
        self.obj.location = (x, y, self.h)
        self.obj.rotation_euler = (0, 0, self.roll)

    def ppm_at(self, z):
        return self.ppm * self.h / np.maximum(self.h - np.asarray(z, float), 1e-3)

    def screen_to_world(self, f, sx, sy, z=0.0):
        x, y = self.pos(f)
        k = float(self.ppm_at(z))
        return Vector((x + (sx - W / 2) / k, y - (sy - H / 2) / k, z))

    def world_to_screen(self, f, p):
        x, y = self.pos(f)
        k = float(self.ppm_at(p[2]))
        return ((p[0] - x) * k + W / 2, H / 2 - (p[1] - y) * k)

    def px(self, n_px, z=0.0):
        """metres corresponding to n_px screen pixels at height z"""
        return n_px / float(self.ppm_at(z))

    def view_rect(self, f, z=0.0, margin=1.25):
        x, y = self.pos(f)
        k = float(self.ppm_at(z))
        return x - W / 2 / k * margin, y - H / 2 / k * margin, x + W / 2 / k * margin, y + H / 2 / k * margin

    def path_rect(self, z=0.0, margin=1.3):
        """ground rectangle covering everything the camera sees during the scene"""
        k = float(self.ppm_at(z))
        hw, hh = W / 2 / k * margin, H / 2 / k * margin
        return float(self.xs.min() - hw), float(self.ys.min() - hh), float(self.xs.max() + hw), float(self.ys.max() + hh)


def camera_series(scene):
    """[frame, dy] measured series for a scene from work/camera.json (cluster-KLT)."""
    data = json.load(open(os.path.join(ROOT, "work", "camera.json")))
    s = [x for x in data["scenes"] if x["scene"] == scene][0]
    return [(r[0], r[1]) for r in s["klt_series"]], s["dy_klt_median"]


# ---------------------------------------------------------------- render loop
def drawing_frames(start, end, step=2):
    """Frames that get a unique drawing. The film is on twos: every odd frame repeats the even one."""
    return [f for f in range(start, end) if (f - start) % step == 0]


def render_frames(frames, out_dir, update, label=""):
    os.makedirs(out_dir, exist_ok=True)
    sc = bpy.context.scene
    t_all = time.time()
    done = 0
    for f in frames:
        path = os.path.join(out_dir, f"f{f:04d}.png")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        t = time.time()
        sc.frame_set(f)
        update(f)
        t1 = time.time()
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        done += 1
        print(f"RENDER {label} f{f} {time.time() - t:.2f}s (update {t1 - t:.2f}s)", flush=True)
    print(f"RENDER {label} done {done} frames in {time.time() - t_all:.1f}s", flush=True)
