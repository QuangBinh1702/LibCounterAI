import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { forwardSignals, readEnv, root } from "./dev-env.mjs";

const host = readEnv("FRONTEND_HOST", "localhost");
const port = readEnv("FRONTEND_PORT", "5173");
const browserRoot = join(root, "surfaces", "browser");
const viteBin = join(browserRoot, "node_modules", "vite", "bin", "vite.js");

if (!existsSync(viteBin)) {
  throw new Error(
    "Vite is not installed under surfaces/browser. Run: npm --prefix surfaces/browser install",
  );
}

// Spawn Vite through node.exe directly. Spawning npm.cmd without a shell
// fails on Windows Node with spawn EINVAL.
const child = spawn(process.execPath, [viteBin, "--host", host, "--port", port], {
  cwd: browserRoot,
  stdio: "inherit",
  env: process.env,
});

// forwardSignals(child); // Bỏ để tránh chết chain
