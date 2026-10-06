// The browser's own speech-to-text (Apple's on iPhone, Google's in Chrome).
// Free and live: words arrive while you talk. Not in every browser (Brave
// has it but it always fails), so Venus falls back to Core's transcription.

export type SpeechResults = ArrayLike<{ 0: { transcript: string } }>;

export type BrowserSpeech = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  abort: () => void;
  onresult: ((event: { results: SpeechResults }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};

// Errors that mean "this browser can't do it": use Core's way instead.
const BROKEN_ERRORS = new Set([
  "network",
  "service-not-allowed",
  "language-not-supported",
  "audio-capture",
]);

let broken = false;

export function markSpeechBroken(error: string): boolean {
  if (BROKEN_ERRORS.has(error)) broken = true;
  return broken;
}

// A new recognizer, or null when this browser has none (or it failed before).
export function makeBrowserSpeech(): BrowserSpeech | null {
  if (broken || typeof window === "undefined") return null;
  const scope = window as unknown as Record<string, unknown>;
  const Speech = (scope.SpeechRecognition ?? scope.webkitSpeechRecognition) as
    (new () => BrowserSpeech) | undefined;
  if (!Speech) return null;
  const speech = new Speech();
  speech.continuous = true;
  speech.interimResults = true;
  speech.lang = navigator.language || "en-US";
  return speech;
}

// How long you can pause before your sentence is sent.
const END_PAUSE_MS = 1500;
// After "uh", "and", "so"... you're still thinking: wait longer.
const THINKING_PAUSE_MS = 3000;
const FILLERS = new Set([
  "uh",
  "uhh",
  "uhm",
  "um",
  "umm",
  "er",
  "erm",
  "hmm",
  "hm",
  "ah",
  "eh",
]);
const LINKS = new Set([
  "and",
  "but",
  "so",
  "or",
  "like",
  "because",
  "cause",
  "then",
  "the",
  "a",
  "to",
  "with",
  "if",
]);

function wordsOf(text: string): string[] {
  return text.toLowerCase().match(/[a-z']+/g) ?? [];
}

export function pauseAfter(text: string): number {
  const last = wordsOf(text).at(-1) ?? "";
  return FILLERS.has(last) || LINKS.has(last)
    ? THINKING_PAUSE_MS
    : END_PAUSE_MS;
}

// "Uh", "um hmm": nothing worth sending.
export function onlyFillers(text: string): boolean {
  return wordsOf(text).every((word) => FILLERS.has(word));
}

// Everything heard since the recognizer (re)started, as one sentence.
export function joinResults(results: SpeechResults): string {
  let text = "";
  for (let index = 0; index < results.length; index++)
    text += results[index][0].transcript;
  return text.replace(/\s+/g, " ").trim();
}
