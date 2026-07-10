import { spawn } from "node:child_process";
import { createConnection } from "node:net";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function readEnv(name, fallback) {
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

function waitTcp(host, port, timeoutMs = 75000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const socket = createConnection({ host, port: Number(port) });
      socket.setTimeout(1500);
      socket.on("connect", () => {
        socket.destroy();
        resolve(true);
      });
      socket.on("timeout", () => {
        socket.destroy();
        if (Date.now() >= deadline) {
          reject(new Error(`Timed out waiting for ${host}:${port}`));
          return;
        }
        setTimeout(tryOnce, 1000);
      });
      socket.on("error", () => {
        socket.destroy();
        if (Date.now() >= deadline) {
          reject(new Error(`Timed out waiting for ${host}:${port}`));
          return;
        }
        setTimeout(tryOnce, 1000);
      });
    };
    tryOnce();
  });
}

function run(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: root,
      stdio: "inherit",
      shell: process.platform === "win32",
    });
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${command} ${args.join(" ")} exited with code ${code}`));
    });
  });
}

const host = readEnv("POSTGRES_HOST", "localhost");
const port = readEnv("POSTGRES_PORT", "5432");

async function main() {
  try {
    await waitTcp(host, port, 2000);
    console.log(`[db] PostgreSQL already reachable at ${host}:${port}`);
    return;
  } catch {
    // not up yet
  }

  console.log(`[db] Starting Docker db + redis...`);
  await run("docker", ["compose", "up", "-d", "db", "redis"]);
  await waitTcp(host, port, 90000);
  console.log(`[db] PostgreSQL is ready at ${host}:${port}`);
}

main().catch((err) => {
  console.error(`[db] ${err.message}`);
  console.error("[db] Make sure Docker Desktop is running, then retry: npm run db:up");
  process.exit(1);
});
