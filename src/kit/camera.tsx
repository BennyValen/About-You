import React from 'react';
import {useThree} from '@react-three/fiber';
import {PerspectiveCamera} from 'three';
import {HEIGHT, WIDTH} from '../timeline';

// Top-down camera. World: X right, Y = "up the frame" (north), Z toward the camera; ground at z = 0.
// One world unit is one output pixel on the ground plane at the base height.
export const BASE_FOV = 30;
export const baseHeight = (fov = BASE_FOV) => HEIGHT / 2 / Math.tan((fov * Math.PI) / 360);

export type CamPose = {x: number; y: number; h: number; fov: number; roll?: number};

export const pose = (x: number, y: number, zoom = 1, fov = BASE_FOV, roll = 0): CamPose => ({
  x,
  y,
  h: baseHeight(fov) / zoom,
  fov,
  roll,
});

// screen pixels per world unit at height z
export const pxPerUnit = (p: CamPose, z = 0) => HEIGHT / (2 * (p.h - z) * Math.tan((p.fov * Math.PI) / 360));

export const screenToWorld = (p: CamPose, sx: number, sy: number, z = 0) => {
  const k = pxPerUnit(p, z);
  const dx = (sx - WIDTH / 2) / k;
  const dy = -(sy - HEIGHT / 2) / k;
  const r = p.roll ?? 0;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return {x: p.x + c * dx - s * dy, y: p.y + s * dx + c * dy};
};

export const worldToScreen = (p: CamPose, x: number, y: number, z = 0) => {
  const k = pxPerUnit(p, z);
  const r = -(p.roll ?? 0);
  const dx = x - p.x;
  const dy = y - p.y;
  const c = Math.cos(r);
  const s = Math.sin(r);
  return {sx: WIDTH / 2 + (c * dx - s * dy) * k, sy: HEIGHT / 2 - (s * dx + c * dy) * k};
};

// half extents of the visible ground rectangle at height z (with margin)
export const viewExtent = (p: CamPose, z = 0, margin = 1.15) => {
  const k = pxPerUnit(p, z);
  return {hw: ((WIDTH / 2) * margin) / k, hh: ((HEIGHT / 2) * margin) / k};
};

export const CameraRig: React.FC<{pose: CamPose}> = ({pose: p}) => {
  const camera = useThree((s) => s.camera) as PerspectiveCamera;
  // Applied during render so the pose is in place before ThreeCanvas advances the frame.
  camera.fov = p.fov;
  camera.aspect = WIDTH / HEIGHT;
  camera.near = Math.max(1, p.h * 0.02);
  camera.far = p.h * 1.5 + 2000;
  const r = p.roll ?? 0;
  camera.up.set(-Math.sin(r), Math.cos(r), 0);
  camera.position.set(p.x, p.y, p.h);
  camera.lookAt(p.x, p.y, 0);
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
  return null;
};
