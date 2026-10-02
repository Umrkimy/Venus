// The layer behind everything. A crimson glow for now; the 3D Venus
// scene replaces this component later, nothing else has to move.
export default function SceneBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_35%,var(--scene-from),var(--scene-to)_70%)]"
    />
  );
}
