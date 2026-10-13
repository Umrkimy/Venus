// npm run build:demo: the portfolio demo as plain files in out/ (Windows and Linux alike).
import { spawnSync } from "node:child_process";

const result = spawnSync("npx", ["next", "build"], {
  stdio: "inherit",
  shell: process.platform === "win32",
  env: { ...process.env, NEXT_PUBLIC_VENUS_DEMO: "1" },
});
process.exit(result.status ?? 1);
