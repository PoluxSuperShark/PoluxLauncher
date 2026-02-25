const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT_DIR = path.resolve(__dirname, "..");
const BACKEND_SCRIPT = path.join(ROOT_DIR, "launcher_cli.py");
const PACKAGED_BACKEND = path.join(process.resourcesPath, "backend", "launcher_cli_backend.exe");

let activeProcess = null;
let ipcRegistered = false;

function resolveBackendRuntime() {
  if (app.isPackaged) {
    return {
      command: PACKAGED_BACKEND,
      argsPrefix: [],
      cwd: process.resourcesPath,
    };
  }

  return {
    command: process.env.POLUX_PYTHON || "python",
    argsPrefix: [BACKEND_SCRIPT],
    cwd: ROOT_DIR,
  };
}

function emitLine(sender, line) {
  const text = String(line || "").trim();
  if (!text) {
    return;
  }

  if (text.startsWith("[STATUS] ")) {
    sender.send("launcher:status", text.slice(9));
    return;
  }

  if (text.startsWith("[ERROR] ")) {
    sender.send("launcher:error", text.slice(8));
    return;
  }

  if (text.startsWith("[LOG] ")) {
    sender.send("launcher:log", text.slice(6));
    return;
  }

  sender.send("launcher:log", text);
}

function pipeStream(sender, stream) {
  let buffer = "";

  stream.setEncoding("utf8");
  stream.on("data", (chunk) => {
    buffer += chunk;
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() || "";
    lines.forEach((line) => emitLine(sender, line));
  });

  stream.on("end", () => {
    if (buffer.trim()) {
      emitLine(sender, buffer);
    }
  });
}

function startBackend(sender, action, username) {
  const runtime = resolveBackendRuntime();

  if (app.isPackaged && !fs.existsSync(runtime.command)) {
    sender.send("launcher:error", "Backend executable introuvable dans le package.");
    return null;
  }

  const args = [...runtime.argsPrefix, action];
  if (action === "launch") {
    args.push("--username", (username || "Player").trim() || "Player");
  }

  return spawn(runtime.command, args, {
    cwd: runtime.cwd,
    windowsHide: true,
  });
}

function registerIpcOnce() {
  if (ipcRegistered) {
    return;
  }

  ipcMain.on("launcher:start", (event, payload) => {
    if (activeProcess) {
      event.sender.send("launcher:status", "Une operation est deja en cours.");
      return;
    }

    const action = payload?.action;
    const username = payload?.username || "Player";

    if (!["install", "launch"].includes(action)) {
      event.sender.send("launcher:error", `Action invalide: ${String(action)}`);
      return;
    }

    activeProcess = startBackend(event.sender, action, username);
    if (!activeProcess) {
      return;
    }

    event.sender.send("launcher:busy", true);
    event.sender.send("launcher:status", action === "install" ? "Installation en cours..." : "Lancement en cours...");

    pipeStream(event.sender, activeProcess.stdout);
    pipeStream(event.sender, activeProcess.stderr);

    activeProcess.on("error", (error) => {
      event.sender.send("launcher:error", `Impossible de lancer le backend: ${error.message}`);
    });

    activeProcess.on("close", (code) => {
      event.sender.send("launcher:busy", false);
      if (code !== 0) {
        event.sender.send("launcher:error", `Operation echouee (code ${code}).`);
      }
      activeProcess = null;
    });
  });

  ipcRegistered = true;
}

function bootstrapLauncher(options) {
  const settings = {
    width: options?.width || 1200,
    height: options?.height || 780,
    minWidth: options?.minWidth || 980,
    minHeight: options?.minHeight || 620,
    title: options?.title || "PoluxLauncher",
    backgroundColor: options?.backgroundColor || "#0f0c29",
    uiFile: options?.uiFile || "index.html",
  };

  registerIpcOnce();

  function createWindow() {
    const window = new BrowserWindow({
      width: settings.width,
      height: settings.height,
      minWidth: settings.minWidth,
      minHeight: settings.minHeight,
      title: settings.title,
      backgroundColor: settings.backgroundColor,
      icon: path.join(ROOT_DIR, "icon.ico"),
      webPreferences: {
        preload: path.join(__dirname, "preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    window.removeMenu();
    window.loadFile(path.join(__dirname, settings.uiFile));
  }

  app.whenReady().then(() => {
    createWindow();

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
      }
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}

module.exports = { bootstrapLauncher };
