import type * as THREE from "three";

// A move that starts crouched (pixiv's Greeting: hips at a third of their
// height for 1.5 s) looks broken when Venus first appears. Such moves start
// where she's standing instead. Moves that start standing are left alone.
const CROUCHED = 0.8; // Hips below this share of their highest point = crouched.
const STANDING = 0.9; // Start once they're back above this share.

// Seconds into the move where she first stands, from the hips height at each keyframe.
export function standingStart(times: ArrayLike<number>, heights: ArrayLike<number>): number {
  if (times.length === 0 || heights.length !== times.length) return 0;
  let highest = -Infinity;
  for (let i = 0; i < heights.length; i++) highest = Math.max(highest, heights[i]);
  if (!(highest > 0) || heights[0] >= CROUCHED * highest) return 0;
  for (let i = 0; i < heights.length; i++) {
    if (heights[i] >= STANDING * highest) return times[i];
  }
  return 0;
}

// The same for a clip made by createVRMAnimationClip: its hips track is "<hips node>.position".
export function clipStandingStart(clip: THREE.AnimationClip, hipsName: string): number {
  const track = clip.tracks.find((each) => each.name === `${hipsName}.position`);
  if (!track) return 0;
  // Positions are x, y, z per keyframe; y is the height.
  const heights = Array.from({ length: track.times.length }, (_, i) => track.values[i * 3 + 1]);
  return standingStart(track.times, heights);
}
