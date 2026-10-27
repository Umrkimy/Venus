import { describe, expect, it } from "vitest";

import { splitSentences } from "./split-lines";

describe("splitSentences", () => {
  it("joins back to the exact text", () => {
    const text = "Opening Spotify for you now. Want me to play your liked songs too?\nJust say the word!";
    expect(splitSentences(text).join("")).toBe(text);
  });

  it("cuts long replies at sentence ends", () => {
    const lines = splitSentences("Your calendar is free all afternoon. The gym class moved to six tonight.");
    expect(lines).toEqual(["Your calendar is free all afternoon. ", "The gym class moved to six tonight."]);
  });

  it("keeps short bits with the next sentence", () => {
    expect(splitSentences("Ok. Opening the bedroom light settings now.")).toEqual([
      "Ok. Opening the bedroom light settings now.",
    ]);
  });

  it("doesn't cut inside numbers", () => {
    expect(splitSentences("Version 3.5 of the model is the cheapest one to run.")).toHaveLength(1);
  });

  it("puts a tiny last bit on the line before", () => {
    expect(splitSentences("Here is everything I found for you today. Bye!")).toEqual([
      "Here is everything I found for you today. Bye!",
    ]);
  });

  it("returns nothing for nothing", () => {
    expect(splitSentences("")).toEqual([]);
  });
});
