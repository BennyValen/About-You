import React, {useMemo} from 'react';
import {AdditiveBlending, ExtrudeGeometry, Shape, Vector2, BoxGeometry} from 'three';
import {CameraRig, CamPose, pose, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint, MIST_FRAG, mistUniforms} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED, toonMaterial} from '../kit/toon';

// Scene 1: night snowy pine forest from above. A train runs up a cleared corridor; its
// headlight lights the track ahead and its windows throw warm pools on the snow.

const SPEED = 6.25; // px per frame, measured from the source
const TRAIN_FRONT_SY = 990; // screen y of the locomotive front
const CAR_LEN = 226;
const CAR_GAP = 12;
const CAR_W = 54;

const camAt = (f: number): CamPose => pose(Math.sin(f * 0.004) * 6, 0 + SPEED * f, 1.0 + f * 0.00008);

const GROUND = /* glsl */ `
uniform float uFront;     // world y of the locomotive front
uniform float uTrainLen;
const vec3 SNOW = ${glc('#4b579c')};
const vec3 SNOW_L = ${glc('#6876ba')};
const vec3 SNOW_D = ${glc('#36407c')};
const vec3 TREE = ${glc('#28324f')};
const vec3 TREE_L = ${glc('#36426a')};
const vec3 TREE_D = ${glc('#1a2038')};
const vec3 TIP = ${glc('#c2cdf0')};
const vec3 ICE = ${glc('#1b2150')};
const vec3 ICE_L = ${glc('#2c3570')};
const vec3 RAIL = ${glc('#1f2240')};
const vec3 LAMP = ${glc('#f09a3c')};
const vec3 BEAM = ${glc('#e6ecff')};
const vec2 L2 = vec2(-0.85, 0.4);   // moon direction in the ground plane (toward the light): from the left

float pondSdf(vec2 p){
  // frozen pond, top-left of the route
  vec2 q = p - vec2(-430.0, 2470.0);
  q.x *= 0.82;
  float d = length(q) - 470.0;
  d += 35.0 * gnoise(p * 0.004 + 3.0) + 12.0 * gnoise(p * 0.013);
  return d;
}

// conifer seen from above: two stacked star tiers with fuzzy branch tips.
// Returns height (-1 if no tree) plus shading info.
float treeAt(vec2 p, vec2 c, float R, float rot, float nb, float seed, out float lit, out float edge, out float tipSnow){
  vec2 d = p - c;
  float r = length(d);
  lit = 0.0; edge = 1e3; tipSnow = 0.0;
  if (r > R * 1.05) return -1.0;
  float a = atan(d.y, d.x);
  float best = -1.0;
  vec2 radial = d / max(r, 1e-3);
  for (int k = 0; k < 2; k++) {
    float fk = float(k);
    float Rk = R * (1.0 - 0.42 * fk);
    float ak = a + rot + fk * PI / nb;
    float sp = 0.5 + 0.5 * cos(ak * nb);
    float spike = pow(sp, 1.6);
    float fuzz = gnoise(vec2(a * 9.0, seed + fk * 3.0)) * 0.07 + gnoise(vec2(a * 31.0, seed)) * 0.035;
    float prof = Rk * (0.6 + 0.36 * spike + fuzz);
    if (r < prof) {
      float h = fk * 0.5 + 0.5 * (1.0 - r / prof);
      if (h > best) {
        best = h;
        float side = sign(sin(ak * nb));
        vec2 nrm = rot2(radial, side * 0.7);
        lit = dot(nrm, normalize(L2)) * 0.5 + 0.5;
        edge = (prof - r);
        // snow dashes: sparse, irregular radial strokes on the side facing the moon
        float u = ak * nb / (2.0 * PI);
        float bin = floor(u + 0.5);
        float rb = floor(r / 26.0 + hash11(bin + seed) * 3.0);
        vec3 hh = hash32(vec2(bin, rb) + c * 0.37 + fk * 7.0);
        float rc = (rb - hash11(bin + seed) * 3.0 + 0.5) * 26.0 + (hh.y - 0.5) * 10.0;
        float spineOff = (fract(u + 0.5) - 0.5 + (hh.z - 0.5) * 0.25) * (2.0 * PI / nb) * r;
        float facing = dot(radial, normalize(L2));
        float on = step(hh.x, 0.28 + 0.55 * facing) * step(0.22 * R, r) * step(r, prof - 3.0);
        float len = 7.0 + 7.0 * hh.y;
        float dash = (1.0 - hstep(1.9 + 1.3 * hh.z, abs(spineOff))) * (1.0 - hstep(len, abs(r - rc)));
        tipSnow = on * dash;
      }
    }
  }
  return best;
}

vec4 paint(vec2 p){
  vec3 col;
  // --- snow ground with wind drifts
  float drift = sin((p.y * 0.9 + p.x * 0.35 + 140.0 * fbm(p * 0.002)) * 0.03) * 0.5;
  float dl = drift + 0.9 * fbm(p * 0.0018 + 7.0);
  col = cel3(SNOW_D, SNOW, SNOW_L, dl * 0.5 + 0.5, 0.22, 0.8);
  col *= brushMod(p, -0.35, 1.0, 0.10);

  // --- corridor (track bed)
  float cx = abs(p.x);
  float bank = 56.0 + 6.0 * gnoise(vec2(p.y * 0.02, 1.0));
  float inCor = 1.0 - hstep(bank, cx);
  vec3 bed = mix(SNOW, SNOW_L, 0.35);
  col = mix(col, bed, inCor);
  // snowbank ink lines along the corridor edges
  col = mix(col, inkOf(SNOW_L) * 1.3, inkBand(cx - bank, 1.1 + 0.6 * vnoise(vec2(p.y * 0.05, 2.0))) * 0.8);
  col = mix(col, SNOW_L * 1.12, inkBand(cx - bank - 7.0, 2.0) * 0.6);
  // rails + ties
  float ties = 1.0 - hstep(3.2, abs(mod(p.y, 15.0) - 7.5));
  ties *= 1.0 - hstep(25.0, cx);
  float rails = inkBand(cx - 15.0, 1.6);
  float track = max(ties * 0.75, rails);

  // --- frozen pond
  float pd = pondSdf(p);
  float inPond = fillCov(pd);
  vec3 ice = mix(ICE, ICE_L, smoothstep(0.2, 0.8, strokeField(p, 0.5, vec2(160.0, 6.0)) * 0.5 + 0.5) * 0.6);
  col = mix(col, ice, inPond);
  col = mix(col, inkOf(SNOW) * 1.2, inkBand(pd, 2.2) );
  col = mix(col, SNOW_L * 1.1, inkBand(pd - 7.0, 2.5) * 0.7);

  // --- forest
  float cell = 150.0;
  vec2 gp = floor(p / cell);
  float topH = -1.0, topLit = 0.0, topEdge = 1e3, topTip = 0.0, topSeed = 0.0;
  float shadow = 0.0;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
    vec2 g = gp + vec2(float(i), float(j));
    vec3 h3 = hash32(g * 1.17 + 3.0);
    vec2 c = (g + 0.5 + (h3.xy - 0.5) * 0.45) * cell;
    float dens = fbm(c * 0.0013 + 11.0) + 0.42;
    bool ok = dens > 0.0 && h3.z < 0.95 && abs(c.x) > 135.0 && pondSdf(c) > 30.0;
    if (!ok) continue;
    float R = mix(84.0, 122.0, hash12(g + 9.1));
    float rot = hash12(g + 4.4) * 6.28;
    float nb = floor(mix(12.0, 17.0, hash12(g + 2.2)));
    float seed = hash12(g + 5.5) * 50.0;
    float l, e, tp;
    float h = treeAt(p, c, R, rot, nb, seed, l, e, tp);
    // tie-break overlapping trees by a per-tree height so they layer
    if (h > -0.5) h += h3.z * 0.6;
    if (h > topH) { topH = h; topLit = l; topEdge = e; topTip = tp; topSeed = seed; }
    // cast shadow, away from the moon
    vec2 sc = c - normalize(L2) * R * 0.55;
    vec2 sd = p - sc;
    float sa = atan(sd.y, sd.x) + rot;
    float sprof = R * 1.02 * (0.6 + 0.36 * pow(0.5 + 0.5 * cos(sa * nb), 1.6));
    shadow = max(shadow, 1.0 - hstep(sprof, length(sd)));
  }
  col = mix(col, col * vec3(0.5, 0.52, 0.72), shadow);

  // --- train light: warm pools from the windows and the headlight beam (computed before trees so trees occlude)
  float relY = p.y - (uFront - uTrainLen);
  float alongTrain = step(0.0, relY) * step(relY, uTrainLen);
  float carPos = mod(uFront - p.y, ${(CAR_LEN + CAR_GAP).toFixed(1)});
  float inCar = step(6.0, carPos) * step(carPos, ${(CAR_LEN - 6).toFixed(1)});
  float win = 0.55 + 0.45 * step(0.35, fract(p.y / 13.0));
  float lateral = cx - ${(CAR_W / 2).toFixed(1)};
  float spillLen = 56.0 + 14.0 * gnoise(vec2(p.y * 0.05, 5.0));
  float rays = 0.6 + 0.4 * smoothstep(-0.2, 0.5, gnoise(vec2(p.y * 0.11, lateral * 0.01 + 2.0)));
  float spill = alongTrain * inCar * win * rays * step(0.0, lateral) * (1.0 - lateral / spillLen);
  spill = max(spill, 0.0);
  float spillQ = hstep(0.1, spill) * 0.35 + hstep(0.55, spill) * 0.45;

  float by = p.y - uFront;
  float bt = by / 900.0;
  float bw = 34.0 + by * 0.07;
  float beam = step(0.0, by) * pow(1.0 - smoothstep(0.0, 1.0, bt), 1.6) * (1.0 - smoothstep(bw * 0.45, bw, cx));
  float beamQ = hstep(0.04, beam) * 0.16 + hstep(0.25, beam) * 0.18 + hstep(0.6, beam) * 0.2;

  // track shows mostly where light falls on it
  col = mix(col, RAIL, track * inCor * (0.35 + 0.5 * beamQ));
  vec3 lit = col;
  lit += BEAM * beamQ * (1.0 - track * 0.85) * 0.9;
  lit = mix(lit, LAMP * 0.95, spillQ * 0.85 * (1.0 - track * 0.5));

  col = lit;
  if (topH > -0.5) {
    vec3 tc = cel3(TREE_D, TREE, TREE_L, topLit, 0.4, 0.86);
    tc *= brushMod(p, 0.9, 0.5, 0.07);
    tc = mix(tc, TIP, topTip * 0.92);
    // ink: darker tint of the needles, variable width
    float w = 0.9 + 0.9 * vnoise(p * 0.05);
    tc = mix(tc, inkOf(TREE) * 0.8, inkBand(topEdge, w) );
    // spill light reaching the near trees
    tc += LAMP * spillQ * 0.35 + BEAM * beamQ * 0.15;
    col = tc;
  }
  return vec4(col, 1.0);
}
`;

// carriage footprint: rounded rectangle, extruded upward
const carGeometry = (len: number, w: number, h: number, nose = false) => {
  const s = new Shape();
  const r = 9;
  const hw = w / 2;
  s.moveTo(-hw + r, 0);
  s.lineTo(hw - r, 0);
  s.quadraticCurveTo(hw, 0, hw, r);
  if (nose) {
    s.lineTo(hw, len - 34);
    s.quadraticCurveTo(hw, len, 0, len);
    s.quadraticCurveTo(-hw, len, -hw, len - 34);
  } else {
    s.lineTo(hw, len - r);
    s.quadraticCurveTo(hw, len, hw - r, len);
    s.lineTo(-hw + r, len);
    s.quadraticCurveTo(-hw, len, -hw, len - r);
  }
  s.lineTo(-hw, r);
  s.quadraticCurveTo(-hw, 0, -hw + r, 0);
  const g = new ExtrudeGeometry(s, {depth: h, bevelEnabled: true, bevelThickness: 5, bevelSize: 4, bevelSegments: 2, curveSegments: 10});
  return g;
};

const BEAM_FRAG = /* glsl */ `
uniform float uFront;
vec4 paint(vec2 p){
  float by = p.y - uFront;
  float bt = by / 950.0;
  float cx = abs(p.x);
  float bw = 26.0 + by * 0.1;
  float core = step(0.0, by) * pow(1.0 - smoothstep(0.0, 1.0, bt), 2.0);
  float lat = 1.0 - smoothstep(bw * 0.3, bw, cx);
  float mist = 0.7 + 0.3 * fbm(vec2(p.x * 0.02, p.y * 0.004 - uTime * 0.6));
  float a = core * lat * mist;
  // painted volume: two hard-edged bands plus a soft core
  float q = hstep(0.12, a) * 0.25 + hstep(0.45, a) * 0.25 + a * 0.5;
  return vec4(vec3(0.85, 0.9, 1.1), q * 0.32);
}`;

// warm window light scattered in the fog around the carriages (additive glow layer above the fog)
const LAMPFOG = /* glsl */ `
uniform float uFront;
uniform float uTrainLen;
uniform float uFog;
vec4 paint(vec2 p){
  float relY = p.y - (uFront - uTrainLen);
  float along = smoothstep(-40.0, 30.0, relY) * (1.0 - smoothstep(uTrainLen - 30.0, uTrainLen + 40.0, relY));
  float cx = abs(p.x);
  float side = exp(-pow(max(cx - 34.0, 0.0) / 60.0, 2.0)) * smoothstep(26.0, 46.0, cx);
  float mist = 0.6 + 0.4 * fbm(vec2(p.x * 0.01, p.y * 0.006 - uTime * 0.2));
  float a = along * side * mist * uFog;
  return vec4(${glc('#ff9a3c')} * a * 0.3, 1.0);
}`;

export const grade = (f: number) =>
  mkGrade({
    exposure: 1.0,
    bloom: 1.25,
    bloomThreshold: 0.62,
    bloomRadius: 0.78,
    streak: 0.5,
    streakThreshold: 0.9,
    streakTint: [1.0, 0.75, 0.5],
    lift: [0.0, 0.015, 0.04],
    haze: 0.06,
    hazeColor: [0.32, 0.36, 0.6],
    vignette: 0.42,
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const front = cam.y - (TRAIN_FRONT_SY - 960);
  const trainLen = 3 * CAR_LEN + 2 * CAR_GAP;

  const groundMat = usePaint(GROUND, {uFront: {value: 0}, uTrainLen: {value: trainLen}});
  groundMat.uniforms.uFront.value = front;
  const beamMat = usePaint(BEAM_FRAG, {uFront: {value: 0}}, {transparent: true, blending: AdditiveBlending, depthWrite: false});
  beamMat.uniforms.uFront.value = front;
  const fogA = usePaint(MIST_FRAG, mistUniforms('#aeb8e6', 0.5, 520, [0.05, -0.012], 3.0, -0.05), {transparent: true, depthWrite: false});
  const fogB = usePaint(MIST_FRAG, mistUniforms('#c4cdf0', 0.36, 380, [-0.03, -0.02], 17.0, 0.1), {transparent: true, depthWrite: false});
  // fog thickens through the middle of the shot, as in the source
  const fogAmt = 0.45 + 0.55 * Math.sin(Math.min(1, f / 260) * Math.PI) ** 1.2;
  fogA.uniforms.uDensity.value = 0.36 * fogAmt;
  fogB.uniforms.uDensity.value = 0.3 * fogAmt;
  const lampFog = usePaint(LAMPFOG, {uFront: {value: 0}, uTrainLen: {value: trainLen}, uFog: {value: 0}}, {transparent: true, blending: AdditiveBlending, depthWrite: false});
  lampFog.uniforms.uFront.value = front;
  lampFog.uniforms.uFog.value = 0.35 + 0.65 * fogAmt;

  const geos = useMemo(
    () => ({
      loco: carGeometry(CAR_LEN, CAR_W, 30, true),
      car: carGeometry(CAR_LEN, CAR_W, 30),
      window: new BoxGeometry(3, CAR_LEN - 24, 6),
      ridge: new BoxGeometry(10, CAR_LEN - 40, 4),
      vent: new BoxGeometry(18, 22, 5),
      link: new BoxGeometry(26, CAR_GAP + 8, 18),
    }),
    [],
  );
  const winMat = useMemo(() => toonMaterial('#ffb24a', {emissive: '#ff9a30', emissiveIntensity: 3.2}), []);

  // moonlight for the toon objects
  SHARED.uLightDir.value.set(-0.5, -0.55, -0.67).normalize();

  const cars = [0, 1, 2].map((i) => front - CAR_LEN - i * (CAR_LEN + CAR_GAP));
  const tail = cars[2];
  const tailS = worldToScreen(cam, 0, tail, 0);

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.55} color="#4a5596" />
      <directionalLight position={[-700, 330, 600]} intensity={1.6} color="#a9b8ff" />
      <PaintedPlane material={groundMat} cam={cam} z={0} />
      {cars.map((y, i) => (
        <group key={i} position={[0, y, 0]}>
          <Inked geometry={i === 0 ? geos.loco : geos.car} color="#262838" inkWidth={2.2} />
          <Inked geometry={geos.ridge} color="#34374d" position={[0, CAR_LEN / 2, 36]} inkWidth={1.2} />
          {[0.22, 0.5, 0.78].map((t) => (
            <Inked key={t} geometry={geos.vent} color="#3c3f58" position={[0, CAR_LEN * t, 37]} inkWidth={1.1} />
          ))}
          <mesh geometry={geos.window} material={winMat} position={[CAR_W / 2 + 3.5, CAR_LEN / 2, 16]} />
          <mesh geometry={geos.window} material={winMat} position={[-CAR_W / 2 - 3.5, CAR_LEN / 2, 16]} />
          {i > 0 ? <Inked geometry={geos.link} color="#1a1b28" position={[0, CAR_LEN + CAR_GAP / 2, 12]} inkWidth={1} /> : null}
        </group>
      ))}
      <PaintedPlane material={beamMat} cam={cam} z={44} renderOrder={5} />
      <PaintedPlane material={fogA} cam={cam} z={160} renderOrder={6} />
      <PaintedPlane material={fogB} cam={cam} z={320} renderOrder={7} />
      <PaintedPlane material={lampFog} cam={cam} z={340} renderOrder={8} />
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{
          id: 's01',
          length: len,
          a: () => ({x: tailS.sx, y: tailS.sy + 2}),
          b: () => ({x: 538, y: 1990}),
          sway: 0.03,
          slack: 1.01,
          seed: 1,
        }}
        look={{z: (s) => 2 + (1 - s) * 2, width: 3.4, renderOrder: 4}}
      />
    </>
  );
};

export {Vector2};
