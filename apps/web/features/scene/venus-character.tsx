"use client";

import { type VRM, VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

import { voiceLevel, wantVoiceLevel } from "@/features/chat/use-speaker";
import { type Body, createBody, moveBody } from "./body-motion";
import { getMood } from "./scene-mood";
import { setResetView, useStage } from "./stage-store";
import { createTemple, disposePlace, type Place, templeFog } from "./temple";
import { type MoveInfo, UploadedMoves } from "./uploaded-moves";

// Shipped with Venus for everyone; your own model comes from Core instead.
// AvatarSample_A by pixiv Inc.; conditions in public/models/CREDITS.md.
const TEMPLATE_URL = "/models/avatar-sample-a.vrm";
const OWN_MODEL_URL = "/api/character/model";
const OWN_PLACE_URL = "/api/character/place";

// Where the camera starts: far enough back to see all of her, aimed a little
// below her middle so she sits high, above the chat box.
const DEFAULT_VIEW = { position: [0, 1.15, 4.6], target: [0, 0.72, 0] };
// A new name when the default view changes, so an old saved view doesn't hide it.
const VIEW_KEY = "venus.camera.3";

type View = typeof DEFAULT_VIEW;

// Storage can be blocked (private window, site data off); then it isn't remembered.
function loadView(): View {
  try {
    const saved = JSON.parse(localStorage.getItem(VIEW_KEY) ?? "null");
    if (saved?.position?.length === 3 && saved?.target?.length === 3) return saved;
  } catch {}
  return DEFAULT_VIEW;
}

function saveView(view: View | null) {
  try {
    if (view) localStorage.setItem(VIEW_KEY, JSON.stringify(view));
    else localStorage.removeItem(VIEW_KEY);
  } catch {}
}

// Seconds between blinks, picked at random in this range.
const BLINK_GAP = [2, 6];
const BLINK_LENGTH = 0.15;

// Body moves with her mood; she blinks, and her mouth follows Luna's voice.
type FaceState = { nextBlink: number; mouth: number };

type Parts = { vrm: VRM; body: Body; moves: UploadedMoves };

function animate({ vrm, body, moves }: Parts, camera: THREE.Camera, time: number, delta: number, state: FaceState) {
  // Eased toward the voice's loudness, so the mouth doesn't flicker.
  state.mouth += (voiceLevel() - state.mouth) * Math.min(1, delta * 18);
  // Uploaded moves first; the coded ones blend over them where there's no file.
  const mood = getMood();
  moves.update(mood, delta);
  moveBody(vrm, body, camera, mood, state.mouth, time, delta, 1 - moves.weight());

  const faces = vrm.expressionManager;
  if (faces) {
    // A blink is a quick close and open: 0 to 1 and back over BLINK_LENGTH.
    const sinceBlink = time - state.nextBlink;
    if (sinceBlink > BLINK_LENGTH) {
      state.nextBlink = time + BLINK_GAP[0] + Math.random() * (BLINK_GAP[1] - BLINK_GAP[0]);
    }
    const blinking = sinceBlink >= 0 && sinceBlink <= BLINK_LENGTH;
    faces.setValue("blink", blinking ? Math.sin((sinceBlink / BLINK_LENGTH) * Math.PI) : 0);
    faces.setValue("aa", state.mouth);
  }
  vrm.update(delta);
}

// Your own model if you uploaded one (Settings), else the template.
async function loadModel(loader: GLTFLoader, own: boolean) {
  if (own) {
    // The browser keeps the file and only asks Core whether it changed.
    // A download cut halfway fails on reading the body: then the template too.
    const response = await fetch(OWN_MODEL_URL).catch(() => null);
    const file = response?.ok ? await response.arrayBuffer().catch(() => null) : null;
    if (file) return loader.parseAsync(file, "");
  }
  return loader.loadAsync(TEMPLATE_URL);
}

// Your own place if one is in use (Settings), else the built-in temple.
async function loadPlace(loader: GLTFLoader, own: boolean): Promise<Place> {
  if (own) {
    const response = await fetch(OWN_PLACE_URL).catch(() => null);
    const file = response?.ok ? await response.arrayBuffer().catch(() => null) : null;
    const gltf = file ? await loader.parseAsync(file, "").catch(() => null) : null;
    if (gltf) return { group: gltf.scene, update: () => {} };
  }
  return createTemple();
}

type VenusCharacterProps = {
  own: boolean;
  // The uploaded place in use: its id, null for the temple, undefined while unknown.
  place: number | null | undefined;
  moves: MoveInfo[];
};

export default function VenusCharacter({ own, place, moves }: VenusCharacterProps) {
  const holder = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const placeRef = useRef<Place | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const [ready, setReady] = useState(false);
  const movesRef = useRef<UploadedMoves | null>(null);
  const stage = useStage();

  useEffect(() => {
    const element = holder.current;
    if (!element) return;
    wantVoiceLevel();

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    // Sharp enough; full 4K-style resolution costs memory for little gain.
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    element.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    // Far enough to see the sky around the place.
    const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
    const view = loadView();
    camera.position.fromArray(view.position);
    camera.lookAt(new THREE.Vector3().fromArray(view.target));
    cameraRef.current = camera;
    const light = new THREE.DirectionalLight(0xffffff, Math.PI);
    light.position.set(1, 1.5, 2);
    scene.add(light);
    // Soft light from all around, so the place isn't black on its shady side.
    scene.add(new THREE.HemisphereLight("#cbbcff", "#4a3b5c", 0.8));

    const fit = () => {
      const { clientWidth: width, clientHeight: height } = element;
      if (!width || !height) return;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const resize = new ResizeObserver(fit);
    resize.observe(element);
    fit();

    let parts: Parts | null = null;
    let stopped = false;
    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));
    loadModel(loader, own).then(
      (gltf) => {
        const loaded = gltf.userData.vrm as VRM;
        if (stopped) {
          VRMUtils.deepDispose(gltf.scene);
          return;
        }
        // Lighter to draw; older VRM 0 models face away until turned.
        VRMUtils.removeUnnecessaryVertices(gltf.scene);
        VRMUtils.combineSkeletons(gltf.scene);
        VRMUtils.rotateVRM0(loaded);
        scene.add(loaded.scene);
        parts = { vrm: loaded, body: createBody(loaded), moves: new UploadedMoves(loaded) };
        movesRef.current = parts.moves;
        setReady(true);
      },
      // No model at all: the plain glow behind stays.
      (problem) => console.warn("Venus 3D model didn't load:", problem),
    );

    // The browser pauses this loop while the tab is hidden.
    const state = { nextBlink: 2, mouth: 0 };
    let last = performance.now();
    renderer.setAnimationLoop((now) => {
      const delta = Math.min(0.1, (now - last) / 1000);
      last = now;
      controlsRef.current?.update(delta);
      if (parts) animate(parts, camera, now / 1000, delta, state);
      placeRef.current?.update(now / 1000, delta);
      renderer.render(scene, camera);
    });

    return () => {
      stopped = true;
      renderer.setAnimationLoop(null);
      resize.disconnect();
      cameraRef.current = null;
      sceneRef.current = null;
      movesRef.current = null;
      parts?.moves.dispose();
      if (parts) VRMUtils.deepDispose(parts.vrm.scene);
      renderer.dispose();
      // Hands the graphics memory back now instead of whenever the browser likes.
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [own]);

  // The place she stands in; switching it in Settings doesn't reload her.
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene || place === undefined) return;
    let stopped = false;
    let shown: Place | null = null;
    const loader = new GLTFLoader();
    void loadPlace(loader, place !== null).then((loaded) => {
      if (stopped) {
        disposePlace(loaded.group);
        return;
      }
      shown = loaded;
      placeRef.current = loaded;
      scene.add(loaded.group);
      // Haze only in the temple; an uploaded place keeps its own look.
      scene.fog = place === null ? templeFog() : null;
    });
    return () => {
      stopped = true;
      if (!shown) return;
      scene.remove(shown.group);
      disposePlace(shown.group);
      if (placeRef.current === shown) placeRef.current = null;
    };
  }, [own, place]);

  // Your uploaded .vrma moves, loaded again when the list changes in Settings.
  useEffect(() => {
    const uploaded = movesRef.current;
    if (!ready || !uploaded) return;
    let stopped = false;
    void uploaded.load(moves, () => stopped || movesRef.current !== uploaded);
    return () => {
      stopped = true;
    };
  }, [ready, moves]);

  // Drag to turn around her, scroll or pinch to zoom, right-drag or two fingers to pan.
  useEffect(() => {
    const camera = cameraRef.current;
    if (!stage || !camera) return;
    const controls = new OrbitControls(camera, stage);
    controls.target.fromArray(loadView().target);
    controls.enableDamping = true;
    controls.minDistance = 0.4;
    controls.maxDistance = 6;
    // Not below the floor: a little under level at most.
    controls.maxPolarAngle = Math.PI * 0.55;
    controls.update();
    controlsRef.current = controls;

    const remember = () =>
      saveView({ position: camera.position.toArray(), target: controls.target.toArray() });
    const reset = () => {
      // Without damping, one update uses up any leftover spin from a drag,
      // so the camera doesn't keep drifting after the jump.
      controls.enableDamping = false;
      controls.update();
      camera.position.fromArray(DEFAULT_VIEW.position);
      controls.target.fromArray(DEFAULT_VIEW.target);
      controls.update();
      controls.enableDamping = true;
      saveView(null);
    };
    controls.addEventListener("end", remember);
    stage.addEventListener("dblclick", reset);
    setResetView(reset);

    return () => {
      controls.removeEventListener("end", remember);
      stage.removeEventListener("dblclick", reset);
      setResetView(null);
      controls.dispose();
      controlsRef.current = null;
    };
  }, [stage, own]);

  return (
    <div
      ref={holder}
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 transition-opacity duration-700 [&>canvas]:size-full ${
        ready ? "opacity-100" : "opacity-0"
      }`}
    />
  );
}
