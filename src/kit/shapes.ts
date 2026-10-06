import {BufferAttribute, IcosahedronGeometry, Vector3} from 'three';
import {mulberry32, rrange} from './random';

// Sea-urchin-like spiky ball: one fluffy canopy clump (trees, bushes).
export const spikyBall = (seed: number, spikes = 150, sharp = 18, amp = 0.5) => {
  const g = new IcosahedronGeometry(1, 4);
  const rng = mulberry32(seed);
  const dirs: Vector3[] = [];
  for (let i = 0; i < spikes; i++) dirs.push(new Vector3(rrange(rng, -1, 1), rrange(rng, -1, 1), rrange(rng, -1, 1)).normalize());
  const pos = g.getAttribute('position') as BufferAttribute;
  const v = new Vector3();
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i).normalize();
    let m = 0;
    for (const d of dirs) m = Math.max(m, Math.pow(Math.max(0, v.dot(d)), sharp));
    const s = 0.74 + amp * m;
    pos.setXYZ(i, v.x * s, v.y * s, v.z * s * 0.8);
  }
  g.computeVertexNormals();
  return g;
};
