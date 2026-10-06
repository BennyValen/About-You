// Animation "on twos": drawings change every 2nd frame (12 drawings/s) while the
// camera moves on every frame. All cuts in this film land on even frames, so the
// local drawing frame keeps the same parity as the global one.
export const onTwos = (frame: number) => frame - (frame % 2);
export const secs = (frames: number) => frames / 24;
