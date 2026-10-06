import React, {useMemo} from 'react';
import {BoxGeometry, BufferAttribute, CapsuleGeometry, CylinderGeometry, IcosahedronGeometry, SphereGeometry, Vector3} from 'three';
import {CameraRig, CamPose, pose, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked, InkedInstances, Instance} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED, makeGradient} from '../kit/toon';

const TREE_GRAD = makeGradient(0.0, 0.5, [0.4, 0.74, 1.0]);
import {mulberry32, rrange} from '../kit/random';

// Scene 9: a cyclist rides up a lakeside path under big fluffy trees.

const SPEED = 4.0;
const RIDER_SY = 1180;
const PATH_X = 0; // path centre (world); the lake lies left of x = -100
const PEDAL = 20;

const camAt = (f: number): CamPose => pose(0, SPEED * f, 1.0 + f * 0.00005);

const GROUND = /* glsl */ `
const vec3 WATER = ${glc('#0f2322')};
const vec3 WATER_L = ${glc('#3d4f42')};
const vec3 GRASS = ${glc('#3d8a3a')};
const vec3 GRASS_D = ${glc('#2a6a30')};
const vec3 GRASS_L = ${glc('#5aa646')};
const vec3 PATH = ${glc('#d9c99c')};
const vec3 PATH_L = ${glc('#e9dcb4')};
const vec3 PAD = ${glc('#5fa04a')};
const vec3 DOCK = ${glc('#9a7a58')};

float shoreX(float y){ return -96.0 + 10.0 * gnoise(vec2(y * 0.004, 1.0)); }

vec4 paint(vec2 p){
  float sx = shoreX(p.y);
  // lawn with streaky grass strokes
  float g1 = strokeField(p, 1.05, vec2(36.0, 2.2));
  float g2 = strokeField(p + 50.0, 0.75, vec2(22.0, 1.8));
  vec3 col = cel3(GRASS_D, GRASS, GRASS_L, 0.5 + 0.35 * g1 + 0.2 * g2 + 0.25 * fbm3(p * 0.003), 0.32, 0.78);
  // path
  float px = abs(p.x - ${PATH_X.toFixed(1)} - 6.0 * gnoise(vec2(p.y * 0.003, 4.0)));
  float edge = 58.0 + 4.0 * gnoise(vec2(p.y * 0.05, 2.0)) + 3.0 * gnoise(vec2(p.y * 0.2, 7.0));
  float onPath = 1.0 - hstep(edge, px);
  vec3 pc = mix(PATH, PATH_L, hstep(0.25, strokeField(p, 1.57, vec2(90.0, 6.0))) * 0.6);
  pc = mix(pc, PATH * 0.86, step(0.8, hash12(floor(p / 4.0))) * 0.5);
  col = mix(col, pc, onPath);
  col = mix(col, inkOf(PATH) * 1.6, inkBand(px - edge, 0.9) * 0.6);
  // lake: dark water with horizontal reflection streaks
  float inLake = 1.0 - hstep(sx, p.x);
  float rs = strokeField(p * vec2(1.0, 1.0), 0.0, vec2(120.0, 3.0));
  float rs2 = strokeField(p + 31.0, 0.0, vec2(60.0, 1.6));
  vec3 wc = mix(WATER, WATER_L, max(hstep(0.4, rs), hstep(0.5, rs2) * 0.7) * 0.9);
  wc = mix(wc, WATER * 0.7, hstep(0.2, fbm3(p * 0.002 + 9.0)) * 0.5);
  col = mix(col, wc, inLake);
  // dark shore line + reeds
  col = mix(col, ${glc('#0b130d')}, inkBand(p.x - sx, 2.2));
  float reed = step(0.86, hash12(floor(vec2(p.y / 12.0, 3.0)))) * (1.0 - hstep(10.0, abs(p.x - sx - 6.0))) * step(fract(p.y / 12.0), 0.25);
  col = mix(col, GRASS_L * 0.9, reed);
  // lily pads in small clusters near the shore
  vec2 lg = floor(p / 70.0);
  vec3 lh = hash32(lg + 41.0);
  vec2 lc = (lg + 0.5 + (lh.xy - 0.5) * 0.5) * 70.0;
  float nearShore = 1.0 - smoothstep(30.0, 230.0, sx - lc.x);
  if (lh.z < 0.5 * nearShore && lc.x < sx - 20.0) {
    vec2 dd = p - lc;
    float r = length(dd) - (11.0 + 6.0 * lh.x);
    float notch = abs(mod(atan(dd.y, dd.x) - lh.y * 6.28 + PI, 2.0 * PI) - PI) * length(dd) - 1.5;
    r = max(r, -notch);
    col = mix(col, cel3(PAD * 0.75, PAD, hiOf(PAD), 0.5 + 0.4 * dot(normalize(dd + 1e-3), vec2(-0.6, 0.8)), 0.3, 0.8), fillCov(r));
    col = mix(col, inkOf(PAD), inkBand(r, 0.8));
  }
  // small wooden dock at the top-left of the route
  vec2 dq = p - vec2(sx - 70.0, 2050.0);
  float dock = max(abs(dq.x) - 70.0, abs(dq.y) - 26.0);
  col = mix(col, mix(DOCK, DOCK * 0.8, step(0.5, fract(dq.x / 12.0))), fillCov(dock));
  col = mix(col, inkOf(DOCK), inkBand(dock, 1.0));
  col *= brushMod(p, 0.9, 1.0, 0.05);
  return vec4(col, 1.0);
}
`;

// sea-urchin-like spiky ball: a fluffy canopy clump
const spikyBall = (seed: number) => {
  const g = new IcosahedronGeometry(1, 4);
  const rng = mulberry32(seed);
  const dirs: Vector3[] = [];
  for (let i = 0; i < 150; i++) {
    const v = new Vector3(rrange(rng, -1, 1), rrange(rng, -1, 1), rrange(rng, -1, 1)).normalize();
    dirs.push(v);
  }
  const pos = g.getAttribute('position') as BufferAttribute;
  const v = new Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i).normalize();
    let m = 0;
    for (const d of dirs) m = Math.max(m, Math.pow(Math.max(0, v.dot(d)), 18));
    const s = 0.74 + 0.5 * m;
    pos.setXYZ(i, v.x * s, v.y * s, v.z * s * 0.8);
  }
  g.computeVertexNormals();
  return g;
};

export const grade = () =>
  mkGrade({
    bloom: 0.45,
    bloomThreshold: 0.95,
    streak: 0.1,
    exposure: 1.04,
    lift: [0.0, 0.008, 0.012],
    saturation: 1.06,
    haze: 0.04,
    hazeColor: [0.8, 0.9, 0.75],
    vignette: 0.34,
    shafts: 0.035,
    shaftAngle: -0.75,
    shaftColor: [1.0, 0.98, 0.85],
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const ry = cam.y - (RIDER_SY - 960);
  const ground = usePaint(GROUND);

  SHARED.uLightDir.value.set(0.55, -0.55, -0.62).normalize();
  SHARED.uShadowColor.value.set('#2a4a2c');
  SHARED.uShadowZ.value = 0.5;

  const g = useMemo(
    () => ({
      ball: spikyBall(909),
      ball2: spikyBall(4242),
      bench: new BoxGeometry(18, 70, 8),
      wheel: new CapsuleGeometry(2.5, 42, 3, 6),
      frame: new BoxGeometry(5, 50, 4),
      torso: new CapsuleGeometry(12, 22, 4, 10),
      hat: new CylinderGeometry(16, 16, 3, 18).rotateX(Math.PI / 2),
      head: new SphereGeometry(9, 12, 8),
      limb: new CapsuleGeometry(4, 26, 3, 6),
      bar: new BoxGeometry(34, 3, 3),
    }),
    [],
  );

  const {clumpsA, clumpsB, benches} = useMemo(() => {
    const rng = mulberry32(99);
    const A: Instance[] = [];
    const B: Instance[] = [];
    const yMax = SPEED * len + 2600;
    const trees: {x: number; y: number; r: number}[] = [];
    // big trees overhanging the path on the lake side, smaller ones on the lawn
    for (let y = -900; y < yMax; y += rrange(rng, 380, 520)) trees.push({x: rrange(rng, -360, -280), y, r: rrange(rng, 165, 215)});
    for (let y = -700; y < yMax; y += rrange(rng, 300, 420)) trees.push({x: rrange(rng, 170, 420), y, r: rrange(rng, 80, 130)});
    for (let y = -800; y < yMax; y += rrange(rng, 420, 600)) trees.push({x: rrange(rng, 300, 560), y: y + 150, r: rrange(rng, 120, 170)});
    for (const t of trees) {
      const n = Math.round(4 + t.r / 40);
      for (let i = 0; i < n; i++) {
        const a = rrange(rng, 0, Math.PI * 2);
        const rr = (i === 0 ? 0 : rrange(rng, 0.25, 0.62)) * t.r;
        const s = t.r * (i === 0 ? 0.55 : rrange(rng, 0.32, 0.46));
        const tone = rng();
        const color = tone < 0.33 ? '#6aa83a' : tone < 0.66 ? '#86c046' : '#a2d052';
        const inst: Instance = {x: t.x + Math.cos(a) * rr, y: t.y + Math.sin(a) * rr, z: t.r * 0.9 + rrange(rng, -10, 30) - rr * 0.3, s, rz: rrange(rng, 0, 6.28), color};
        (rng() < 0.5 ? A : B).push(inst);
      }
    }
    const benches: number[] = [];
    for (let y = 300; y < yMax; y += rrange(rng, 700, 1100)) benches.push(y);
    return {clumpsA: A, clumpsB: B, benches};
  }, [len]);

  // pedalling on twos
  const ph = (d / PEDAL) * Math.PI * 2;
  const tail = worldToScreen(cam, PATH_X - 6, ry - 46, 4);

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.7} color="#cfe6c4" />
      <directionalLight position={[-550, 550, 620]} intensity={1.75} color="#fff8dc" />
      <PaintedPlane material={ground} cam={cam} />
      {benches.map((y) => (
        <Inked key={y} geometry={g.bench} color="#8a5a36" ink="#3a2414" position={[72, y, 10]} inkWidth={1.2} shadow />
      ))}
      {/* cyclist */}
      <group position={[PATH_X - 6, ry, 0]}>
        <Inked geometry={g.wheel} color="#1b1b1e" position={[0, 34, 26]} inkWidth={0.8} shadow />
        <Inked geometry={g.wheel} color="#1b1b1e" position={[0, -34, 26]} inkWidth={0.8} shadow />
        <Inked geometry={g.frame} color="#2c2c34" position={[0, 0, 40]} inkWidth={0.8} shadow />
        <Inked geometry={g.bar} color="#3a3a42" position={[0, 34, 62]} inkWidth={0.7} shadow />
        <Inked geometry={g.limb} color="#232328" position={[-9, -6 + Math.sin(ph) * 9, 46]} inkWidth={0.8} shadow />
        <Inked geometry={g.limb} color="#232328" position={[9, -6 - Math.sin(ph) * 9, 46]} inkWidth={0.8} shadow />
        <Inked geometry={g.torso} color="#dcdad2" ink="#6e6c64" position={[0, 0, 74]} rotation={[0.9, 0, 0]} inkWidth={1.2} shadow />
        <Inked geometry={g.limb} color="#d0cec6" ink="#6e6c64" position={[-11, 22, 70]} rotation={[0.3, 0, 0.2]} inkWidth={0.8} />
        <Inked geometry={g.limb} color="#d0cec6" ink="#6e6c64" position={[11, 22, 70]} rotation={[0.3, 0, -0.2]} inkWidth={0.8} />
        <Inked geometry={g.head} color="#3a2e28" position={[0, 16, 92]} inkWidth={0.8} />
        <Inked geometry={g.hat} color="#d8c08a" ink="#6e5a34" position={[0, 16, 100]} inkWidth={1.0} shadow />
      </group>
      <InkedInstances geometry={g.ball} items={clumpsA} inkWidth={2.6} inkMul={[0.22, 0.32, 0.2]} toon={{fur: 1, gradient: TREE_GRAD}} shadow shadowStrength={1} />
      <InkedInstances geometry={g.ball2} items={clumpsB} inkWidth={2.6} inkMul={[0.22, 0.32, 0.2]} toon={{fur: 1, gradient: TREE_GRAD}} shadow shadowStrength={1} />
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{id: 's09', length: len, a: () => ({x: tail.sx, y: tail.sy}), b: () => ({x: 500, y: 1990}), sway: 0.04, waves: 1.2, slack: 1.012, seed: 9}}
        look={{z: () => 2, width: 3.2}}
      />
    </>
  );
};
