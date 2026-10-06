"""Per-scene rope (red thread) configuration, tuned offline with scripts/tune_rope.py against work/thread_stats.json.

owner_px: measured owner screen position in the original (thread attach point).  z: attach height (m).
owner_motion(s)(t) -> (dx, dy, dz) world offsets of the attach point added to the owner's path: gait sway, meander,
pendulum swing... The Blender scenes add the same terms to their real attach points.
"""
import math
import numpy as np
from . import rope as R

PPM = {1: 30.0, 2: 30.0, 3: 92.0, 4: 100.0, 5: 95.0, 6: 90.0, 7: 30.0, 8: 80.0, 9: 75.0, 10: 120.0, 11: 92.0, 12: 130.0}
TAU = 2 * math.pi


def screen_len(s, z=0.0):
    """two screen heights, in metres at the attach height"""
    ppm = PPM[s]
    h = (1920 / ppm) * 60.0 / 24.0
    k = ppm * h / (h - z)
    return 2.0 * 1920 / k


ROPE = {
    # night train: coupler of the last carriage, rope on the ballast, fluttering in the slipstream
    1: dict(owner_px=(510, 1648), z=0.6, mode="ground", ground=0.12, friction=1.2, air_drag=2.5,
            wind=dict(base=(0.0, -1.0), curl=1.2, scale=4.0, evolve=0.2, gust=0.3, gust_hz=0.2, lateral=4.0, lateral_hz=0.15, seed=11)),
    # tea garden train: as scene 1, calmer
    2: dict(owner_px=(540, 1712), z=0.6, mode="ground", ground=0.2, friction=1.5, air_drag=2.0,
            wind=dict(base=(0.0, -0.6), curl=0.6, scale=4.0, evolve=0.2, gust=0.2, lateral=3.4, lateral_hz=0.24, seed=12)),
    # rowboat: floats, viscous drag toward slow eddies and the wake
    3: dict(owner_px=(548, 1336), z=0.25, mode="water", water_drag=3.0,
            current=dict(base=(0.0, 0.0), curl=0.10, scale=2.5, evolve=0.12, lateral=0.07, lateral_hz=0.18, seed=13)),
    # skater on ice: low friction, slides and whips with the S-curve strokes
    4: dict(owner_px=(506, 1206), z=0.95, mode="ground", ground=0.004, friction=0.5, air_drag=0.6,
            wind=dict(base=(0.2, 0.0), curl=0.4, scale=3.0, evolve=0.2, gust=0.3, seed=14)),
    # horse on sand: strong friction, lies along the trail
    5: dict(owner_px=(578, 1246), z=0.95, mode="ground", ground=0.01, friction=22.0, air_drag=1.0,
            wind=dict(base=(0.2, 0.0), curl=0.3, scale=2.0, evolve=0.3, gust=0.2, lateral=0.1, lateral_hz=0.3, seed=15)),
    # lagoon sailboat: floats on the wake
    6: dict(owner_px=(550, 1332), z=0.3, mode="water", water_drag=3.0,
            current=dict(base=(0.0, 0.0), curl=0.10, scale=3.0, evolve=0.12, lateral=0.06, lateral_hz=0.19, seed=16)),
    # paraglider: hangs and streams in the relative wind, long sway
    7: dict(owner_px=(542, 1232), z=51.5, mode="air", air_drag=0.9, gravity=0.35,
            wind=dict(base=(0.0, -3.0), curl=0.35, scale=5.0, evolve=0.6, gust=0.3, gust_hz=0.3, lateral=0.12, lateral_hz=0.5, seed=17)),
    # moonlit skier: snow, moderate friction, S-turns
    8: dict(owner_px=(540, 1250), z=0.9, mode="ground", ground=0.02, friction=3.0, air_drag=1.0,
            wind=dict(base=(0.05, 0.0), curl=0.3, scale=2.5, evolve=0.3, gust=0.1, seed=18)),
    # cyclist on a gravel path
    9: dict(owner_px=(512, 1454), z=0.8, mode="ground", ground=0.01, friction=10.0, air_drag=1.2,
            wind=dict(base=(0.2, 0.0), curl=0.6, scale=2.0, evolve=0.3, gust=0.3, lateral=0.2, lateral_hz=0.3, seed=19)),
    # walker: the rope rides over the flower heads, gait sway shows near the owner
    10: dict(owner_px=(569, 1220), z=1.0, mode="ground", ground=0.9, friction=3.0, air_drag=1.5,
             wind=dict(base=(0.2, 0.0), curl=0.3, scale=1.6, evolve=0.8, gust=0.2, gust_hz=0.5, lateral=0.1, lateral_hz=0.9, seed=20)),
    # traveller hanging below the birds: air, long sway
    11: dict(owner_px=(535, 1278), z=2.0, mode="air", air_drag=0.9, gravity=0.25,
             wind=dict(base=(0.0, -4.0), curl=0.2, scale=4.0, evolve=0.3, gust=0.2, lateral=0.12, lateral_hz=0.3, seed=21)),
    # dunes: A walks, rope on sand
    12: dict(owner_px=(434, 1330), z=0.95, mode="ground", ground=0.01, friction=12.0, air_drag=1.5,
             wind=dict(base=(0.5, 0.0), curl=0.9, scale=1.8, evolve=0.4, gust=0.6, gust_hz=0.25, lateral=0.35, lateral_hz=0.4, seed=22)),
}


# owner path terms (world metres, Hz): gait = the body's own sway (realism, small); meander = slow weaving of the
# path / boat yaw / skating S-curve / pendulum swing (tuned so the rope's curves match the original's).
MOTION = {
    # v4: heroes travel straight (no path weave, no lateral gait sway); only the skater keeps the original's S-curve.
    # The thread's curves come from the wind/current field (tuned per scene) and the owner's speed pulses.
    1: dict(gait=(0.0, 0.55), meander=(0.0, 0.3)),
    2: dict(gait=(0.01, 0.55), meander=(0.0, 0.4)),
    3: dict(gait=(0.0, 0.4), meander=(0.0, 0.141)),
    4: dict(gait=(0.07, 0.62), meander=(0.32, 0.255)),
    5: dict(gait=(0.0, 0.95), meander=(0.0, 0.3)),
    6: dict(gait=(0.0, 0.2), meander=(0.0, 0.192)),
    7: dict(gait=(0.0, 0.85), meander=(0.0, 0.24)),
    8: dict(gait=(0.0, 0.7), meander=(0.0, 0.25)),
    9: dict(gait=(0.0, 1.1), meander=(0.0, 0.267)),
    10: dict(gait=(0.0, 0.9), meander=(0.0, 0.3)),           # v5: no lateral body sway on the walker
    11: dict(gait=(0.0, 0.6), meander=(0.0, 0.28)),
    12: dict(gait=(0.0, 0.9), meander=(0.0, 0.469)),
}



# v4 retune (owners travel straight; curves from the wind/current field), scripts/tune_rope.py --search2
V4_ROPE = {
 "3": {
  "owner_px": [
   548,
   1336
  ],
  "z": 0.25,
  "mode": "water",
  "water_drag": 3.0,
  "current": {
   "base": [
    0.0,
    0.0
   ],
   "curl": 0.3,
   "scale": 1.2,
   "evolve": 0.12,
   "lateral": 0.6,
   "lateral_hz": 0.20123877318307734,
   "seed": 13
  }
 },
 "5": {
  "owner_px": [
   578,
   1246
  ],
  "z": 0.95,
  "mode": "ground",
  "ground": 0.01,
  "friction": 8.0,
  "air_drag": 1.0,
  "wind": {
   "base": [
    0.2,
    0.0
   ],
   "curl": 0.3,
   "scale": 0.6,
   "evolve": 0.3,
   "gust": 0.2,
   "lateral": 4.0,
   "lateral_hz": 0.2994631054199077,
   "seed": 15
  }
 },
 "6": {
  "owner_px": [
   550,
   1332
  ],
  "z": 0.3,
  "mode": "water",
  "water_drag": 3.0,
  "current": {
   "base": [
    0.0,
    0.0
   ],
   "curl": 0.3,
   "scale": 1.2,
   "evolve": 0.12,
   "lateral": 0.6,
   "lateral_hz": 0.19177358515331017,
   "seed": 16
  }
 },
 "7": {
  "owner_px": [
   542,
   1232
  ],
  "z": 51.5,
  "mode": "air",
  "air_drag": 0.9,
  "gravity": 0.35,
  "wind": {
   "base": [
    0.0,
    -3.0
   ],
   "curl": 0.35,
   "scale": 1.2,
   "evolve": 0.6,
   "gust": 0.3,
   "gust_hz": 0.3,
   "lateral": 3.3333333333333335,
   "lateral_hz": 0.7184036681513625,
   "seed": 17
  }
 },
 "8": {
  "owner_px": [
   540,
   1250
  ],
  "z": 0.9,
  "mode": "ground",
  "ground": 0.02,
  "friction": 4.0,
  "air_drag": 1.0,
  "wind": {
   "base": [
    0.05,
    0.0
   ],
   "curl": 2.0,
   "scale": 0.6,
   "evolve": 0.3,
   "gust": 0.1,
   "seed": 18,
   "lateral": 4.0,
   "lateral_hz": 0.304722020085363
  }
 },
 "9": {
  "owner_px": [
   512,
   1454
  ],
  "z": 0.8,
  "mode": "ground",
  "ground": 0.01,
  "friction": 4.0,
  "air_drag": 1.2,
  "wind": {
   "base": [
    0.2,
    0.0
   ],
   "curl": 2.0,
   "scale": 0.6,
   "evolve": 0.3,
   "gust": 0.3,
   "lateral": 4.0,
   "lateral_hz": 0.2672031541999412,
   "seed": 19
  }
 },
 "11": {
  "owner_px": [
   535,
   1278
  ],
  "z": 2.0,
  "mode": "air",
  "air_drag": 0.9,
  "gravity": 0.25,
  "wind": {
   "base": [
    0.0,
    -4.0
   ],
   "curl": 0.2,
   "scale": 2.5,
   "evolve": 0.3,
   "gust": 0.2,
   "lateral": 0.6666666666666666,
   "lateral_hz": 0.3099809347508183,
   "seed": 21
  }
 },
 "12": {
  "owner_px": [
   434,
   1330
  ],
  "z": 0.95,
  "mode": "ground",
  "ground": 0.01,
  "friction": 8.0,
  "air_drag": 1.5,
  "wind": {
   "base": [
    0.5,
    0.0
   ],
   "curl": 0.9,
   "scale": 0.6,
   "evolve": 0.4,
   "gust": 0.6,
   "gust_hz": 0.25,
   "lateral": 4.0,
   "lateral_hz": 0.6706386702478491,
   "seed": 22
  }
 }
}
for _k, _v in V4_ROPE.items():
    _v['owner_px'] = tuple(_v['owner_px'])
    ROPE[int(_k)] = _v

def owner_motion(s, motion=None):
    """attach-point motion added to the owner's path (world metres), t in frames"""
    m = motion or MOTION[s]
    ag, fg = m["gait"]
    am, fm = m["meander"]
    ph = 0.37 * s

    def f(t):
        ts = t / 24.0
        dx = ag * math.sin(TAU * fg * ts) + am * (0.8 * math.sin(TAU * fm * ts + ph) + 0.2 * math.sin(TAU * fm * 1.7 * ts + 2 * ph))
        dz = 0.15 * ag * math.sin(TAU * 2 * fg * ts)
        return dx, 0.0, dz
    return f


def make_rope(s, ppm=None, ground_fn=None, push=None, n_seg=260, seed_offset=0):
    c = ROPE[s]
    L = screen_len(s, c.get("z", 0.0) if c["mode"] == "air" else 0.0)
    kw = dict(n_seg=n_seg, length=L, mode=c["mode"], substeps=c.get("substeps", 6), bend=c.get("bend", 0.02),
              damping=c.get("damping", 0.3), radius=0.01, push=push, gravity=c.get("gravity", 1.0))
    if c["mode"] == "water":
        cur = dict(c["current"])
        cur["seed"] = cur.get("seed", 0) + seed_offset
        kw.update(water_level=0.0, water_drag=c.get("water_drag", 3.0), current=R.Field(**cur))
    else:
        wd = dict(c["wind"])
        wd["seed"] = wd.get("seed", 0) + seed_offset
        kw.update(air_drag=c.get("air_drag", 1.0), wind=R.Field(**wd), friction=c.get("friction", 5.0))
        if ground_fn is not None:
            kw["ground"] = ground_fn
        elif c["mode"] == "air":
            kw["ground"] = lambda x, y: np.full_like(x, -1e4)
        else:
            g = c.get("ground", 0.0)
            kw["ground"] = lambda x, y, g=g: np.full_like(x, g)
    return R.Rope(**kw)
