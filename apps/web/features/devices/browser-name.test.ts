import { describe, expect, it } from "vitest";

import { browserName } from "./browser-name";

const IPHONE_SAFARI =
  "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1";
const WINDOWS_EDGE =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36 Edg/140.0";
const MAC_CHROME =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36";
const LINUX_FIREFOX = "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0";

describe("browserName", () => {
  it.each([
    [IPHONE_SAFARI, "iPhone · Safari"],
    [WINDOWS_EDGE, "Windows PC · Edge"],
    [MAC_CHROME, "Mac · Chrome"],
    [LINUX_FIREFOX, "Linux · Firefox"],
  ])("names %s", (agent, name) => expect(browserName(agent)).toBe(name));

  it("says unknown when there's nothing to go on", () => {
    expect(browserName(null)).toBe("Unknown browser");
    expect(browserName("curl/8.0")).toBe("Unknown browser");
  });
});
