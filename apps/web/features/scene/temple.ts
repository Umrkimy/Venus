import * as THREE from "three";

// Venus's built-in place: a marble platform among the clouds, open columns
// behind her, a faint halo and gold motes drifting up. All made in code (no
// file to download), a few thousand triangles, so it costs almost nothing.

const SKY_TOP = new THREE.Color("#0e0f2e");
const SKY_MIDDLE = new THREE.Color("#3b2a63");
const HORIZON = new THREE.Color("#e9a67c");
const MARBLE = "#ece6f2";
const FLOOR = "#cfc4dc";
const GOLD = "#e8c27a";

export type Place = {
  group: THREE.Group;
  // Called every frame: clouds drift, motes rise.
  update: (time: number, delta: number) => void;
};

// A big ball around everything, painted from the inside: dark at the top,
// warm at the horizon, so it reads as dusk in the sky.
function sky(): THREE.Mesh {
  const material = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: {
      top: { value: SKY_TOP },
      middle: { value: SKY_MIDDLE },
      horizon: { value: HORIZON },
    },
    vertexShader: `
      varying vec3 place;
      void main() {
        place = normalize(position);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform vec3 top;
      uniform vec3 middle;
      uniform vec3 horizon;
      varying vec3 place;
      void main() {
        float up = place.y;
        vec3 color = up > 0.0
          ? mix(mix(horizon, middle, smoothstep(0.0, 0.25, up)), top, smoothstep(0.25, 0.8, up))
          : mix(horizon, middle, smoothstep(0.0, -0.4, up));
        gl_FragColor = vec4(color, 1.0);
      }`,
  });
  return new THREE.Mesh(new THREE.SphereGeometry(60, 32, 16), material);
}

// A soft white blob drawn once on a small canvas: every cloud and mote uses it.
function softDot(): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 64;
  const context = canvas.getContext("2d")!;
  const glow = context.createRadialGradient(32, 32, 0, 32, 32, 32);
  glow.addColorStop(0, "rgba(255,255,255,1)");
  glow.addColorStop(0.4, "rgba(255,255,255,0.5)");
  glow.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = glow;
  context.fillRect(0, 0, 64, 64);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

// Three stacked discs: she stands on the top one at height 0.
function platform(floor: THREE.Material, gold: THREE.Material): THREE.Group {
  const group = new THREE.Group();
  [
    { radius: 3.4, y: -0.12 },
    { radius: 3.9, y: -0.36 },
    { radius: 4.4, y: -0.6 },
  ].forEach(({ radius, y }) => {
    const step = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius + 0.05, 0.24, 64), floor);
    step.position.y = y;
    group.add(step);
  });
  // A thin gold circle in the floor around her feet.
  const inlay = new THREE.Mesh(new THREE.RingGeometry(1.08, 1.11, 96), gold);
  inlay.rotation.x = -Math.PI / 2;
  inlay.position.y = 0.002;
  group.add(inlay);
  return group;
}

const COLUMN_RING = 3.1;
const COLUMN_HEIGHT = 3;

// Columns in a half circle behind her with a curved beam on top; the front
// stays open for the camera.
function columns(marble: THREE.Material): THREE.Group {
  const group = new THREE.Group();
  const shaft = new THREE.CylinderGeometry(0.16, 0.19, COLUMN_HEIGHT, 20);
  const block = new THREE.BoxGeometry(0.5, 0.18, 0.5);
  const count = 7;
  for (let i = 0; i < count; i++) {
    // Angle 0 is in front (the camera's side): from her left, round the back, to her right.
    const angle = Math.PI / 2 + Math.PI * (i / (count - 1));
    const column = new THREE.Group();
    const body = new THREE.Mesh(shaft, marble);
    body.position.y = COLUMN_HEIGHT / 2;
    const base = new THREE.Mesh(block, marble);
    base.position.y = 0.09;
    const top = new THREE.Mesh(block, marble);
    top.position.y = COLUMN_HEIGHT + 0.09;
    column.add(body, base, top);
    column.position.set(Math.sin(angle) * COLUMN_RING, 0, Math.cos(angle) * COLUMN_RING);
    group.add(column);
  }
  // The beam: a slice of a hollow cylinder over the column tops.
  const beam = new THREE.Mesh(
    new THREE.CylinderGeometry(COLUMN_RING, COLUMN_RING, 0.3, 64, 1, true, Math.PI / 2, Math.PI),
    marble,
  );
  beam.position.y = COLUMN_HEIGHT + 0.33;
  group.add(beam);
  return group;
}

function clouds(dot: THREE.Texture): THREE.Group {
  const group = new THREE.Group();
  const material = new THREE.SpriteMaterial({
    map: dot,
    color: "#f3dcef",
    transparent: true,
    opacity: 0.55,
    depthWrite: false,
  });
  // Fixed numbers instead of random, so every visit looks the same.
  for (let i = 0; i < 26; i++) {
    const angle = i * 2.4;
    const distance = 12 + (i % 5) * 3;
    const cloud = new THREE.Sprite(material);
    const size = 5 + (i % 4) * 2;
    cloud.scale.set(size * 1.8, size, 1);
    cloud.position.set(Math.sin(angle) * distance, -0.8 + (i % 3) * 0.9, Math.cos(angle) * distance);
    group.add(cloud);
  }
  return group;
}

const MOTES = 160;

function motes(dot: THREE.Texture): THREE.Points {
  const positions = new Float32Array(MOTES * 3);
  for (let i = 0; i < MOTES; i++) {
    const angle = Math.random() * Math.PI * 2;
    const distance = 0.8 + Math.random() * 4;
    positions.set([Math.sin(angle) * distance, Math.random() * 4, Math.cos(angle) * distance], i * 3);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({
    map: dot,
    color: GOLD,
    size: 0.06,
    transparent: true,
    opacity: 0.8,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  return new THREE.Points(geometry, material);
}

export function createTemple(): Place {
  const group = new THREE.Group();
  const dot = softDot();
  const marble = new THREE.MeshStandardMaterial({ color: MARBLE, roughness: 0.35, side: THREE.DoubleSide });
  const floor = new THREE.MeshStandardMaterial({ color: FLOOR, roughness: 0.25, metalness: 0.1 });
  const gold = new THREE.MeshStandardMaterial({
    color: GOLD,
    emissive: GOLD,
    emissiveIntensity: 0.3,
    side: THREE.DoubleSide,
  });

  // A faint gold ring high behind her, like a halo on the sky.
  const halo = new THREE.Mesh(
    new THREE.TorusGeometry(2.2, 0.02, 8, 96),
    new THREE.MeshBasicMaterial({ color: GOLD, transparent: true, opacity: 0.35, fog: false }),
  );
  halo.position.set(0, 2.1, -3.4);

  const cloudLayer = clouds(dot);
  const floating = motes(dot);
  group.add(sky(), platform(floor, gold), columns(marble), halo, cloudLayer, floating);

  const rising = floating.geometry.getAttribute("position") as THREE.BufferAttribute;
  return {
    group,
    update(time, delta) {
      cloudLayer.rotation.y = time * 0.004;
      for (let i = 0; i < MOTES; i++) {
        // Up slowly, and back to the floor once past her head height.
        const y = rising.getY(i) + delta * (0.08 + (i % 7) * 0.02);
        rising.setY(i, y > 4 ? 0 : y);
      }
      rising.needsUpdate = true;
      halo.material.opacity = 0.3 + Math.sin(time * 0.6) * 0.06;
    },
  };
}

// Haze toward the horizon colour, so the far clouds melt into the sky.
export function templeFog(): THREE.Fog {
  return new THREE.Fog(HORIZON.clone().lerp(SKY_MIDDLE, 0.5), 14, 40);
}

// Frees the graphics memory of everything in a place (made or uploaded).
export function disposePlace(group: THREE.Object3D) {
  group.traverse((object) => {
    const mesh = object as THREE.Mesh;
    mesh.geometry?.dispose();
    const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    materials.forEach((material) => {
      Object.values(material).forEach((value) => {
        if (value instanceof THREE.Texture) value.dispose();
      });
      material.dispose();
    });
  });
}
