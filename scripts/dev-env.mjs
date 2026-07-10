import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const root = join(dirname(fileURLToPath(import.meta.url)), "..");

export function readEnv(name, fallback) {
  const envPath = join(root, ".env");
  if (!existsSync(envPath)) {
    return fallback;
  }

  const line = readFileSync(envPath, "utf8")
    .split(/\r?\n/)
    .map((value) => value.trim())
    .filter((value) => value && !value.startsWith("#"))
    .find((value) => value.startsWith(`${name}=`));

  if (!line) {
    return fallback;
  }

  let value = line.slice(name.length + 1).trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return value || fallback;
}

export function pythonPath() {
  const win = join(root, ".venv", "Scripts", "python.exe");
  const unix = join(root, ".venv", "bin", "python");
  if (existsSync(win)) {
    return win;
  }
  if (existsSync(unix)) {
    return unix;
  }
  throw new Error("Python venv not found. Run: npm run prepare:dev");
}

export function forwardSignals(child) {
  for (const signal of ["SIGINT", "SIGTERM"]) {
    process.on(signal, () => {
      if (!child.killed) {
        child.kill(signal);
      }
    });
  }

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
      return;
    }
    process.exit(code ?? 0);
  });
}
