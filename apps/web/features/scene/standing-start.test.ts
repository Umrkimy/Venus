import { describe, expect, it } from "vitest";

import { standingStart } from "./standing-start";

describe("standingStart", () => {
  it("leaves a move that starts standing alone", () => {
    expect(standingStart([0, 0.5, 1], [1, 0.95, 1])).toBe(0);
  });

  it("skips a crouched start to where she's up again", () => {
    // pixiv's Greeting: hips at a third of their height, standing from 1.5 s.
    expect(standingStart([0, 0.5, 1, 1.5, 2], [0.33, 0.33, 0.6, 0.95, 1])).toBe(1.5);
  });

  it("is safe with odd tracks", () => {
    expect(standingStart([], [])).toBe(0);
    expect(standingStart([0, 1], [1])).toBe(0);
    expect(standingStart([0, 1], [0, 0])).toBe(0);
  });
});
