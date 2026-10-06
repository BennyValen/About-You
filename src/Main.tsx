import React, {useEffect, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import {HEIGHT, WIDTH, sceneAt} from './timeline';
import {SCENES} from './scenes';
import {Post} from './kit/post';
import {SHARED, resetShared} from './kit/toon';
import {SCENE_U} from './kit/layers';
import {onTwos} from './kit/frame';

// After a scene mounts, the effect composer is built asynchronously. Hold the
// frame until two animation frames have passed and the frame has been drawn again.
const WarmupGate: React.FC = () => {
  const advance = useThree((s) => s.advance);
  const [handle] = useState(() => delayRender('Warming up scene'));
  useEffect(() => {
    let done = false;
    let r2 = 0;
    const r1 = requestAnimationFrame(() => {
      r2 = requestAnimationFrame(() => {
        advance(performance.now());
        done = true;
        continueRender(handle);
      });
    });
    return () => {
      cancelAnimationFrame(r1);
      cancelAnimationFrame(r2);
      if (!done) continueRender(handle);
    };
  }, [advance, handle]);
  return null;
};

export const Main: React.FC = () => {
  const frame = useCurrentFrame();
  const span = sceneAt(frame);
  const S = SCENES[span.index];
  const f = frame - span.start;
  const d = onTwos(frame) - span.start;
  // per-frame shared uniforms
  resetShared();
  SHARED.uBoil.value = Math.floor(frame / 2);
  SCENE_U.uTime.value = f / 24;
  SCENE_U.uDraw.value = d / 24;
  SCENE_U.uFrame.value = f;
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <ThreeCanvas
        width={WIDTH}
        height={HEIGHT}
        dpr={1}
        flat
        gl={{antialias: false, preserveDrawingBuffer: true, stencil: true, powerPreference: 'high-performance'}}
      >
        <S.Component key={span.index} f={f} d={d} len={span.length} />
        <Post g={S.grade(f)} frame={frame} />
        <WarmupGate key={'warm' + span.index} />
      </ThreeCanvas>
    </AbsoluteFill>
  );
};
