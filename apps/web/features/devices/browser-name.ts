// Turns a browser's User-Agent line into "iPhone · Safari".
// Order matters: an iPhone line also says "Mac OS X", Edge also says "Chrome".
const DEVICES: [RegExp, string][] = [
  [/iPhone/, "iPhone"],
  [/iPad/, "iPad"],
  [/Android/, "Android"],
  [/Windows/, "Windows PC"],
  [/Macintosh|Mac OS X/, "Mac"],
  [/Linux/, "Linux"],
];

const BROWSERS: [RegExp, string][] = [
  // Brave on iPhone adds "Brave" at the end; elsewhere it hides as Chrome.
  [/Brave/, "Brave"],
  [/Edg\//, "Edge"],
  [/OPR\/|Opera/, "Opera"],
  [/Firefox\/|FxiOS/, "Firefox"],
  [/Chrome\/|CriOS/, "Chrome"],
  [/Safari\//, "Safari"],
];

function firstMatch(text: string, rules: [RegExp, string][]) {
  return rules.find(([pattern]) => pattern.test(text))?.[1];
}

export function browserName(userAgent: string | null) {
  if (!userAgent) return "Unknown browser";
  const device = firstMatch(userAgent, DEVICES);
  const browser = firstMatch(userAgent, BROWSERS);
  if (device && browser) return `${device} · ${browser}`;
  return device ?? browser ?? "Unknown browser";
}
