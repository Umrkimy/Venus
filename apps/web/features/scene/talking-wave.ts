// Venus talking on the PC's speakers: this browser has no sound to measure,
// so her mouth opens and closes in a speech-like rhythm instead.
let pcTalking = false;

export function setPcTalking(on: boolean) {
  pcTalking = on;
}

export function isPcTalking(): boolean {
  return pcTalking;
}

// 0 to about 0.8 at a given time in seconds. Two waves at odd speeds never
// line up the same way twice, so it reads as syllables, not a metronome.
export function talkingWave(time: number): number {
  const syllables = Math.abs(Math.sin(time * 9));
  const phrasing = 0.55 + 0.45 * Math.sin(time * 2.3 + 1);
  return 0.8 * syllables * phrasing;
}
