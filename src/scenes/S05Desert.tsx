import React, {useMemo} from 'react';
import {CapsuleGeometry, SphereGeometry, CylinderGeometry} from 'three';
import {CameraRig, CamPose, pose, worldToScreen} from '../kit/camera';
import {glc} from '../kit/glsl';
import {Inked} from '../kit/Inked';
import {PaintedPlane, SceneProps, usePaint} from '../kit/layers';
import {grade as mkGrade} from '../kit/post';
import {RedThread} from '../kit/thread';
import {SHARED} from '../kit/toon';

// Scene 5: desert. A camel and rider walk up between meandering purple dune shadows;
// the low sun from the left throws the camel's long side-profile shadow to the right.

const SPEED = 3.0;
const CAMEL_SY = 1170;
const CAMEL_X = 34;
const STEP = 36; // frames per walk cycle

const camAt = (f: number): CamPose => pose(0, SPEED * f, 1.0 + f * 0.00005);

const GROUND = /* glsl */ `
uniform float uTail;    // world y of the camel's hind feet
const vec3 SAND_A = ${glc('#e39572')};
const vec3 SAND_B = ${glc('#efb06e')};
const vec3 SAND_C = ${glc('#d58a6c')};
const vec3 LINE_L = ${glc('#fad29a')};
const vec3 LINE_D = ${glc('#bd7a64')};
const vec3 PURP = ${glc('#5f417a')};
const vec3 PURP_D = ${glc('#47305e')};
const vec3 PURP_L = ${glc('#7c5e98')};
const vec3 LAV = ${glc('#b49ac8')};
const vec3 PRINT = ${glc('#9a5e5c')};

float bandX(int k, float y){
  float fk = float(k);
  float base = fk == 0.0 ? -270.0 : fk == 1.0 ? 285.0 : fk == 2.0 ? -640.0 : 650.0;
  return base + 70.0 * sin(y * 0.0042 + fk * 1.9) + 34.0 * sin(y * 0.011 + fk * 4.1) + 40.0 * fbm(vec2(y * 0.002, fk * 3.0));
}
float bandW(int k, float y){
  float fk = float(k);
  return (fk < 2.0 ? 135.0 : 190.0) + 40.0 * sin(y * 0.006 + fk) + 26.0 * gnoise(vec2(y * 0.008, fk * 7.0));
}

vec4 paint(vec2 p){
  // dune "height" whose iso-lines are the striations: every line inherits the meander of the
  // nearest shadow bands (weighted by distance), and lines bunch up toward the bands
  float H = 0.0;
  float wsum = 0.0;
  float inPurple = 0.0;
  float edgeD = 1e3;
  float deep = 0.0;
  float comp = 0.0;
  for (int k = 0; k < 4; k++) {
    float bx = bandX(k, p.y);
    float base = k == 0 ? -270.0 : k == 1 ? 285.0 : k == 2 ? -640.0 : 650.0;
    float bw = bandW(k, p.y) * 0.5;
    float u = p.x - bx;
    float wk = 1.0 / (1.0 + pow(abs(u) / 220.0, 2.0));
    H += wk * (bx - base);
    wsum += wk;
    comp += 38.0 * tanh(u / 70.0);
    float e = abs(u) - bw - 14.0 * gnoise(vec2(p.y * 0.02, float(k)));
    inPurple = max(inPurple, fillCov(e));
    edgeD = min(edgeD, abs(e));
    deep = max(deep, 1.0 - smoothstep(0.0, bw, abs(u + bw * 0.25)));
  }
  H = p.x - H / max(wsum, 1e-3) + comp + 5.0 * gnoise(p * 0.01);
  float ph = H / 12.0;
  float ln = 1.0 - abs(fract(ph) - 0.5) * 2.0;
  float line = hstep(0.8, ln);
  float dline = hstep(0.84, 1.0 - abs(fract(ph + 0.5) - 0.5) * 2.0);
  // sand: broad warm variation, lit lines + darker grooves
  float reg = fbm(p * 0.0012 + 3.0) + 0.55 + 0.25 * smoothstep(200.0, 0.0, abs(p.x - 40.0)) * 0.0;
  vec3 sand = mix(SAND_C, SAND_A, smoothstep(0.1, 0.5, reg));
  sand = mix(sand, SAND_B, smoothstep(0.5, 0.9, reg));
  vec3 col = sand;
  col = mix(col, LINE_D, dline * 0.55);
  col = mix(col, LINE_L, line * 0.9);
  // shadowed lee faces (purple), striations in lavender
  vec3 pc = cel3(PURP_D, PURP, PURP_L, 1.0 - deep * 0.9, 0.3, 0.8);
  pc = mix(pc, LAV * 0.9, line * 0.7);
  pc = mix(pc, PURP_D * 0.9, dline * 0.4);
  col = mix(col, pc, inPurple);
  col = mix(col, inkOf(PURP) * 1.4, inkBand(edgeD, 1.0) * 0.5);
  col *= brushMod(p, 1.57, 0.8, 0.06);

  // footprints: two staggered rows behind the camel
  float n = floor(p.y / 46.0);
  float side = mod(n, 2.0) * 2.0 - 1.0;
  vec2 fc = vec2(${CAMEL_X.toFixed(1)} + side * 13.0 + 3.0 * gnoise(vec2(n, 2.0)), (n + 0.5) * 46.0);
  vec2 fd = (p - fc) / vec2(4.6, 6.4);
  float fp = length(fd) - 1.0;
  float onP = step(fc.y, uTail);
  col = mix(col, PRINT, fillCov(fp * 5.0) * onP * 0.9);
  col = mix(col, LINE_L, inkBand((length((p - fc - vec2(-1.5, 2.0)) / vec2(4.6, 6.4)) - 1.0) * 5.0, 0.8) * onP * 0.6);
  return vec4(col, 1.0);
}
`;

export const grade = () =>
  mkGrade({
    bloom: 0.4,
    bloomThreshold: 0.97,
    streak: 0.1,
    exposure: 1.0,
    lift: [0.0, 0.004, 0.012],
    splitShadow: [-0.01, 0.0, 0.03],
    splitHigh: [0.03, 0.01, -0.02],
    saturation: 1.02,
    haze: 0.05,
    hazeColor: [0.95, 0.75, 0.75],
    vignette: 0.3,
    shafts: 0.012,
    shaftAngle: 0.2,
  });

export const Component: React.FC<SceneProps> = ({f, d, len}) => {
  const cam = camAt(f);
  const cy = cam.y - (CAMEL_SY - 960);
  const ground = usePaint(GROUND, {uTail: {value: 0}});
  ground.uniforms.uTail.value = cy - 70;

  SHARED.uLightDir.value.set(0.74, 0.06, -0.67).normalize();
  SHARED.uShadowColor.value.set('#8466a8');
  SHARED.uShadowAlpha.value = 0.82;
  SHARED.uShadowZ.value = 0.5;

  const g = useMemo(
    () => ({
      body: new SphereGeometry(1, 20, 14),
      hump: new SphereGeometry(1, 16, 12),
      neck: new CapsuleGeometry(6.5, 72, 4, 10),
      head: new CapsuleGeometry(6.5, 24, 4, 10),
      leg: new CapsuleGeometry(7, 90, 4, 8),
      tail: new CapsuleGeometry(3, 26, 3, 6),
      rider: new SphereGeometry(1, 16, 12),
      hat: new CylinderGeometry(14, 14, 5, 20).rotateX(Math.PI / 2),
      hatTop: new SphereGeometry(9, 12, 8),
    }),
    [],
  );
  // walk cycle on twos: diagonal pairs of legs swing in opposition
  const ph = (d / STEP) * Math.PI * 2;
  const swing = (o: number) => Math.sin(ph + o) * 0.42;
  const bob = Math.sin(ph * 2) * 2.5;
  const legZ = 55;
  const tailS = worldToScreen(cam, CAMEL_X, cy - 62, 60);
  const C = '#ece4dc';
  const INK = '#7a6a6e';
  const legs: [number, number, number][] = [
    [-11, 34, 0],
    [11, 34, Math.PI],
    [-11, -40, Math.PI],
    [11, -40, 0],
  ];

  return (
    <>
      <CameraRig pose={cam} />
      <ambientLight intensity={0.8} color="#e8c8c8" />
      <directionalLight position={[-740, -60, 670]} intensity={1.45} color="#fff0dc" />
      <PaintedPlane material={ground} cam={cam} />
      <group position={[CAMEL_X, cy, bob]}>
        {legs.map(([x, y, o], i) => (
          <Inked
            key={i}
            geometry={g.leg}
            color="#ddd3ca"
            ink={INK}
            position={[x, y, legZ]}
            rotation={[Math.PI / 2 + swing(o), 0, 0]}
            inkWidth={1.0}
            shadow
            shadowMode="tint"
          />
        ))}
        <Inked geometry={g.body} color={C} ink={INK} position={[0, -4, 106]} scale={[16, 50, 17]} inkWidth={1.5} shadow shadowMode="tint" />
        <Inked geometry={g.hump} color={C} ink={INK} position={[0, 6, 122]} scale={[13, 22, 14]} inkWidth={1.2} shadow shadowMode="tint" />
        <Inked geometry={g.neck} color={C} ink={INK} position={[0, 76, 128]} rotation={[0.45, 0, 0]} inkWidth={1.2} shadow shadowMode="tint" />
        <Inked geometry={g.head} color="#e6ddd4" ink={INK} position={[0, 118, 150]} rotation={[-0.15, 0, 0]} inkWidth={1.1} shadow shadowMode="tint" />
        <Inked geometry={g.tail} color="#d8cdc4" ink={INK} position={[0, -70, 92]} rotation={[1.04, 0, 0]} inkWidth={0.9} shadow shadowMode="tint" />
        {/* rider sitting just behind the hump: dark round hat seen from above */}
        <Inked geometry={g.rider} color="#5a5266" ink="#262030" position={[0, -14, 140]} scale={[14, 12, 22]} inkWidth={1.3} shadow shadowMode="tint" />
        <Inked geometry={g.hat} color="#3c3644" ink="#17141b" position={[0, -12, 164]} inkWidth={1.3} shadow shadowMode="tint" />
        <Inked geometry={g.hatTop} color="#4a4452" ink="#17141b" position={[0, -12, 168]} scale={[1, 1, 0.6]} inkWidth={1} />
      </group>
      <RedThread
        cam={cam}
        drawFrame={d}
        cfg={{id: 's05', length: len, a: () => ({x: tailS.sx, y: tailS.sy}), b: () => ({x: 570, y: 1990}), sway: 0.07, waves: 2.0, slack: 1.02, seed: 5}}
        look={{z: (s) => 1.5 + (1 - s) * 50, width: 3.4}}
      />
    </>
  );
};
