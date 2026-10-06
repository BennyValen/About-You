import React, {useMemo} from 'react';
import {CapsuleGeometry, CylinderGeometry, SphereGeometry} from 'three';
import {CameraRig, CamPose, pose, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked, InkedInstances, Instance} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED, makeGradient} from '../kit/toon';
import {spikyBall} from '../kit/shapes';
import {mulberry32, rrange} from '../kit/random';

// Scene 10: late afternoon. A walker follows a dirt path between sunflower fields and a
// harvested field with round hay bales; the low sun stretches every shadow to the lower left.

const SPEED = 3.0;
const WALKER_SY = 1180;
const WALKER_X = 60;
const STEP = 26;
const ROAD_K = 0.2125; // diagonal road: y = ROAD_Y0 + ROAD_K * x
const ROAD_Y0 = 420;

const camAt = (f: number): CamPose => pose(Math.sin(f * 0.003) * 10 + f * 0.02, SPEED * f, 1.0 + f * 0.00006);

const GROUND = /* glsl */ `
const vec3 STUB = ${glc('#c9a865')};
const vec3 STUB_L = ${glc('#dcc07a')};
const vec3 STUB_D = ${glc('#a8874e')};
const vec3 SOIL = ${glc('#43301f')};
const vec3 SOIL_L = ${glc('#5c432a')};
const vec3 LEAF = ${glc('#7d7c50')};
const vec3 LEAF_D = ${glc('#56553a')};
const vec3 PETAL = ${glc('#e8b832')};
const vec3 PETAL_D = ${glc('#c98f22')};
const vec3 DISC = ${glc('#5a3a1e')};
const vec3 PATHC = ${glc('#cbb37a')};
const vec3 ROADC = ${glc('#8f7558')};
const vec3 STONE = ${glc('#c8c4be')};

float roadD(vec2 p){ return (p.y - (${ROAD_Y0.toFixed(1)} + ${ROAD_K} * p.x)) * 0.978; }

vec4 paint(vec2 p){
  float rd = roadD(p);
  float px = p.x - ${WALKER_X.toFixed(1)} - 8.0 * gnoise(vec2(p.y * 0.004, 2.0));
  float pathW = 44.0 + 6.0 * gnoise(vec2(p.y * 0.02, 5.0));
  vec3 col;
  bool left = px < -pathW;
  bool above = rd > 36.0 && p.y < 1440.0 + 20.0 * gnoise(vec2(p.x * 0.01, 3.0));
  if (left && above) {
    // harvested field: golden stubble in fine rows
    float rows = sin((p.x * 0.35 + p.y * 0.94) * 0.42 + 2.0 * gnoise(p * 0.01));
    col = mix(STUB, STUB_L, hstep(0.4, rows) * 0.6);
    col = mix(col, STUB_D, hstep(0.75, -rows) * 0.35);
    col *= brushMod(p, 0.35, 0.8, 0.08);
    // field margin
    col = mix(col, STUB_D * 0.9, inkBand(-px - pathW - 30.0, 6.0) * 0.5);
  } else {
    // sunflower rows on dark soil
    vec2 q = rot2(p, 0.05);
    vec2 cell = vec2(86.0, 70.0);
    vec2 g = floor(q / cell);
    col = mix(SOIL, SOIL_L, hstep(0.3, fbm3(p * 0.02)) * 0.5);
    float best = 1e3; vec3 fc = col;
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
      vec2 gg = g + vec2(float(i), float(j));
      vec3 h = hash32(gg + 77.0);
      vec2 c = (gg + 0.5 + (h.xy - 0.5) * 0.35) * cell;
      vec2 d = q - c;
      // leaves: a few grey-green ovals around each stem
      for (int k = 0; k < 3; k++) {
        float a = h.z * 6.28 + float(k) * 2.1;
        vec2 lc = vec2(cos(a), sin(a)) * 28.0;
        vec2 ld = rot2(d - lc, -a);
        float l = length(ld / vec2(27.0, 15.0)) - 1.0;
        if (l < 0.0) {
          float lit = 0.5 + 0.5 * dot(normalize(lc), vec2(0.6, 0.7));
          fc = mix(fc, cel3(LEAF_D, LEAF, hiOf(LEAF), lit, 0.35, 0.8), 1.0);
          best = min(best, l * 13.0);
        }
      }
    }
    col = fc;
    col = mix(col, inkOf(LEAF), inkBand(best, 0.8) * 0.7);
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
      vec2 gg = g + vec2(float(i), float(j));
      vec3 h = hash32(gg + 77.0);
      vec2 c = (gg + 0.5 + (h.xy - 0.5) * 0.35) * cell + vec2(0.0, 4.0);
      vec2 d = q - c;
      float r = length(d);
      float R = 25.0 + 4.0 * h.x;
      float a = atan(d.y, d.x);
      float petals = R * (0.86 + 0.14 * cos(a * 13.0 + h.y * 6.0));
      float sd = r - petals;
      if (sd < 1.0) {
        vec3 pc = mix(PETAL_D, PETAL, step(0.0, dot(d, vec2(0.6, 0.7))));
        pc = mix(pc, DISC, 1.0 - hstep(R * 0.48, r));
        pc = mix(pc, DISC * 1.4, (1.0 - hstep(R * 0.3, r)) * step(0.5, hash12(floor(d / 3.0) + gg)) * 0.6);
        col = mix(col, pc, fillCov(sd));
        col = mix(col, inkOf(PETAL), inkBand(sd, 0.9) * 0.8);
      }
    }
  }
  // diagonal dirt road with wheel ruts and a few pale stones
  float onRoad = 1.0 - hstep(34.0, abs(rd) + 3.0 * gnoise(p * 0.03));
  vec3 rc = mix(ROADC, ROADC * 1.15, hstep(0.3, strokeField(p, 0.21, vec2(80.0, 4.0))) * 0.5);
  rc = mix(rc, ROADC * 0.7, (inkBand(rd - 12.0, 3.0) + inkBand(rd + 12.0, 3.0)) * 0.6);
  col = mix(col, rc, onRoad);
  col = mix(col, inkOf(ROADC) * 1.4, inkBand(abs(rd) - 34.0, 1.0) * 0.6);
  vec2 sg = floor(p / 46.0);
  vec3 sh = hash32(sg + 5.0);
  vec2 stc = (sg + 0.5 + (sh.xy - 0.5) * 0.6) * 46.0;
  float st = length(p - stc) - (6.0 + 5.0 * sh.x);
  float nearRoad = 1.0 - smoothstep(30.0, 70.0, abs(roadD(stc) - 46.0));
  col = mix(col, STONE, fillCov(st) * step(0.55, sh.z) * nearRoad * step(0.0, stc.x - 120.0));
  // the path: straw-edged dirt track
  float onPath = 1.0 - hstep(pathW, abs(px));
  vec3 ptc = mix(PATHC, PATHC * 0.88, hstep(0.3, strokeField(p, 1.57, vec2(60.0, 3.0))) * 0.6);
  float straw = (1.0 - hstep(pathW + 26.0, abs(px))) * (1.0 - onPath) * (left && above ? 0.0 : 1.0);
  col = mix(col, mix(STUB, STUB_D, hstep(0.2, strokeField(p, 1.3, vec2(20.0, 1.5)))), straw * 0.9);
  col = mix(col, ptc, onPath);
  return vec4(col, 1.0);
}
`;

export const grade = () =>
  mkGrade({
    bloom: 0.5,
    bloomThreshold: 0.92,
    streak: 0.15,
    exposure: 1.02,
    lift: [0.0, 0.006, 0.012],
    splitHigh: [0.04, 0.02, -0.03],
    saturation: 1.0,
    haze: 0.03,
    hazeColor: [0.95, 0.85, 0.6],
    gamma: [0.96, 0.96, 0.96],
    vignette: 0.36,
    shafts: 0.03,
    shaftAngle: -2.3,
    shaftColor: [1.0, 0.9, 0.7],
  });

const TREE_GRAD = makeGradient(0.0, 0.5, [0.42, 0.75, 1.0]);

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const wy = cam.y - (WALKER_SY - 960);
  const wx = WALKER_X;
  const ground = usePaint(GROUND);

  SHARED.uLightDir.value.set(-0.3, -0.82, -0.44).normalize();
  SHARED.uShadowColor.value.set('#5a3a2a');
  SHARED.uShadowAlpha.value = 0.68;
  SHARED.uShadowZ.value = 0.5;

  const g = useMemo(
    () => ({
      bale: new CylinderGeometry(1, 1, 1, 28).rotateX(Math.PI / 2),
      clump: spikyBall(1010),
      trunk: new CylinderGeometry(10, 13, 210, 8).rotateX(Math.PI / 2),
      torso: new CapsuleGeometry(13, 20, 4, 10),
      head: new SphereGeometry(10, 12, 8),
      limb: new CapsuleGeometry(4.5, 30, 3, 6),
      leg: new CapsuleGeometry(5.5, 60, 3, 6),
    }),
    [],
  );
  const bales: Instance[] = useMemo(
    () =>
      [
        [-90, 871],
        [-140, 766],
        [-202, 659],
        [-278, 568],
        [-363, 483],
      ].map(([x, y]) => ({x, y, z: 30, sx: 47, sy: 47, sz: 60, color: '#efd47e'})),
    [],
  );
  const tree: Instance[] = useMemo(() => {
    const rng = mulberry32(31);
    const out: Instance[] = [];
    const cx = -265;
    const cy = 1190;
    for (let i = 0; i < 9; i++) {
      const a = rrange(rng, 0, 6.28);
      const r = i === 0 ? 0 : rrange(rng, 20, 75);
      out.push({x: cx + Math.cos(a) * r * 1.3, y: cy + Math.sin(a) * r * 1.3, z: 230 + rrange(rng, -25, 30), s: rrange(rng, 52, 74), rz: rrange(rng, 0, 6), color: i % 3 === 0 ? '#8a9a4a' : i % 3 === 1 ? '#9aaa58' : '#72843e'});
    }
    return out;
  }, []);

  // walking on twos
  const ph = (d / STEP) * Math.PI * 2;
  const sw = Math.sin(ph) * 0.5;
  const tail = worldToScreen(cam, wx, wy - 18, 80);
  const SHIRT = '#ecebe6';
  const INK = '#5e5a52';

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.8} color="#f0d8b0" />
      <directionalLight position={[300, 820, 440]} intensity={1.6} color="#fff0d0" />
      <PaintedPlane material={ground} cam={cam} />
      <InkedInstances geometry={g.bale} items={bales} inkWidth={1.6} inkMul={[0.5, 0.42, 0.3]} toon={{spiral: 7}} shadow shadowMode="tint" />
      <Inked geometry={g.trunk} color="#4a3524" position={[-265, 1190, 105]} inkWidth={1} shadow shadowMode="tint" />
      <InkedInstances geometry={g.clump} items={tree} inkWidth={2.2} inkMul={[0.3, 0.36, 0.2]} toon={{fur: 1, gradient: TREE_GRAD}} shadow shadowMode="tint" />
      {/* walker */}
      <group position={[wx, wy, 0]} scale={1.35}>
        <Inked geometry={g.leg} color="#3a3a44" ink="#18181e" position={[-7, sw * 22, 36]} rotation={[Math.PI / 2 + sw, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
        <Inked geometry={g.leg} color="#3a3a44" ink="#18181e" position={[7, -sw * 22, 36]} rotation={[Math.PI / 2 - sw, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
        <Inked geometry={g.torso} color={SHIRT} ink={INK} position={[0, 0, 98]} rotation={[0, Math.PI / 2, 0]} scale={[1, 1, 1.25]} inkWidth={1.3} shadow shadowMode="tint" />
        <Inked geometry={g.limb} color={SHIRT} ink={INK} position={[-20, -sw * 14, 96]} rotation={[Math.PI / 2 - sw * 0.8, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
        <Inked geometry={g.limb} color={SHIRT} ink={INK} position={[20, sw * 14, 96]} rotation={[Math.PI / 2 + sw * 0.8, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
        <Inked geometry={g.head} color="#2a1e18" ink="#0e0a08" position={[0, 2, 132]} inkWidth={1.1} shadow shadowMode="tint" />
      </group>
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{id: 's10', length: len, a: () => ({x: tail.sx, y: tail.sy}), b: () => ({x: 575, y: 1990}), sway: 0.07, waves: 1.6, slack: 1.025, seed: 10}}
        look={{z: (s) => 1.5 + (1 - s) * 50, width: 3.4}}
      />
    </>
  );
};
