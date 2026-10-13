// The portfolio demo (docs: README "Portfolio demo"): the real pages with a
// pretend Core in the browser. Set at build time by `npm run build:demo`.
export const DEMO = process.env.NEXT_PUBLIC_VENUS_DEMO === "1";

// A static site can only have pages made at build time, so the demo's chats
// and projects use these ids: the first ones are filled in, the rest are
// handed out as you start new ones.
export const DEMO_CHAT_IDS = Array.from({ length: 30 }, (_, i) => `demo-chat-${i + 1}`);
export const DEMO_PROJECT_IDS = Array.from({ length: 10 }, (_, i) => `demo-project-${i + 1}`);
