import React, {useMemo} from 'react';
import {BufferGeometry, Color, Float32BufferAttribute, SphereGeometry, Shape, ExtrudeGeometry} from 'three';
import {CameraRig, CamPose, pose, screenToWorld, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint, MIST_FRAG, mistUniforms} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED} from '../kit/toon';

// Scene 7: a paraglider seen from above, high over grey rock, lichen-yellow plateaus and
// rust patches; cloud wisps drift between, two birds wheel nearby.

const SPEED = 2.0;
const GLIDER_SY = 1190;
const GLIDER_Z = 420;

const camAt = (f: number): CamPose => pose(Math.sin(f * 0.004) * 6, SPEED * f, 1.0 + f * 0.00005);

const GROUND = /* glsl */ `
const vec3 ROCK = ${glc('#7f8594')};
const vec3 ROCK_D = ${glc('#4c5366')};
const vec3 ROCK_L = ${glc('#a9adb6')};
const vec3 LICH = ${glc('#d9bb48')};
const vec3 LICH_O = ${glc('#e09a34')};
const vec3 LICH_D = ${glc('#9c8040')};
const vec3 RUST = ${glc('#c4602e')};
const vec3 RUST_D = ${glc('#8e4a36')};
const vec3 ROAD = ${glc('#9aa0aa')};
const vec3 ROAD_L = ${glc('#c9ccd2')};

float height(vec2 p){
  vec2 q = p + 180.0 * vec2(fbm3(p * 0.0008), fbm3(p * 0.0008 + 7.0));
  return fbm(q * 0.00075) + 0.18 * ridged(q * 0.0019) - 0.12;
}

vec4 paint(vec2 p){
  float h = height(p);
  float e = 6.0;
  float hx = height(p + vec2(e, 0.0)) - height(p - vec2(e, 0.0));
  float hy = height(p + vec2(0.0, e)) - height(p - vec2(0.0, e));
  vec3 n = normalize(vec3(-hx * 60.0, -hy * 60.0, 1.0));
  float lit = dot(n, normalize(vec3(0.6, 0.35, 0.72)));
  // rock: three tone cel by slope lighting, blue-grey
  vec3 col = cel3(ROCK_D, ROCK, ROCK_L, lit, 0.62, 0.86);
  col *= 0.9 + 0.2 * hstep(0.1, fbm3(p * 0.009 + 5.0));
  col *= brushMod(p, 0.9, 1.0, 0.14);
  // plateaus with lichen (yellow/ochre), with mottled painterly texture
  float plat = hstep(-0.02, h);
  float mott = fbm3(p * 0.006 + 3.0) + 0.35 * gnoise(p * 0.03);
  vec2 lid, lc;
  vec3 lv = voronoi(p / 9.0, 1.0, lid, lc);
  float speck = hash12(lid);
  vec3 lich = mix(LICH_D, LICH, hstep(-0.15, mott));
  lich = mix(lich, LICH_O, hstep(0.25, mott + (speck - 0.5) * 0.4));
  lich = mix(lich, ROCK_L * 0.95, step(0.78, speck) * 0.8);
  lich = mix(lich, lich * 0.75, step(lit, 0.66));
  float lmask = plat * hstep(0.0, fbm3(p * 0.0012 + 11.0) + 0.38 - 0.25 * smoothstep(-200.0, 400.0, p.x));
  col = mix(col, lich, lmask);
  // cliff edge ink + cast shadow below plateau rims
  col = mix(col, inkOf(ROCK) * 1.1, inkBand((h + 0.02) * 500.0, 1.2) * 0.7);
  float hs = height(p + vec2(26.0, 14.0));
  col = mix(col, col * vec3(0.62, 0.66, 0.82), hstep(-0.02, hs) * (1.0 - plat) * 0.9);
  // dark valleys in the low ground, with a lit rim
  float val = 1.0 - hstep(-0.2, h + 0.04 * gnoise(p * 0.01));
  vec3 cv = mix(${glc('#3e465b')}, ${glc('#30374a')}, 1.0 - hstep(-0.32, h));
  cv *= brushMod(p, 1.2, 1.0, 0.1);
  col = mix(col, cv, val);
  col = mix(col, ROCK_L * 1.06, inkBand((h + 0.2) * 420.0, 1.6) * 0.6);
  // rust patches
  float rust = hstep(0.42, fbm3(p * 0.0024 + vec2(-5.0, 2.0)) + 0.12 * speck);
  vec3 rc = mix(RUST_D, RUST, hstep(0.0, mott + 0.1));
  col = mix(col, rc, rust * (0.85 - 0.3 * plat));
  // winding tracks (zero set of a noise), drawn as thin double lines
  float rn = p.x * 0.0016 - 0.3 + 0.55 * fbm3(vec2(p.y * 0.0009, 3.0)) + 0.2 * fbm3(p * 0.0012 + 13.0);
  float rg = max(fwidth(rn), 1e-5);
  float rd = abs(rn) / rg;
  col = mix(col, ROAD * 0.8, inkBand(rd, 3.2) * 0.9);
  col = mix(col, ROAD_L, inkBand(rd, 1.1));

  return vec4(col, 1.0);
}
`;

// canopy: arc of airfoil cells (span curves down at the tips), coloured per cell
const canopyGeometry = () => {
  const cells = 26;
  const R = 230;
  const th = (64 * Math.PI) / 180;
  const chord = 104;
  const pos: number[] = [];
  const col: number[] = [];
  const baseA = new Color('#2f9590');
  const baseB = new Color('#287f80');
  const lead = new Color('#1c4f58');
  const under = new Color('#d6dedb');
  const prof = (t: number) => {
    // upper surface z offset and lower surface along the chord (t: 0 = leading edge)
    const up = 22 * Math.sin(Math.PI * Math.pow(1 - t, 0.6)) * (1 - t * 0.3);
    return {up, low: -6 * Math.sin(Math.PI * t)};
  };
  const pt = (s: number, t: number, surf: 'up' | 'low') => {
    const a = s * th;
    const pr = prof(t);
    const r = R + (surf === 'up' ? pr.up : pr.low) * (1 - 0.4 * s * s);
    // crescent planform: tips swept back, chord tapering toward the tips
    const ch = chord * (1 - 0.42 * s * s);
    const y = ch * (0.5 - t) - 72 * s * s + 24;
    return [Math.sin(a) * r * 1.08, y, Math.cos(a) * r - R];
  };
  const quad = (p0: number[], p1: number[], p2: number[], p3: number[], c: Color) => {
    pos.push(...p0, ...p1, ...p2, ...p0, ...p2, ...p3);
    for (let i = 0; i < 6; i++) col.push(c.r, c.g, c.b);
  };
  const NT = 8;
  for (let i = 0; i < cells; i++) {
    const s0 = -1 + (2 * i) / cells;
    const s1 = -1 + (2 * (i + 1)) / cells;
    const c = i % 2 === 0 ? baseA : baseB;
    for (let k = 0; k < NT; k++) {
      const t0 = k / NT;
      const t1 = (k + 1) / NT;
      const cc = k === 0 ? lead : c;
      // upper surface (normals outward/up)
      quad(pt(s0, t0, 'up'), pt(s0, t1, 'up'), pt(s1, t1, 'up'), pt(s1, t0, 'up'), cc);
      // lower surface (reversed winding)
      quad(pt(s0, t0, 'low'), pt(s1, t0, 'low'), pt(s1, t1, 'low'), pt(s0, t1, 'low'), under);
    }
  }
  const g = new BufferGeometry();
  g.setAttribute('position', new Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new Float32BufferAttribute(col, 3));
  g.computeVertexNormals();
  return g;
};

const wingShape = () => {
  const s = new Shape();
  s.moveTo(0, 0);
  s.bezierCurveTo(10, 8, 26, 10, 40, 4);
  s.bezierCurveTo(30, -2, 14, -6, 0, -4);
  s.closePath();
  return s;
};

export const grade = () =>
  mkGrade({
    bloom: 0.45,
    bloomThreshold: 0.95,
    streak: 0.12,
    exposure: 1.02,
    lift: [0.0, 0.008, 0.02],
    saturation: 1.04,
    haze: 0.04,
    hazeColor: [0.78, 0.8, 0.86],
    vignette: 0.3,
    shafts: 0.012,
    shaftAngle: -2.2,
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  // keep the glider fixed on screen: world position at its height
  const gw = screenToWorld(cam, 540, GLIDER_SY, GLIDER_Z);
  const gx = gw.x;
  const gy = gw.y;
  const ground = usePaint(GROUND);
  const cloudA = usePaint(MIST_FRAG, mistUniforms('#eceef2', 0.78, 480, [0.02, -0.004], 7.0, 0.02), {transparent: true, depthWrite: false});
  const cloudB = usePaint(MIST_FRAG, mistUniforms('#f4f4f6', 0.6, 300, [-0.015, -0.006], 31.0, 0.12), {transparent: true, depthWrite: false});

  SHARED.uLightDir.value.set(-0.72, -0.32, -0.95).normalize();
  SHARED.uShadowColor.value.set('#3e465e');
  SHARED.uShadowAlpha.value = 0.55;
  SHARED.uShadowZ.value = 0.5;

  const g = useMemo(
    () => ({
      canopy: canopyGeometry(),
      body: new SphereGeometry(1, 10, 8),
      wing: new ExtrudeGeometry(wingShape(), {depth: 1.5, bevelEnabled: false}),
    }),
    [],
  );
  // two birds wheeling up-right of the glider (on twos)
  const birds = [0, 1].map((i) => {
    const t = d + i * 17;
    const bx = cam.x + 150 + i * 40 + Math.sin(t * 0.02 + i) * 50;
    const by = cam.y + 520 - i * 70 + Math.cos(t * 0.017 + i) * 40 - d * 0.6;
    const flap = Math.sin(t * 0.5) * 0.6;
    return {bx, by, flap, ang: -0.5 + Math.sin(t * 0.02) * 0.3};
  });
  const threadA = worldToScreen(cam, gx, gy - 8, GLIDER_Z - 10);

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.85} color="#d6dbe6" />
      <directionalLight position={[720, 320, 950]} intensity={1.35} color="#fff4e4" />
      <PaintedPlane material={ground} cam={cam} />
      <PaintedPlane material={cloudA} cam={cam} z={160} renderOrder={6} />
      <Inked
        geometry={g.canopy}
        color="#ffffff"
        ink="#123a40"
        inkWidth={2.0}
        toon={{vertexColors: true, side: 2}}
        position={[gx, gy, GLIDER_Z]}
        scale={0.92}
        shadow
        shadowMode="tint"
      />
      {birds.map((b, i) => (
        <group key={i} position={[b.bx, b.by, 300]} rotation={[0, 0, b.ang]}>
          <Inked geometry={g.body} color="#7a5a3e" ink="#3a2618" scale={[5, 12, 4]} inkWidth={0.8} shadow shadowMode="tint" />
          <Inked geometry={g.wing} color="#8a6646" ink="#3a2618" position={[3, 2, 0]} rotation={[0, b.flap, 0]} inkWidth={0.7} shadow shadowMode="tint" />
          <Inked geometry={g.wing} color="#8a6646" ink="#3a2618" position={[-3, 2, 0]} rotation={[0, Math.PI - b.flap, 0]} inkWidth={0.7} shadow shadowMode="tint" />
        </group>
      ))}
      <PaintedPlane material={cloudB} cam={cam} z={260} renderOrder={7} />
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{id: 's07', length: len, a: () => ({x: threadA.sx, y: threadA.sy}), b: () => ({x: 528, y: 1990}), sway: 0.05, waves: 1.2, slack: 1.012, seed: 7}}
        look={{z: (s) => 300 * (1 - s) + 2, width: 3.0}}
      />
    </>
  );
};
