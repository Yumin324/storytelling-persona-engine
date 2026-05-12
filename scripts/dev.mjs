import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const backendDir = path.join(rootDir, "backend");
const frontendDir = path.join(rootDir, "frontend");
const isWindows = process.platform === "win32";

const venvPython = path.join(backendDir, ".venv", isWindows ? "Scripts/python.exe" : "bin/python");
const pythonCommand = existsSync(venvPython) ? venvPython : isWindows ? "python" : "python3";

const processes = [];
let shuttingDown = false;

function prefixOutput(name, stream) {
  let pending = "";

  stream.on("data", (chunk) => {
    pending += chunk.toString();
    const lines = pending.split(/\r?\n/);
    pending = lines.pop() ?? "";

    for (const line of lines) {
      if (line.length > 0) {
        console.log(`[${name}] ${line}`);
      }
    }
  });

  stream.on("end", () => {
    if (pending.length > 0) {
      console.log(`[${name}] ${pending}`);
    }
  });
}

function start(name, command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    env: process.env,
    stdio: ["inherit", "pipe", "pipe"],
  });

  processes.push({ name, child });
  prefixOutput(name, child.stdout);
  prefixOutput(name, child.stderr);

  child.on("error", (error) => {
    console.error(`[${name}] Failed to start: ${error.message}`);
    shutdown(1);
  });

  child.on("exit", (code, signal) => {
    if (shuttingDown) {
      return;
    }

    const reason = signal ? `signal ${signal}` : `code ${code ?? 0}`;
    console.error(`[${name}] exited with ${reason}`);
    shutdown(code ?? 1);
  });
}

function shutdown(code = 0) {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;
  for (const { child } of processes) {
    if (!child.killed) {
      child.kill();
    }
  }

  setTimeout(() => process.exit(code), 100);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

start(
  "backend",
  pythonCommand,
  ["-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
  backendDir,
);

if (isWindows) {
  start(
    "frontend",
    process.env.ComSpec || "cmd.exe",
    ["/d", "/s", "/c", "npm run dev -- --host 127.0.0.1"],
    frontendDir,
  );
} else {
  start("frontend", "npm", ["run", "dev", "--", "--host", "127.0.0.1"], frontendDir);
}
