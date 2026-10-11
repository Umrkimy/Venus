"use client";

// What Venus is doing right now, so her body can show it. The chat sets it;
// the 3D loop reads it every frame with getMood(), which costs nothing.
export type Mood = "idle" | "listening" | "thinking" | "talking";

let mood: Mood = "idle";

export function setMood(next: Mood) {
  mood = next;
}

export function getMood(): Mood {
  return mood;
}
