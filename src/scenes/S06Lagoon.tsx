import React, {useMemo} from 'react';
import {
  BoxGeometry,
  BufferGeometry,
  CapsuleGeometry,
  CylinderGeometry,
  ExtrudeGeometry,
  Float32BufferAttribute,
  Path,
  Shape,
  SphereGeometry,
  Vector3,
  Vector4,
} from 'three';
import {CameraRig, CamPose, pose, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED} from '../kit/toon';

// Scene 6: a small sailboat crosses a turquoise lagoon of shallows, deep channels and coral
// heads. A manta ray glides ahead and to the left; turtles and starfish dot the seabed.

const SPEED = 3.5;
const BOAT_SY = 1180;
const BOAT_X = 25;
const BOAT_LEN = 300;
const BOAT_W = 112;

const camAt = (f: number): CamPose => pose(0, SPEED * f, 1.0 + f * 0.00004);

const mantaAt = (f: number) => ({x: -250 + 60 * Math.sin(f * 0.008 + 0.5), y: 560 + 1.92 * f});

const TURTLES = [
  {x0: 220, y0: 900, vx: -0.1, vy: 1.2, ph: 0},
  {x0: -330, y0: 1500, vx: 0.2, vy: 0.8, ph: 2},
  {x0: 300, y0: 2300, vx: -0.15, vy: 1.0, ph: 4},
];

const GROUND = /* glsl */ `
uniform vec2 uBoat;          // stern of the boat (world)
uniform vec4 uTurtle[3];     // x, y, heading, stroke phase
const vec3 DEEP = ${glc('#1f8eac')};
const vec3 MID = ${glc('#34a6bf')};
const vec3 SHAL = ${glc('#86d0d0')};
const vec3 SAND = ${glc('#d9f2ec')};
const vec3 SAND_L = ${glc('#f2fcf8')};
const vec3 FOAM = ${glc('#f4fbfa')};

float chan(vec2 p){
  vec2 q = p + 110.0 * vec2(fbm3(p * 0.0009 + 2.0), fbm3(p * 0.0009 + 9.0));
  float n = fbm3(q * 0.0007 + vec2(0.3, 1.7)) + 0.04 * gnoise(p * 0.006);
  float n2 = fbm3(q * 0.0011 + vec2(4.0, -2.0));
  return min(abs(n) / 0.115, abs(n2 - 0.22) / 0.05 + 0.5);   // 0 at channel centre, 1 at its bank
}

vec3 coralColor(float h){
  vec3 c = ${glc('#7a6aa2')};
  c = mix(c, ${glc('#6e8a52')}, step(0.22, h));
  c = mix(c, ${glc('#b8955e')}, step(0.52, h));
  c = mix(c, ${glc('#4a7466')}, step(0.68, h));
  c = mix(c, ${glc('#b98257')}, step(0.9, h));
  return c;
}

float starSdf(vec2 d, float R, float rot){
  float a = atan(d.y, d.x) + rot;
  float r = length(d);
  float k = 0.5 + 0.5 * cos(a * 5.0);
  return r - R * (0.38 + 0.62 * pow(k, 2.5));
}

vec4 paint(vec2 p){
  // --- water depth: deep turquoise channels winding through pale sandy shallows
  float c = chan(p);
  float depth = 1.0 - c;
  vec3 col = SAND;
  col = mix(col, SHAL, hstep(0.05, depth));
  col = mix(col, MID, hstep(0.4, depth));
  col = mix(col, DEEP, hstep(0.7, depth));
  // painterly white strokes and caustic streaks across the shallows
  float s1 = strokeField(p, 0.8, vec2(80.0, 5.0));
  float s2 = strokeField(p + 77.0, -0.6, vec2(60.0, 4.0));
  float strokes = max(hstep(0.35, s1), hstep(0.42, s2));
  col = mix(col, mix(SAND_L, SHAL * 1.15, hstep(0.28, depth)), strokes * 0.55);
  col *= brushMod(p, 0.4, 1.0, 0.07);
  col = mix(col, inkOf(MID) * 1.8, inkBand((depth - 0.28) * 90.0, 0.8) * 0.25);

  // --- starfish
  vec2 sg = floor(p / 150.0);
  vec3 sh3 = hash32(sg + 31.0);
  if (sh3.z < 0.16) {
    vec2 sc = (sg + 0.5 + (sh3.xy - 0.5) * 0.6) * 150.0;
    float R = 11.0 + 6.0 * sh3.x;
    float sd = starSdf(p - sc, R, sh3.y * 6.28);
    vec3 stc = sh3.x < 0.6 ? ${glc('#4c5fae')} : ${glc('#d29a48')};
    col = mix(col, stc, fillCov(sd));
    col = mix(col, inkOf(stc), inkBand(sd, 0.8));
  }

  // --- turtles (on twos via the uniforms)
  for (int i = 0; i < 3; i++) {
    vec4 t = uTurtle[i];
    vec2 d = p - t.xy;
    if (dot(d, d) > 90.0 * 90.0) continue;
    vec2 fw = vec2(cos(t.z), sin(t.z));
    vec2 q = vec2(dot(d, vec2(fw.y, -fw.x)), dot(d, fw));   // q.y forward
    float shell = length(q / vec2(24.0, 30.0)) - 1.0;
    float head = length(q - vec2(0.0, 36.0)) - 9.0;
    float st = sin(t.w);
    vec2 fl = vec2(abs(q.x) - 30.0, q.y - 14.0);
    fl = rot2(fl, -0.5 * sign(q.x) * (0.6 + 0.6 * st));
    float flip = length(fl / vec2(18.0, 7.0)) - 1.0;
    vec2 bl = vec2(abs(q.x) - 18.0, q.y + 26.0);
    float back = length(bl / vec2(8.0, 6.0)) - 1.0;
    float body = min(min(shell * 24.0, head), min(flip * 7.0, back * 6.0));
    vec3 tc = ${glc('#8f9c7c')};
    vec3 shc = mix(${glc('#6f7f5e')}, ${glc('#9aa886')}, step(0.5, fract(length(q) / 9.0)));
    vec3 cc = mix(tc, shc, fillCov(shell * 24.0 + 3.0));
    cc = mix(cc, inkOf(tc) * 1.2, inkBand(body, 1.0));
    col = mix(col, mix(cc, col, 0.22), fillCov(body));
  }

  // --- coral heads: noisy lobed masses made of small shaded knobs, mottled colours, inked edge
  float cell = 240.0;
  vec2 g0 = floor(p / cell);
  float best = 1e3; float bestId = 0.0; vec2 bestC = vec2(0.0); float bestR = 1.0;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 g = g0 + vec2(float(i), float(j));
    vec3 h = hash32(g + 13.0);
    vec2 cc = (g + 0.5 + (h.xy - 0.5) * 0.5) * cell;
    float side = smoothstep(150.0, 420.0, abs(cc.x - ${BOAT_X.toFixed(1)}));
    if (h.z > 0.34 + 0.45 * side) continue;
    float R = mix(22.0, 52.0, hash12(g + 2.0)) * (1.0 + side * 0.8);
    vec2 dd = p - cc;
    float lobes = length(dd) - R;
    vec2 off = (hash22(g + 4.0) - 0.5) * R * 1.4;
    lobes = min(lobes, length(dd - off) - R * 0.7);
    vec2 off2 = (hash22(g + 8.0) - 0.5) * R * 1.6;
    lobes = min(lobes, length(dd - off2) - R * 0.55);
    lobes += R * 0.5 * fbm3(p / (R * 0.6) + h.xy * 20.0) + 5.0 * gnoise(p * 0.08);
    if (lobes < best) { best = lobes; bestId = hash12(g + 6.0); bestC = cc; bestR = R; }
  }
  if (best < 2.0) {
    vec2 kid, kc;
    vec3 kv = voronoi(p / 13.0, 0.9, kid, kc);
    vec2 kd = (p - kc * 13.0) / 9.0;
    vec3 n = normalize(vec3(kd, sqrt(max(0.0, 1.0 - dot(kd, kd)))));
    float lit = dot(n, normalize(vec3(-0.5, 0.55, 0.65)));
    float tone = fract(bestId * 3.7 + fbm3(p * 0.012 + bestId * 10.0) * 0.8 + hash12(kid) * 0.22);
    vec3 base = coralColor(tone);
    base = mix(base, vec3(luma(base)), 0.22);
    vec3 cc3 = cel3(shadeOf(base), base, hiOf(base), lit, 0.3, 0.86);
    cc3 = mix(cc3, inkOf(base) * 1.3, inkBand(kv.z * 13.0, 0.7) * 0.55);
    float cov = fillCov(best);
    col = mix(col, cc3, cov);
    col = mix(col, inkOf(base) * 0.85, inkBand(best, 1.2) * step(best, 3.0));
  } else {
    // soft dark halo of the reef on the sand
    col *= mix(1.0, 0.86, (1.0 - smoothstep(2.0, 26.0, best)));
  }

  // --- wake: foam bubbles trailing the stern
  float dy = uBoat.y - p.y;
  if (dy > -10.0 && dy < 700.0) {
    float wdt = 14.0 + dy * 0.1;
    float lat = abs(p.x - uBoat.x);
    float zone = (1.0 - smoothstep(wdt * 0.6, wdt, lat)) * (1.0 - smoothstep(150.0, 700.0, dy));
    vec2 fid, fc2;
    vec3 fv = voronoi(p / 7.0, 1.0, fid, fc2);
    float bub = fillCov(fv.x * 7.0 - 1.6 - 1.2 * hash12(fid)) * step(1.0 - zone * 0.9, hash12(fid + 3.0));
    col = mix(col, FOAM, bub * 0.85);
  }
  return vec4(col, 1.0);
}
`;

const hullShape = (len: number, w: number, inset = 0) => {
  const s = new Shape();
  const L = len / 2 - inset;
  const W = w / 2 - inset;
  s.moveTo(0, L);
  s.bezierCurveTo(W * 0.6, L * 0.8, W, L * 0.32, W, -L * 0.3);
  s.bezierCurveTo(W, -L * 0.85, W * 0.75, -L, 0, -L);
  s.bezierCurveTo(-W * 0.75, -L, -W, -L * 0.85, -W, -L * 0.3);
  s.bezierCurveTo(-W, L * 0.32, -W * 0.6, L * 0.8, 0, L);
  return s;
};

// billowed triangular sail between mast foot A, masthead B and clew C
const sailGeometry = (A: Vector3, B: Vector3, C: Vector3, billow: number) => {
  const N = 14;
  const pos: number[] = [];
  const idx: number[] = [];
  const n = new Vector3().subVectors(B, A).cross(new Vector3().subVectors(C, A)).normalize();
  const id = (i: number, j: number) => (i * (2 * N + 3 - i)) / 2 + j;
  for (let i = 0; i <= N; i++) {
    for (let j = 0; j <= N - i; j++) {
      const u = i / N;
      const v = j / N;
      const w = 1 - u - v;
      const p = new Vector3().addScaledVector(A, w).addScaledVector(B, u).addScaledVector(C, v);
      p.addScaledVector(n, billow * 27 * u * v * w);
      pos.push(p.x, p.y, p.z);
    }
  }
  for (let i = 0; i < N; i++) {
    for (let j = 0; j < N - i; j++) {
      idx.push(id(i, j), id(i + 1, j), id(i, j + 1));
      if (j < N - i - 1) idx.push(id(i + 1, j), id(i + 1, j + 1), id(i, j + 1));
    }
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
};

const mantaShape = () => {
  const s = new Shape();
  s.moveTo(0, 70);
  s.bezierCurveTo(30, 66, 60, 40, 140, 6);
  s.bezierCurveTo(110, -10, 60, -40, 18, -58);
  s.lineTo(0, -64);
  s.lineTo(-18, -58);
  s.bezierCurveTo(-60, -40, -110, -10, -140, 6);
  s.bezierCurveTo(-60, 40, -30, 66, 0, 70);
  return s;
};

export const grade = () =>
  mkGrade({
    bloom: 0.5,
    bloomThreshold: 0.95,
    streak: 0.12,
    exposure: 1.0,
    lift: [0.0, 0.006, 0.012],
    saturation: 1.05,
    haze: 0.04,
    hazeColor: [0.85, 0.97, 0.97],
    splitHigh: [0.0, 0.01, 0.01],
    gain: [0.99, 1.0, 1.01],
    vignette: 0.28,
    shafts: 0.015,
    shaftAngle: -0.7,
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const by = cam.y - (BOAT_SY - 960);
  const ground = usePaint(GROUND, {uBoat: {value: [0, 0]}, uTurtle: {value: TURTLES.map(() => new Vector4())}});
  ground.uniforms.uBoat.value = [BOAT_X, by - BOAT_LEN / 2];
  TURTLES.forEach((t, i) => {
    const x = t.x0 + t.vx * d;
    const y = t.y0 + t.vy * d;
    (ground.uniforms.uTurtle.value as Vector4[])[i].set(x, y, Math.atan2(t.vy, t.vx), d * 0.12 + t.ph);
  });

  SHARED.uLightDir.value.set(0.55, -0.5, -0.67).normalize();
  SHARED.uShadowColor.value.set('#1a6a80');
  SHARED.uShadowAlpha.value = 0.42;
  SHARED.uShadowZ.value = 0.5;
  SHARED.uShadowDepth.value = 60;

  const g = useMemo(() => {
    const ring = hullShape(BOAT_LEN, BOAT_W);
    ring.holes.push(new Path(hullShape(BOAT_LEN, BOAT_W, 9).getPoints(40).reverse()));
    const heel = 0.95;
    const A = new Vector3(0, 70, 0);
    const B = new Vector3(0, 76, 280);
    const C = new Vector3(0, -96, 16);
    const rot = (v: Vector3) => v.clone().applyAxisAngle(new Vector3(0, 1, 0), heel);
    return {
      gunwale: new ExtrudeGeometry(ring, {depth: 30, bevelEnabled: true, bevelThickness: 2, bevelSize: 2, bevelSegments: 1, curveSegments: 24}),
      floor: new ExtrudeGeometry(hullShape(BOAT_LEN, BOAT_W, 9), {depth: 10, bevelEnabled: false, curveSegments: 24}),
      thwart: new BoxGeometry(BOAT_W - 8, 18, 5),
      plank: new BoxGeometry(2.5, BOAT_LEN * 0.72, 1),
      sail: sailGeometry(rot(A), rot(B), rot(C), 1.2),
      mast: new CylinderGeometry(3, 3, 286, 8),
      boom: new CylinderGeometry(2.6, 2.6, 176, 8),
      body: new CapsuleGeometry(15, 34, 5, 10),
      head: new SphereGeometry(12, 12, 8),
      limb: new CapsuleGeometry(5, 30, 3, 8),
      manta: new ExtrudeGeometry(mantaShape(), {depth: 6, bevelEnabled: true, bevelThickness: 4, bevelSize: 5, bevelSegments: 2, curveSegments: 16}),
      horn: new CapsuleGeometry(4, 18, 3, 6),
      tail: new CapsuleGeometry(2, 70, 2, 6),
      heel,
    };
  }, []);

  const m = mantaAt(d);
  const flap = Math.sin(d * 0.09);
  const tailS = worldToScreen(cam, BOAT_X, by - BOAT_LEN / 2 + 2, 6);

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.85} color="#d8f0ee" />
      <directionalLight position={[-550, 500, 670]} intensity={1.45} color="#fff6e6" />
      <PaintedPlane material={ground} cam={cam} />
      {/* manta ray, gliding just under the surface */}
      <group position={[m.x, m.y, 6]} rotation={[0, 0, 0.12 * Math.sin(d * 0.01)]}>
        <Inked geometry={g.manta} color="#4a5c6c" ink="#1b242e" scale={[1 - 0.12 * Math.abs(flap), 1, 1]} inkWidth={1.8} shadow shadowMode="tint" />
        <Inked geometry={g.horn} color="#36444f" ink="#1b242e" position={[16, 74, 6]} rotation={[0, 0, -0.2]} inkWidth={1} />
        <Inked geometry={g.horn} color="#36444f" ink="#1b242e" position={[-16, 74, 6]} rotation={[0, 0, 0.2]} inkWidth={1} />
        <Inked geometry={g.tail} color="#33414c" ink="#1b242e" position={[0, -100, 4]} inkWidth={0.8} />
      </group>
      {/* sailboat */}
      <group position={[BOAT_X, by, 2]}>
        <Inked geometry={g.gunwale} color="#c8955c" ink="#5e3c20" inkWidth={2.2} shadow shadowMode="tint" />
        <Inked geometry={g.floor} color="#b07e4c" ink="#5e3c20" inkWidth={1} />
        {[-24, 0, 24].map((x) => (
          <Inked key={x} geometry={g.plank} color="#8a6038" position={[x, -6, 11]} noInk />
        ))}
        {[60, -10, -90].map((y) => (
          <Inked key={y} geometry={g.thwart} color="#d2a26a" ink="#5e3c20" position={[0, y, 27]} inkWidth={1.1} />
        ))}
        <group rotation={[0, g.heel, 0]}>
          <Inked geometry={g.mast} color="#a77a4c" ink="#4a2e18" position={[0, 72, 143]} rotation={[Math.PI / 2, 0, 0]} inkWidth={1} shadow shadowMode="tint" />
          <Inked geometry={g.boom} color="#a77a4c" ink="#4a2e18" position={[0, -10, 15]} inkWidth={1} shadow shadowMode="tint" />
        </group>
        <Inked geometry={g.sail} color="#f3f1ea" ink="#8a8a92" inkWidth={1.4} toon={{side: 2}} shadow shadowMode="tint" />
        {/* sailor hiking out over the left gunwale */}
        <group position={[-BOAT_W / 2 - 4, -40, 34]}>
          <Inked geometry={g.body} color="#2f3672" ink="#151838" rotation={[0, 0, Math.PI / 2 - 0.25]} inkWidth={1.4} shadow shadowMode="tint" />
          <Inked geometry={g.head} color="#1f1a22" ink="#0c0a0e" position={[-36, 8, 6]} inkWidth={1.2} shadow shadowMode="tint" />
          <Inked geometry={g.limb} color="#2f3672" ink="#151838" position={[10, 26, 2]} rotation={[0, 0, -0.9]} inkWidth={1} />
          <Inked geometry={g.limb} color="#2b2f5e" ink="#151838" position={[30, -12, -4]} rotation={[0, 0, 1.2]} inkWidth={1} />
        </group>
      </group>
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{id: 's06', length: len, a: () => ({x: tailS.sx, y: tailS.sy}), b: () => ({x: 560, y: 1990}), sway: 0.05, waves: 1.4, slack: 1.015, seed: 6}}
        look={{z: () => 3, width: 3.4}}
      />
    </>
  );
};
