import { describe, expect, it } from "vitest";

import { answer } from "./script";

describe("demo answer", () => {
  it("remembers facts", () => {
    expect(answer("remember that I like ramen.")).toEqual({
      kind: "memory",
      fact: "I like ramen",
      reply: "got it, I'll remember that",
    });
  });

  it("opens pretend apps and searches sites", () => {
    const spotify = answer("open spotify");
    expect(spotify.kind).toBe("command");

    const search = answer("youtube lofi beats");
    expect(search.kind === "command" && search.command.url).toContain("lofi%20beats");
  });

  it("controls the pretend home", () => {
    const light = answer("turn off the bedroom light");
    expect(light.kind === "command" && light.command.title).toBe("Bedroom light: off");
  });

  it("opens links", () => {
    const link = answer("github.com");
    expect(link.kind === "command" && link.command.url).toBe("https://github.com");
  });

  it("says what it can do when it doesn't know", () => {
    const unknown = answer("write my essay");
    expect(unknown.kind).toBe("reply");
  });
});
