// What demo Venus says. Real Venus asks an AI model; the demo matches a few
// phrases, like Core's own rules do before the AI ever sees a message.

export type DemoApp = { name: string; id: string };

// The pretend PC's Start menu.
export const DEMO_APPS: DemoApp[] = [
  { name: "Spotify", id: "spotify" },
  { name: "Discord", id: "discord" },
  { name: "Steam", id: "steam" },
  { name: "Visual Studio Code", id: "vscode" },
  { name: "Notepad", id: "notepad" },
  { name: "Calculator", id: "calculator" },
  { name: "File Explorer", id: "explorer" },
  { name: "OBS Studio", id: "obs" },
];

export const DEMO_PROJECTS = ["venus", "portfolio", "uni-assignments"];

export const DEMO_SUGGESTIONS = [
  "open spotify",
  "youtube lofi beats",
  "remember I like ramen",
  "how do you work?",
  "who made you?",
];

const SITES: Record<string, { label: string; home: string; search: string }> = {
  youtube: {
    label: "YouTube",
    home: "https://www.youtube.com",
    search: "https://www.youtube.com/results?search_query=",
  },
  google: {
    label: "Google",
    home: "https://www.google.com",
    search: "https://www.google.com/search?q=",
  },
  netflix: {
    label: "Netflix",
    home: "https://www.netflix.com",
    search: "https://www.netflix.com/search?q=",
  },
};

// A command Venus would send to the PC: an app (pretend) or a real link.
export type DemoCommand = { label: string; url?: string };

export type DemoAnswer =
  | { kind: "reply"; reply: string }
  | { kind: "memory"; fact: string; reply: string }
  | { kind: "command"; command: DemoCommand; reply: string };

const looksLikeUrl = (text: string) => /^(https?:\/\/)?[\w-]+(\.[\w-]+)+(\/\S*)?$/i.test(text);
const withScheme = (text: string) => (/^https?:\/\//i.test(text) ? text : `https://${text}`);

function command(text: string): DemoAnswer | null {
  const [first, ...restWords] = text.split(/\s+/);
  const word = first.toLowerCase();
  const rest = restWords.join(" ");

  const site = SITES[word];
  if (site) {
    const url = rest ? site.search + encodeURIComponent(rest) : site.home;
    const label = rest ? `${site.label} search: ${rest}` : site.label;
    return { kind: "command", command: { label, url }, reply: rest ? `searching ${site.label} for ${rest}` : `opening ${site.label}` };
  }

  if (word !== "open" || !rest) return looksLikeUrl(text) ? link(text) : null;

  const project = rest.match(/^(?:my )?project (.+)$/i);
  if (project) {
    const name = DEMO_PROJECTS.find((each) => each === project[1].toLowerCase().trim());
    return name
      ? { kind: "command", command: { label: `project ${name} in VS Code` }, reply: `opening ${name} in vs code` }
      : { kind: "reply", reply: `no project called ${project[1]} here. this pretend pc has ${DEMO_PROJECTS.join(", ")}` };
  }
  if (looksLikeUrl(rest)) return link(rest);
  const named = SITES[rest.toLowerCase()];
  if (named) return command(rest);
  const app = DEMO_APPS.find((each) => each.name.toLowerCase().startsWith(rest.toLowerCase()));
  if (app) return { kind: "command", command: { label: app.name }, reply: `opening ${app.name}` };
  return { kind: "reply", reply: `I don't see ${rest} on this pretend pc. try spotify, discord or steam` };
}

function link(text: string): DemoAnswer {
  const url = withScheme(text);
  return { kind: "command", command: { label: url, url }, reply: `opening ${text}` };
}

const REPLIES: { match: RegExp; reply: () => string }[] = [
  {
    match: /^(hi|hey|hello|yo|sup)\b/,
    reply: () => "hey! I'm Venus, the demo version. ask me to open an app, search youtube, or remember something",
  },
  {
    match: /what can you do|help|what do you do/,
    reply: () =>
      "on the real pc I open apps, links and code projects, search youtube or google, remember stuff about you, and talk out loud when you say hey venus. here everything's pretend except the links, those really open",
  },
  {
    match: /who (made|built|created) you|your (creator|maker)/,
    reply: () =>
      "Umar built me. he's a student and made me to learn how real apps fit together: a server, a database, a web page and a little app on his pc",
  },
  {
    match: /how (do|does) (you|it|this) work|how (are|were) you (made|built)|architecture|tech stack/,
    reply: () =>
      "the page you're on is next.js. on the real setup it talks to my core, a fastapi server with postgres. core sends commands over a websocket to a small python app on the pc, and that app is what opens things and listens for hey venus",
  },
  {
    match: /is this real|demo|are you real/,
    reply: () =>
      "this is a demo running only in your browser. no server, no ai, nothing touches a real pc. the real me lives on Umar's pc",
  },
  {
    match: /what time|the time/,
    reply: () => `it's ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} for you`,
  },
  {
    match: /joke/,
    reply: () => "why did the assistant go to therapy? too many unresolved promises",
  },
  {
    match: /thank|thanks|ty\b/,
    reply: () => "anytime",
  },
  {
    match: /bye|goodbye|see you/,
    reply: () => "bye! come back anytime",
  },
];

const FALLBACK =
  "I'm the demo version so I only know a few lines. try: open spotify, youtube lofi beats, remember I like ramen, or ask how I work";

export function answer(message: string): DemoAnswer {
  const text = message.trim().replace(/[.!?,;:]+$/, "");
  const fact = text.match(/^(?:remember(?:\s+that)?|save\s+this)\s*[:,-]?\s*(.+)$/i);
  if (fact) return { kind: "memory", fact: fact[1], reply: "got it, I'll remember that" };
  const asCommand = command(text);
  if (asCommand) return asCommand;
  const lowered = text.toLowerCase();
  const scripted = REPLIES.find((each) => each.match.test(lowered));
  return { kind: "reply", reply: scripted ? scripted.reply() : FALLBACK };
}
