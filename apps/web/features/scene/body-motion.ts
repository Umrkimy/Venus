import type { VRM, VRMHumanBoneName } from "@pixiv/three-vrm";
import * as THREE from "three";

import {
  FIDGETS,
  type Gesture,
  moodPose,
  type Pose,
  TALKING_GESTURES,
  type Turn,
  WAVE,
} from "./poses";
import type { Mood } from "./scene-mood";

// How fast bones glide toward where they should be. Bigger is snappier.
const EASE_SPEED = 6;

// Seconds between moves: fidgets when idle, hand moves while talking.
const FIDGET_GAP = [6, 14];
const TALKING_GAP = [1.2, 2.6];
// Seconds between glances away from you when idle, and how long one lasts.
const GLANCE_GAP = [4, 9];
const GLANCE_LENGTH = [0.8, 1.8];

const between = ([low, high]: number[]) => low + Math.random() * (high - low);
const pick = <T>(list: T[]) => list[Math.floor(Math.random() * list.length)];

type Playing = { move: Gesture; start: number; mood: Mood | null };

// Everything her body remembers between frames.
export type Body = {
  turns: Map<VRMHumanBoneName, Turn>;
  // Every bone the model has, and where her hips stand, to go back to after an uploaded move.
  bones: [VRMHumanBoneName, THREE.Object3D][];
  hipsRest: THREE.Vector3;
  playing: Playing | null;
  nextMove: number;
  // Where her eyes go: the camera plus a small offset when she glances away.
  eyes: THREE.Object3D;
  glance: THREE.Vector3;
  glanceTo: THREE.Vector3;
  nextGlance: number;
  glanceEnd: number;
};

export function createBody(vrm: VRM): Body {
  const eyes = new THREE.Object3D();
  if (vrm.lookAt) vrm.lookAt.target = eyes;
  const bones = Object.keys(vrm.humanoid?.humanBones ?? {}).flatMap((name) => {
    const node = vrm.humanoid?.getNormalizedBoneNode(name as VRMHumanBoneName);
    return node ? [[name as VRMHumanBoneName, node] as [VRMHumanBoneName, THREE.Object3D]] : [];
  });
  const hips = vrm.humanoid?.getNormalizedBoneNode("hips");
  return {
    turns: new Map(),
    bones,
    hipsRest: hips ? hips.position.clone() : new THREE.Vector3(),
    // Hello as soon as she appears; the start time is filled in on the first frame.
    playing: { move: WAVE, start: -1, mood: null },
    nextMove: 0,
    eyes,
    glance: new THREE.Vector3(),
    glanceTo: new THREE.Vector3(),
    nextGlance: 0,
    glanceEnd: 0,
  };
}

// Starts a new move when it's time, and drops one that no longer fits the mood.
function chooseMove(body: Body, mood: Mood, time: number) {
  const playing = body.playing;
  if (playing && playing.start < 0) playing.start = time;
  if (
    playing &&
    (time - playing.start > playing.move.length || (playing.mood && playing.mood !== mood))
  ) {
    body.playing = null;
    body.nextMove = time + between(mood === "talking" ? TALKING_GAP : FIDGET_GAP);
  }
  if (body.playing || time < body.nextMove) return;
  if (mood === "idle") body.playing = { move: pick(FIDGETS), start: time, mood };
  else if (mood === "talking") body.playing = { move: pick(TALKING_GESTURES), start: time, mood };
}

// Eyes on you, glancing away now and then when idle, up and aside when thinking.
function moveEyes(body: Body, camera: THREE.Camera, mood: Mood, time: number, ease: number) {
  if (mood === "thinking") body.glanceTo.set(0.5, 0.6, 0);
  else if (mood !== "idle") body.glanceTo.set(0, 0, 0);
  else if (time > body.glanceEnd && body.glanceTo.lengthSq() > 0) {
    body.glanceTo.set(0, 0, 0);
    body.nextGlance = time + between(GLANCE_GAP);
  } else if (time > body.nextGlance && body.glanceTo.lengthSq() === 0) {
    body.glanceTo.set((Math.random() - 0.5) * 1.4, (Math.random() - 0.3) * 0.6, 0);
    body.glanceEnd = time + between(GLANCE_LENGTH);
  }
  body.glance.lerp(body.glanceTo, ease);
  body.eyes.position.copy(camera.position).add(body.glance);
  body.eyes.updateMatrixWorld();
}

const goal = new THREE.Quaternion();
const turnEuler = new THREE.Euler();

// One frame of body movement: the mood's pose, any move on top, then small
// always-on motion (breathing, weight shift, head drift, nods while talking).
// weight: how much of this wins over an uploaded move already on the bones (1 = all).
export function moveBody(
  vrm: VRM,
  body: Body,
  camera: THREE.Camera,
  mood: Mood,
  voice: number,
  time: number,
  delta: number,
  weight = 1,
) {
  chooseMove(body, mood, time);
  const target: Pose = { ...moodPose(mood) };
  if (body.playing) Object.assign(target, body.playing.move.pose(time - body.playing.start));

  // Same glide whatever the frame rate.
  const ease = 1 - Math.exp(-EASE_SPEED * delta);
  for (const name of Object.keys(target) as VRMHumanBoneName[]) {
    if (!body.turns.has(name)) body.turns.set(name, [0, 0, 0]);
  }
  for (const [name, turn] of body.turns) {
    const goal = target[name] ?? [0, 0, 0];
    for (let axis = 0; axis < 3; axis++) turn[axis] += (goal[axis] - turn[axis]) * ease;
  }
  moveEyes(body, camera, mood, time, ease);

  const breath = Math.sin(time * 1.6);
  const shift = Math.sin(time * 0.25);
  const glance = body.glance;
  // Small extra turns added on top of the eased ones, not eased themselves.
  const extra: Pose = {
    chest: [breath * 0.015, 0, 0],
    leftUpperArm: [0, 0, breath * 0.015],
    rightUpperArm: [0, 0, -breath * 0.015],
    // Weight from one foot to the other: hips tip, spine and legs straighten back.
    hips: [0, Math.sin(time * 0.4) * 0.04, shift * 0.03],
    spine: [0, 0, -shift * 0.03],
    leftUpperLeg: [0, 0, -shift * 0.03],
    rightUpperLeg: [0, 0, -shift * 0.03],
    // The head drifts a little and follows her eyes; nods along while she talks.
    head: [
      Math.sin(time * 5) * 0.04 * voice - glance.y * 0.1,
      Math.sin(time * 0.21) * 0.04 + glance.x * 0.15,
      Math.sin(time * 0.3) * 0.03,
    ],
  };

  // Older VRM 0 models are turned around to face you, which swaps the sign of
  // turns around x and z. Poses are written for VRM 1.
  const flip = vrm.meta?.metaVersion === "0" ? -1 : 1;
  for (const [name, node] of body.bones) {
    const turn = body.turns.get(name) ?? [0, 0, 0];
    const add = extra[name] ?? [0, 0, 0];
    turnEuler.set(flip * (turn[0] + add[0]), turn[1] + add[1], flip * (turn[2] + add[2]));
    // Bones the coded moves don't use get no turn: back to rest after an uploaded move.
    goal.setFromEuler(turnEuler);
    if (weight >= 1) node.quaternion.copy(goal);
    else node.quaternion.slerp(goal, weight);
    if (name === "hips") node.position.lerp(body.hipsRest, weight);
  }
}
