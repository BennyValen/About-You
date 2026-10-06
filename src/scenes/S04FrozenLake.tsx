import React, {useMemo} from 'react';
import {AdditiveBlending, CapsuleGeometry, SphereGeometry} from 'three';
import {CameraRig, CamPose, pose, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED} from '../kit/toon';

// Scene 4: a skater crosses a frozen lake at night. The aurora is reflected in the ice
// (a screen-fixed band near the top); cracks, frost bubbles and drifting snow pass under.

const SPEED = 5.0;
const SKATER_SY = 1165;
const STRIDE = 30; // frames per stride

const camAt = (f: number): CamPose => pose(Math.sin(f * 0.005) * 8, SPEED * f, 1.0 + f * 0.00006);

const sway = (fd: number) => Math.sin((fd / STRIDE) * Math.PI) * 14; // lateral sway, on twos

const ICE = /* glsl */ `
const vec3 ICE = ${glc('#163470')};
const vec3 ICE_L = ${glc('#21458c')};
const vec3 ICE_D = ${glc('#0e2152')};
const vec3 CRACK = ${glc('#4f9ec0')};
const vec3 BUB = ${glc('#b7cbe8')};
const vec3 SNOWC = ${glc('#d8e0f0')};
const vec3 SCRATCH = ${glc('#c8d6ee')};
uniform float uSkY;

float crackLines(vec2 p){
  float best = 1e3;
  for (int i = 0; i < 9; i++) {
    float fi = float(i);
    vec2 h = hash22(vec2(fi, 4.0));
    float ang = h.x * PI;
    vec2 n = vec2(cos(ang), sin(ang));
    vec2 o = vec2((h.y - 0.5) * 1400.0, hash11(fi * 3.1) * 2600.0 - 300.0);
    float dd = abs(dot(p - o, n));
    // segments: cracks fade in and out along their length
    vec2 t = vec2(-n.y, n.x);
    float along = dot(p - o, t);
    float seg = step(0.35, vnoise(vec2(along * 0.002, fi * 7.0)));
    best = min(best, mix(1e3, dd, seg));
  }
  return best;
}

vec4 paint(vec2 p){
  // ice: deep blue with long painted streaks
  float st = strokeField(p, 0.25, vec2(220.0, 10.0));
  float st2 = strokeField(p + 300.0, -0.35, vec2(320.0, 26.0));
  vec3 col = cel3(ICE_D, ICE, ICE_L, st * 0.35 + st2 * 0.35 + 0.5, 0.3, 0.72);
  col *= brushMod(p, 0.25, 1.4, 0.10);
  // dark under-ice patches
  col = mix(col, ICE_D * 0.85, hstep(0.35, fbm(p * 0.0015 + 4.0)) * 0.6);

  // fracture lines: long straight teal cracks plus a fine voronoi crack net
  float cl = crackLines(p);
  float w = 1.0 + 0.9 * vnoise(p * 0.02);
  col = mix(col, CRACK, inkBand(cl, w * 0.8) * 0.5);
  col = mix(col, CRACK * 0.6, inkBand(cl - 4.0, 0.6) * 0.25);
  vec2 cid, cc;
  vec3 vo = voronoi(p / 210.0, 0.9, cid, cc);
  float netOn = step(0.8, hash12(cid + 2.0));
  col = mix(col, CRACK * 0.8, inkBand(vo.z * 210.0, 0.6) * netOn * 0.35);

  // frost bubbles: clusters and vertical strings
  float clusterMask = smoothstep(0.25, 0.45, fbm(p * 0.004 + 9.0));
  float strings = 0.0;
  for (int i = 0; i < 3; i++) {
    float fi = float(i);
    float xs = -420.0 + fi * 380.0 + 60.0 * gnoise(vec2(p.y * 0.002, fi));
    strings = max(strings, (1.0 - smoothstep(10.0, 34.0, abs(p.x - xs))) * step(0.3, vnoise(vec2(p.y * 0.004, fi * 5.0))));
  }
  float bm = max(clusterMask * 0.9, strings);
  vec2 bid, bc;
  float bs = 19.0;
  vec3 bv = voronoi(p / bs, 1.0, bid, bc);
  float bh = hash12(bid + 7.0);
  float br = (0.14 + 0.3 * bh) * bs;
  float bubble = fillCov(bv.x * bs - br) * step(1.0 - bm * 0.8, hash12(bid + 1.3));
  col = mix(col, BUB, bubble * 0.85);
  col = mix(col, inkOf(BUB) * 1.4, inkBand(bv.x * bs - br, 0.7) * bubble * 0.5);

  // wind-blown snow patches (mostly to the right), streaked
  vec2 sr = rot2(p, 0.55);
  float sm = fbm(sr * vec2(0.0012, 0.0055) + 2.0) + 0.32 * smoothstep(-100.0, 450.0, p.x) - 0.2;
  float snow = hstep(0.16, sm);
  float streak = smoothstep(-0.2, 0.45, strokeField(p, -0.55, vec2(70.0, 2.6)));
  vec3 sc = mix(SNOWC * 0.78, SNOWC * 1.08, streak);
  col = mix(col, sc, snow * (0.5 + 0.5 * streak) * smoothstep(0.16, 0.34, sm));

  // skate scratches: the skater's trail plus a few older strokes
  float ty = uSkY - p.y;
  float trail = 0.0;
  if (ty > 30.0) {
    float sx = 14.0 * sin(((uSkY - ty) / ${(SPEED * STRIDE).toFixed(1)}) * PI);
    float on = step(0.4, fract((uSkY - ty) / ${(SPEED * STRIDE * 2).toFixed(1)}));
    trail = inkBand(p.x - sx - 6.0, 1.0) * on * (1.0 - smoothstep(300.0, 900.0, ty));
  }
  col = mix(col, SCRATCH, trail * 0.8);
  vec2 sid, scc;
  vec3 sv = voronoi(p / 260.0, 0.8, sid, scc);
  float scr = inkBand(abs(dot(p - scc * 260.0, normalize(hash22(sid) - 0.5))) , 0.8) * step(sv.x, 0.25) * step(0.72, hash12(sid + 5.0));
  col = mix(col, SCRATCH, scr * 0.6);
  return vec4(col, 1.0);
}
`;

// aurora reflection: screen-anchored, painted in stepped bands, additive (feeds the bloom)
const AURORA = /* glsl */ `
uniform vec2 uCamXY;
vec4 paint(vec2 p){
  vec2 s = p - uCamXY;                 // camera-relative (px), +y up
  float y = (960.0 - s.y);             // screen y from the top
  float centre = 330.0 - s.x * 0.2 + 40.0 * gnoise(vec2(s.x * 0.0025, uTime * 0.04));
  float d = (y - centre) / 300.0;
  float band = exp(-d * d * 2.0) * (0.75 + 0.25 * smoothstep(400.0, -300.0, s.x));
  float folds = 0.75 + 0.25 * strokeField(vec2(s.x, y) + vec2(uTime * 5.0, 0.0), 0.2, vec2(260.0, 30.0));
  float a = band * folds;
  // painted in a few soft steps
  float q = smoothstep(0.08, 0.3, a) * 0.35 + smoothstep(0.35, 0.6, a) * 0.35 + smoothstep(0.65, 0.9, a) * 0.3;
  vec3 lav = ${glc('#7c73bd')};
  vec3 pink = ${glc('#d58ab4')};
  vec3 gold = ${glc('#f2d29a')};
  vec3 c = mix(lav, pink, smoothstep(0.25, 0.55, a));
  float goldLine = exp(-pow((y - centre + 25.0) / 70.0, 2.0));
  c = mix(c, gold, smoothstep(0.45, 0.95, goldLine * a * 1.3) * 0.8);
  return vec4(c, q * 0.55);
}`;

export const grade = () =>
  mkGrade({
    bloom: 1.1,
    bloomThreshold: 0.55,
    bloomRadius: 0.85,
    streak: 0.4,
    streakThreshold: 0.6,
    streakTint: [1.0, 0.8, 0.9],
    exposure: 1.05,
    lift: [0.0, 0.01, 0.035],
    vignette: 0.4,
    haze: 0.04,
    hazeColor: [0.25, 0.3, 0.6],
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const skY = cam.y - (SKATER_SY - 960);
  const sx = sway(d);
  const ice = usePaint(ICE, {uSkY: {value: 0}});
  ice.uniforms.uSkY.value = skY;
  const aurora = usePaint(AURORA, {uCamXY: {value: [0, 0]}}, {transparent: true, blending: AdditiveBlending, depthWrite: false});
  aurora.uniforms.uCamXY.value = [cam.x, cam.y];

  SHARED.uLightDir.value.set(-0.5, -0.75, -0.42).normalize();
  SHARED.uShadowColor.value.set('#2c3f78');
  SHARED.uShadowZ.value = 0.5;

  const g = useMemo(
    () => ({
      body: new CapsuleGeometry(26, 34, 6, 14),
      head: new SphereGeometry(16, 14, 10),
      hair: new CapsuleGeometry(13, 30, 5, 10),
      arm: new CapsuleGeometry(8, 46, 4, 8),
      hand: new SphereGeometry(7, 8, 6),
      leg: new CapsuleGeometry(9, 50, 4, 8),
    }),
    [],
  );
  // stride pose (on twos)
  const ph = (d / STRIDE) * Math.PI;
  const lean = Math.sin(ph) * 0.18;
  const legSwing = Math.sin(ph) * 0.5;
  const skS = worldToScreen(cam, sx, skY - 10, 40);

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.75} color="#7d8cc8" />
      <directionalLight position={[450, 600, 600]} intensity={1.5} color="#e8ecff" />
      <PaintedPlane material={ice} cam={cam} />
      <group position={[sx, skY, 0]} rotation={[0, 0, lean]}>
        {/* legs, pushing alternately */}
        <Inked geometry={g.leg} color="#2b2c3c" ink="#12121c" position={[10, -14, 22]} rotation={[0.9 + legSwing, 0, -0.25]} inkWidth={1.2} shadow />
        <Inked geometry={g.leg} color="#2b2c3c" ink="#12121c" position={[-10, -14, 22]} rotation={[0.9 - legSwing, 0, 0.25]} inkWidth={1.2} shadow />
        {/* white coat */}
        <Inked geometry={g.body} color="#ece9ee" ink="#6d6a86" position={[0, 0, 60]} rotation={[0.25, 0, 0]} scale={[1.15, 0.95, 0.8]} inkWidth={1.8} shadow />
        {/* arms: right arm reaching forward, left arm back for balance */}
        <Inked geometry={g.arm} color="#e6e3ea" ink="#6d6a86" position={[22, 40, 82]} rotation={[0, 0, -0.35 + lean]} inkWidth={1.4} shadow />
        <Inked geometry={g.arm} color="#e6e3ea" ink="#6d6a86" position={[-34, -6, 74]} rotation={[0, 0, 1.0 - lean]} inkWidth={1.4} shadow />
        <Inked geometry={g.hand} color="#d9c2b0" ink="#6b5546" position={[30, 68, 82]} inkWidth={1} />
        {/* head + long dark hair falling down the back */}
        <Inked geometry={g.head} color="#2a2026" ink="#100c10" position={[0, 14, 96]} inkWidth={1.4} shadow />
        <Inked geometry={g.hair} color="#2f242b" ink="#100c10" position={[0, -6, 92]} rotation={[0.4, 0, 0]} inkWidth={1.4} />
      </group>
      <PaintedPlane material={aurora} cam={cam} z={4} renderOrder={6} />
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{
          id: 's04',
          length: len,
          a: (ff) => {
            const c = camAt(ff);
            const s = worldToScreen(c, sway(ff - (ff % 2)), c.y - (SKATER_SY - 960) - 10, 40);
            return {x: s.sx, y: s.sy};
          },
          b: () => ({x: 545, y: 1990}),
          sway: 0.07,
          waves: 1.3,
          slack: 1.03,
          seed: 4,
        }}
        look={{z: (s) => 2 + (1 - s) * 30, width: 3.6}}
      />
      {skS ? null : null}
    </>
  );
};
