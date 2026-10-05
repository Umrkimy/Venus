// How often pages ask Core for changes made elsewhere (a voice turn on the PC).
// Only while the tab is visible: React Query pauses polling in background tabs.
export const POLL_MS = 1500;

// The orb follows the PC's voice loop closer, and its asking tells Core this tab is watching.
export const VOICE_POLL_MS = 400;
