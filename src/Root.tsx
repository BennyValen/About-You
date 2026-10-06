import {Composition} from 'remotion';
import {Main} from './Main';
import {FPS, TOTAL_FRAMES, WIDTH, HEIGHT} from './timeline';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Main"
      component={Main}
      durationInFrames={TOTAL_FRAMES}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
  );
};
