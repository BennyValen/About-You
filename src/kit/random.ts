// Seeded randomness and noise for JS-side placement. All generation goes through
// these so every render is deterministic.

export const mulberry32 = (seed: number) => {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
};

export type Rng = ReturnType<typeof mulberry32>;

export const rrange = (rng: Rng, a: number, b: number) => a + (b - a) * rng();
export const rpick = <T,>(rng: Rng, arr: T[]): T => arr[Math.floor(rng() * arr.length) % arr.length];

export const hash1 = (n: number) => {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453123;
  return s - Math.floor(s);
};
export const hash2 = (x: number, y: number) => {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453123;
  return s - Math.floor(s);
};

const fade = (t: number) => t * t * (3 - 2 * t);
export const vnoise1 = (x: number) => {
  const i = Math.floor(x);
  const f = x - i;
  return hash1(i) + (hash1(i + 1) - hash1(i)) * fade(f);
};
export const vnoise2 = (x: number, y: number) => {
  const ix = Math.floor(x);
  const iy = Math.floor(y);
  const fx = fade(x - ix);
  const fy = fade(y - iy);
  const a = hash2(ix, iy);
  const b = hash2(ix + 1, iy);
  const c = hash2(ix, iy + 1);
  const d = hash2(ix + 1, iy + 1);
  return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
};
// signed smooth noise in [-1,1]
export const snoise1 = (x: number) => vnoise1(x) * 2 - 1;
export const fbm1 = (x: number, oct = 3) => {
  let s = 0;
  let a = 0.5;
  let f = 1;
  for (let i = 0; i < oct; i++) {
    s += a * snoise1(x * f + i * 17.3);
    a *= 0.5;
    f *= 2.07;
  }
  return s;
};

// Poisson-ish scatter in a rectangle with minimum spacing (dart throwing, seeded).
export const scatter = (
  rng: Rng,
  count: number,
  x0: number,
  y0: number,
  x1: number,
  y1: number,
  minDist: number,
  accept?: (x: number, y: number) => boolean,
  tries = 30,
) => {
  const pts: {x: number; y: number}[] = [];
  const cell = minDist / Math.SQRT2;
  const grid = new Map<string, number>();
  const key = (gx: number, gy: number) => gx + ',' + gy;
  let attempts = 0;
  while (pts.length < count && attempts < count * tries) {
    attempts++;
    const x = rrange(rng, x0, x1);
    const y = rrange(rng, y0, y1);
    if (accept && !accept(x, y)) continue;
    const gx = Math.floor(x / cell);
    const gy = Math.floor(y / cell);
    let ok = true;
    for (let j = -2; j <= 2 && ok; j++) {
      for (let i = -2; i <= 2 && ok; i++) {
        const idx = grid.get(key(gx + i, gy + j));
        if (idx !== undefined) {
          const p = pts[idx];
          if ((p.x - x) ** 2 + (p.y - y) ** 2 < minDist * minDist) ok = false;
        }
      }
    }
    if (!ok) continue;
    grid.set(key(gx, gy), pts.length);
    pts.push({x, y});
  }
  return pts;
};

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const smoothstep = (a: number, b: number, x: number) => {
  const t = clamp((x - a) / (b - a));
  return t * t * (3 - 2 * t);
};
export const easeInOut = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
