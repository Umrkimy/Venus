import { describe, expect, it } from "vitest";

import { isPcTalking, setPcTalking, talkingWave } from "./talking-wave";

describe("talkingWave", () => {
  it("stays between shut and wide open", () => {
    for (let time = 0; time < 20; time += 0.01) {
      const level = talkingWave(time);
      expect(level).toBeGreaterThanOrEqual(0);
      expect(level).toBeLessThanOrEqual(0.8);
    }
  });

  it("opens and closes within a second, like syllables", () => {
    const levels = Array.from({ length: 60 }, (_, frame) => talkingWave(frame / 60));
    expect(Math.max(...levels)).toBeGreaterThan(0.3);
    expect(Math.min(...levels)).toBeLessThan(0.05);
  });

  it("is off until the PC says Venus is speaking", () => {
    expect(isPcTalking()).toBe(false);
    setPcTalking(true);
    expect(isPcTalking()).toBe(true);
    setPcTalking(false);
  });
});
