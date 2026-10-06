// Scene cut table. Cut frames were measured from the source by frame differencing
// (scripts/cutdetect.py); every cut is a hard cut.
export const FPS = 24;
export const WIDTH = 1080;
export const HEIGHT = 1920;
export const TOTAL_FRAMES = 4005;

export const CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, TOTAL_FRAMES];

export type SceneSpan = {index: number; start: number; end: number; length: number};

export const SPANS: SceneSpan[] = CUTS.slice(0, -1).map((start, i) => ({
  index: i,
  start,
  end: CUTS[i + 1],
  length: CUTS[i + 1] - start,
}));

export const sceneAt = (frame: number): SceneSpan => {
  for (let i = SPANS.length - 1; i >= 0; i--) {
    if (frame >= SPANS[i].start) return SPANS[i];
  }
  return SPANS[0];
};
