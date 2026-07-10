import { spawn } from "node:child_process";
import { createConnection } from "node:net";
import { forwardSignals, pythonPath, readEnv, root } from "./dev-env.mjs";

const host = readEnv("BACKEND_HOST", "localhost");
const port = readEnv("BACKEND_PORT", "8000");
const postgresHost = readEnv("POSTGRES_HOST", "localhost");
const postgresPort = Number(readEnv("POSTGRES_PORT", "5432"));

function checkTcp(checkHost, checkPort, timeoutMs = 1500) {
  return new Promise((resolve) => {
    const socket = createConnection({ host: checkHost, port: checkPort });
    const timer = setTimeout(() => {
      socket.destroy();
      resolve(false);
    }, timeoutMs);

    socket.on("connect", () => {
      clearTimeout(timer);
      socket.destroy();
      resolve(true);
    });
    socket.on("error", () => {
      clearTimeout(timer);
      socket.destroy();
      resolve(false);
    });
  });
}

const dbUp = await checkTcp(postgresHost, postgresPort);
if (!dbUp) {
  console.warn("");
  console.warn(`[api] PostgreSQL is NOT running at ${postgresHost}:${postgresPort}`);
  console.warn("[api] Start it yourself, then refresh the app:");
  console.warn("[api]   npm run db:up");
  console.warn("[api]   or: docker compose up -d db redis");
  console.warn("");
} else {
  console.log(`[api] PostgreSQL reachable at ${postgresHost}:${postgresPort}`);
}

const child = spawn(
  pythonPath(),
  ["-m", "uvicorn", "main:app", "--app-dir", "app", "--host", host, "--port", port, "--reload"],
  {
    cwd: root,
    stdio: "inherit",
    env: process.env,
  },
);

forwardSignals(child);
