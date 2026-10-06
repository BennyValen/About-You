import {
  BackSide,
  BufferGeometry,
  Color,
  CustomBlending,
  DataTexture,
  DstColorFactor,
  FrontSide,
  MeshToonMaterial,
  NearestFilter,
  NotEqualStencilFunc,
  OneFactor,
  RedFormat,
  ReplaceStencilOp,
  ShaderMaterial,
  Side,
  UnsignedByteType,
  Vector3,
  ZeroFactor,
} from 'three';
import {mergeVertices} from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import {GLSL_NOISE} from './glsl';

// ---------------------------------------------------------------------------
// Shared per-frame uniforms. Main.tsx writes these once per frame.
// uBoil is the drawing index: it only changes every 2nd frame (animation on twos).
export const SHARED = {
  uBoil: {value: 0},
  uBoilAmp: {value: 1.1},
  uLightDir: {value: new Vector3(0.35, -0.45, -1).normalize()},
  uShadowColor: {value: new Color('#7d6fa8')},
  uShadowZ: {value: 0.6},
  uShadowAlpha: {value: 0.6},
  uShadowDepth: {value: 0},
};

// Reset per-frame shared state to defaults (scenes override what they need), so a
// render never depends on which scene a browser tab happened to draw before.
export const resetShared = () => {
  SHARED.uBoilAmp.value = 1.1;
  SHARED.uLightDir.value.set(0.35, -0.45, -1).normalize();
  SHARED.uShadowColor.value.set('#7d6fa8');
  SHARED.uShadowZ.value = 0.6;
  SHARED.uShadowAlpha.value = 0.6;
  SHARED.uShadowDepth.value = 0;
};

const BOIL_GLSL = /* glsl */ `
uniform float uBoil;
uniform float uBoilAmp;
vec2 boilOffset(vec3 wp){
  float s = uBoil * 1.618;
  vec2 q = wp.xy * 0.045;
  return (vec2(vnoise(q + vec2(s*3.1, s*1.7)), vnoise(q.yx + vec2(s*2.3 + 11.0, s*4.1))) - 0.5) * 2.0 * uBoilAmp;
}
`;

// 3-step gradient map for MeshToonMaterial: shadow / base / highlight, hard edges.
// dotNL in [-1,1] maps to the texture's 0..1, split at tShadow / tHigh.
export const makeGradient = (tShadow = 0.12, tHigh = 0.78, levels: [number, number, number] = [0.46, 0.78, 1.0]) => {
  const n = 32;
  const data = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const d = -1 + (2 * (i + 0.5)) / n;
    const v = d < tShadow ? levels[0] : d < tHigh ? levels[1] : levels[2];
    data[i] = Math.round(v * 255);
  }
  const tex = new DataTexture(data, n, 1, RedFormat, UnsignedByteType);
  tex.minFilter = NearestFilter;
  tex.magFilter = NearestFilter;
  tex.generateMipmaps = false;
  tex.needsUpdate = true;
  return tex;
};

export const GRADIENT3 = makeGradient();

export type ToonOpts = {
  emissive?: string;
  emissiveIntensity?: number;
  transparent?: boolean;
  opacity?: number;
  side?: Side;
  gradient?: DataTexture;
  boil?: boolean;
  vertexColors?: boolean;
  fur?: number; // radial strand streaks (fluffy canopies), strength 0..1
  spiral?: number; // rolled hay bale top: spiral stripes on up-facing faces, turns
};

// MeshToonMaterial + hand-drawn boil: the whole drawing jitters ~1px per drawing (on twos).
export const toonMaterial = (color: string | Color, o: ToonOpts = {}) => {
  const m = new MeshToonMaterial({
    color: color instanceof Color ? color : new Color(color),
    gradientMap: o.gradient ?? GRADIENT3,
    emissive: o.emissive ? new Color(o.emissive) : new Color(0x000000),
    emissiveIntensity: o.emissiveIntensity ?? 1,
    transparent: o.transparent ?? false,
    opacity: o.opacity ?? 1,
    side: o.side ?? FrontSide,
    vertexColors: o.vertexColors ?? false,
  });
  const boil = o.boil ?? true;
  const fur = o.fur ?? 0;
  const spiral = o.spiral ?? 0;
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uBoil = SHARED.uBoil;
    shader.uniforms.uBoilAmp = boil ? SHARED.uBoilAmp : {value: 0};
    if (fur > 0) {
      // radial strands seen from above: streaks along the meridians of the clump
      shader.uniforms.uFur = {value: fur};
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vObjN;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvObjN = normalize(position);');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vObjN;\nuniform float uFur;\n' + GLSL_NOISE)
        .replace(
          '#include <color_fragment>',
          /* glsl */ `#include <color_fragment>
          {
            vec3 on = normalize(vObjN);
            float a = atan(on.y, on.x);
            float el = acos(clamp(on.z, -1.0, 1.0));
            float strands = vnoise(vec2(a * 22.0 + el * 9.0, el * 3.5)) * 0.6 + vnoise(vec2(a * 47.0 - el * 13.0, el * 7.0 + 3.0)) * 0.4;
            float tuft = smoothstep(0.35, 0.75, strands);
            float tip = smoothstep(0.3, 1.3, el);
            diffuseColor.rgb *= mix(1.0, mix(0.7, 1.2, tuft) * mix(1.08, 0.86, tip), uFur);
          }`,
        );
    }
    if (spiral > 0) {
      // rolled hay bale: spiral stripes on the up-facing end
      shader.uniforms.uSpiral = {value: spiral};
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vObjP;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvObjP = position;');
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vObjP;\nuniform float uSpiral;')
        .replace(
          '#include <color_fragment>',
          /* glsl */ `#include <color_fragment>
          {
            float r = length(vObjP.xy);
            float a = atan(vObjP.y, vObjP.x);
            float sp = fract(r * uSpiral - a / 6.2831853);
            float line = 1.0 - smoothstep(0.0, 0.06, abs(sp - 0.5) - 0.3);
            float top = step(0.45, vObjP.z);
            diffuseColor.rgb *= mix(1.0, mix(1.0, 0.7, line), top);
          }`,
        );
    }
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\n' + GLSL_NOISE + BOIL_GLSL)
      .replace(
        '#include <project_vertex>',
        /* glsl */ `
        vec4 wpos0 = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          wpos0 = instanceMatrix * wpos0;
        #endif
        wpos0 = modelMatrix * wpos0;
        wpos0.xy += boilOffset(wpos0.xyz);
        vec4 mvPosition = viewMatrix * wpos0;
        gl_Position = projectionMatrix * mvPosition;`,
      );
  };
  m.customProgramCacheKey = () => (boil ? 'toon-boil' : 'toon-still') + (fur > 0 ? '-fur' : '') + (spiral > 0 ? '-spiral' : '');
  return m;
};

// Darker tint of a fill color for ink (not black): lower lightness, push hue slightly toward violet.
export const inkColor = (fill: string | Color, k = 0.38): Color => {
  const c = fill instanceof Color ? fill.clone() : new Color(fill);
  const hsl = {h: 0, s: 0, l: 0};
  c.getHSL(hsl);
  const h = hsl.h + (0.72 - hsl.h) * 0.12;
  return new Color().setHSL(h, Math.min(1, hsl.s * 1.1 + 0.05), hsl.l * k);
};

// Inverted-hull ink line. Width varies along the line and per drawing; it boils with the fill.
export const inkMaterial = (ink: Color | string, width = 2.2, widthVar = 0.45, opacity = 1) => {
  return new ShaderMaterial({
    uniforms: {
      uBoil: SHARED.uBoil,
      uBoilAmp: SHARED.uBoilAmp,
      uWidth: {value: width},
      uWidthVar: {value: widthVar},
      uInk: {value: ink instanceof Color ? ink : new Color(ink)},
      uInkMul: {value: new Color(0.34, 0.31, 0.4)},
      uOpacity: {value: opacity},
    },
    vertexShader:
      GLSL_NOISE +
      BOIL_GLSL +
      /* glsl */ `
      uniform float uWidth;
      uniform float uWidthVar;
      uniform vec3 uInk;
      uniform vec3 uInkMul;
      varying vec3 vInk;
      void main(){
        vec4 wp = vec4(position, 1.0);
        vec3 n = normal;
        #ifdef USE_INSTANCING
          wp = instanceMatrix * wp;
          n = mat3(instanceMatrix) * n;
        #endif
        wp = modelMatrix * wp;
        n = normalize(mat3(modelMatrix) * n);
        vec2 b = boilOffset(wp.xyz);
        float s = uBoil * 1.618;
        float v = vnoise(wp.xy * 0.03 + vec2(s * 5.3, s * 2.9));
        float w = uWidth * mix(1.0 - uWidthVar, 1.0 + uWidthVar, v);
        wp.xyz += n * w;
        wp.xy += b;
        #ifdef USE_INSTANCING_COLOR
          vInk = instanceColor * uInkMul;
        #else
          vInk = uInk;
        #endif
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader: /* glsl */ `
      uniform float uOpacity;
      varying vec3 vInk;
      void main(){ gl_FragColor = vec4(vInk, uOpacity); }`,
    side: BackSide,
    transparent: opacity < 1,
  });
};

// Hull geometry: welded vertices with smooth normals so the extruded shell has no cracks.
export const hullGeometry = (g: BufferGeometry) => {
  const c = g.clone();
  for (const k of Object.keys(c.attributes)) {
    if (k !== 'position') c.deleteAttribute(k);
  }
  const m = mergeVertices(c, 1e-2);
  m.computeVertexNormals();
  return m;
};

// Planar projected cel shadow: the caster is flattened onto z = uShadowZ along the light,
// drawn with multiply blending, and the stencil stops overlapping shadows from darkening twice.
export const shadowMaterial = (strength = 1, mode: 'multiply' | 'tint' = 'multiply') =>
  new ShaderMaterial({
    uniforms: {
      uBoil: SHARED.uBoil,
      uBoilAmp: SHARED.uBoilAmp,
      uLightDir: SHARED.uLightDir,
      uShadowColor: SHARED.uShadowColor,
      uShadowZ: SHARED.uShadowZ,
      uShadowAlpha: SHARED.uShadowAlpha,
      uShadowDepth: SHARED.uShadowDepth,
      uStrength: {value: strength},
    },
    vertexShader:
      GLSL_NOISE +
      BOIL_GLSL +
      /* glsl */ `
      uniform vec3 uLightDir;
      uniform float uShadowZ;
      uniform float uShadowDepth;
      void main(){
        vec4 wp = vec4(position, 1.0);
        #ifdef USE_INSTANCING
          wp = instanceMatrix * wp;
        #endif
        wp = modelMatrix * wp;
        wp.xy += boilOffset(wp.xyz);
        float t = (wp.z - (uShadowZ - uShadowDepth)) / max(-uLightDir.z, 0.05);
        wp.xy += uLightDir.xy * t;
        wp.z = uShadowZ;
        gl_Position = projectionMatrix * viewMatrix * wp;
      }`,
    fragmentShader:
      mode === 'multiply'
        ? /* glsl */ `
      uniform vec3 uShadowColor;
      uniform float uStrength;
      void main(){ gl_FragColor = vec4(mix(vec3(1.0), uShadowColor, uStrength), 1.0); }`
        : /* glsl */ `
      uniform vec3 uShadowColor;
      uniform float uStrength;
      uniform float uShadowAlpha;
      void main(){ gl_FragColor = vec4(uShadowColor, uShadowAlpha * uStrength); }`,
    transparent: true,
    depthWrite: false,
    ...(mode === 'multiply'
      ? {blending: CustomBlending, blendSrc: DstColorFactor, blendDst: ZeroFactor, blendSrcAlpha: ZeroFactor, blendDstAlpha: OneFactor}
      : {}),
    stencilWrite: true,
    stencilRef: 1,
    stencilFunc: NotEqualStencilFunc,
    stencilZPass: ReplaceStencilOp,
  });
