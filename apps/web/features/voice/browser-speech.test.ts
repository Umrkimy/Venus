import { describe, expect, it } from "vitest";

import { joinResults, onlyFillers, pauseAfter } from "./browser-speech";

describe("onlyFillers", () => {
  it("is true for thinking noises only", () => {
    expect(onlyFillers("uh")).toBe(true);
    expect(onlyFillers("Um, hmm...")).toBe(true);
    expect(onlyFillers("")).toBe(true);
  });

  it("is false once there's a real word", () => {
    expect(onlyFillers("um open spotify")).toBe(false);
  });
});

describe("pauseAfter", () => {
  it("waits the normal time after a finished sentence", () => {
    expect(pauseAfter("open spotify", 1500)).toBe(1500);
  });

  it("waits twice as long after a filler or a joining word", () => {
    expect(pauseAfter("open spotify and", 1500)).toBe(3000);
    expect(pauseAfter("play something uh", 1000)).toBe(2000);
  });
});

describe("joinResults", () => {
  it("joins every result into one tidy sentence", () => {
    const results = [{ 0: { transcript: "open " } }, { 0: { transcript: " spotify   and" } }, { 0: { transcript: " play lofi " } }];
    expect(joinResults(results)).toBe("open spotify and play lofi");
  });
});
