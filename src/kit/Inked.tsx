import React, {useEffect, useMemo} from 'react';
import {BufferGeometry, Color, InstancedMesh, Material, Matrix4, Euler, Quaternion, Vector3} from 'three';
import {hullGeometry, inkColor, inkMaterial, shadowMaterial, toonMaterial, ToonOpts} from './toon';

type V3 = [number, number, number];

export type InkedProps = {
  geometry: BufferGeometry;
  color: string;
  ink?: string;
  inkWidth?: number;
  inkVar?: number;
  noInk?: boolean;
  toon?: ToonOpts;
  material?: Material;
  shadow?: boolean;
  shadowStrength?: number;
  shadowMode?: 'multiply' | 'tint';
  position?: V3;
  rotation?: V3;
  scale?: V3 | number;
  renderOrder?: number;
  visible?: boolean;
};

// A cel object: toon fill + inverted-hull ink + optional planar cel shadow.
export const Inked: React.FC<InkedProps> = ({
  geometry,
  color,
  ink,
  inkWidth = 2.2,
  inkVar = 0.45,
  noInk,
  toon,
  material,
  shadow,
  shadowStrength = 1,
  shadowMode = 'multiply',
  position,
  rotation,
  scale,
  renderOrder,
  visible = true,
}) => {
  const toonKey = JSON.stringify({...(toon ?? {}), gradient: toon?.gradient?.uuid});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const fill = useMemo(() => material ?? toonMaterial(color, toon), [material, color, toonKey]);
  const hull = useMemo(() => (noInk ? null : hullGeometry(geometry)), [geometry, noInk]);
  const inkMat = useMemo(
    () => (noInk ? null : inkMaterial(ink ? new Color(ink) : inkColor(color), inkWidth, inkVar)),
    [noInk, ink, color, inkWidth, inkVar],
  );
  const sh = useMemo(() => (shadow ? shadowMaterial(shadowStrength, shadowMode) : null), [shadow, shadowStrength, shadowMode]);
  useEffect(
    () => () => {
      hull?.dispose();
      inkMat?.dispose();
      sh?.dispose();
      if (!material) fill.dispose();
    },
    [hull, inkMat, sh, fill, material],
  );
  const sc: V3 | undefined = typeof scale === 'number' ? [scale, scale, scale] : scale;
  return (
    <group position={position} rotation={rotation} scale={sc} visible={visible}>
      <mesh geometry={geometry} material={fill} renderOrder={renderOrder ?? 0} />
      {hull && inkMat ? <mesh geometry={hull} material={inkMat} renderOrder={renderOrder ?? 0} /> : null}
      {sh ? <mesh geometry={geometry} material={sh} renderOrder={2} /> : null}
    </group>
  );
};

export type Instance = {
  x: number;
  y: number;
  z?: number;
  rx?: number;
  ry?: number;
  rz?: number;
  s?: number;
  sx?: number;
  sy?: number;
  sz?: number;
  color: string | Color;
};

const tmpM = new Matrix4();
const tmpQ = new Quaternion();
const tmpE = new Euler();
const tmpP = new Vector3();
const tmpS = new Vector3();

const fillMatrices = (mesh: InstancedMesh, items: Instance[], withColor: boolean) => {
  items.forEach((it, i) => {
    tmpE.set(it.rx ?? 0, it.ry ?? 0, it.rz ?? 0);
    tmpQ.setFromEuler(tmpE);
    const s = it.s ?? 1;
    tmpS.set((it.sx ?? 1) * s, (it.sy ?? 1) * s, (it.sz ?? 1) * s);
    tmpP.set(it.x, it.y, it.z ?? 0);
    tmpM.compose(tmpP, tmpQ, tmpS);
    mesh.setMatrixAt(i, tmpM);
    if (withColor) mesh.setColorAt(i, it.color instanceof Color ? it.color : new Color(it.color));
  });
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  mesh.computeBoundingSphere();
  mesh.frustumCulled = false;
};

// Many cel objects sharing one geometry (lily pads, sunflowers, bales...).
export const InkedInstances: React.FC<{
  geometry: BufferGeometry;
  items: Instance[];
  inkWidth?: number;
  inkVar?: number;
  inkMul?: [number, number, number];
  noInk?: boolean;
  toon?: ToonOpts;
  shadow?: boolean;
  shadowStrength?: number;
  shadowMode?: 'multiply' | 'tint';
  renderOrder?: number;
}> = ({geometry, items, inkWidth = 2.0, inkVar = 0.45, inkMul, noInk, toon, shadow, shadowStrength = 1, shadowMode = 'multiply', renderOrder = 0}) => {
  const toonKey = JSON.stringify({...(toon ?? {}), gradient: toon?.gradient?.uuid});
  const inkKey = JSON.stringify(inkMul ?? null);
  const meshes = useMemo(() => {
    const fill = new InstancedMesh(geometry, toonMaterial('#ffffff', toon), Math.max(1, items.length));
    fillMatrices(fill, items, true);
    fill.renderOrder = renderOrder;
    let hull: InstancedMesh | null = null;
    if (!noInk) {
      const im = inkMaterial('#000000', inkWidth, inkVar);
      if (inkMul) im.uniforms.uInkMul.value = new Color(inkMul[0], inkMul[1], inkMul[2]);
      hull = new InstancedMesh(hullGeometry(geometry), im, Math.max(1, items.length));
      fillMatrices(hull, items, true);
      hull.renderOrder = renderOrder;
    }
    let sh: InstancedMesh | null = null;
    if (shadow) {
      sh = new InstancedMesh(geometry, shadowMaterial(shadowStrength, shadowMode), Math.max(1, items.length));
      fillMatrices(sh, items, false);
      sh.renderOrder = 2;
    }
    fill.count = hull ? (hull.count = items.length) : items.length;
    if (sh) sh.count = items.length;
    return {fill, hull, sh};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geometry, items, inkWidth, inkVar, inkKey, noInk, toonKey, shadow, shadowStrength, shadowMode, renderOrder]);
  useEffect(
    () => () => {
      for (const m of [meshes.fill, meshes.hull, meshes.sh]) {
        if (!m) continue;
        (m.material as Material).dispose();
        m.dispose();
      }
      meshes.hull?.geometry.dispose();
    },
    [meshes],
  );
  return (
    <group>
      <primitive object={meshes.fill} />
      {meshes.hull ? <primitive object={meshes.hull} /> : null}
      {meshes.sh ? <primitive object={meshes.sh} /> : null}
    </group>
  );
};
