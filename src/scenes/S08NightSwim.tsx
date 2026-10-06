import React, {useMemo} from 'react';
import {AdditiveBlending, CapsuleGeometry, SphereGeometry} from 'three';
import {CameraRig, CamPose, pose, screenToWorld, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED} from '../kit/toon';

// Scene 8: pitch-black sea at night. A swimmer pulls forward, leaving a glowing cyan
// bioluminescent wake; the red thread runs back through the glow.

const SPEED = 1.0;
const SWIM_SY = 1190;
const STROKE = 34;

const camAt = (f: number): CamPose => pose(0, SPEED * f, 1.0 + f * 0.0001);

const WATER = /* glsl */ `
vec4 paint(vec2 p){
  vec3 col = ${glc('#060d1a')};
  float st = strokeField(p, 0.1, vec2(260.0, 12.0));
  col = mix(col, ${glc('#0a1424')}, hstep(0.25, st) * 0.7);
  col = mix(col, ${glc('#03080f')}, hstep(0.3, fbm3(p * 0.0015 + 2.0)) * 0.6);
  // faint plankton specks, twinkling on twos
  vec2 id, c;
  vec3 v = voronoi(p / 22.0, 1.0, id, c);
  float tw = step(0.93, hash12(id + floor(uDraw * 4.0) * 0.37));
  col += ${glc('#1d4d66')} * fillCov(v.x * 22.0 - 1.2) * tw * 0.8;
  return vec4(col, 1.0);
}`;

// wake: anchored to the swimmer, turbulence flowing back; painted in stepped glow bands (additive)
const WAKE = /* glsl */ `
uniform vec2 uSwim;   // swimmer feet (world)
vec4 paint(vec2 p){
  vec2 r = p - uSwim;
  float back = -r.y;                      // distance behind the swimmer
  if (back < -60.0) return vec4(0.0);
  float cx = back * 0.2 + 26.0 * sin(back * 0.006 + uDraw * 0.5);
  float w = 30.0 + back * 0.16;
  float lat = (r.x - cx) / w;
  vec2 q = vec2(r.x * 0.018, (back + uDraw * 70.0) * 0.012);
  float turb = fbm(q + vec2(fbm(q * 0.7 + uDraw * 0.2), 0.0));
  float body = exp(-lat * lat * 1.4) * (1.0 - smoothstep(380.0, 900.0, back)) * smoothstep(-60.0, 10.0, back);
  float wisps = exp(-lat * lat * 0.45) * smoothstep(0.0, 0.5, turb + 0.15) * (1.0 - smoothstep(200.0, 950.0, back)) * smoothstep(-30.0, 40.0, back);
  float near = 1.0 - smoothstep(60.0, 420.0, back);
  float a = max(body * (0.45 + 0.65 * turb) * (1.0 + 0.6 * near), wisps * 0.6);
  // soft painted steps: the glow layer
  float q1 = smoothstep(0.06, 0.3, a), q2 = smoothstep(0.3, 0.55, a), q3 = smoothstep(0.58, 0.85, a);
  vec3 c = ${glc('#0f3a70')} * q1 * 0.8 + ${glc('#1a92c4')} * q2 * 0.8 + ${glc('#9ff6ff')} * q3 * 0.7;
  // streaky filaments inside the glow
  float fil = smoothstep(0.2, 0.6, strokeField(vec2(r.x - cx, back + uDraw * 50.0), 1.5, vec2(70.0, 3.5)));
  c += ${glc('#39c6e6')} * fil * q1 * 0.35;
  // the splash glow at the hands
  float hand = exp(-dot(r - vec2(-14.0, 130.0), r - vec2(-14.0, 130.0)) / 900.0);
  c += ${glc('#bfffff')} * hand * 1.8;
  return vec4(c * 1.45, 1.0);
}`;

export const grade = () =>
  mkGrade({
    bloom: 1.6,
    bloomThreshold: 0.35,
    bloomRadius: 0.85,
    streak: 0.22,
    streakThreshold: 1.1,
    streakTint: [0.6, 0.95, 1.1],
    exposure: 1.0,
    lift: [0.0, 0.006, 0.018],
    vignette: 0.45,
    grain: 0.04,
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const sw = screenToWorld(cam, 540, SWIM_SY, 0);
  const water = usePaint(WATER);
  const wake = usePaint(WAKE, {uSwim: {value: [0, 0]}}, {transparent: true, blending: AdditiveBlending, depthWrite: false});
  wake.uniforms.uSwim.value = [sw.x, sw.y];

  SHARED.uLightDir.value.set(0.3, -0.4, -0.86).normalize();

  const g = useMemo(
    () => ({
      torso: new CapsuleGeometry(20, 36, 5, 10),
      head: new SphereGeometry(13, 14, 10),
      arm: new CapsuleGeometry(5.5, 46, 3, 8),
      leg: new CapsuleGeometry(6.5, 50, 3, 8),
    }),
    [],
  );
  // freestyle stroke on twos: one arm reaches forward while the other pulls back
  const ph = (d / STROKE) * Math.PI * 2;
  const reach = Math.sin(ph);
  const kick = Math.sin(ph * 2) * 0.25;
  const roll = Math.sin(ph) * 0.35;
  const feet = worldToScreen(cam, sw.x, sw.y - 30, 0);
  const DARK = '#1a2a40';
  const INK = '#04070c';

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.35} color="#284a70" />
      <directionalLight position={[0, -400, 300]} intensity={1.6} color="#7fe8ff" />
      <PaintedPlane material={water} cam={cam} />
      <PaintedPlane material={wake} cam={cam} z={1} renderOrder={3} />
      <group position={[sw.x, sw.y + 40, 8]} rotation={[0, roll, 0]}>
        <Inked geometry={g.torso} color={DARK} ink={INK} inkWidth={1.2} />
        <Inked geometry={g.head} color="#0e1626" ink={INK} position={[2, 52, 4]} inkWidth={1.2} />
        <Inked geometry={g.arm} color={DARK} ink={INK} position={[-16, 40 + reach * 30, 6]} rotation={[0, 0, 0.15]} scale={[1, 0.8 + 0.35 * Math.max(0, reach), 1]} inkWidth={1.0} />
        <Inked geometry={g.arm} color={DARK} ink={INK} position={[16, 10 - reach * 26, 4]} rotation={[0, 0, -0.35 - reach * 0.3]} inkWidth={1.0} />
        <Inked geometry={g.leg} color={DARK} ink={INK} position={[-7, -50, 0]} rotation={[kick, 0, 0.05]} inkWidth={1.0} />
        <Inked geometry={g.leg} color={DARK} ink={INK} position={[7, -50, 0]} rotation={[-kick, 0, -0.05]} inkWidth={1.0} />
      </group>
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{id: 's08', length: len, a: () => ({x: feet.sx, y: feet.sy}), b: () => ({x: 680, y: 1990}), sway: 0.06, waves: 1.4, slack: 1.02, seed: 8}}
        look={{z: () => 3, width: 3.6, glowStrength: 0.2}}
      />
    </>
  );
};
