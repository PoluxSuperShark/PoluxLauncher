const usernameInput = document.getElementById("username");
const themeModeSelect = document.getElementById("themeMode");
const ramGbSelect = document.getElementById("ramGb");
const installBtn = document.getElementById("installBtn");
const playBtn = document.getElementById("playBtn");
const clearBtn = document.getElementById("clearBtn");
const statusNode = document.getElementById("status");
const consoleNode = document.getElementById("console");
const crashReportNode = document.getElementById("crashReport");
const changelogNode = document.getElementById("changelog");
const tabConsoleBtn = document.getElementById("tabConsole");
const tabLogsBtn = document.getElementById("tabLogs");
const tabChangelogBtn = document.getElementById("tabChangelog");
const updateNoticeNode = document.getElementById("updateNotice");
const updateNoticeTextNode = document.getElementById("updateNoticeText");
const updateBtn = document.getElementById("updateBtn");
const runState = document.getElementById("runState");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");

let busy = false;
let selectedRamGb = 4;
let activeTab = "console";
let releaseInfo = null;

function setActiveTab(tab) {
  if (tab === "logs" || tab === "changelog") {
    activeTab = tab;
  } else {
    activeTab = "console";
  }

  const isConsole = activeTab === "console";
  const isLogs = activeTab === "logs";
  const isChangelog = activeTab === "changelog";
  tabConsoleBtn.classList.toggle("active", isConsole);
  tabLogsBtn.classList.toggle("active", isLogs);
  tabChangelogBtn.classList.toggle("active", isChangelog);
  tabConsoleBtn.setAttribute("aria-selected", String(isConsole));
  tabLogsBtn.setAttribute("aria-selected", String(isLogs));
  tabChangelogBtn.setAttribute("aria-selected", String(isChangelog));

  consoleNode.classList.toggle("active", isConsole);
  crashReportNode.classList.toggle("active", isLogs);
  changelogNode.classList.toggle("active", isChangelog);
}

function normalizeRamGb(value) {
  const parsed = Number.parseInt(String(value), 10);
  if (Number.isNaN(parsed)) {
    return 4;
  }
  return Math.max(2, Math.min(16, parsed));
}

function appendLog(line) {
  const stamp = new Date().toLocaleTimeString();
  consoleNode.textContent += `[${stamp}] ${line}\n`;
  consoleNode.scrollTop = consoleNode.scrollHeight;
}

function setStatus(text, isError = false) {
  statusNode.textContent = text;
  statusNode.classList.toggle("error", isError);
}

function updateProgressFromStatus(text) {
  const match = String(text).match(/(\d+(?:\.\d+)?)%/);
  if (!match) {
    if (!busy) {
      progressFill.style.width = "0%";
      progressText.textContent = "0%";
    }
    return;
  }

  const value = Math.max(0, Math.min(100, Number(match[1])));
  progressFill.style.width = `${value}%`;
  progressText.textContent = `${value.toFixed(0)}%`;
}

function applySettings(settings) {
  const theme = settings?.theme === "tactical" ? "tactical" : "friendly";
  const ramGb = normalizeRamGb(settings?.ramGb);

  selectedRamGb = ramGb;
  themeModeSelect.value = theme;
  ramGbSelect.value = String(ramGb);
}

async function persistSettings(updates) {
  if (!window.launcherAPI?.updateSettings) {
    return;
  }

  try {
    const nextSettings = await window.launcherAPI.updateSettings(updates);
    applySettings(nextSettings);
  } catch (error) {
    appendLog(`ERROR: Could not save settings (${error.message}).`);
  }
}

async function loadInitialSettings() {
  if (!window.launcherAPI?.getSettings) {
    return;
  }

  try {
    const settings = await window.launcherAPI.getSettings();
    applySettings(settings);
    appendLog(`Settings loaded: theme=${settings.theme}, RAM=${settings.ramGb}G`);
  } catch (error) {
    appendLog(`ERROR: Could not load settings (${error.message}).`);
  }
}

function setBusy(nextBusy) {
  busy = Boolean(nextBusy);
  installBtn.disabled = busy;
  playBtn.disabled = busy;
  usernameInput.disabled = busy;
  themeModeSelect.disabled = busy;
  ramGbSelect.disabled = busy;

  if (busy) {
    runState.textContent = "Working";
    runState.classList.add("busy");
  } else {
    runState.textContent = "Idle";
    runState.classList.remove("busy");
  }
}

function formatPublishedDate(isoText) {
  if (!isoText) {
    return "";
  }

  const date = new Date(isoText);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function renderReleaseInfo(info) {
  releaseInfo = info || null;
  if (!info) {
    changelogNode.textContent = "Changelog unavailable.";
    return;
  }

  const published = formatPublishedDate(info.publishedAt);
  const headerLines = [
    `Current version: ${info.currentVersion || "unknown"}`,
    `Latest release: ${info.latestVersion || "unknown"}`,
    info.releaseName ? `Title: ${info.releaseName}` : "",
    published ? `Published: ${published}` : "",
    info.releaseUrl ? `Link: ${info.releaseUrl}` : "",
    "",
    "=== CHANGELOG ===",
    info.body || "No changelog available.",
  ].filter(Boolean);

  changelogNode.textContent = headerLines.join("\n");

  if (info.error) {
    appendLog(`UPDATE ERROR: ${info.error}`);
  }

  if (info.updateAvailable) {
    updateNoticeTextNode.textContent = `Update available: ${info.latestVersion}`;
    updateNoticeNode.classList.remove("hidden");
    tabChangelogBtn.textContent = "Changelog *";
    appendLog(`Update detected: ${info.latestVersion} (current ${info.currentVersion}).`);
    setStatus("Launcher update available.");
  } else {
    updateNoticeNode.classList.add("hidden");
    tabChangelogBtn.textContent = "Changelog";
  }
}

async function loadReleaseInfo() {
  if (!window.launcherAPI?.getReleaseInfo) {
    return;
  }

  try {
    const info = await window.launcherAPI.getReleaseInfo();
    renderReleaseInfo(info);
  } catch (error) {
    appendLog(`UPDATE ERROR: ${error.message}`);
    changelogNode.textContent = "Failed to load GitHub changelog.";
  }
}

if (!window.launcherAPI) {
  setStatus("Error: Electron API unavailable.", true);
  appendLog("ERROR: Electron API unavailable.");
} else {
  window.launcherAPI.onLog((line) => appendLog(line));
  window.launcherAPI.onStatus((text) => {
    setStatus(text, false);
    updateProgressFromStatus(text);
  });
  window.launcherAPI.onError((text) => {
    appendLog(`ERROR: ${text}`);
    setStatus(text, true);
  });
  window.launcherAPI.onCrashReport((report) => {
    crashReportNode.textContent += `${report || ""}\n`;
    crashReportNode.scrollTop = crashReportNode.scrollHeight;
    setActiveTab("logs");
    appendLog("Crash report available in Logs tab.");
    setStatus("Crash report available.", true);
  });
  window.launcherAPI.onBusy((value) => {
    setBusy(value);
    if (!value) {
      progressFill.style.width = "100%";
      progressText.textContent = "Done";
      setTimeout(() => {
        progressFill.style.width = "0%";
        progressText.textContent = "0%";
      }, 1200);
    }
  });
}

themeModeSelect.addEventListener("change", async () => {
  const nextTheme = themeModeSelect.value === "tactical" ? "tactical" : "friendly";
  appendLog(`Switching theme to ${nextTheme}...`);
  await persistSettings({ theme: nextTheme });
});

ramGbSelect.addEventListener("change", async () => {
  selectedRamGb = normalizeRamGb(ramGbSelect.value);
  appendLog(`Allocated RAM set to ${selectedRamGb}G.`);
  await persistSettings({ ramGb: selectedRamGb });
});

installBtn.addEventListener("click", () => {
  if (busy || !window.launcherAPI) {
    return;
  }

  appendLog("Starting installation...");
  setStatus("Installing Forge and mods...");
  progressFill.style.width = "0%";
  progressText.textContent = "0%";
  window.launcherAPI.startInstall();
});

playBtn.addEventListener("click", () => {
  if (busy || !window.launcherAPI) {
    return;
  }

  const username = (usernameInput.value || "").trim() || "Player";
  crashReportNode.textContent = "";
  appendLog(`Starting game for ${username} with ${selectedRamGb}G...`);
  setStatus("Launching Minecraft...");
  window.launcherAPI.startLaunch(username, selectedRamGb);
});

clearBtn.addEventListener("click", () => {
  consoleNode.textContent = "";
});

tabConsoleBtn.addEventListener("click", () => setActiveTab("console"));
tabLogsBtn.addEventListener("click", () => setActiveTab("logs"));
tabChangelogBtn.addEventListener("click", () => setActiveTab("changelog"));
updateBtn.addEventListener("click", async () => {
  const url = releaseInfo?.releaseUrl;
  if (!url || !window.launcherAPI?.openExternal) {
    return;
  }

  const ok = await window.launcherAPI.openExternal(url);
  if (!ok) {
    appendLog("ERROR: Could not open release page.");
  }
});

appendLog("Interface ready.");
setBusy(false);
setActiveTab("console");
loadInitialSettings();
loadReleaseInfo();
