const { app, BrowserWindow, ipcMain, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const https = require("https");
const path = require("path");

const ROOT_DIR = path.resolve(__dirname, "..");
const BACKEND_SCRIPT = path.join(ROOT_DIR, "launcher_cli.py");
const PACKAGED_BACKEND = path.join(process.resourcesPath, "backend", "launcher_cli_backend.exe");

const MIN_RAM_GB = 2;
const MAX_RAM_GB = 16;
const DEFAULT_RAM_GB = 4;

const THEMES = {
  tactical: "index.html",
  friendly: "friendly.html",
};
const GITHUB_REPO = "PoluxSuperShark/PoluxLauncher";
const LATEST_RELEASE_API = `https://api.github.com/repos/${GITHUB_REPO}/releases/latest`;

let activeProcess = null;
let ipcRegistered = false;
let releaseInfoCache = null;
let launcherSettings = {
  theme: "tactical",
  ramGb: DEFAULT_RAM_GB,
  accountMode: "offline",
};

function parseComparableVersion(versionText) {
  const normalized = String(versionText || "")
    .trim()
    .replace(/^v/i, "")
    .split("-")[0];
  const rawParts = normalized.split(".");
  const numbers = rawParts.map((part) => Number.parseInt(part, 10));
  if (!numbers.length || numbers.some((part) => Number.isNaN(part))) {
    return null;
  }
  return numbers;
}

function compareVersions(left, right) {
  const a = parseComparableVersion(left);
  const b = parseComparableVersion(right);
  if (!a || !b) {
    return 0;
  }

  const maxLen = Math.max(a.length, b.length);
  for (let index = 0; index < maxLen; index += 1) {
    const av = a[index] ?? 0;
    const bv = b[index] ?? 0;
    if (av > bv) {
      return 1;
    }
    if (av < bv) {
      return -1;
    }
  }
  return 0;
}

function requestJson(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      {
        headers: {
          Accept: "application/vnd.github+json",
          "User-Agent": "PoluxLauncher",
        },
      },
      (res) => {
        const chunks = [];
        res.setEncoding("utf8");
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          const body = chunks.join("");

          if (res.statusCode && res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
            requestJson(res.headers.location).then(resolve).catch(reject);
            return;
          }

          if (res.statusCode !== 200) {
            reject(new Error(`GitHub API HTTP ${res.statusCode || 0}`));
            return;
          }

          try {
            resolve(JSON.parse(body));
          } catch (error) {
            reject(new Error(`JSON invalide: ${error.message}`));
          }
        });
      },
    );

    req.setTimeout(10000, () => req.destroy(new Error("Timeout GitHub API")));
    req.on("error", reject);
  });
}

async function buildReleaseInfo() {
  const currentVersion = app.getVersion();
  const baseInfo = {
    currentVersion,
    latestVersion: currentVersion,
    updateAvailable: false,
    releaseName: "",
    releaseUrl: `https://github.com/${GITHUB_REPO}/releases`,
    publishedAt: "",
    body: "Aucun changelog disponible.",
    error: "",
  };

  try {
    const latest = await requestJson(LATEST_RELEASE_API);
    const latestVersion = String(latest?.tag_name || latest?.name || "").trim() || currentVersion;
    const updateAvailable = compareVersions(latestVersion, currentVersion) > 0;

    return {
      ...baseInfo,
      latestVersion,
      updateAvailable,
      releaseName: String(latest?.name || latestVersion || "").trim(),
      releaseUrl: String(latest?.html_url || baseInfo.releaseUrl),
      publishedAt: String(latest?.published_at || ""),
      body: String(latest?.body || "Aucun changelog disponible."),
    };
  } catch (error) {
    return {
      ...baseInfo,
      error: `Impossible de verifier les mises a jour: ${error.message}`,
    };
  }
}

function normalizeTheme(theme, fallback = "tactical") {
  return Object.prototype.hasOwnProperty.call(THEMES, theme) ? theme : fallback;
}

function normalizeRamGb(ramGb) {
  const parsed = Number.parseInt(String(ramGb), 10);
  if (Number.isNaN(parsed)) {
    return DEFAULT_RAM_GB;
  }
  return Math.max(MIN_RAM_GB, Math.min(MAX_RAM_GB, parsed));
}

function normalizeAccountMode(accountMode) {
  return accountMode === "microsoft" ? "microsoft" : "offline";
}

function getSettingsPath() {
  return path.join(app.getPath("userData"), "launcher-settings.json");
}

function loadSettings(defaultTheme) {
  const normalizedTheme = normalizeTheme(defaultTheme, "tactical");
  const defaults = {
    theme: normalizedTheme,
    ramGb: DEFAULT_RAM_GB,
    accountMode: "offline",
  };

  try {
    const filePath = getSettingsPath();
    if (!fs.existsSync(filePath)) {
      return defaults;
    }

    const raw = fs.readFileSync(filePath, "utf8");
    const parsed = JSON.parse(raw);

    return {
      theme: normalizeTheme(parsed?.theme, defaults.theme),
      ramGb: normalizeRamGb(parsed?.ramGb),
      accountMode: normalizeAccountMode(parsed?.accountMode),
    };
  } catch {
    return defaults;
  }
}

function saveSettings(settings) {
  try {
    const filePath = getSettingsPath();
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, JSON.stringify(settings, null, 2), "utf8");
  } catch {
    // Ignore write failures and keep app running.
  }
}

function getUiFileForTheme(theme) {
  return THEMES[normalizeTheme(theme, launcherSettings.theme)] || THEMES.tactical;
}

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

  if (text.startsWith("[CRASH] ")) {
    sender.send("launcher:crash-report", text.slice(8));
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

function startBackend(sender, action, username, ramGb, accountMode) {
  const runtime = resolveBackendRuntime();

  if (app.isPackaged && !fs.existsSync(runtime.command)) {
    sender.send("launcher:error", "Backend executable introuvable dans le package.");
    return null;
  }

  const args = [...runtime.argsPrefix, action];
  if (action === "launch") {
    args.push("--username", (username || "Player").trim() || "Player");
    args.push("--ram-gb", String(normalizeRamGb(ramGb)));
    args.push("--account-mode", normalizeAccountMode(accountMode));
  }

  return spawn(runtime.command, args, {
    cwd: runtime.cwd,
    windowsHide: true,
  });
}

function parseBackendOutput(buffer) {
  const lines = String(buffer || "").split(/\r?\n/);
  const result = {
    data: null,
    logs: [],
    errors: [],
    statuses: [],
  };

  for (const rawLine of lines) {
    const line = String(rawLine || "").trim();
    if (!line) {
      continue;
    }
    if (line.startsWith("[DATA] ")) {
      const payload = line.slice(7);
      try {
        result.data = JSON.parse(payload);
      } catch {
        result.errors.push(`JSON invalide: ${payload}`);
      }
      continue;
    }
    if (line.startsWith("[ERROR] ")) {
      result.errors.push(line.slice(8));
      continue;
    }
    if (line.startsWith("[STATUS] ")) {
      result.statuses.push(line.slice(9));
      continue;
    }
    if (line.startsWith("[LOG] ")) {
      result.logs.push(line.slice(6));
      continue;
    }
    result.logs.push(line);
  }

  return result;
}

function runBackendCommand(args) {
  const runtime = resolveBackendRuntime();

  return new Promise((resolve, reject) => {
    if (app.isPackaged && !fs.existsSync(runtime.command)) {
      reject(new Error("Backend executable introuvable dans le package."));
      return;
    }

    const child = spawn(runtime.command, [...runtime.argsPrefix, ...args], {
      cwd: runtime.cwd,
      windowsHide: true,
    });

    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");

    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });

    child.on("error", (error) => {
      reject(new Error(`Impossible de lancer le backend: ${error.message}`));
    });

    child.on("close", (code) => {
      const parsed = parseBackendOutput(`${stdout}\n${stderr}`);
      if (code !== 0) {
        const message = parsed.errors[0] || `Commande backend echouee (code ${code}).`;
        reject(new Error(message));
        return;
      }
      resolve(parsed);
    });
  });
}

function registerIpcOnce() {
  if (ipcRegistered) {
    return;
  }

  ipcMain.handle("launcher:get-settings", () => ({ ...launcherSettings }));
  ipcMain.handle("launcher:auth-status", async () => {
    const result = await runBackendCommand(["auth-status"]);
    return result.data || { connected: false, provider: "offline", name: "", id: "" };
  });
  ipcMain.handle("launcher:auth-start", async () => {
    const result = await runBackendCommand(["auth-start"]);
    if (!result.data?.login_url) {
      throw new Error("Aucune URL Microsoft retournee par le backend.");
    }
    return result.data;
  });
  ipcMain.handle("launcher:auth-complete", async (_event, payload) => {
    const redirectUrl = String(payload?.redirectUrl || "").trim();
    if (!redirectUrl) {
      throw new Error("redirectUrl manquant.");
    }
    const result = await runBackendCommand(["auth-complete", "--redirect-url", redirectUrl]);
    return result.data || { connected: false, provider: "offline", name: "", id: "" };
  });
  ipcMain.handle("launcher:auth-logout", async () => {
    const result = await runBackendCommand(["auth-logout"]);
    return result.data || { connected: false, provider: "offline", name: "", id: "" };
  });
  ipcMain.handle("launcher:get-release-info", async () => {
    if (!releaseInfoCache) {
      releaseInfoCache = await buildReleaseInfo();
    }
    return releaseInfoCache;
  });
  ipcMain.handle("launcher:open-external", async (_event, url) => {
    if (typeof url !== "string" || !url.trim()) {
      return false;
    }
    try {
      await shell.openExternal(url);
      return true;
    } catch {
      return false;
    }
  });

  ipcMain.handle("launcher:update-settings", async (event, updates) => {
    const previousTheme = launcherSettings.theme;

    const theme = Object.prototype.hasOwnProperty.call(updates || {}, "theme")
      ? normalizeTheme(updates.theme, launcherSettings.theme)
      : launcherSettings.theme;

    const ramGb = Object.prototype.hasOwnProperty.call(updates || {}, "ramGb")
      ? normalizeRamGb(updates.ramGb)
      : launcherSettings.ramGb;
    const accountMode = Object.prototype.hasOwnProperty.call(updates || {}, "accountMode")
      ? normalizeAccountMode(updates.accountMode)
      : launcherSettings.accountMode;

    launcherSettings = { theme, ramGb, accountMode };
    saveSettings(launcherSettings);

    if (theme !== previousTheme) {
      const window = BrowserWindow.fromWebContents(event.sender);
      if (window) {
        await window.loadFile(path.join(__dirname, getUiFileForTheme(theme)));
      }
    }

    return { ...launcherSettings };
  });

  ipcMain.on("launcher:start", (event, payload) => {
    if (activeProcess) {
      event.sender.send("launcher:status", "Une operation est deja en cours.");
      return;
    }

    const action = payload?.action;
    const username = payload?.username || "Player";
    const ramGb = normalizeRamGb(payload?.ramGb ?? launcherSettings.ramGb);
    const accountMode = normalizeAccountMode(payload?.accountMode ?? launcherSettings.accountMode);

    if (!["install", "launch"].includes(action)) {
      event.sender.send("launcher:error", `Action invalide: ${String(action)}`);
      return;
    }

    launcherSettings = {
      ...launcherSettings,
      ramGb,
      accountMode,
    };
    saveSettings(launcherSettings);

    activeProcess = startBackend(event.sender, action, username, ramGb, accountMode);
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
  const defaultTheme = normalizeTheme(
    options?.defaultTheme || (options?.uiFile === "friendly.html" ? "friendly" : "tactical"),
    "tactical",
  );

  const settings = {
    width: options?.width || 1200,
    height: options?.height || 780,
    minWidth: options?.minWidth || 980,
    minHeight: options?.minHeight || 620,
    title: options?.title || "PoluxLauncher",
  };

  registerIpcOnce();

  function createWindow() {
    const theme = launcherSettings.theme;
    const backgroundColor = theme === "friendly" ? "#e8eef9" : "#0f0c29";

    const window = new BrowserWindow({
      width: settings.width,
      height: settings.height,
      minWidth: settings.minWidth,
      minHeight: settings.minHeight,
      title: settings.title,
      backgroundColor,
      icon: path.join(ROOT_DIR, "icon.ico"),
      webPreferences: {
        preload: path.join(__dirname, "preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
      },
    });

    window.removeMenu();
    window.loadFile(path.join(__dirname, getUiFileForTheme(theme)));
  }

  app.whenReady().then(() => {
    launcherSettings = loadSettings(defaultTheme);
    saveSettings(launcherSettings);
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
