// How a sentence ends a hands-free conversation, matching the PC's rules
// (apps/node/venus_node/voice/stop_words.py):
// "stop" -> Luna stops; "bye" -> she says bye back, then listening turns off.
export type Ending = "stop" | "bye";

const STOP = new Set(["stop", "stop it", "stop talking", "never mind", "nevermind", "cancel", "be quiet", "quiet", "forget it", "enough", "thats enough"]);
const BYE = new Set(["goodbye", "bye", "good night", "goodnight", "see you", "see you later", "thats all", "talk later", "talk to you later"]);

// Around a stop or a bye these change nothing: "thank you, stop", "okay goodbye now".
const FILLER = new Set(["hey", "venus", "please", "okay", "ok", "oh", "alright", "now", "so", "and", "thank", "thanks", "you"]);
const STOP_WORDS = new Set(["stop", "cancel"]);
const BYE_WORDS = new Set(["bye", "goodbye"]);

function words(text: string): string[] {
  const all = text.toLowerCase().replace(/[^a-z ]/g, " ").split(/\s+/).filter(Boolean);
  // "stop stop", "bye bye": said twice to be sure, counts once.
  return all.filter((word, index) => word !== all[index - 1]);
}

export function endingOf(text: string): Ending | null {
  const said = words(text);
  // Thanks with her name closes it; plain "thank you" keeps talking.
  const joined = said.join(" ");
  if (joined === "thank you venus" || joined === "thanks venus") return "bye";
  const rest = said.filter((word) => !FILLER.has(word));
  const phrase = rest.join(" ");
  if (STOP.has(phrase)) return "stop";
  if (BYE.has(phrase)) return "bye";
  // Only stop and bye words left, e.g. "stop goodbye".
  if (rest.length > 0 && rest.every((word) => STOP_WORDS.has(word) || BYE_WORDS.has(word))) {
    return rest.some((word) => BYE_WORDS.has(word)) ? "bye" : "stop";
  }
  return null;
}
