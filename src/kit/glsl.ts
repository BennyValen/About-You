import {Color} from 'three';

// Hex sRGB color -> GLSL vec3 literal in linear working space (three.js renders in linear sRGB).
export const glc = (hex: string): string => {
  const c = new Color(hex); // converts sRGB hex -> linear
  return `vec3(${c.r.toFixed(5)},${c.g.toFixed(5)},${c.b.toFixed(5)})`;
};

export const lin = (hex: string): Color => new Color(hex);

// Shared GLSL helpers: hashing, noise, voronoi, brush strokes, ink, cel steps.
// Everything is deterministic: no time-based randomness, only explicit seeds.
export const GLSL_NOISE = /* glsl */ `
#ifndef PI
#define PI 3.141592653589793
#endif
float hash11(float p){ p = fract(p*0.1031); p *= p+33.33; p *= p+p; return fract(p); }
float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*0.1031); p3 += dot(p3, p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
vec2 hash22(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*vec3(.1031,.1030,.0973)); p3 += dot(p3, p3.yzx+33.33); return fract((p3.xx+p3.yz)*p3.zy); }
vec3 hash32(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*vec3(.1031,.1030,.0973)); p3 += dot(p3, p3.yxz+33.33); return fract((p3.xxy+p3.yzz)*p3.zyx); }

float vnoise(vec2 p){
  vec2 i = floor(p), f = fract(p); vec2 u = f*f*(3.0-2.0*f);
  return mix(mix(hash12(i), hash12(i+vec2(1.0,0.0)), u.x), mix(hash12(i+vec2(0.0,1.0)), hash12(i+vec2(1.0,1.0)), u.x), u.y);
}
// gradient noise in roughly [-1,1]
float gnoise(vec2 p){
  vec2 i = floor(p), f = fract(p);
  vec2 u = f*f*f*(f*(f*6.0-15.0)+10.0);
  vec2 ga = hash22(i)*2.0-1.0, gb = hash22(i+vec2(1.0,0.0))*2.0-1.0;
  vec2 gc = hash22(i+vec2(0.0,1.0))*2.0-1.0, gd = hash22(i+vec2(1.0,1.0))*2.0-1.0;
  float va = dot(ga, f), vb = dot(gb, f-vec2(1.0,0.0)), vc = dot(gc, f-vec2(0.0,1.0)), vd = dot(gd, f-vec2(1.0,1.0));
  return 1.6*(va + u.x*(vb-va) + u.y*(vc-va) + u.x*u.y*(va-vb-vc+vd));
}
const mat2 ROT_FBM = mat2(0.8, -0.6, 0.6, 0.8);
float fbm(vec2 p){ float a = 0.5, s = 0.0; for(int i=0;i<5;i++){ s += a*gnoise(p); p = ROT_FBM*p*2.03 + 17.1; a *= 0.5; } return s; }
float fbm3(vec2 p){ float a = 0.5, s = 0.0; for(int i=0;i<3;i++){ s += a*gnoise(p); p = ROT_FBM*p*2.03 + 17.1; a *= 0.5; } return s; }
float ridged(vec2 p){ float a = 0.5, s = 0.0; for(int i=0;i<4;i++){ s += a*(1.0-abs(gnoise(p))); p = ROT_FBM*p*2.03 + 5.3; a *= 0.5; } return s; }

vec2 rot2(vec2 p, float a){ float c = cos(a), s = sin(a); return vec2(c*p.x - s*p.y, s*p.x + c*p.y); }

// Voronoi. Returns (F1, F2, distance to cell border). id/center of the nearest cell via out params.
vec3 voronoi(vec2 x, float jitter, out vec2 cellId, out vec2 center){
  vec2 n = floor(x), f = fract(x);
  vec2 mg = vec2(0.0), mr = vec2(0.0);
  float md = 8.0, md2 = 8.0;
  for(int j=-1;j<=1;j++) for(int i=-1;i<=1;i++){
    vec2 g = vec2(float(i), float(j));
    vec2 o = 0.5 + jitter*(hash22(n+g) - 0.5);
    vec2 r = g + o - f;
    float d = dot(r, r);
    if(d < md){ md2 = md; md = d; mr = r; mg = g; } else if(d < md2){ md2 = d; }
  }
  float bd = 8.0;
  for(int j=-2;j<=2;j++) for(int i=-2;i<=2;i++){
    vec2 g = mg + vec2(float(i), float(j));
    vec2 o = 0.5 + jitter*(hash22(n+g) - 0.5);
    vec2 r = g + o - f;
    if(dot(mr-r, mr-r) > 0.00001) bd = min(bd, dot(0.5*(mr+r), normalize(r-mr)));
  }
  cellId = n + mg;
  center = n + mg + 0.5 + jitter*(hash22(n+mg) - 0.5);
  return vec3(sqrt(md), sqrt(md2), bd);
}

`;

// Fragment-only helpers (use screen derivatives).
export const GLSL_CEL = /* glsl */ `
// --- cel helpers ---------------------------------------------------------
// antialiased hard step (cel edge), width from screen derivatives
float hstep(float edge, float x){ float w = max(fwidth(x), 1e-5); return smoothstep(edge - w, edge + w, x); }
// coverage of an ink band around the zero set of signed distance d (world units ~ px), half width w
float inkBand(float d, float w){ float aa = max(fwidth(d), 1e-4); return 1.0 - smoothstep(w - aa, w + aa, abs(d)); }
// fill coverage, d < 0 inside
float fillCov(float d){ float aa = max(fwidth(d), 1e-4); return 1.0 - smoothstep(-aa, aa, d); }
// three tone cel: lit in [0,1] -> shadow / base / highlight
vec3 cel3(vec3 shadowC, vec3 baseC, vec3 hiC, float lit, float t1, float t2){
  return mix(mix(shadowC, baseC, hstep(t1, lit)), hiC, hstep(t2, lit));
}
vec3 shadeOf(vec3 c){ return c*vec3(0.56, 0.58, 0.72); }
vec3 hiOf(vec3 c){ return min(c*1.22 + vec3(0.035, 0.03, 0.015), vec3(4.0)); }
vec3 inkOf(vec3 c){ return c*vec3(0.30, 0.28, 0.36); }
float luma(vec3 c){ return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

// --- painted background texture ------------------------------------------
// anisotropic noise, aligned to angle a, stretched by sc (along, across)
float strokeField(vec2 p, float a, vec2 sc){
  vec2 q = rot2(p, -a) / sc;
  return gnoise(q)*0.65 + gnoise(q*2.13 + 7.7)*0.35;
}
// brush-stroke modulation: returns value around 1.0 (multiplier for a flat fill)
float brushMod(vec2 p, float a, float scale, float amt){
  float s1 = strokeField(p, a, vec2(70.0, 9.0)*scale);
  float s2 = strokeField(p + 311.0, a + 0.45, vec2(120.0, 16.0)*scale);
  float b1 = smoothstep(0.05, 0.25, s1) - smoothstep(-0.25, -0.05, s1)*0.8;
  float b2 = smoothstep(0.15, 0.35, s2);
  float bristle = gnoise(rot2(p, -a) / (vec2(26.0, 1.3)*scale)) * 0.5;
  return 1.0 + amt*(0.55*b1 + 0.35*b2 + 0.25*bristle - 0.2);
}
`;

export const GLSL_LIB = GLSL_NOISE + GLSL_CEL;

// Common vertex shader for world-anchored painted planes.
export const WORLD_VERT = /* glsl */ `
varying vec3 vWorld;
varying vec2 vUv;
void main(){
  vec4 wp = modelMatrix * vec4(position, 1.0);
  vWorld = wp.xyz;
  vUv = uv;
  gl_Position = projectionMatrix * viewMatrix * wp;
}
`;
