import React, {useEffect, useMemo} from 'react';
import {Blending, Color, NormalBlending, ShaderMaterial, Side, DoubleSide, IUniform} from 'three';
import {CamPose, viewExtent} from './camera';
import {GLSL_LIB, WORLD_VERT} from './glsl';

// Per-scene time uniforms shared by every painted material. Main.tsx writes them each frame.
// uTime: smooth seconds (camera-rate). uDraw: seconds quantised to drawings (on twos).
export const SCENE_U = {
  uTime: {value: 0},
  uDraw: {value: 0},
  uFrame: {value: 0},
  uCam: {value: [0, 0, 0] as [number, number, number]},
};

export type SceneProps = {f: number; d: number; len: number};

export type PaintOpts = {
  transparent?: boolean;
  blending?: Blending;
  depthWrite?: boolean;
  depthTest?: boolean;
  side?: Side;
  extraHeader?: string;
};

// A ShaderMaterial whose fragment code defines `vec4 paint(vec2 p)` with p in world units.
export const paintMaterial = (frag: string, uniforms: Record<string, IUniform> = {}, o: PaintOpts = {}) =>
  new ShaderMaterial({
    uniforms: {
      uTime: SCENE_U.uTime,
      uDraw: SCENE_U.uDraw,
      uFrame: SCENE_U.uFrame,
      ...uniforms,
    },
    vertexShader: WORLD_VERT,
    fragmentShader:
      'uniform float uTime;\nuniform float uDraw;\nuniform float uFrame;\nvarying vec3 vWorld;\nvarying vec2 vUv;\n' +
      GLSL_LIB +
      (o.extraHeader ?? '') +
      frag +
      '\nvoid main(){ vec4 c = paint(vWorld.xy); gl_FragColor = c; }\n',
    transparent: o.transparent ?? false,
    blending: o.blending ?? NormalBlending,
    depthWrite: o.depthWrite ?? !(o.transparent ?? false),
    depthTest: o.depthTest ?? true,
    side: o.side ?? DoubleSide,
  });

// A world-anchored plane at height z that always covers the camera view.
export const PaintedPlane: React.FC<{
  material: ShaderMaterial;
  cam: CamPose;
  z?: number;
  margin?: number;
  renderOrder?: number;
}> = ({material, cam, z = 0, margin = 1.2, renderOrder = 0}) => {
  useEffect(() => () => material.dispose(), [material]);
  const {hw, hh} = viewExtent(cam, z, margin);
  const r = Math.abs(cam.roll ?? 0) > 1e-4;
  const ex = r ? Math.hypot(hw, hh) : hw;
  const ey = r ? Math.hypot(hw, hh) : hh;
  return (
    <mesh material={material} position={[cam.x, cam.y, z]} scale={[ex * 2, ey * 2, 1]} renderOrder={renderOrder} frustumCulled={false}>
      <planeGeometry args={[1, 1]} />
    </mesh>
  );
};

export const usePaint = (frag: string, uniforms: Record<string, IUniform> = {}, o: PaintOpts = {}) =>
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useMemo(() => paintMaterial(frag, uniforms, o), []);

// Drifting mist / fog wisps at height z: painted, soft-edged noise with brush streaks.
export const MIST_FRAG = /* glsl */ `
uniform vec3 uColor;
uniform float uDensity;
uniform float uScale;
uniform vec2 uWind;
uniform float uSeed;
uniform float uCover;
vec4 paint(vec2 p){
  vec2 q = p / uScale + uWind * uTime + uSeed;
  float n = fbm(q * 0.9 + 0.3 * vec2(fbm(q * 0.5 + 3.1), fbm(q * 0.5 - 7.7)));
  float m = smoothstep(uCover, uCover + 0.55, n);
  float streak = 0.85 + 0.15 * gnoise(rot2(p, 0.4) / vec2(90.0, 8.0) + uSeed);
  float a = m * uDensity * streak;
  return vec4(uColor, a);
}`;

export const mistUniforms = (color: string, density: number, scale: number, wind: [number, number], seed: number, cover = 0.0) => ({
  uColor: {value: new Color(color)},
  uDensity: {value: density},
  uScale: {value: scale},
  uWind: {value: wind},
  uSeed: {value: seed},
  uCover: {value: cover},
});
