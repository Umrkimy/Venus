import type { VRM } from "@pixiv/three-vrm";
import {
  createVRMAnimationClip,
  type VRMAnimation,
  VRMAnimationLoaderPlugin,
} from "@pixiv/three-vrm-animation";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

import type { Mood } from "./scene-mood";

// When an uploaded move plays: idle loops, hello once when she appears, the rest with her mood.
export type MoveUse = "idle" | "hello" | Exclude<Mood, "idle">;

// One uploaded .vrma as Core lists it (the file itself comes separately).
export type MoveInfo = {
  id: number;
  name: string;
  use: MoveUse;
  size: number;
  uploaded_at: string;
};

// Seconds to blend from one move (or the coded moves) into the next.
const FADE = 0.5;

const pick = <T>(list: T[]) => list[Math.floor(Math.random() * list.length)];

// Plays the owner's .vrma files with three.js's AnimationMixer. Moods without
// a file are left to the coded moves; weight() says how much the files own her.
export class UploadedMoves {
  private mixer: THREE.AnimationMixer;
  private clips = new Map<MoveUse, THREE.AnimationClip[]>();
  private action: THREE.AnimationAction | null = null;
  private use: MoveUse | null = null;
  // Until the files are in; then false if there is a hello move to play.
  private saidHello = true;
  private fading: THREE.AnimationAction[] = [];

  constructor(private vrm: VRM) {
    this.mixer = new THREE.AnimationMixer(vrm.scene);
  }

  // Fetches and turns each file into a clip for this model; a broken file is skipped.
  async load(moves: MoveInfo[], isStopped: () => boolean) {
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
    const clips = new Map<MoveUse, THREE.AnimationClip[]>();
    for (const move of moves) {
      try {
        // Core says the file never changes under its id, so the browser keeps it.
        const gltf = await loader.loadAsync(`/api/character/animations/${move.id}`);
        const animation = (gltf.userData.vrmAnimations as VRMAnimation[] | undefined)?.[0];
        if (!animation) continue;
        clips.set(move.use, [
          ...(clips.get(move.use) ?? []),
          createVRMAnimationClip(animation, this.vrm),
        ]);
      } catch (problem) {
        console.warn(`Venus animation ${move.name} didn't load:`, problem);
      }
    }
    if (isStopped()) return;
    this.mixer.stopAllAction();
    this.action = null;
    this.use = null;
    this.fading = [];
    this.clips = clips;
    this.saidHello = !this.has("hello");
  }

  private play(use: MoveUse | null) {
    const old = this.action;
    if (old) {
      old.fadeOut(FADE);
      this.fading.push(old);
    }
    this.use = use;
    this.action = null;
    const clips = use ? this.clips.get(use) : undefined;
    if (!clips?.length) return;
    const action = this.mixer.clipAction(pick(clips));
    // The same idle picked again: start it over instead of fading it into itself.
    this.fading = this.fading.filter((other) => other !== action);
    // Each idle plays once, then another is picked, so she doesn't loop one move forever.
    const once = use === "hello" || use === "idle";
    action.setLoop(once ? THREE.LoopOnce : THREE.LoopRepeat, Infinity);
    action.clampWhenFinished = true;
    action.reset().fadeIn(FADE).play();
    this.action = action;
  }

  private has(use: MoveUse) {
    return (this.clips.get(use)?.length ?? 0) > 0;
  }

  // One frame: picks the move for her mood (if there's a file for it) and moves the bones.
  update(mood: Mood, delta: number) {
    const finished = this.action !== null && !this.action.isRunning();
    if (finished && this.use === "hello") this.saidHello = true;
    const wanted = !this.saidHello ? "hello" : this.has(mood) ? mood : null;
    if (wanted !== this.use || (finished && wanted === "idle")) this.play(wanted);

    this.mixer.update(delta);
    // A faded-out move is stopped so it no longer costs anything.
    this.fading = this.fading.filter((done) => {
      if (done.getEffectiveWeight() > 0) return true;
      done.stop();
      return false;
    });
  }

  // How much of her pose comes from the files right now (0 = only coded moves).
  weight(): number {
    let total = this.action?.getEffectiveWeight() ?? 0;
    for (const action of this.fading) total += action.getEffectiveWeight();
    return Math.min(1, total);
  }

  dispose() {
    this.mixer.stopAllAction();
    this.mixer.uncacheRoot(this.vrm.scene);
  }
}
