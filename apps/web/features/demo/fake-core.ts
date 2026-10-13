// A pretend Core inside the browser, for the portfolio demo only.
//
// Every page asks Core through fetch("/api/..."). In the demo that call is
// answered here from data kept in memory, so the real pages run unchanged
// with no server, no keys and nothing that can touch a PC. Changes last for
// this browser tab (sessionStorage); a new tab starts over. Other fetches
// (the 3D model, page files) go out as usual.

import { DEMO_CHAT_IDS, DEMO_PROJECT_IDS } from "./demo-mode";
import { DEMO_APPS, answer, type DemoCommand } from "./script";

type Message = {
  role: "user" | "assistant";
  content: string;
  actions?: ({ kind: "command"; command_id: string; label: string } | { kind: "memory"; text: string })[];
};
type Conversation = {
  id: string;
  title: string;
  updated_at: string;
  archived: boolean;
  project_id: string | null;
  messages: Message[];
};
type Command = DemoCommand & { command_id: string; status: string };

const DEVICE = "demo-pc";
const now = () => new Date().toISOString();
const ago = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString();

const SAVE_KEY = "venus-demo";
let nextId = 1;
const newId = (prefix: string) => `${prefix}-${nextId++}`;

// Static pages exist only for these ids, so new chats and projects take the next free one.
function freeId(ids: string[], used: Map<string, unknown>) {
  return ids.find((id) => !used.has(id)) ?? null;
}

const state = {
  mode: "confirm" as "confirm" | "full",
  conversations: new Map<string, Conversation>(),
  projects: new Map<string, Record<string, unknown>>(),
  memories: new Map<string, Record<string, unknown>>(),
  personalities: new Map<string, Record<string, unknown>>(),
  shortcuts: new Map<string, Record<string, unknown>>(),
  devices: new Map<string, Record<string, unknown>>(),
  sessions: new Map<string, Record<string, unknown>>(),
  commands: new Map<string, Command>(),
  settings: {
    llm: { provider: "openai", model: "gpt-6-luna", has_key: true },
    voice: { voice_id: "demo-voice", model: "s2.1-pro-free", has_key: true },
    time: { time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone, country: "" },
    listening: { end_pause_ms: 1000, mic: "" },
  } as Record<string, Record<string, unknown>>,
};

function seed() {
  const welcome: Conversation = {
    id: DEMO_CHAT_IDS[0],
    title: "Welcome to the demo",
    updated_at: ago(5),
    archived: false,
    project_id: null,
    messages: [
      { role: "user", content: "hey venus, what is this?" },
      {
        role: "assistant",
        content:
          "hey! this is a demo of me running only in your browser. the real me lives on Umar's pc and opens his apps when he says hey venus. try a new chat and ask me to open spotify",
      },
    ],
  };
  state.conversations.set(welcome.id, welcome);

  const project = DEMO_PROJECT_IDS[0];
  state.projects.set(project, {
    id: project,
    name: "Uni",
    updated_at: ago(60),
    archived: false,
    chat_count: 1,
    instructions: "Keep answers short, I'm studying.",
  });
  const study: Conversation = {
    id: DEMO_CHAT_IDS[1],
    title: "Exam week plan",
    updated_at: ago(60),
    archived: false,
    project_id: project,
    messages: [
      { role: "user", content: "remember my exam is on friday" },
      { role: "assistant", content: "got it, I'll remember that", actions: [{ kind: "memory", text: "my exam is on friday" }] },
    ],
  };
  state.conversations.set(study.id, study);

  for (const text of ["my exam is on friday", "I like lo-fi while studying"]) {
    const id = newId("memory");
    state.memories.set(id, { id, text, created_at: ago(90) });
  }
  state.personalities.set("professional", {
    id: "professional",
    name: "Professional",
    text: "Friendly and to the point. Short replies, casual texting style.",
    active: true,
    updated_at: ago(600),
  });
  state.shortcuts.set("comix", {
    keyword: "comix",
    label: "Comix",
    home_url: "https://example.com/comics",
    search_url: null,
  });
  state.devices.set("main", {
    id: "main",
    name: "Main PC",
    device_id: DEVICE,
    created_at: ago(60 * 24 * 30),
    last_seen_at: now(),
    revoked_at: null,
    main: true,
    connected: true,
  });
  state.sessions.set("this", {
    id: "this",
    user_agent: navigator.userAgent,
    created_at: now(),
    last_seen_at: now(),
    current: true,
  });
}

// Kept per tab, so a full page load (a static host can't always do the
// quick in-app switch) doesn't wipe your chats.
const STORES = ["conversations", "projects", "memories", "personalities", "shortcuts", "devices", "sessions", "commands"] as const;

function save() {
  try {
    const stores = Object.fromEntries(STORES.map((name) => [name, [...state[name].entries()]]));
    sessionStorage.setItem(SAVE_KEY, JSON.stringify({ nextId, mode: state.mode, settings: state.settings, stores }));
  } catch {
    // Private mode or full storage: the demo still works, it just forgets on reload.
  }
}

function load(): boolean {
  try {
    const saved = JSON.parse(sessionStorage.getItem(SAVE_KEY) ?? "null");
    if (!saved) return false;
    nextId = saved.nextId;
    state.mode = saved.mode;
    state.settings = saved.settings;
    for (const name of STORES) {
      (state[name] as Map<string, unknown>) = new Map(saved.stores[name]);
    }
    return true;
  } catch {
    return false;
  }
}

// --- answers --------------------------------------------------------------

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const empty = () => new Response(null, { status: 204 });
const missing = (detail = "Not in the demo") => json({ detail }, 404);

function summary(conversation: Conversation) {
  const { id, title, updated_at, project_id } = conversation;
  return { id, title, updated_at, project_id };
}

function projectBody(project: Record<string, unknown>) {
  const chats = [...state.conversations.values()].filter((each) => each.project_id === project.id);
  return { ...project, chat_count: chats.length };
}

function finish(command: Command, approved: boolean) {
  command.status = approved ? "succeeded" : "denied";
  // The one real thing the demo does: a link opens in a new tab.
  if (approved && command.url) window.open(command.url, "_blank", "noopener,noreferrer");
}

function chat(body: { message: string; conversation_id?: string; project_id?: string }) {
  let conversation = body.conversation_id ? state.conversations.get(body.conversation_id) : undefined;
  if (body.conversation_id && !conversation) return missing("Conversation not found");
  if (!conversation) {
    const id = freeId(DEMO_CHAT_IDS, state.conversations);
    if (id === null) return json({ detail: "That's all the chats the demo can hold. Reload to start over." }, 409);
    conversation = {
      id,
      title: body.message.slice(0, 60),
      updated_at: now(),
      archived: false,
      project_id: body.project_id ?? null,
      messages: [],
    };
    state.conversations.set(id, conversation);
  }
  conversation.messages.push({ role: "user", content: body.message });
  conversation.updated_at = now();

  const result = answer(body.message);
  let reply: Record<string, unknown>;
  if (result.kind === "memory") {
    const id = newId("memory");
    state.memories.set(id, { id, text: result.fact, created_at: now() });
    reply = { type: "reply", reply: result.reply, actions: [{ kind: "memory", text: result.fact }] };
  } else if (result.kind === "command") {
    const command: Command = { ...result.command, command_id: newId("command"), status: "awaiting_approval" };
    state.commands.set(command.command_id, command);
    // Full mode: no Approve button, Venus just does it.
    if (state.mode === "full") finish(command, true);
    const actions = [{ kind: "command", command_id: command.command_id, label: command.label }];
    reply = { type: "command", command_id: command.command_id, label: command.label, reply: result.reply, actions };
  } else {
    reply = { type: "reply", reply: result.reply, actions: [] };
  }
  conversation.messages.push({
    role: "assistant",
    content: reply.reply as string,
    actions: reply.actions as Message["actions"],
  });
  return json({ ...reply, conversation_id: conversation.id });
}

// A plain list resource: GET the list, POST adds, PATCH/PUT changes, DELETE removes.
function collection(
  store: Map<string, Record<string, unknown>>,
  method: string,
  id: string | undefined,
  body: Record<string, unknown>,
  make: (body: Record<string, unknown>) => Record<string, unknown> | null,
) {
  if (!id) {
    if (method === "GET") return json([...store.values()]);
    if (method === "POST") {
      const item = make(body);
      if (item === null) return json({ detail: "The demo is full. Reload to start over." }, 409);
      store.set(String(item.id ?? item.keyword), item);
      return json(item, 201);
    }
  }
  const item = id ? store.get(id) : undefined;
  if (!item) return missing();
  if (method === "DELETE") {
    store.delete(id!);
    return empty();
  }
  Object.assign(item, body, { updated_at: now() });
  return json(item);
}

async function route(method: string, path: string, query: URLSearchParams, body: Record<string, unknown>) {
  const parts = path.split("/").filter(Boolean);
  const [area, id, more] = parts;

  switch (area) {
    case "auth":
      if (id === "me") return json({ username: "visitor" });
      // Any username and password works: there's nothing to protect here.
      if (id === "login") return json({ username: "visitor" });
      if (id === "logout") return empty();
      if (id === "sessions") {
        if (more === "sign-out-others") return json({ signed_out: 0 });
        return collection(state.sessions, method, parts[2], body, () => null);
      }
      return missing();

    case "nodes":
      if (!id) return json([{ device_id: DEVICE, apps: DEMO_APPS.length }]);
      if (more === "chat" && method === "POST") return chat(body as Parameters<typeof chat>[0]);
      if (more === "apps") return json({ device_id: DEVICE, apps: DEMO_APPS.map((a) => ({ name: a.name, app_id: a.id })) });
      return missing();

    case "commands": {
      const command = id ? state.commands.get(id) : undefined;
      if (!command) return missing("Command not found");
      if (more === "approval" && method === "POST") {
        if (command.status !== "awaiting_approval") return json({ detail: "Command is not awaiting approval" }, 409);
        finish(command, Boolean(body.approved));
      }
      return json({ command_id: command.command_id, status: command.status });
    }

    case "conversations": {
      if (!id && method === "GET") {
        const archived = query.get("archived") === "true";
        const list = [...state.conversations.values()]
          .filter((each) => each.archived === archived)
          .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
        return json(list.map(summary));
      }
      const conversation = id ? state.conversations.get(id) : undefined;
      if (!conversation) return missing("Conversation not found");
      if (method === "DELETE") {
        state.conversations.delete(conversation.id);
        return empty();
      }
      if (method === "PATCH") {
        if ("archived" in body) conversation.archived = Boolean(body.archived);
        if ("project_id" in body) conversation.project_id = (body.project_id as string | null) ?? null;
        if (typeof body.title === "string") conversation.title = body.title;
        return json({ id: conversation.id, archived: conversation.archived, project_id: conversation.project_id });
      }
      return json({ id: conversation.id, title: conversation.title, messages: conversation.messages });
    }

    case "projects": {
      if (!id && method === "GET") {
        const archived = query.get("archived") === "true";
        return json([...state.projects.values()].filter((p) => p.archived === archived).map(projectBody));
      }
      if (method === "DELETE" && id) {
        for (const each of [...state.conversations.values()]) {
          if (each.project_id === id) state.conversations.delete(each.id);
        }
      }
      const response = collection(state.projects, method, id, body, (b) => {
        const newProject = freeId(DEMO_PROJECT_IDS, state.projects);
        return newProject === null
          ? null
          : { id: newProject, name: b.name, updated_at: now(), archived: false, chat_count: 0, instructions: null };
      });
      return response;
    }

    case "memories":
      return collection(state.memories, method, id, body, (b) => {
        const memory = newId("memory");
        return { id: memory, text: b.text, created_at: now() };
      });

    case "personalities":
      if (method === "PATCH" && body.active === true) {
        for (const each of state.personalities.values()) each.active = false;
      }
      return collection(state.personalities, method, id, body, (b) => ({
        id: newId("personality"),
        name: b.name,
        text: b.text,
        active: false,
        updated_at: now(),
      }));

    case "shortcuts":
      if (!id && method === "GET") return json({ shortcuts: [...state.shortcuts.values()] });
      if (method === "PUT" && id) {
        state.shortcuts.delete(id);
        state.shortcuts.set(String(body.keyword ?? id), { ...body });
        return json(body);
      }
      return collection(state.shortcuts, method, id, body, (b) => ({ ...b }));

    case "devices":
      if (more === "revoke") {
        const device = id ? state.devices.get(id) : undefined;
        if (!device || device.main) return json({ detail: "The main PC can't be revoked" }, 409);
        Object.assign(device, { revoked_at: now(), connected: false });
        return json(device);
      }
      if (method === "POST" && !id) {
        const device = newId("device");
        state.devices.set(device, {
          id: device,
          name: body.name,
          device_id: null,
          created_at: now(),
          last_seen_at: null,
          revoked_at: null,
          main: false,
          connected: false,
        });
        // Looks like a token, works nowhere.
        return json({ ...state.devices.get(device), token: "demo-token-not-real" }, 201);
      }
      return collection(state.devices, method, id, body, () => null);

    case "settings": {
      if (id === "mode") {
        if (method === "PUT") state.mode = body.mode === "full" ? "full" : "confirm";
        return json({ mode: state.mode });
      }
      const saved = id ? state.settings[id] : undefined;
      if (!saved) return missing();
      if (method === "PUT") {
        const { api_key, ...rest } = body;
        Object.assign(saved, rest, api_key ? { has_key: true } : {});
      }
      return json(saved);
    }

    case "voice":
      if (id === "state") {
        return json({ state: "idle", subtitle: "", muted: false, online: false, conversation_id: null });
      }
      if (id === "mics") return json({ mics: [] });
      if (id === "stop") return empty();
      return json({ detail: "The demo has no voice. On the real PC she talks back." }, 503);

    case "usage": {
      const total = (scale: number) => ({
        input_tokens: 1840 * scale,
        cached_tokens: 900 * scale,
        output_tokens: 310 * scale,
        cost_usd: 0.0021 * scale,
        unpriced_models: [],
      });
      return json({ today: total(1), month: total(23), all_time: total(61) });
    }

    case "character":
      if (!id) return json({ custom: false });
      if (id === "models" || id === "animations") return method === "GET" ? json([]) : json({ detail: "Uploads are off in the demo" }, 403);
      if (id === "active") return json({ custom: false });
      return missing("No own model; use the template");

    case "health":
      return json({ status: "ok" });

    default:
      return missing();
  }
}

let installed = false;

export function installFakeCore() {
  if (installed || typeof window === "undefined") return;
  installed = true;
  if (!load()) seed();
  const realFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const request = new Request(input, init);
    const url = new URL(request.url);
    if (url.origin !== window.location.origin || !url.pathname.startsWith("/api/")) {
      return realFetch(input, init);
    }
    let body: Record<string, unknown> = {};
    if (request.method !== "GET" && request.method !== "HEAD") {
      const text = await request.text();
      try {
        body = text ? JSON.parse(text) : {};
      } catch {
        body = {};
      }
    }
    // A short pause, so "thinking" shows like it does with a real server.
    await new Promise((resolve) => setTimeout(resolve, url.pathname.endsWith("/chat") ? 700 : 60));
    const response = await route(request.method, url.pathname.slice("/api".length), url.searchParams, body);
    if (request.method !== "GET") save();
    return response;
  };
}
