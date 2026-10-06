import React, {useMemo} from 'react';
import {Bloom, EffectComposer} from '@react-three/postprocessing';
import {BlendFunction, Effect, EffectAttribute} from 'postprocessing';
import {
  Camera,
  Color,
  HalfFloatType,
  LinearFilter,
  Mesh,
  OrthographicCamera,
  PlaneGeometry,
  Scene,
  ShaderMaterial,
  Texture,
  TextureDataType,
  Uniform,
  Vector2,
  Vector4,
  WebGLRenderer,
  WebGLRenderTarget,
} from 'three';

// ---------------------------------------------------------------------------
// Grade: one look for the whole film (cool teal shadows, warm highlights), tuned per scene.
export type Grade = {
  exposure: number;
  lift: [number, number, number]; // added in shadows (display space)
  gamma: [number, number, number];
  gain: [number, number, number];
  saturation: number;
  splitShadow: [number, number, number]; // teal tint in the shadows
  splitHigh: [number, number, number]; // warm tint in the highlights
  split: number;
  vignette: number;
  grain: number;
  ca: number; // chromatic aberration at the edges
  edgeBlur: number; // depth of field at the frame edges
  streak: number; // anamorphic streak strength
  streakThreshold: number;
  streakTint: [number, number, number];
  bloom: number;
  bloomThreshold: number;
  bloomRadius: number;
  shafts: number; // volumetric light shafts strength
  shaftAngle: number; // radians, direction the shafts travel across the frame
  shaftColor: [number, number, number];
  haze: number;
  hazeColor: [number, number, number];
  fade: number; // 0..1 to black
};

export const BASE_GRADE: Grade = {
  exposure: 1.0,
  lift: [0.0, 0.012, 0.022],
  gamma: [1.0, 1.0, 1.0],
  gain: [1.03, 1.0, 0.96],
  saturation: 1.04,
  splitShadow: [-0.02, 0.012, 0.03],
  splitHigh: [0.03, 0.012, -0.022],
  split: 1.0,
  vignette: 0.32,
  grain: 0.035,
  ca: 0.9,
  edgeBlur: 0.45,
  streak: 0.35,
  streakThreshold: 1.0,
  streakTint: [0.75, 0.85, 1.0],
  bloom: 0.9,
  bloomThreshold: 0.72,
  bloomRadius: 0.72,
  shafts: 0.0,
  shaftAngle: -0.9,
  shaftColor: [1.0, 0.93, 0.8],
  haze: 0.0,
  hazeColor: [0.8, 0.85, 1.0],
  fade: 0,
};

export const grade = (g: Partial<Grade>): Grade => ({...BASE_GRADE, ...g});

// ---------------------------------------------------------------------------
// Minimal full-screen pass helper used by the finish effect's internal passes.
const QUAD_VERT = /* glsl */ `
varying vec2 vUv;
void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`;

class Quad {
  scene = new Scene();
  cam = new OrthographicCamera(-1, 1, 1, -1, 0, 1);
  mesh: Mesh;
  constructor() {
    this.mesh = new Mesh(new PlaneGeometry(2, 2));
    this.mesh.frustumCulled = false;
    this.scene.add(this.mesh);
  }
  render(renderer: WebGLRenderer, mat: ShaderMaterial, target: WebGLRenderTarget | null) {
    this.mesh.material = mat;
    renderer.setRenderTarget(target);
    renderer.render(this.scene, this.cam);
  }
}

const brightMat = () =>
  new ShaderMaterial({
    uniforms: {tInput: {value: null}, uThreshold: {value: 1.0}},
    vertexShader: QUAD_VERT,
    fragmentShader: /* glsl */ `
      uniform sampler2D tInput; uniform float uThreshold;
      varying vec2 vUv;
      void main(){
        vec3 c = texture2D(tInput, vUv).rgb;
        float l = max(c.r, max(c.g, c.b));
        float k = max(l - uThreshold, 0.0);
        k = k*k / (k + 0.6);
        gl_FragColor = vec4(c / max(l, 1e-4) * k, 1.0);
      }`,
    depthTest: false,
    depthWrite: false,
  });

const blurMat = () =>
  new ShaderMaterial({
    uniforms: {tInput: {value: null}, uDir: {value: new Vector2(1, 0)}},
    vertexShader: QUAD_VERT,
    fragmentShader: /* glsl */ `
      uniform sampler2D tInput; uniform vec2 uDir;
      varying vec2 vUv;
      void main(){
        vec3 s = texture2D(tInput, vUv).rgb * 0.2270270270;
        s += texture2D(tInput, vUv + uDir*1.3846153846).rgb * 0.3162162162;
        s += texture2D(tInput, vUv - uDir*1.3846153846).rgb * 0.3162162162;
        s += texture2D(tInput, vUv + uDir*3.2307692308).rgb * 0.0702702703;
        s += texture2D(tInput, vUv - uDir*3.2307692308).rgb * 0.0702702703;
        gl_FragColor = vec4(s, 1.0);
      }`,
    depthTest: false,
    depthWrite: false,
  });

const FINISH_FRAG = /* glsl */ `
uniform sampler2D tBlur;
uniform sampler2D tStreak;
uniform float uFrame;
uniform float uTime;
uniform float uExposure;
uniform vec3 uLift;
uniform vec3 uGamma;
uniform vec3 uGain;
uniform float uSat;
uniform vec3 uSplitShadow;
uniform vec3 uSplitHigh;
uniform float uSplit;
uniform float uVignette;
uniform float uGrain;
uniform float uCA;
uniform float uEdgeBlur;
uniform float uStreak;
uniform vec3 uStreakTint;
uniform vec4 uShafts;
uniform vec3 uShaftColor;
uniform vec4 uHaze;
uniform float uFade;

float fHash(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*0.1031); p3 += dot(p3, p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
float fNoise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f*f*(3.0-2.0*f);
  return mix(mix(fHash(i), fHash(i+vec2(1.0,0.0)), u.x), mix(fHash(i+vec2(0.0,1.0)), fHash(i+vec2(1.0,1.0)), u.x), u.y); }
float fLuma(vec3 c){ return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor){
  vec2 c = uv - 0.5;
  vec2 ca = vec2(c.x, c.y / aspect);            // isotropic (pixel-square) coordinates, x in [-0.5,0.5]
  float r2 = dot(ca, ca);
  // chromatic aberration: radial, only noticeable toward the edges
  vec2 shift = c * uCA * 0.0042 * smoothstep(0.1, 1.0, r2 * 2.4);
  vec3 col;
  col.r = texture2D(inputBuffer, uv + shift).r;
  col.g = inputColor.g;
  col.b = texture2D(inputBuffer, uv - shift).b;
  // soft depth of field at the frame edges (top/bottom strongest, like a long lens tilt)
  float edge = smoothstep(0.33, 0.5, abs(c.y)) + 0.6 * smoothstep(0.38, 0.5, abs(c.x));
  edge = clamp(edge * uEdgeBlur, 0.0, 1.0);
  vec3 bl;
  bl.r = texture2D(tBlur, uv + shift * 1.4).r;
  bl.g = texture2D(tBlur, uv).g;
  bl.b = texture2D(tBlur, uv - shift * 1.4).b;
  col = mix(col, bl, edge);
  // anamorphic streaks on the brightest points
  col += texture2D(tStreak, uv).rgb * uStreakTint * uStreak;
  // volumetric light shafts: soft parallel beams crossing the frame, drifting slowly
  if (uShafts.x > 0.0) {
    vec2 d = vec2(cos(uShafts.y), sin(uShafts.y));
    vec2 q = vec2(dot(ca, d), dot(ca, vec2(-d.y, d.x)));
    float beams = fNoise(vec2(q.y * 4.0 * uShafts.z + uTime * 0.05, 0.5)) * 0.65 + fNoise(vec2(q.y * 11.0 * uShafts.z - uTime * 0.03, 3.5)) * 0.35;
    beams = smoothstep(0.35, 0.95, beams);
    float along = smoothstep(-0.9, 0.3, -q.x);    // fade along the light direction
    col += uShaftColor * beams * along * uShafts.x * (0.6 + 0.4 * fNoise(ca * 3.0 + uTime * 0.02));
  }
  // atmospheric haze (aerial perspective), stronger toward the edges
  col = mix(col, uHaze.rgb, uHaze.a * (0.55 + 0.45 * smoothstep(0.1, 0.6, r2 * 3.0)));
  // exposure + gentle filmic shoulder
  col *= uExposure;
  col = col / (1.0 + max(col - 0.75, 0.0) * 0.55);
  // display-referred grade
  vec3 g = pow(max(col, 0.0), vec3(1.0 / 2.2));
  float l = fLuma(g);
  g += uSplit * (uSplitShadow * (1.0 - smoothstep(0.0, 0.55, l)) + uSplitHigh * smoothstep(0.45, 1.0, l));
  g = g * uGain + uLift * (1.0 - g);
  g = pow(max(g, 0.0), 1.0 / uGamma);
  g = mix(vec3(fLuma(g)), g, uSat);
  // vignette
  float vig = 1.0 - smoothstep(0.32, 0.95, length(ca * vec2(1.0, 0.78)) * 1.25);
  g *= mix(1.0, vig, uVignette);
  // film grain: new grain every frame, a little stronger in the mids and shadows
  vec2 px = uv * resolution;
  float n = (fHash(px + vec2(uFrame * 37.1, uFrame * 11.7)) + fHash(px * 1.37 + vec2(uFrame * 5.3, 91.0)) - 1.0);
  g += n * uGrain * (0.45 + 0.55 * (1.0 - l));
  g *= (1.0 - uFade);
  outputColor = vec4(pow(max(g, 0.0), vec3(2.2)), 1.0);
}
`;

export class FinishEffect extends Effect {
  quad = new Quad();
  bright = brightMat();
  blur = blurMat();
  blurA = new WebGLRenderTarget(1, 1, {type: HalfFloatType, depthBuffer: false});
  blurB = new WebGLRenderTarget(1, 1, {type: HalfFloatType, depthBuffer: false});
  stA = new WebGLRenderTarget(1, 1, {type: HalfFloatType, depthBuffer: false});
  stB = new WebGLRenderTarget(1, 1, {type: HalfFloatType, depthBuffer: false});
  size = new Vector2(1, 1);

  constructor() {
    super('FinishEffect', FINISH_FRAG, {
      blendFunction: BlendFunction.SRC,
      attributes: EffectAttribute.CONVOLUTION,
      uniforms: new Map<string, Uniform>([
        ['tBlur', new Uniform(null)],
        ['tStreak', new Uniform(null)],
        ['uFrame', new Uniform(0)],
        ['uTime', new Uniform(0)],
        ['uExposure', new Uniform(1)],
        ['uLift', new Uniform(new Color())],
        ['uGamma', new Uniform(new Color(1, 1, 1))],
        ['uGain', new Uniform(new Color(1, 1, 1))],
        ['uSat', new Uniform(1)],
        ['uSplitShadow', new Uniform(new Color())],
        ['uSplitHigh', new Uniform(new Color())],
        ['uSplit', new Uniform(1)],
        ['uVignette', new Uniform(0.3)],
        ['uGrain', new Uniform(0.03)],
        ['uCA', new Uniform(1)],
        ['uEdgeBlur', new Uniform(1)],
        ['uStreak', new Uniform(0.3)],
        ['uStreakTint', new Uniform(new Color(1, 1, 1))],
        ['uShafts', new Uniform(new Vector4(0, 0, 1, 0))],
        ['uShaftColor', new Uniform(new Color(1, 1, 1))],
        ['uHaze', new Uniform(new Vector4(0, 0, 0, 0))],
        ['uFade', new Uniform(0)],
      ]),
    });
    for (const t of [this.blurA, this.blurB, this.stA, this.stB]) {
      t.texture.minFilter = LinearFilter;
      t.texture.magFilter = LinearFilter;
    }
  }

  initialize(renderer: WebGLRenderer, alpha: boolean, frameBufferType: TextureDataType) {
    for (const t of [this.blurA, this.blurB, this.stA, this.stB]) t.texture.type = frameBufferType;
  }

  setSize(width: number, height: number) {
    this.size.set(width, height);
    this.blurA.setSize(Math.ceil(width / 2), Math.ceil(height / 2));
    this.blurB.setSize(Math.ceil(width / 2), Math.ceil(height / 2));
    this.stA.setSize(Math.ceil(width / 4), Math.ceil(height / 4));
    this.stB.setSize(Math.ceil(width / 4), Math.ceil(height / 4));
  }

  update(renderer: WebGLRenderer, inputBuffer: WebGLRenderTarget) {
    const src: Texture = inputBuffer.texture;
    // edge depth of field: half-res separable gaussian, two rounds
    const bw = this.blurA.width;
    const bh = this.blurA.height;
    let tex: Texture = src;
    for (let i = 0; i < 2; i++) {
      const s = 1 + i * 1.5;
      this.blur.uniforms.tInput.value = tex;
      this.blur.uniforms.uDir.value.set(s / bw, 0);
      this.quad.render(renderer, this.blur, this.blurB);
      this.blur.uniforms.tInput.value = this.blurB.texture;
      this.blur.uniforms.uDir.value.set(0, s / bh);
      this.quad.render(renderer, this.blur, this.blurA);
      tex = this.blurA.texture;
    }
    // anamorphic streaks: bright pass, then very wide horizontal blur
    const sw = this.stA.width;
    this.bright.uniforms.tInput.value = src;
    this.quad.render(renderer, this.bright, this.stA);
    let a = this.stA;
    let b = this.stB;
    for (const o of [1, 2, 4, 8, 16, 24]) {
      this.blur.uniforms.tInput.value = a.texture;
      this.blur.uniforms.uDir.value.set(o / sw, 0);
      this.quad.render(renderer, this.blur, b);
      const t = a;
      a = b;
      b = t;
    }
    this.uniforms.get('tBlur')!.value = this.blurA.texture;
    this.uniforms.get('tStreak')!.value = a.texture;
  }

  applyGrade(g: Grade, frame: number) {
    const u = this.uniforms;
    u.get('uFrame')!.value = frame;
    u.get('uTime')!.value = frame / 24;
    u.get('uExposure')!.value = g.exposure;
    (u.get('uLift')!.value as Color).setRGB(...g.lift);
    (u.get('uGamma')!.value as Color).setRGB(...g.gamma);
    (u.get('uGain')!.value as Color).setRGB(...g.gain);
    u.get('uSat')!.value = g.saturation;
    (u.get('uSplitShadow')!.value as Color).setRGB(...g.splitShadow);
    (u.get('uSplitHigh')!.value as Color).setRGB(...g.splitHigh);
    u.get('uSplit')!.value = g.split;
    u.get('uVignette')!.value = g.vignette;
    u.get('uGrain')!.value = g.grain;
    u.get('uCA')!.value = g.ca;
    u.get('uEdgeBlur')!.value = g.edgeBlur;
    u.get('uStreak')!.value = g.streak;
    (u.get('uStreakTint')!.value as Color).setRGB(...g.streakTint);
    (u.get('uShafts')!.value as Vector4).set(g.shafts, g.shaftAngle, 1, 0);
    (u.get('uShaftColor')!.value as Color).setRGB(...g.shaftColor);
    (u.get('uHaze')!.value as Vector4).set(g.hazeColor[0], g.hazeColor[1], g.hazeColor[2], g.haze);
    u.get('uFade')!.value = g.fade;
    this.bright.uniforms.uThreshold.value = g.streakThreshold;
  }

  dispose() {
    for (const t of [this.blurA, this.blurB, this.stA, this.stB]) t.dispose();
    this.bright.dispose();
    this.blur.dispose();
    super.dispose();
  }
}

export const Post: React.FC<{g: Grade; frame: number}> = ({g, frame}) => {
  const finish = useMemo(() => new FinishEffect(), []);
  finish.applyGrade(g, frame);
  return (
    <EffectComposer multisampling={4} stencilBuffer frameBufferType={HalfFloatType} mergeMode="none">
      <Bloom
        mipmapBlur
        intensity={g.bloom}
        luminanceThreshold={g.bloomThreshold}
        luminanceSmoothing={0.25}
        radius={g.bloomRadius}
        levels={7}
      />
      <primitive object={finish} />
    </EffectComposer>
  );
};

export type {Camera};
