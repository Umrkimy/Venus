import { describe, expect, it } from "vitest";

import { errorText } from "./error-text";

describe("errorText", () => {
  it("shows Venus's own message as it is", () => {
    expect(errorText({ detail: "No such email account" }, "Oops")).toBe("No such email account");
  });

  it("takes the first field error and drops pydantic's prefix", () => {
    const detail = [{ msg: "Value error, The name must be one line" }, { msg: "second" }];
    expect(errorText({ detail }, "Oops")).toBe("The name must be one line");
  });

  it("falls back when there's nothing readable", () => {
    expect(errorText({}, "Oops")).toBe("Oops");
    expect(errorText({ detail: [] }, "Oops")).toBe("Oops");
    expect(errorText({ detail: { code: 3 } }, "Oops")).toBe("Oops");
  });
});
