import { describe, expect, it } from "vitest";

import { endingOf } from "./stop-phrases";

describe("endingOf", () => {
  it.each(["stop", "Stop talking.", "okay stop stop", "never mind", "thank you, stop", "hey venus cancel"])(
    "%s stops Luna",
    (text) => expect(endingOf(text)).toBe("stop"),
  );

  it.each(["goodbye", "bye bye", "okay goodbye now", "thank you venus", "talk to you later", "see you later", "stop, goodbye"])(
    "%s ends the conversation",
    (text) => expect(endingOf(text)).toBe("bye"),
  );

  it.each(["thank you", "stop the music", "open spotify", "say goodbye to my friend", ""])(
    "%s keeps talking",
    (text) => expect(endingOf(text)).toBeNull(),
  );
});
