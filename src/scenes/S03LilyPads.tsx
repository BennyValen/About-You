import React, {useMemo} from 'react';
import {BoxGeometry, CapsuleGeometry, CylinderGeometry, ExtrudeGeometry, Path, Shape, SphereGeometry, Vector4} from 'three';
import {CameraRig, CamPose, pose, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED} from '../kit/toon';
import {onTwos} from '../kit/frame';

// Scene 3: a rowing boat moves up a channel between lily pads; koi glide underneath.

const SPEED = 2.0;
const BOAT_SY = 1175; // screen y of the boat centre
const BOAT_LEN = 330;
const BOAT_W = 118;
const STROKE = 52; // frames per oar stroke

const camAt = (f: number): CamPose => pose(Math.sin(f * 0.006) * 4, SPEED * f, 1.0 + f * 0.00005);

// koi paths: each fish swims along a slow curve (world coordinates), drawn on twos
type Koi = {x0: number; y0: number; vx: number; vy: number; wob: number; len: number; phase: number};
const KOI: Koi[] = [
  {x0: -120, y0: 200, vx: 0.15, vy: 1.6, wob: 60, len: 150, phase: 0},
  {x0: 150, y0: 650, vx: -0.25, vy: 2.4, wob: 50, len: 135, phase: 1.3},
  {x0: -60, y0: -620, vx: 0.2, vy: 2.9, wob: 70, len: 128, phase: 2.1},
  {x0: 90, y0: -300, vx: -0.1, vy: 2.6, wob: 40, len: 120, phase: 0.6},
  {x0: -230, y0: 1100, vx: 0.35, vy: 1.2, wob: 55, len: 140, phase: 3.1},
  {x0: 260, y0: -900, vx: -0.3, vy: 3.2, wob: 45, len: 118, phase: 4.2},
  {x0: -150, y0: 1500, vx: 0.1, vy: 1.0, wob: 30, len: 132, phase: 5.0},
];
const koiAt = (k: Koi, f: number) => {
  const x = k.x0 + k.vx * f + Math.sin(f * 0.013 + k.phase) * k.wob;
  const y = k.y0 + k.vy * f;
  const dx = k.vx + Math.cos(f * 0.013 + k.phase) * k.wob * 0.013;
  const ang = Math.atan2(k.vy, dx);
  return {x, y, ang};
};

const GROUND = /* glsl */ `
uniform vec4 uKoi[7];       // x, y, heading, length
uniform float uKoiPh[7];
uniform vec4 uRip[4];       // ripple centre x,y, age (s), strength
const vec3 WATER = ${glc('#1f3c2e')};
const vec3 WATER_L = ${glc('#284a38')};
const vec3 WATER_D = ${glc('#173024')};
const vec3 DARKPAD = ${glc('#264a39')};
const vec3 DARKPAD_L = ${glc('#2f5743')};
const vec3 KOI = ${glc('#e2d6b4')};
const vec3 KOI_D = ${glc('#b9a888')};
const vec2 LP = vec2(-0.6, 0.8);

float density(vec2 p){
  float edge = 215.0 + 70.0 * gnoise(vec2(p.y * 0.0022, 3.0)) + 40.0 * gnoise(vec2(p.y * 0.006, 9.0));
  return abs(p.x - 20.0 * gnoise(vec2(p.y * 0.001, 1.0))) - edge;
}

// one lily pad: returns signed distance (px, <0 inside) and pad-local polar info
float padSdf(vec2 p, vec2 c, float R, float seed, out float ang, out float rr){
  vec2 d = p - c;
  float r = length(d);
  float a = atan(d.y, d.x);
  float wav = 1.0 + 0.025 * sin(a * 7.0 + seed * 6.0) + 0.02 * gnoise(vec2(a * 3.0, seed));
  float sd = r - R * wav;
  // notch (V cut) from the rim toward the centre
  float na = seed * 6.2831;
  float da = abs(mod(a - na + PI, 2.0 * PI) - PI);
  float notch = da * r - (0.4 + r * 0.035);
  sd = max(sd, mix(-1e3, -notch, step(R * 0.33, r)));
  ang = a; rr = r / R;
  return sd;
}

vec4 paint(vec2 p){
  // --- water with painted ripples
  float st = strokeField(p, 0.15, vec2(140.0, 7.0));
  vec3 col = cel3(WATER_D, WATER, WATER_L, st * 0.5 + 0.5, 0.25, 0.8);
  col *= brushMod(p, 0.1, 1.2, 0.08);
  // oar ripples: thin expanding rings
  for (int i = 0; i < 4; i++) {
    vec4 rp = uRip[i];
    if (rp.w <= 0.0) continue;
    float rad = 14.0 + rp.z * 55.0;
    float dist = length(p - rp.xy);
    float ring = inkBand(dist - rad, 1.2) + inkBand(dist - rad * 0.62, 1.0) * 0.7;
    col = mix(col, WATER_L * 1.6, ring * rp.w * (1.0 - smoothstep(0.6, 1.6, rp.z)));
  }

  float dn = density(p);
  // --- submerged dark pads (lower layer)
  float cellD = 150.0;
  vec2 g0 = floor(p / cellD);
  float bestD = 1e3; float bestR = 0.0; vec2 bestC = vec2(0.0);
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 g = g0 + vec2(float(i), float(j));
    vec3 h = hash32(g + 51.0);
    vec2 c = (g + 0.5 + (h.xy - 0.5) * 0.5) * cellD;
    if (density(c) < -60.0) continue;
    float R = mix(72.0, 104.0, h.z);
    float a, rr;
    float sd = padSdf(p, c, R, h.x * 3.0 + h.y, a, rr);
    if (sd < bestD) { bestD = sd; bestR = R; bestC = c; }
  }
  float inDark = fillCov(bestD);
  vec3 dp = mix(DARKPAD, DARKPAD_L, step(0.5, dot(normalize(p - bestC + 1e-3), normalize(LP)) * 0.5 + 0.5) * 0.6);
  dp *= brushMod(p, 0.7, 0.6, 0.06);
  col = mix(col, dp, inDark);
  col = mix(col, inkOf(DARKPAD) * 0.8, inkBand(bestD, 1.3) * 0.9);

  // --- koi, under the floating pads
  for (int i = 0; i < 7; i++) {
    vec4 k = uKoi[i];
    vec2 d = p - k.xy;
    if (dot(d, d) > k.w * k.w) continue;
    vec2 fwd = vec2(cos(k.z), sin(k.z));
    vec2 q = vec2(dot(d, fwd), dot(d, vec2(-fwd.y, fwd.x)));     // q.x forward
    float u = 0.5 - q.x / k.w;                                    // 0 at head, 1 at tail
    float sw = sin(u * 4.0 - uKoiPh[i]) * u * 9.0;               // swimming bend
    float lat = q.y - sw;
    float wprof = k.w * 0.085 * pow(max(sin(PI * clamp(u * 0.92 + 0.05, 0.0, 1.0)), 0.0), 0.75);
    float body = abs(lat) - wprof;
    if (u > 0.95 || u < 0.0) body = 1e3;
    // tail fan
    float tu = (u - 0.86) / 0.22;
    float tail = (tu > 0.0 && tu < 1.0) ? abs(lat) - k.w * 0.09 * tu : 1e3;
    // pectoral fins
    float fin = length(vec2(u - 0.3, (abs(lat) - wprof * 1.4) / k.w * 3.0)) * k.w - k.w * 0.05;
    float sdf = min(min(body, tail), fin);
    float cov = fillCov(sdf);
    vec3 kc = mix(KOI, KOI_D, hstep(0.0, -lat * sign(fwd.x + 0.001)) * 0.5);
    kc = mix(kc, inkOf(KOI) * 1.6, inkBand(sdf, 1.0));
    col = mix(col, kc, cov * 0.88);
  }

  // --- floating pads (top layer)
  float cell = 185.0;
  g0 = floor(p / cell);
  float topH = -1.0, topSd = 1e3, topA = 0.0, topRR = 0.0, topSeed = 0.0, topR = 0.0;
  vec3 topCol = vec3(0.0);
  float padShadow = 0.0;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 g = g0 + vec2(float(i), float(j));
    vec3 h = hash32(g + 7.0);
    vec2 c = (g + 0.5 + (h.xy - 0.5) * 0.45) * cell;
    if (density(c) < 0.0 || hash12(g + 3.3) < 0.08) continue;
    float R = mix(78.0, 150.0, pow(hash12(g + 1.9), 1.3));
    float a, rr;
    float seed = h.z * 7.0 + h.x;
    float sd = padSdf(p, c, R, seed, a, rr);
    float hgt = hash12(g + 8.8);
    if (sd < 0.0 && hgt > topH) {
      topH = hgt; topSd = sd; topA = a; topRR = rr; topSeed = seed; topR = R;
      float tone = hash12(g + 4.1);
      vec3 b = mix(${glc('#5a9450')}, ${glc('#8fb95c')}, step(0.3, tone));
      b = mix(b, ${glc('#b6d872')}, step(0.68, tone));
      topCol = b;
    }
    // cast shadow on the water
    float a2, rr2;
    float sds = padSdf(p - vec2(7.0, -9.0), c, R, seed, a2, rr2);
    padShadow = max(padShadow, fillCov(sds));
  }
  col = mix(col, col * vec3(0.55, 0.62, 0.6), padShadow * (1.0 - inDark * 0.3));
  if (topSd < 0.0) {
    // veins: radial lighter lines, cel shaded cup + curled rim
    float nv = floor(18.0 + fract(topSeed) * 8.0);
    float va = (fract((topA + topSeed) * nv / (2.0 * PI)) - 0.5) * (2.0 * PI / nv) * topRR * topR;
    float vein = (1.0 - hstep(0.8 + 0.9 * topRR, abs(va))) * step(0.06, topRR) * (1.0 - step(0.95, topRR));
    vec2 dir = vec2(cos(topA), sin(topA));
    float side = dot(dir, normalize(LP));
    float rim = smoothstep(0.86, 0.9, topRR);
    float lit = 0.62 - side * 0.25 * (1.0 - rim) + side * 0.45 * rim;
    vec3 pc = cel3(topCol * vec3(0.72, 0.78, 0.7), topCol, hiOf(topCol), lit, 0.42, 0.85);
    pc = mix(pc, hiOf(topCol) * 1.12, vein * 0.7);
    pc = mix(pc, hiOf(topCol) * 1.1, (1.0 - hstep(0.035, topRR)) * 0.8);
    pc *= brushMod(p, topA, 0.4, 0.06);
    col = pc;
  }
  float inkW = 1.1 + 0.8 * vnoise(p * 0.04);
  col = mix(col, inkOf(topCol) * 1.05, inkBand(topSd, inkW) * step(topSd, inkW + 1.0));
  return vec4(col, 1.0);
}
`;

// boat hull outline: pointed bow (+y), rounded stern
const hullShape = (len: number, w: number, inset = 0) => {
  const s = new Shape();
  const L = len / 2 - inset;
  const W = w / 2 - inset;
  s.moveTo(0, L);
  s.bezierCurveTo(W * 0.55, L * 0.78, W, L * 0.3, W, -L * 0.25);
  s.bezierCurveTo(W, -L * 0.75, W * 0.8, -L, 0, -L);
  s.bezierCurveTo(-W * 0.8, -L, -W, -L * 0.75, -W, -L * 0.25);
  s.bezierCurveTo(-W, L * 0.3, -W * 0.55, L * 0.78, 0, L);
  return s;
};

const boatGeos = () => {
  const outer = hullShape(BOAT_LEN, BOAT_W);
  const inner = hullShape(BOAT_LEN, BOAT_W, 10);
  const ring = hullShape(BOAT_LEN, BOAT_W);
  const hole = new Path(inner.getPoints(40).reverse());
  ring.holes.push(hole);
  return {
    gunwale: new ExtrudeGeometry(ring, {depth: 34, bevelEnabled: true, bevelThickness: 2, bevelSize: 2, bevelSegments: 1, curveSegments: 24}),
    floor: new ExtrudeGeometry(inner, {depth: 10, bevelEnabled: false, curveSegments: 24}),
    thwart: new BoxGeometry(BOAT_W - 8, 22, 5),
    plank: new BoxGeometry(2.5, BOAT_LEN * 0.7, 1),
    oar: new CylinderGeometry(3.2, 3.2, 210, 8),
    blade: new SphereGeometry(1, 12, 8),
    body: new CapsuleGeometry(20, 22, 6, 12),
    head: new SphereGeometry(15, 14, 10),
    arm: new CapsuleGeometry(5.5, 40, 4, 8),
    outerShape: outer,
  };
};

export const grade = () =>
  mkGrade({
    bloom: 0.45,
    bloomThreshold: 0.95,
    streak: 0.1,
    exposure: 1.04,
    lift: [0.0, 0.006, 0.01],
    saturation: 1.06,
    haze: 0.03,
    hazeColor: [0.7, 0.85, 0.75],
    vignette: 0.34,
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const boatY = cam.y - (BOAT_SY - 960) + 0;
  const boatX = cam.x * 0.0;
  const ground = usePaint(GROUND, {
    uKoi: {value: KOI.map(() => new Vector4())},
    uKoiPh: {value: KOI.map(() => 0)},
    uRip: {value: [0, 1, 2, 3].map(() => new Vector4())},
  });
  // koi on twos
  KOI.forEach((k, i) => {
    const s = koiAt(k, d);
    (ground.uniforms.uKoi.value as Vector4[])[i].set(s.x, s.y, s.ang, k.len);
    (ground.uniforms.uKoiPh.value as number[])[i] = d * 0.22 + k.phase;
  });
  // rowing: stroke phase on twos
  const ph = ((d % STROKE) / STROKE) * Math.PI * 2;
  const sweep = Math.sin(ph); // -1..1
  const oarAng = 0.62 + sweep * 0.38; // angle from the beam toward the bow
  const oarLift = Math.cos(ph) > 0 ? 6 : 0;
  // ripples where the blades enter the water: each catch leaves a ring pair fixed in the world
  const rips = ground.uniforms.uRip.value as Vector4[];
  const CATCH_A = 1.0;
  for (let i = 0; i < 2; i++) {
    const catchF = Math.floor((d - STROKE * 0.25) / STROKE) * STROKE + STROKE * 0.25 - i * STROKE;
    const age = (d - catchF) / 24;
    const yW = SPEED * catchF - (BOAT_SY - 960) + 8 + Math.sin(CATCH_A) * 168;
    const xW = BOAT_W / 2 + Math.cos(CATCH_A) * 168;
    const on = age >= 0 ? 1 : 0;
    rips[i * 2].set(xW, yW, age, on);
    rips[i * 2 + 1].set(-xW, yW, age, on);
  }

  SHARED.uLightDir.value.set(0.5, -0.6, -0.65).normalize();
  SHARED.uShadowColor.value.set('#3a5a48');
  SHARED.uShadowZ.value = 0.5;

  const g = useMemo(boatGeos, []);
  const boatS = worldToScreen(cam, boatX, boatY - BOAT_LEN / 2 + 4, 10);
  const oarPivotY = 8;
  const rowerY = -6;

  const oar = (sideSign: number) => {
    const a = oarAng;
    // oar runs from the handle (inboard) through the oarlock out to the blade
    const lockX = sideSign * (BOAT_W / 2);
    const dirX = sideSign * Math.cos(a);
    const dirY = Math.sin(a);
    const centerX = lockX + dirX * 70;
    const centerY = oarPivotY + dirY * 70;
    const rot = Math.atan2(dirY, dirX) - Math.PI / 2;
    const bladeX = lockX + dirX * 168;
    const bladeY = oarPivotY + dirY * 168;
    return (
      <group key={sideSign}>
        <Inked geometry={g.oar} color="#c49a62" position={[centerX, centerY, 40 + oarLift]} rotation={[0, 0, rot]} inkWidth={1.0} shadow />
        <Inked
          geometry={g.blade}
          color="#cfa36a"
          position={[bladeX, bladeY, 36 + oarLift]}
          rotation={[0, 0, rot]}
          scale={[9, 26, 2.5]}
          inkWidth={1.0}
          shadow
        />
      </group>
    );
  };

  // oar handles: 35 px inboard of the oarlocks
  const handle = (side: number) => ({x: side * (BOAT_W / 2 - Math.cos(oarAng) * 35), y: oarPivotY - Math.sin(oarAng) * 35});

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.8} color="#c8dccb" />
      <directionalLight position={[-500, 600, 650]} intensity={1.5} color="#fff3dc" />
      <PaintedPlane material={ground} cam={cam} />
      <group position={[boatX, boatY, 2]}>
        <Inked geometry={g.gunwale} color="#b9895a" ink="#5a3a22" inkWidth={2.2} shadow />
        <Inked geometry={g.floor} color="#9c7148" ink="#5a3a22" inkWidth={1.0} />
        {[-26, 0, 26].map((x) => (
          <Inked key={x} geometry={g.plank} color="#7f5a39" position={[x, -10, 11]} noInk />
        ))}
        {[92, oarPivotY - 14, -96].map((y) => (
          <Inked key={y} geometry={g.thwart} color="#c79a66" ink="#5a3a22" position={[0, y, 30]} inkWidth={1.2} />
        ))}
        {oar(1)}
        {oar(-1)}
        {/* rower: hunched in a purple-blue coat, leaning with the stroke */}
        <group position={[0, rowerY + sweep * 6, 36]}>
          <Inked geometry={g.body} color="#3f3f92" ink="#1d1a44" rotation={[0, 0, 0]} scale={[1.05, 0.85, 0.7]} inkWidth={1.6} shadow />
          <Inked geometry={g.head} color="#2c2748" ink="#141126" position={[0, 6 + sweep * 3, 26]} inkWidth={1.4} />
          {[1, -1].map((s) => {
            const h = handle(s);
            const hx = h.x;
            const hy = h.y - (rowerY + sweep * 6);
            const sx = s * 16;
            const sy = 8;
            const mx = (hx + sx) / 2;
            const my = (hy + sy) / 2;
            const ang = Math.atan2(hy - sy, hx - sx) - Math.PI / 2;
            const alen = Math.hypot(hx - sx, hy - sy);
            return (
              <Inked key={s} geometry={g.arm} color="#38388a" ink="#1d1a44" position={[mx, my, 10]} rotation={[0, 0, ang]} scale={[1, alen / 51, 1]} inkWidth={1.2} />
            );
          })}
        </group>
      </group>
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{
          id: 's03',
          length: len,
          a: () => ({x: boatS.sx, y: boatS.sy}),
          b: () => ({x: 530, y: 1990}),
          sway: 0.09,
          waves: 1.6,
          slack: 1.03,
          seed: 3,
        }}
        look={{z: (s) => 1.5 + (1 - s) * 10, width: 3.6}}
      />
    </>
  );
};

export {onTwos};
