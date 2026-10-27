import { describe, expect, it } from "vitest";

import { pagePath } from "./use-page-path";

describe("pagePath", () => {
  it("drops the demo's trailing slash", () => {
    expect(pagePath("/settings/voice/")).toBe("/settings/voice");
    expect(pagePath("/settings/voice")).toBe("/settings/voice");
  });

  it("keeps the home page as /", () => {
    expect(pagePath("/")).toBe("/");
  });
});
