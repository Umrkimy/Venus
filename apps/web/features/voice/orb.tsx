"use client";

import { useEffect, useRef } from "react";

import { cn } from "@/lib/utils";

import type { VoiceStateName } from "./use-voice-state";

// The same orb as the desktop one (apps/node/venus_node/voice/orb.py): a
// glowing particle sphere. Keep the numbers in step with it so both match.
const COUNT = 1500;
const TILT = 0.35;
// 30 frames a second is smooth for a slow orb and half the work of 60.
const FRAME_MS = 1000 / 30;
// Top to bottom: cool blue, purple, pink, warm orange.
const GRADIENT = [
  [90, 150, 255],
  [150, 80, 220],
  [240, 60, 130],
  [255, 150, 70],
];

type Motion = { spin: number; wobble: number; scale: number; glow: number };

// How the orb moves in each state (as on the desktop). The web doesn't get
// your mic level, so listening breathes on its own. Idle and muted have a
// calm resting look here, because the web orb never hides.
function motion(state: VoiceStateName, quiet: boolean, seconds: number): Motion {
  if (quiet) return { spin: 0.02, wobble: 0.02, scale: 0.3, glow: 0.55 };
  if (state === "listening") {
    const level = 0.35 + 0.25 * Math.sin(2 * Math.PI * 0.8 * seconds);
    return { spin: 0.08, wobble: 0.04 + 0.12 * level, scale: 0.25 + 0.14 * level, glow: 0.8 + 0.2 * level };
  }
  if (state === "thinking") return { spin: 0.35, wobble: 0.08, scale: 0.34, glow: 0.9 };
  if (state === "speaking") {
    const beat = Math.abs(Math.sin(2 * Math.PI * 2 * seconds));
    return { spin: 0.1, wobble: 0.06 + 0.08 * beat, scale: 0.35, glow: 1 };
  }
  if (state === "sleeping") return { spin: 0.03, wobble: 0.02, scale: 0.22, glow: 0.45 };
  return { spin: 0.05, wobble: 0.03, scale: 0.3, glow: 0.75 };
}

// Evenly spread points on a sphere (Fibonacci spiral).
const POINTS = Array.from({ length: COUNT }, (_, n) => {
  const i = n + 0.5;
  const y = 1 - (2 * i) / COUNT;
  const ring = Math.sqrt(1 - y * y);
  const angle = Math.PI * (3 - Math.sqrt(5)) * i;
  return [ring * Math.cos(angle), y, ring * Math.sin(angle)];
});
// A few points sparkle white. A fixed pattern, so it doesn't flicker.
const SPARKLE = POINTS.map((_, i) => (i * 7919) % 100 < 3);

function drawDots(ctx: CanvasRenderingContext2D, size: number, m: Motion, seconds: number) {
  const half = size / 2;
  const radius = size * m.scale;
  const a = 2 * Math.PI * m.spin * seconds;
  ctx.clearRect(0, 0, size, size);
  ctx.globalCompositeOperation = "lighter"; // Overlapping dots add up, like the desktop's.
  for (let i = 0; i < COUNT; i++) {
    let [x, y, z] = POINTS[i];
    // Ripples drifting over the surface.
    const bump = Math.sin(3 * x + 2.1 * seconds) * Math.sin(4 * y + 1.7 * seconds) * Math.sin(5 * z + 2.6 * seconds);
    const r = 1 + m.wobble * bump;
    [x, z] = [x * Math.cos(a) + z * Math.sin(a), -x * Math.sin(a) + z * Math.cos(a)];
    [y, z] = [y * Math.cos(TILT) - z * Math.sin(TILT), y * Math.sin(TILT) + z * Math.cos(TILT)];
    x *= r;
    y *= r;
    z = Math.max(-1, Math.min(1, z * r));

    const px = half + x * radius;
    const py = half - y * radius;
    // Front brighter, rim brightest.
    const bright = (0.25 + 0.5 * ((z + 1) / 2)) * (0.5 + 0.9 * (1 - Math.abs(z))) * m.glow;

    let color: number[];
    if (SPARKLE[i]) {
      color = [255, 245, 250];
    } else {
      const where = Math.max(0, Math.min(1, py / (size - 1))) * (GRADIENT.length - 1);
      const low = Math.min(Math.floor(where), GRADIENT.length - 2);
      const mix = where - low;
      color = GRADIENT[low].map((c, k) => c * (1 - mix) + GRADIENT[low + 1][k] * mix);
    }
    ctx.fillStyle = `rgb(${color[0] * bright},${color[1] * bright},${color[2] * bright})`;
    ctx.fillRect(px, py, 1, 1);
  }
  ctx.globalCompositeOperation = "source-over";
}

type OrbProps = {
  state: VoiceStateName;
  // Muted: grey and slow.
  quiet?: boolean;
  // Width and height in CSS pixels.
  size: number;
  className?: string;
};

export default function Orb({ state, quiet = false, size, className }: OrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // The latest look, read by the running animation without restarting it.
  const lookRef = useRef({ state, quiet });
  useEffect(() => {
    lookRef.current = { state, quiet };
  }, [state, quiet]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const scale = window.devicePixelRatio || 1;
    canvas.width = size * scale;
    canvas.height = size * scale;
    // Dots go on a side canvas first, so they can be drawn twice: blurred halo + sharp.
    const dots = document.createElement("canvas");
    dots.width = canvas.width;
    dots.height = canvas.height;
    const dotsCtx = dots.getContext("2d");
    if (!dotsCtx) return;
    dotsCtx.scale(scale, scale);

    const start = performance.now();
    let last = 0;
    let frame = 0;
    // requestAnimationFrame pauses by itself while the tab is hidden.
    const draw = (now: number) => {
      frame = requestAnimationFrame(draw);
      if (now - last < FRAME_MS) return;
      last = now;
      const seconds = (now - start) / 1000;
      const m = motion(lookRef.current.state, lookRef.current.quiet, seconds);
      drawDots(dotsCtx, size, m, seconds);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      // Soft dark core keeps the orb readable over light pages too.
      const half = canvas.width / 2;
      const radius = canvas.width * m.scale * 1.08;
      const core = ctx.createRadialGradient(half, half, radius * 0.7, half, half, radius);
      core.addColorStop(0, `rgba(0,0,0,${0.92 * Math.min(m.glow * 1.1, 1)})`);
      core.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = core;
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.globalCompositeOperation = "lighter";
      ctx.filter = `blur(${1.5 * scale}px)`;
      ctx.drawImage(dots, 0, 0);
      ctx.drawImage(dots, 0, 0);
      ctx.filter = "none";
      ctx.drawImage(dots, 0, 0);
      ctx.globalCompositeOperation = "source-over";
    };
    frame = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frame);
  }, [size]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{ width: size, height: size }}
      className={cn("transition-[filter] duration-500", quiet && "grayscale", className)}
    />
  );
}
