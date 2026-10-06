import React, {useEffect, useMemo} from 'react';
import {AdditiveBlending, BufferAttribute, BufferGeometry, Color, DoubleSide, Mesh, ShaderMaterial} from 'three';
import {CamPose, screenToWorld} from './camera';
import {fbm1} from './random';

// ---------------------------------------------------------------------------
// The red thread: a verlet rope in screen space, pinned at both ends (usually the
// traveler and a point below the bottom edge). Soft sway comes from a travelling
// wave force plus low-frequency turbulence, damped by the constraints. The whole
// scene is simulated deterministically from frame 0, cached per tab, and drawn
// on twos like the rest of the line work.

export type Pt = {x: number; y: number};
export type ThreadConfig = {
  id: string;
  length: number; // frames to simulate
  a: (f: number) => Pt; // pinned end A (screen px), usually the traveler
  b: (f: number) => Pt; // pinned end B (screen px), usually below the frame
  segments?: number;
  slack?: number; // rest length / straight distance
  sway?: number; // px/frame^2 lateral force
  waves?: number; // number of travelling waves along the thread
  waveSpeed?: number; // cycles per frame
  flow?: number; // downward drift (ground flow), px/frame
  damping?: number;
  seed?: number;
};

const cache = new Map<string, {n: number; data: Float32Array}>();

export const simulateThread = (cfg: ThreadConfig) => {
  const hit = cache.get(cfg.id);
  if (hit) return hit;
  const N = cfg.segments ?? 44;
  const slack = cfg.slack ?? 1.025;
  const sway = cfg.sway ?? 0.06;
  const waves = cfg.waves ?? 1.4;
  const wspeed = cfg.waveSpeed ?? 0.012;
  const flow = cfg.flow ?? 0.0;
  const damp = cfg.damping ?? 0.94;
  const seed = cfg.seed ?? 1;
  const warm = 72;
  const P = new Float64Array((N + 1) * 2);
  const Q = new Float64Array((N + 1) * 2);
  const a0 = cfg.a(0);
  const b0 = cfg.b(0);
  for (let i = 0; i <= N; i++) {
    const s = i / N;
    P[i * 2] = a0.x + (b0.x - a0.x) * s;
    P[i * 2 + 1] = a0.y + (b0.y - a0.y) * s;
    Q[i * 2] = P[i * 2];
    Q[i * 2 + 1] = P[i * 2 + 1];
  }
  const out = new Float32Array(cfg.length * (N + 1) * 2);
  for (let step = -warm; step < cfg.length; step++) {
    const f = Math.max(0, step);
    const t = step;
    const A = cfg.a(f);
    const B = cfg.b(f);
    const dist = Math.hypot(B.x - A.x, B.y - A.y);
    const rest = (dist * slack) / N;
    // integrate
    for (let i = 1; i < N; i++) {
      const s = i / N;
      const env = Math.sin(Math.PI * s) ** 0.8;
      const wave = Math.sin(2 * Math.PI * (s * waves - t * wspeed) + seed * 1.7);
      const turb = fbm1(s * 2.3 + t * 0.006 + seed * 11.1, 3);
      const ax = sway * env * (0.65 * wave + 0.8 * turb);
      const ay = 0.02 * flow;
      const x = P[i * 2];
      const y = P[i * 2 + 1];
      const vx = (x - Q[i * 2]) * damp;
      const vy = (y - Q[i * 2 + 1]) * damp;
      Q[i * 2] = x;
      Q[i * 2 + 1] = y;
      P[i * 2] = x + vx + ax;
      P[i * 2 + 1] = y + vy + ay;
    }
    // constraints
    for (let it = 0; it < 14; it++) {
      P[0] = A.x;
      P[1] = A.y;
      P[N * 2] = B.x;
      P[N * 2 + 1] = B.y;
      for (let i = 0; i < N; i++) {
        const ax = P[i * 2];
        const ay = P[i * 2 + 1];
        const bx = P[i * 2 + 2];
        const by = P[i * 2 + 3];
        const dx = bx - ax;
        const dy = by - ay;
        const d = Math.hypot(dx, dy) || 1e-6;
        const diff = (d - rest) / d;
        const wa = i === 0 ? 0 : 0.5;
        const wb = i + 1 === N ? 0 : 0.5;
        const ws = wa + wb || 1;
        P[i * 2] += dx * diff * (wa / ws);
        P[i * 2 + 1] += dy * diff * (wa / ws);
        P[i * 2 + 2] -= dx * diff * (wb / ws);
        P[i * 2 + 3] -= dy * diff * (wb / ws);
      }
    }
    P[0] = A.x;
    P[1] = A.y;
    P[N * 2] = B.x;
    P[N * 2 + 1] = B.y;
    if (step >= 0) out.set(P, step * (N + 1) * 2);
  }
  const res = {n: N, data: out};
  cache.set(cfg.id, res);
  return res;
};

// Catmull-Rom resample of the sim polyline.
const resample = (pts: Pt[], per: number): Pt[] => {
  const res: Pt[] = [];
  const n = pts.length;
  for (let i = 0; i < n - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(n - 1, i + 2)];
    for (let k = 0; k < per; k++) {
      const t = k / per;
      const t2 = t * t;
      const t3 = t2 * t;
      res.push({
        x: 0.5 * (2 * p1.x + (-p0.x + p2.x) * t + (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 + (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3),
        y: 0.5 * (2 * p1.y + (-p0.y + p2.y) * t + (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 + (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3),
      });
    }
  }
  res.push(pts[n - 1]);
  return res;
};

const THREAD_VERT = /* glsl */ `
attribute float aSide;
varying float vSide;
void main(){
  vSide = aSide;
  gl_Position = projectionMatrix * viewMatrix * modelMatrix * vec4(position, 1.0);
}`;

const makeCoreMat = (core: Color, ink: Color) =>
  new ShaderMaterial({
    uniforms: {uCore: {value: core}, uInk: {value: ink}},
    vertexShader: THREAD_VERT,
    fragmentShader: /* glsl */ `
      uniform vec3 uCore; uniform vec3 uInk;
      varying float vSide;
      void main(){
        float a = abs(vSide);
        float aa = max(fwidth(vSide), 1e-3);
        float cov = 1.0 - smoothstep(1.0 - aa, 1.0 + aa*0.5, a);
        vec3 c = mix(uCore, uInk, smoothstep(0.55, 0.9, a));
        gl_FragColor = vec4(c, cov);
      }`,
    transparent: true,
    depthWrite: false,
    side: DoubleSide,
  });

const makeGlowMat = (glow: Color, strength: number) =>
  new ShaderMaterial({
    uniforms: {uGlow: {value: glow}, uStrength: {value: strength}},
    vertexShader: THREAD_VERT,
    fragmentShader: /* glsl */ `
      uniform vec3 uGlow; uniform float uStrength;
      varying float vSide;
      void main(){
        float a = abs(vSide);
        float g = exp(-a*a*4.0) * uStrength;
        gl_FragColor = vec4(uGlow * g, 1.0);
      }`,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
    side: DoubleSide,
  });

export type ThreadLook = {
  width?: number; // px
  core?: string;
  ink?: string;
  glow?: string;
  glowWidth?: number;
  glowStrength?: number;
  z?: (s: number) => number; // world height along the thread (s=0 at A)
  renderOrder?: number;
  visible?: (f: number) => boolean;
};

const MAX_PTS = 400;

export const RedThread: React.FC<{cfg: ThreadConfig; look?: ThreadLook; drawFrame: number; cam: CamPose}> = ({
  cfg,
  look = {},
  drawFrame,
  cam,
}) => {
  const width = look.width ?? 3.6;
  const glowWidth = look.glowWidth ?? 18;
  const {core, glow, geo, glowGeo} = useMemo(() => {
    const mk = () => {
      const g = new BufferGeometry();
      g.setAttribute('position', new BufferAttribute(new Float32Array(MAX_PTS * 2 * 3), 3));
      const side = new Float32Array(MAX_PTS * 2);
      for (let i = 0; i < MAX_PTS; i++) {
        side[i * 2] = -1;
        side[i * 2 + 1] = 1;
      }
      g.setAttribute('aSide', new BufferAttribute(side, 1));
      const idx: number[] = [];
      for (let i = 0; i < MAX_PTS - 1; i++) {
        const a = i * 2;
        idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
      }
      g.setIndex(idx);
      return g;
    };
    const geo = mk();
    const glowGeo = mk();
    const core = new Mesh(geo, makeCoreMat(new Color(look.core ?? '#e3262a'), new Color(look.ink ?? '#7a1016')));
    const glow = new Mesh(glowGeo, makeGlowMat(new Color(look.glow ?? '#ff3a30'), look.glowStrength ?? 0.12));
    core.frustumCulled = false;
    glow.frustumCulled = false;
    core.renderOrder = look.renderOrder ?? 4;
    glow.renderOrder = (look.renderOrder ?? 4) - 0.5;
    return {core, glow, geo, glowGeo};
  }, [look.core, look.ink, look.glow, look.glowStrength, look.renderOrder]);
  useEffect(
    () => () => {
      geo.dispose();
      glowGeo.dispose();
      (core.material as ShaderMaterial).dispose();
      (glow.material as ShaderMaterial).dispose();
    },
    [core, glow, geo, glowGeo],
  );

  const sim = simulateThread(cfg);
  const f = Math.max(0, Math.min(cfg.length - 1, drawFrame));
  const base = f * (sim.n + 1) * 2;
  const raw: Pt[] = [];
  for (let i = 0; i <= sim.n; i++) raw.push({x: sim.data[base + i * 2], y: sim.data[base + i * 2 + 1]});
  const pts = resample(raw, Math.max(1, Math.floor((MAX_PTS - 1) / sim.n)));
  const zf = look.z ?? (() => 1.5);

  const writeRibbon = (g: BufferGeometry, w: number) => {
    const pos = g.getAttribute('position') as BufferAttribute;
    const arr = pos.array as Float32Array;
    const n = Math.min(MAX_PTS, pts.length);
    for (let i = 0; i < MAX_PTS; i++) {
      const j = Math.min(i, n - 1);
      const p = pts[j];
      const pa = pts[Math.max(0, j - 1)];
      const pb = pts[Math.min(n - 1, j + 1)];
      let tx = pb.x - pa.x;
      let ty = pb.y - pa.y;
      const tl = Math.hypot(tx, ty) || 1;
      tx /= tl;
      ty /= tl;
      const nx = -ty;
      const ny = tx;
      const s = j / (n - 1);
      const z = zf(s);
      const l = screenToWorld(cam, p.x + (nx * w) / 2, p.y + (ny * w) / 2, z);
      const r = screenToWorld(cam, p.x - (nx * w) / 2, p.y - (ny * w) / 2, z);
      arr[i * 6] = l.x;
      arr[i * 6 + 1] = l.y;
      arr[i * 6 + 2] = z;
      arr[i * 6 + 3] = r.x;
      arr[i * 6 + 4] = r.y;
      arr[i * 6 + 5] = z;
    }
    pos.needsUpdate = true;
  };
  writeRibbon(geo, width);
  writeRibbon(glowGeo, glowWidth);
  const visible = look.visible ? look.visible(f) : true;
  return (
    <group visible={visible}>
      <primitive object={glow} />
      <primitive object={core} />
    </group>
  );
};
