import React, {useMemo} from 'react';
import {CapsuleGeometry, ExtrudeGeometry, Shape, SphereGeometry} from 'three';
import {CameraRig, CamPose, pose, screenToWorld, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED, makeGradient} from '../kit/toon';

const BIRD_GRAD = makeGradient(0.0, 0.6, [0.72, 0.9, 1.0]);
import {smoothstep} from '../kit/random';

// Scene 11: a V of white cranes flies over peach-lavender cumulus; their shadows slide
// over the cloud tops and the gaps open onto the deep blue below.

const BIRD_Z = 380;
const FLAP = 30;

// camera: 5 px/frame, easing almost to a stop over the last part of the shot
const camY = (f: number) => {
  const a = 190;
  const b = 250;
  if (f <= a) return 5 * f;
  if (f >= b) return 5 * a + 5 * (b - a) * 0.5 + 0.4 * (f - b);
  const t = (f - a) / (b - a);
  return 5 * a + 5 * (b - a) * (t - (t * t) / 2) + 0.4 * (b - a) * (t * t) / 2;
};
const camAt = (f: number): CamPose => pose(Math.sin(f * 0.004) * 8, camY(f), 1.0 + f * 0.00005);

// formation, screen positions (px) measured from the source
const V: [number, number][] = [
  [540, 1190],
  [370, 1320],
  [690, 1350],
  [230, 1450],
  [840, 1484],
  [110, 1616],
  [980, 1650],
];

const CLOUD = /* glsl */ `
const vec3 GAP = ${glc('#38457a')};
const vec3 GAP_D = ${glc('#2b3664')};
const vec3 GAP_L = ${glc('#55598c')};
const vec3 SHD = ${glc('#8474ac')};
const vec3 MIDC = ${glc('#dcc2c8')};
const vec3 LITC = ${glc('#f8e8e0')};
const vec3 HOT = ${glc('#fff1e6')};

float cloudH(vec2 p){
  vec2 q = p + 90.0 * vec2(fbm3(p * 0.0021), fbm3(p * 0.0021 + 5.0));
  float big = fbm(q * 0.0012 + 3.0);
  float puffs = fbm3(q * 0.0034 + 9.0) * 0.28 + fbm3(q * 0.009 + 2.0) * 0.06;
  // cover thins out further along the route (gaps widen during the shot)
  float cover = mix(0.32, -0.12, smoothstep(600.0, 1600.0, p.y));
  return big + puffs + cover;
}

// cauliflower relief: the highest of many round puffs at two scales, inside the cover mask
float puff(vec2 p, float cell, float seed, out vec2 nrm){
  vec2 g0 = floor(p / cell);
  float best = -1.0; nrm = vec2(0.0);
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 g = g0 + vec2(float(i), float(j));
    vec3 h = hash32(g + seed);
    vec2 c = (g + 0.5 + (h.xy - 0.5) * 0.8) * cell;
    float R = cell * (0.62 + 0.4 * h.z);
    vec2 d = (p - c) / R;
    float q = 1.0 - dot(d, d);
    if (q > 0.0) {
      float hh = sqrt(q) * (0.7 + 0.3 * h.z);
      if (hh > best) { best = hh; nrm = d; }
    }
  }
  return best;
}

vec4 paint(vec2 p){
  float h = cloudH(p);
  // deep blue gaps with soft wind streaks
  float st = strokeField(p, 0.35, vec2(200.0, 6.0));
  vec3 col = mix(GAP_D, GAP, hstep(-0.1, st));
  col = mix(col, GAP_L, hstep(0.45, st) * 0.6);
  float inC = hstep(0.0, h);
  vec2 n1, n2;
  float b1 = puff(p, 150.0, 3.0, n1);
  float b2 = puff(p + 40.0, 62.0, 9.0, n2);
  float use2 = step(b1 * 0.85, b2 * 0.75 + 0.05);
  vec2 nn = mix(n1, n2, use2);
  vec3 n = normalize(vec3(nn, sqrt(max(0.0, 1.0 - dot(nn, nn))) + 0.15));
  float lit = dot(n, normalize(vec3(0.45, 0.35, 0.8)));
  // the cloud mass is shaded overall toward its edges and in low ground
  lit -= (1.0 - smoothstep(0.0, 0.35, h)) * 0.35;
  lit -= step(min(b1, b2), 0.0) * 0.2;
  vec3 cc = cel3(SHD, MIDC, LITC, lit, 0.42, 0.78);
  cc = mix(cc, HOT, hstep(0.95, lit) * 0.6);
  // curly painted texture
  float ang = atan(nn.y, nn.x) + 1.57;
  float curl = strokeField(p, ang, vec2(22.0, 4.5));
  cc *= 1.0 + 0.06 * hstep(0.2, curl) - 0.05 * hstep(0.35, -curl);
  col = mix(col, cc, inC);
  // puff outlines (only inside the cloud), and the cloud's outer edge
  float edge1 = (1.0 - mix(b1, b2, use2)) ;
  col = mix(col, inkOf(MIDC) * 1.7, inkBand(edge1 * 40.0, 0.9) * inC * 0.25);
  col = mix(col, inkOf(SHD) * 1.3, inkBand(h * 260.0, 1.1) * 0.6);
  return vec4(col, 1.0);
}`;

// broad wing (leading edge forward, +y) and the black primaries at its tip
const wingShape = () => {
  const s = new Shape();
  s.moveTo(0, 14);
  s.bezierCurveTo(26, 20, 56, 20, 78, 14);
  s.lineTo(80, -16);
  s.bezierCurveTo(60, -26, 30, -30, 0, -26);
  s.closePath();
  return s;
};
const tipShape = () => {
  const s = new Shape();
  s.moveTo(0, 14);
  s.bezierCurveTo(12, 14, 22, 8, 30, -6);
  s.lineTo(26, -14);
  s.lineTo(20, -10);
  s.lineTo(16, -20);
  s.lineTo(10, -14);
  s.lineTo(4, -22);
  s.lineTo(0, -16);
  s.closePath();
  return s;
};

export const grade = () =>
  mkGrade({
    bloom: 0.55,
    bloomThreshold: 0.9,
    streak: 0.15,
    exposure: 1.02,
    lift: [0.0, 0.01, 0.03],
    saturation: 1.02,
    haze: 0.05,
    hazeColor: [0.85, 0.78, 0.9],
    vignette: 0.3,
    shafts: 0.02,
    shaftAngle: -2.4,
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const cloud = usePaint(CLOUD);

  SHARED.uLightDir.value.set(-0.35, -0.14, -0.93).normalize();
  SHARED.uShadowColor.value.set('#6f6494');
  SHARED.uShadowAlpha.value = 0.6;
  SHARED.uShadowZ.value = 0.5;

  const g = useMemo(
    () => ({
      body: new SphereGeometry(1, 16, 12),
      neck: new CapsuleGeometry(3.2, 50, 3, 8),
      head: new SphereGeometry(5, 10, 8),
      leg: new CapsuleGeometry(1.6, 56, 2, 6),
      wing: new ExtrudeGeometry(wingShape(), {depth: 2, bevelEnabled: true, bevelThickness: 1.5, bevelSize: 1.5, bevelSegments: 1, curveSegments: 10}),
      tip: new ExtrudeGeometry(tipShape(), {depth: 2.5, bevelEnabled: true, bevelThickness: 1.5, bevelSize: 1.5, bevelSegments: 1, curveSegments: 8}),
    }),
    [],
  );

  const birds = V.map(([sx, sy], i) => {
    const bob = Math.sin(d * 0.05 + i * 1.3) * 6;
    const w = screenToWorld(cam, sx + Math.sin(d * 0.03 + i) * 4, sy + bob, BIRD_Z);
    const flap = Math.sin(((d + i * 7) / FLAP) * Math.PI * 2) * 0.32;
    return {x: w.x, y: w.y, flap, s: i === 0 ? 1.08 : 0.98};
  });
  const lead = birds[0];
  const tail = worldToScreen(cam, lead.x, lead.y - 62, BIRD_Z - 4);
  void smoothstep;

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.85} color="#e8d8e8" />
      <directionalLight position={[350, 140, 930]} intensity={1.35} color="#fff4ec" />
      <PaintedPlane material={cloud} cam={cam} />
      {birds.map((b, i) => (
        <group key={i} position={[b.x, b.y, BIRD_Z]} scale={b.s}>
          <Inked geometry={g.body} color="#f6f5f3" ink="#8a8894" toon={{gradient: BIRD_GRAD, emissive: "#ffffff", emissiveIntensity: 0.28}} scale={[11, 30, 9]} inkWidth={1.2} shadow shadowMode="tint" />
          <Inked geometry={g.neck} color="#f1f0ee" ink="#8a8894" position={[0, 52, 2]} inkWidth={0.9} shadow shadowMode="tint" />
          <Inked geometry={g.head} color="#26232a" ink="#0c0a0e" position={[0, 82, 3]} scale={[1, 1.5, 1]} inkWidth={0.8} shadow shadowMode="tint" />
          <Inked geometry={g.leg} color="#2c2a30" ink="#0c0a0e" position={[-3, -52, -2]} inkWidth={0.6} shadow shadowMode="tint" />
          <Inked geometry={g.leg} color="#2c2a30" ink="#0c0a0e" position={[3, -52, -2]} inkWidth={0.6} shadow shadowMode="tint" />
          {[1, -1].map((side) => (
            <group key={side} position={[side * 6, 4, 2]} rotation={[0, side * b.flap, 0]} scale={[side, 1, 1]}>
              <Inked geometry={g.wing} color="#ffffff" ink="#9a98a6" toon={{gradient: BIRD_GRAD, emissive: "#ffffff", emissiveIntensity: 0.3}} inkWidth={1.2} shadow shadowMode="tint" />
              <Inked geometry={g.tip} color="#24222a" ink="#0c0a0e" position={[76, -2, 0.5]} rotation={[0, 0, -0.25]} inkWidth={0.8} shadow shadowMode="tint" />
            </group>
          ))}
        </group>
      ))}
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{id: 's11', length: len, a: () => ({x: tail.sx, y: tail.sy}), b: () => ({x: 520, y: 1990}), sway: 0.05, waves: 1.3, slack: 1.015, seed: 11}}
        look={{z: (s) => (BIRD_Z - 8) * (1 - s) + 4, width: 3.0}}
      />
    </>
  );
};
