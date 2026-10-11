import type { VRMHumanBoneName } from "@pixiv/three-vrm";

import type { Mood } from "./scene-mood";

// A pose: for each bone, how far to turn it (radians around x, y, z) from the
// T-pose the model is saved in. Bones left out stay as the relaxed pose has them.
// Facing you: +x is her left, +y up, +z toward you. So for most bones
// x+ bends forward, y+ turns to her left, z+ tilts toward her right.
export type Turn = [number, number, number];
export type Pose = Partial<Record<VRMHumanBoneName, Turn>>;

// Standing easy: arms down by her sides, elbows a little soft.
export const RELAXED: Pose = {
  leftShoulder: [0, 0, -0.05],
  rightShoulder: [0, 0, 0.05],
  leftUpperArm: [0, -0.1, -1.3],
  rightUpperArm: [0, 0.1, 1.3],
  leftLowerArm: [0, -0.3, 0],
  rightLowerArm: [0, 0.3, 0],
  leftHand: [0, 0, -0.1],
  rightHand: [0, 0, 0.1],
};

// Leaning in, head a little to one side: she's paying attention.
const LISTENING: Pose = {
  spine: [0.05, 0, 0],
  chest: [0.04, 0, 0],
  neck: [0.04, 0, 0],
  head: [0.05, 0, 0.1],
};

// Right hand up to her chin, left arm across under it.
const THINKING: Pose = {
  head: [0.08, 0.05, -0.08],
  rightUpperArm: [-0.7, 0.35, 1.2],
  rightLowerArm: [0, 2.5, 0],
  rightHand: [0, 0, 0.3],
  leftUpperArm: [-0.25, -0.2, -1.2],
  leftLowerArm: [0, -1.5, 0],
};

const MOOD_POSES: Record<Mood, Pose> = {
  idle: {},
  listening: LISTENING,
  thinking: THINKING,
  talking: {},
};

// The relaxed pose with the mood's changes on top.
export function moodPose(mood: Mood): Pose {
  return { ...RELAXED, ...MOOD_POSES[mood] };
}

// A short move played on top of the pose, like a fidget. pose(t) gets the
// seconds since it started and says where the bones should be then.
export type Gesture = { length: number; pose: (t: number) => Pose };

// Small hand moves while she talks, picked at random.
export const TALKING_GESTURES: Gesture[] = [
  // Right hand comes up and out a little, palm open.
  {
    length: 1.6,
    pose: () => ({
      rightUpperArm: [-0.25, 0.1, 1.15],
      rightLowerArm: [0, 1.0, 0],
      rightHand: [0, 0, -0.3],
    }),
  },
  // Same with the left.
  {
    length: 1.6,
    pose: () => ({
      leftUpperArm: [-0.25, -0.1, -1.15],
      leftLowerArm: [0, -1.0, 0],
      leftHand: [0, 0, 0.3],
    }),
  },
  // Both hands open in front of her.
  {
    length: 1.8,
    pose: () => ({
      leftUpperArm: [-0.2, -0.1, -1.15],
      rightUpperArm: [-0.2, 0.1, 1.15],
      leftLowerArm: [0, -0.8, 0],
      rightLowerArm: [0, 0.8, 0],
    }),
  },
];

// Things she does now and then when nothing is happening.
export const FIDGETS: Gesture[] = [
  // Shoulders up and down, like a small stretch.
  {
    length: 1.4,
    pose: (t) => {
      const up = Math.sin((t / 1.4) * Math.PI) * 0.15;
      return {
        leftShoulder: [0, 0, -0.05 + up],
        rightShoulder: [0, 0, 0.05 - up],
      };
    },
  },
  // Hands together in front of her.
  {
    length: 3,
    pose: () => ({
      leftUpperArm: [-0.3, -0.3, -1.25],
      rightUpperArm: [-0.3, 0.3, 1.25],
      leftLowerArm: [0, -1.2, 0],
      rightLowerArm: [0, 1.2, 0],
    }),
  },
  // Hand on her hip.
  {
    length: 3,
    pose: () => ({
      leftUpperArm: [0.2, 0, -0.9],
      leftLowerArm: [0, -0.2, -1.7],
      leftHand: [0, 0, 0.4],
    }),
  },
];
