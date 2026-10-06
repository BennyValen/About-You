import React, {useMemo} from 'react';
import {BoxGeometry, CylinderGeometry, DodecahedronGeometry, ExtrudeGeometry, IcosahedronGeometry, Shape} from 'three';
import {CameraRig, CamPose, pose, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked, InkedInstances, Instance} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint, MIST_FRAG, mistUniforms} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED} from '../kit/toon';
import {mulberry32, rrange, scatter, smoothstep} from '../kit/random';

// Scene 2: a bright forest drawn as fingerprint-like contour hedges. A white train runs
// straight up the centre track. The rings morph quickly for the first ~5 s, then drift.

const SPEED = 7.0;
const TRAIN_FRONT_SY = 980;
const CAR_LEN = 228;
const CAR_GAP = 10;
const CAR_W = 58;
const MORPH_END = 119; // local frame where the fast morph settles (17.2 s)

const camAt = (f: number): CamPose => pose(0, SPEED * f, 1.0 + f * 0.00006);

// drawing-time used by the ring morph: fast at first, then slow (on twos via uDraw)
export const morphClock = (t: number) => {
  const te = MORPH_END / 24;
  return t < te ? t * 1.0 : te + (t - te) * 0.12;
};

const GROUND = /* glsl */ `
uniform float uMorph;     // morph clock (drawing rate)
uniform float uTeal;      // amount of teal-blue patches (grows over the shot)
const vec3 GAP = ${glc('#1b3b20')};
const vec3 GAP2 = ${glc('#22472b')};
const vec3 LIME = ${glc('#c2e86a')};
const vec3 LIME2 = ${glc('#96d250')};
const vec3 GREEN = ${glc('#5aae50')};
const vec3 DEEP = ${glc('#3a8a4e')};
const vec3 TEAL = ${glc('#4aa58e')};
const vec3 BALLAST = ${glc('#d9d5c8')};
const vec3 BALLAST_D = ${glc('#b3ad9f')};
const vec3 TIE = ${glc('#8d877c')};
const vec3 RAILC = ${glc('#6f6d6b')};
const vec3 RUST = ${glc('#a2532c')};
const vec3 GRASS = ${glc('#5ca443')};
const vec3 L3 = normalize(vec3(-0.55, 0.6, 0.75));

// smooth-min distance to jittered ring centres -> rings with even spacing, meeting in fingerprint deltas
float ringField(vec2 p, float m){
  vec2 w = vec2(fbm(p * 0.0014 + vec2(1.3, m * 0.35)), fbm(p * 0.0014 + vec2(-4.1, 2.0 - m * 0.3)));
  vec2 q = p + w * 60.0;
  float cell = 520.0;
  vec2 g0 = floor(q / cell);
  float k = 26.0;
  float acc = 0.0;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 g = g0 + vec2(float(i), float(j));
    vec3 h = hash32(g + 17.0);
    vec2 c = (g + 0.5 + (h.xy - 0.5) * 0.7) * cell + vec2(sin(m * 0.9 + h.z * 6.0), cos(m * 0.7 + h.x * 6.0)) * 40.0;
    vec2 dq = q - c;
    float ang = h.z * 3.1416;
    dq = rot2(dq, ang);
    dq.x *= 0.75 + 0.5 * h.y;
    float d = length(dq);
    acc += exp(-d / k);
  }
  return -k * log(max(acc, 1e-6));
}

vec4 paint(vec2 p){
  float cx = abs(p.x);
  // --- hedge rings
  float d = ringField(p, uMorph);
  float spacing = 20.0;
  float ph = d / spacing - uMorph * 0.9;
  float fr = fract(ph);
  float tri = 1.0 - abs(fr - 0.5) * 2.0;        // 1 at the ridge centre
  // line breaks / terminations: the ridge thins out where this noise is high
  float br = smoothstep(0.25, 0.75, vnoise(p * 0.011 + uMorph * 0.4) * 0.6 + vnoise(p * 0.03 - uMorph * 0.2) * 0.4);
  float thr = mix(0.3, 0.98, br * br * 0.7);
  float ridge = hstep(thr, tri);
  // rounded cross-section normal -> 3-step cel shading
  vec2 gd = vec2(dFdx(d), dFdy(d));
  gd /= max(length(gd), 1e-4);
  float across = clamp((fr - 0.5) * 2.0 / max(1.0 - thr, 0.05), -1.0, 1.0);
  vec3 n = normalize(vec3(gd * across * 1.15, 1.0));
  float lit = dot(n, L3);
  // regional colour: lime -> green -> teal patches
  float reg = fbm(p * 0.0014 + vec2(5.0, uMorph * 0.05)) * 1.0 + 0.62;
  vec3 base = mix(DEEP, GREEN, smoothstep(0.1, 0.45, reg));
  base = mix(base, LIME2, smoothstep(0.45, 0.7, reg));
  base = mix(base, LIME, smoothstep(0.7, 0.95, reg));
  float teal = smoothstep(0.25, 0.55, fbm(p * 0.0012 + vec2(-8.0, 3.0)) + 0.5) * uTeal;
  base = mix(base, TEAL, teal * 0.85);
  vec3 rc = cel3(base * vec3(0.66, 0.72, 0.72), base, hiOf(base) + vec3(0.04, 0.035, 0.0), lit, 0.36, 0.8);
  rc *= brushMod(p, atan(gd.y, gd.x) + 1.57, 0.35, 0.10);
  vec3 gap = mix(GAP, GAP2, vnoise(p * 0.02));
  // ink: thin darker line hugging each ridge edge
  float edgeD = (tri - thr) * spacing * 0.5;
  vec3 col = mix(gap, rc, ridge);
  col = mix(col, inkOf(base) * 1.1, inkBand(edgeD, 0.9) * ridge * 0.85);

  // --- track bed
  float bedW = 64.0;
  float inBed = 1.0 - hstep(bedW, cx);
  vec3 bed = mix(BALLAST, BALLAST_D, step(0.62, hash12(floor(p / 3.0))) * 0.6 + vnoise(p * 0.08) * 0.3);
  float tie = (1.0 - hstep(3.6, abs(mod(p.y, 22.0) - 11.0))) * (1.0 - hstep(42.0, cx));
  bed = mix(bed, TIE, tie);
  float rail = 1.0 - hstep(2.6, abs(cx - 27.0));
  bed = mix(bed, RAILC, rail);
  bed = mix(bed, RAILC * 1.8, (1.0 - hstep(0.9, abs(cx - 26.0))) * rail);
  // edge strips: rust on the left, grass on the right
  float rust = (1.0 - hstep(5.0, abs(p.x + bedW - 4.0))) * step(p.x, 0.0);
  float grass = (1.0 - hstep(8.0, abs(p.x - bedW - 6.0))) * step(0.0, p.x);
  col = mix(col, bed, inBed);
  col = mix(col, RUST, rust);
  col = mix(col, GRASS * (0.9 + 0.2 * vnoise(p * 0.1)), grass);
  col = mix(col, inkOf(BALLAST), inkBand(cx - bedW, 1.1));
  // clear strip beside the bed
  float verge = (1.0 - hstep(84.0, cx)) * (1.0 - inBed) * (1.0 - grass) * (1.0 - rust);
  col = mix(col, GAP2 * 1.1, verge);
  return vec4(col, 1.0);
}
`;

const trainCar = (len: number, w: number, h: number, nose: boolean) => {
  const s = new Shape();
  const hw = w / 2;
  const r = 10;
  s.moveTo(-hw + r, 0);
  s.lineTo(hw - r, 0);
  s.quadraticCurveTo(hw, 0, hw, r);
  if (nose) {
    s.lineTo(hw, len - 46);
    s.bezierCurveTo(hw, len - 12, hw * 0.45, len, 0, len);
    s.bezierCurveTo(-hw * 0.45, len, -hw, len - 12, -hw, len - 46);
  } else {
    s.lineTo(hw, len - r);
    s.quadraticCurveTo(hw, len, hw - r, len);
    s.lineTo(-hw + r, len);
    s.quadraticCurveTo(-hw, len, -hw, len - r);
  }
  s.lineTo(-hw, r);
  s.quadraticCurveTo(-hw, 0, -hw + r, 0);
  return new ExtrudeGeometry(s, {depth: h, bevelEnabled: true, bevelThickness: 7, bevelSize: 6, bevelSegments: 3, curveSegments: 14});
};

const windshield = () => {
  const s = new Shape();
  s.moveTo(-22, 0);
  s.bezierCurveTo(-20, 22, 20, 22, 22, 0);
  s.lineTo(16, -4);
  s.bezierCurveTo(10, 12, -10, 12, -16, -4);
  s.closePath();
  return new ExtrudeGeometry(s, {depth: 3, bevelEnabled: false, curveSegments: 10});
};

export const grade = (f: number) =>
  mkGrade({
    bloom: 0.55,
    bloomThreshold: 0.92,
    streak: 0.15,
    exposure: 1.06,
    lift: [0.0, 0.004, 0.008],
    saturation: 1.1,
    haze: 0.04 + 0.08 * smoothstep(120, 300, f),
    hazeColor: [0.75, 0.88, 0.85],
    vignette: 0.3,
    shafts: 0.012,
    shaftAngle: -0.8,
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const front = cam.y - (TRAIN_FRONT_SY - 960);
  const tm = morphClock(d / 24);
  const ground = usePaint(GROUND, {uMorph: {value: 0}, uTeal: {value: 0}});
  ground.uniforms.uMorph.value = tm;
  ground.uniforms.uTeal.value = 0.35 + 0.65 * smoothstep(60, 200, f);
  const mistA = usePaint(MIST_FRAG, mistUniforms('#e4f4ec', 0.0, 480, [0.03, -0.01], 5.0, 0.05), {transparent: true, depthWrite: false});
  const mistB = usePaint(MIST_FRAG, mistUniforms('#d6efe8', 0.0, 330, [-0.02, -0.015], 23.0, 0.15), {transparent: true, depthWrite: false});
  const mist = smoothstep(100, 230, f);
  mistA.uniforms.uDensity.value = 0.45 * mist;
  mistB.uniforms.uDensity.value = 0.3 * mist;

  SHARED.uLightDir.value.set(0.5, -0.55, -0.68).normalize();
  SHARED.uShadowColor.value.set('#4f7a58');
  SHARED.uShadowZ.value = 0.5;

  const geos = useMemo(
    () => ({
      loco: trainCar(CAR_LEN, CAR_W, 34, true),
      car: trainCar(CAR_LEN, CAR_W, 34, false),
      plate: new BoxGeometry(34, 44, 4),
      fan: new CylinderGeometry(7.5, 7.5, 3, 16).rotateX(Math.PI / 2),
      vent: new BoxGeometry(26, 18, 3),
      link: new BoxGeometry(34, CAR_GAP + 10, 24),
      shield: windshield(),
      bush: new IcosahedronGeometry(1, 2),
      rock: new DodecahedronGeometry(1, 0),
    }),
    [],
  );

  const {bushes, rocks} = useMemo(() => {
    const rng = mulberry32(202);
    const yMax = SPEED * len + 2400;
    const pts = scatter(rng, 520, -760, -1200, 760, yMax, 120, (x) => Math.abs(x) > 110);
    const bushes: Instance[] = pts.map((p) => {
      const r = rrange(rng, 16, 27);
      const g = rrange(rng, 0, 1);
      return {x: p.x, y: p.y, z: r * 0.5, s: r, sz: 0.8, color: g < 0.5 ? '#2f6b3e' : g < 0.8 ? '#3a7a44' : '#2a5e3a'};
    });
    const rp = scatter(rng, 160, -760, -1200, 760, yMax, 240, (x) => Math.abs(x) > 110);
    const rocks: Instance[] = rp.map((p) => {
      const r = rrange(rng, 6, 10);
      return {x: p.x, y: p.y, z: r * 0.25, s: r, sz: 0.55, rz: rrange(rng, 0, 6.28), rx: rrange(rng, 0, 1), color: '#e2ded2'};
    });
    return {bushes, rocks};
  }, [len]);

  const cars = [0, 1, 2].map((i) => front - CAR_LEN - i * (CAR_LEN + CAR_GAP));
  const tailS = worldToScreen(cam, 0, cars[2] - 6, 0);

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.85} color="#cfe8d4" />
      <directionalLight position={[-550, 600, 750]} intensity={1.55} color="#fff6e0" />
      <PaintedPlane material={ground} cam={cam} />
      <InkedInstances geometry={geos.bush} items={bushes} inkWidth={1.8} shadow shadowStrength={0.9} />
      <InkedInstances geometry={geos.rock} items={rocks} inkWidth={1.2} inkMul={[0.55, 0.53, 0.5]} shadow shadowStrength={0.5} />
      {cars.map((y, i) => (
        <group key={i} position={[0, y, 0]}>
          <Inked geometry={i === 0 ? geos.loco : geos.car} color="#efede6" ink="#8d8a86" inkWidth={2.0} shadow />
          {[0.3, 0.7].map((t) => (
            <group key={t} position={[0, CAR_LEN * t, 41]}>
              <Inked geometry={geos.plate} color="#cfccc4" ink="#7d7a74" inkWidth={1.0} />
              <Inked geometry={geos.fan} color="#3c3d42" position={[0, 10, 3]} inkWidth={0.8} />
              <Inked geometry={geos.fan} color="#3c3d42" position={[0, -10, 3]} inkWidth={0.8} />
            </group>
          ))}
          <Inked geometry={geos.vent} color="#d9d6ce" position={[0, CAR_LEN * 0.5, 41]} inkWidth={0.8} />
          {i === 0 ? <Inked geometry={geos.shield} color="#2b2e38" position={[0, CAR_LEN - 30, 40]} inkWidth={0.8} /> : null}
          {i > 0 ? <Inked geometry={geos.link} color="#55565c" position={[0, CAR_LEN + CAR_GAP / 2, 10]} inkWidth={1} /> : null}
        </group>
      ))}
      <PaintedPlane material={mistA} cam={cam} z={180} renderOrder={6} />
      <PaintedPlane material={mistB} cam={cam} z={330} renderOrder={7} />
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{id: 's02', length: len, a: () => ({x: tailS.sx, y: tailS.sy}), b: () => ({x: 536, y: 1990}), sway: 0.03, slack: 1.01, seed: 2}}
        look={{z: () => 3, width: 3.4}}
      />
    </>
  );
};
