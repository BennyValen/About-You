import React, {useMemo} from 'react';
import {AdditiveBlending, CapsuleGeometry, ExtrudeGeometry, Shape, SphereGeometry} from 'three';
import {CameraRig, CamPose, pose, screenToWorld, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED} from '../kit/toon';
import {easeInOut, lerp, smoothstep} from '../kit/random';

// Scene 12: pink-lavender tidal flats. The traveler walks on; near the end the camera
// settles, a second figure walks in from the top along the red thread, and they meet.
// (The source has no fade to black: it ends on this bright frame.)

const V0 = 10; // px/frame, camera speed while following
const HOLD_A = 250; // camera starts to ease off
const HOLD_B = 330; // camera at rest

// velocity V0 until HOLD_A, eased to 0 by HOLD_B (smoothstep), integrated exactly
const camY = (f: number) => {
  if (f <= HOLD_A) return V0 * f;
  const t = Math.min(1, (f - HOLD_A) / (HOLD_B - HOLD_A));
  return V0 * HOLD_A + V0 * (HOLD_B - HOLD_A) * (t - t * t * t + (t * t * t * t) / 2);
};
const camAt = (f: number): CamPose => pose(Math.sin(f * 0.004) * 6, camY(f), 1.0 + f * 0.00005);

// screen-space choreography measured from the source
const walkerScreen = (f: number) => {
  const t = smoothstep(HOLD_A, 356, f);
  const e = 1 - (1 - t) * (1 - t);
  return {x: lerp(405, 513, e), y: lerp(1335, 958, e)};
};
const ENTER = 262;
const meetScreen = (f: number) => {
  const t = Math.min(1, Math.max(0, (f - ENTER) / (356 - ENTER)));
  const e = 1 - Math.pow(1 - t, 2.2);
  return {x: lerp(660, 567, e), y: lerp(-90, 810, e)};
};

const GROUND = /* glsl */ `
const vec3 WAT = ${glc('#ad93b4')};
const vec3 WAT_L = ${glc('#d2b4c4')};
const vec3 WAT_D = ${glc('#9282aa')};
const vec3 SANDB = ${glc('#cdb2ba')};
const vec3 SANDB_L = ${glc('#d8bec2')};
const vec3 SANDB_D = ${glc('#bca2b4')};
const vec3 CREEK = ${glc('#8a7598')};
float barField(vec2 p){
  vec2 q = p + 120.0 * vec2(fbm3(p * 0.0016), fbm3(p * 0.0016 + 4.0));
  return fbm(q * 0.0011 + vec2(2.0, -1.0)) + 0.1 * gnoise(p * 0.006) - 0.06;
}
vec4 paint(vec2 p){
  // glossy shallow water: horizontal wind streaks
  float s1 = strokeField(p, 0.0, vec2(160.0, 5.0));
  float s2 = strokeField(p + 91.0, 0.05, vec2(90.0, 2.5));
  vec3 col = mix(WAT_D, WAT, hstep(-0.25, s1));
  col = mix(col, WAT_L, max(hstep(0.4, s1), hstep(0.5, s2) * 0.7) * 0.8);
  // sandbars with ripple marks and branching purple creeks
  float b = barField(p);
  float onBar = hstep(0.0, b);
  vec2 rp = rot2(p, -0.5);
  float rip = sin(rp.x * 0.16 + 3.0 * sin(rp.y * 0.01) + 2.0 * gnoise(p * 0.004));
  vec3 bar = mix(SANDB, SANDB_L, hstep(0.45, rip) * 0.7);
  bar = mix(bar, SANDB_D, hstep(0.6, -rip) * 0.6);
  float dend = 0.0;
  float sc = 1.0;
  for (int i = 0; i < 3; i++) {
    float n = fbm3(p * 0.0028 * sc + float(i) * 13.0);
    float dpx = abs(n) / max(fwidth(n), 1e-5);
    float wdt = (9.0 - float(i) * 3.0) * smoothstep(0.05, 0.3, b);
    dend = max(dend, (1.0 - smoothstep(wdt * 0.6, wdt, dpx)) * step(0.1, b - float(i) * 0.03));
    sc *= 1.8;
  }
  bar = mix(bar, CREEK, dend * 0.7);
  // shallow pools
  float pool = hstep(0.42, fbm3(p * 0.006 + 7.0)) * step(0.1, b);
  bar = mix(bar, mix(WAT, CREEK, 0.3), pool * 0.8);
  col = mix(col, bar, onBar);
  col = mix(col, inkOf(SANDB) * 1.6, inkBand(b * 300.0, 1.2) * 0.5);
  col = mix(col, mix(col, WAT_D, 0.5), (1.0 - hstep(0.0, b)) * (1.0 - smoothstep(0.0, 0.08, -b)) * 0.6);
  col *= brushMod(p, 0.05, 1.3, 0.06);
  return vec4(col, 1.0);
}`;

// warm sun glare on the wet flats: screen-anchored reflection (additive glow)
const GLARE = /* glsl */ `
uniform vec2 uCamXY;
vec4 paint(vec2 p){
  vec2 s = p - uCamXY;
  vec2 c = vec2(s.x - 20.0, (s.y - 120.0) * 0.72);
  float g = exp(-dot(c, c) / (2.0 * 300.0 * 300.0));
  float streak = 0.7 + 0.3 * strokeField(p, 0.0, vec2(120.0, 4.0));
  float q = smoothstep(0.15, 0.45, g) * 0.35 + smoothstep(0.5, 0.85, g) * 0.35 + g * 0.3;
  return vec4(${glc('#f6d6a2')} * q * streak * 0.85, 1.0);
}`;

const gullShape = () => {
  const s = new Shape();
  s.moveTo(-22, -2);
  s.quadraticCurveTo(-10, 6, 0, 2);
  s.quadraticCurveTo(10, 6, 22, -2);
  s.quadraticCurveTo(10, 1, 3, -4);
  s.lineTo(0, -10);
  s.lineTo(-3, -4);
  s.quadraticCurveTo(-10, 1, -22, -2);
  return s;
};

export const grade = () =>
  mkGrade({
    bloom: 0.7,
    bloomThreshold: 0.85,
    bloomRadius: 0.8,
    streak: 0.2,
    exposure: 1.02,
    lift: [0.0, 0.006, 0.02],
    splitHigh: [0.02, 0.012, 0.0],
    saturation: 1.0,
    haze: 0.04,
    hazeColor: [0.95, 0.85, 0.9],
    vignette: 0.3,
    shafts: 0.02,
    shaftAngle: -2.3,
  });

type Pose = {x: number; y: number; heading: number; phase: number; moving: number};

const Figure: React.FC<{p: Pose; g: Record<string, any>; coat: string; coatInk: string; hair: string; reach?: number}> = ({p, g, coat, coatInk, hair, reach = 0}) => {
  const sw = Math.sin(p.phase) * 0.55 * p.moving;
  return (
    <group position={[p.x, p.y, 0]} rotation={[0, 0, p.heading]} scale={1.2}>
      <Inked geometry={g.leg} color="#3a3540" ink="#151218" position={[-7, sw * 20, 34]} rotation={[Math.PI / 2 + sw, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
      <Inked geometry={g.leg} color="#3a3540" ink="#151218" position={[7, -sw * 20, 34]} rotation={[Math.PI / 2 - sw, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
      <Inked geometry={g.torso} color={coat} ink={coatInk} position={[0, 0, 92]} rotation={[0, Math.PI / 2, 0]} scale={[1, 1, 1.3]} inkWidth={1.3} shadow shadowMode="tint" />
      <Inked geometry={g.limb} color={coat} ink={coatInk} position={[-20, -sw * 12 + reach * 18, 92]} rotation={[Math.PI / 2 - sw * 0.8 - reach * 1.1, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
      <Inked geometry={g.limb} color={coat} ink={coatInk} position={[20, sw * 12, 92]} rotation={[Math.PI / 2 + sw * 0.8, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
      <Inked geometry={g.head} color={hair} ink="#0c0a0c" position={[0, 2, 126]} inkWidth={1.1} shadow shadowMode="tint" />
    </group>
  );
};

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const ground = usePaint(GROUND);
  const glare = usePaint(GLARE, {uCamXY: {value: [0, 0]}}, {transparent: true, blending: AdditiveBlending, depthWrite: false});
  glare.uniforms.uCamXY.value = [cam.x, cam.y];

  SHARED.uLightDir.value.set(-0.55, -0.66, -0.38).normalize();
  SHARED.uShadowColor.value.set('#6a5490');
  SHARED.uShadowAlpha.value = 0.66;
  SHARED.uShadowZ.value = 0.5;

  const g = useMemo(
    () => ({
      torso: new CapsuleGeometry(13, 20, 4, 10),
      head: new SphereGeometry(10, 12, 8),
      limb: new CapsuleGeometry(4.5, 30, 3, 6),
      leg: new CapsuleGeometry(5.5, 56, 3, 6),
      gull: new ExtrudeGeometry(gullShape(), {depth: 2, bevelEnabled: true, bevelThickness: 1, bevelSize: 1, bevelSegments: 1}),
    }),
    [],
  );

  // walker: world position from the measured screen path, walk phase from distance travelled (on twos)
  const ws = walkerScreen(d);
  const ww = screenToWorld(cam, ws.x, ws.y, 0);
  const walkDist = (ff: number) => {
    const c = camAt(ff);
    const s = walkerScreen(ff);
    return screenToWorld(c, s.x, s.y, 0).y;
  };
  const walker: Pose = {
    x: ww.x,
    y: ww.y,
    heading: d > HOLD_A ? -0.25 * smoothstep(HOLD_A, 330, d) : -0.05,
    phase: walkDist(d) / 22,
    moving: 1 - smoothstep(340, 356, d),
  };
  const ms = meetScreen(d);
  const mw = screenToWorld(cam, ms.x, ms.y, 0);
  const meet: Pose = {x: mw.x, y: mw.y, heading: Math.PI - 0.3, phase: d * 0.24, moving: 1 - smoothstep(338, 356, d)};
  const showMeet = d >= ENTER - 30;

  // gulls: wheel near the walker early, then drift off to the upper left (on twos)
  const gulls = [0, 1, 2].map((i) => {
    const t = d + i * 23;
    const away = smoothstep(150, 330, d);
    const sx = ws.x - 210 - i * 60 + Math.sin(t * 0.05) * 30 - away * 120;
    const sy = ws.y - 100 + i * 35 + Math.cos(t * 0.045) * 20 - away * 700;
    const w = screenToWorld(cam, sx, sy, 150);
    return {x: w.x, y: w.y, flap: 1 + 0.25 * Math.sin(t * 0.6), ang: 0.6 + Math.sin(t * 0.03) * 0.5};
  });

  const wS = worldToScreen(cam, walker.x, walker.y, 80);
  const mS = worldToScreen(cam, meet.x, meet.y, 80);
  const lowerCfg = {
    id: 's12a',
    length: len,
    a: (ff: number) => {
      const c = camAt(ff);
      const s = walkerScreen(ff - (ff % 2));
      const w = screenToWorld(c, s.x, s.y, 0);
      const r = worldToScreen(c, w.x, w.y - 16, 80);
      return {x: r.sx, y: r.sy};
    },
    b: () => ({x: 455, y: 1990}),
    sway: 0.07,
    waves: 1.5,
    slack: 1.03,
    seed: 12,
  };
  const midCfg = {
    id: 's12b',
    length: len,
    a: (ff: number) => {
      const c = camAt(ff);
      const s = meetScreen(ff - (ff % 2));
      const w = screenToWorld(c, s.x, s.y, 0);
      const r = worldToScreen(c, w.x, w.y + 10, 80);
      return {x: r.sx, y: r.sy};
    },
    b: (ff: number) => {
      const c = camAt(ff);
      const s = walkerScreen(ff - (ff % 2));
      const w = screenToWorld(c, s.x, s.y, 0);
      const r = worldToScreen(c, w.x, w.y + 18, 80);
      return {x: r.sx, y: r.sy};
    },
    sway: 0.05,
    waves: 1.0,
    slack: 1.04,
    seed: 13,
  };
  const topCfg = {
    id: 's12c',
    length: len,
    a: () => ({x: 870, y: -70}),
    b: (ff: number) => {
      const c = camAt(ff);
      const s = meetScreen(ff - (ff % 2));
      const w = screenToWorld(c, s.x, s.y, 0);
      const r = worldToScreen(c, w.x, w.y - 12, 80);
      return {x: r.sx, y: r.sy};
    },
    sway: 0.05,
    waves: 1.2,
    slack: 1.02,
    seed: 14,
  };
  void wS;
  void mS;
  void easeInOut;

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.85} color="#ead6e6" />
      <directionalLight position={[550, 660, 380]} intensity={1.4} color="#fff0e0" />
      <PaintedPlane material={ground} cam={cam} />
      <PaintedPlane material={glare} cam={cam} z={1} renderOrder={3} />
      <Figure p={walker} g={g} coat="#3e4c96" coatInk="#1a1f48" hair="#251c1c" reach={smoothstep(320, 356, d)} />
      {showMeet ? <Figure p={meet} g={g} coat="#e6e2e0" coatInk="#6a6670" hair="#1c1418" reach={smoothstep(320, 356, d)} /> : null}
      {gulls.map((b, i) => (
        <group key={i} position={[b.x, b.y, 150]} rotation={[0, 0, b.ang]} scale={[b.flap, 1, 1]}>
          <Inked geometry={g.gull} color="#f4f2ee" ink="#8a8690" inkWidth={0.8} shadow shadowMode="tint" />
        </group>
      ))}
      <RedThread cam={cam} drawFrame={d} cfg={lowerCfg} look={{z: (s) => 1.5 + (1 - s) * 70, width: 3.4}} />
      <RedThread cam={cam} drawFrame={d} cfg={midCfg} look={{z: () => 70, width: 3.4, visible: (ff) => ff >= ENTER - 30}} />
      <RedThread cam={cam} drawFrame={d} cfg={topCfg} look={{z: (s) => 2 + s * 68, width: 3.4, visible: (ff) => ff >= ENTER - 30}} />
    </>
  );
};
