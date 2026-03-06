const usernameInput = document.getElementById("username");
const themeModeSelect = document.getElementById("themeMode");
const ramGbSelect = document.getElementById("ramGb");
const installBtn = document.getElementById("installBtn");
const playBtn = document.getElementById("playBtn");
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
const runtimeText = document.getElementById("runtime-text");
const runtimeDot = document.getElementById("runtime-dot");

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

function syncRuntimeIndicator() {
  runtimeDot.classList.remove("online", "busy");

  if (busy) {
    runtimeDot.classList.add("busy");
    runtimeText.textContent = "Runtime: BUSY";
    return;
  }

  runtimeDot.classList.add("online");
  runtimeText.textContent = "Runtime: IDLE";
}

function applySettings(settings) {
  const theme = settings?.theme === "friendly" ? "friendly" : "tactical";
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
    appendLog(`ERREUR: Impossible d'enregistrer les preferences (${error.message}).`);
  }
}

async function loadInitialSettings() {
  if (!window.launcherAPI?.getSettings) {
    return;
  }

  try {
    const settings = await window.launcherAPI.getSettings();
    applySettings(settings);
    appendLog(`Parametres charges: theme=${settings.theme}, RAM=${settings.ramGb}G`);
  } catch (error) {
    appendLog(`ERREUR: Lecture des preferences impossible (${error.message}).`);
  }
}

function setBusy(nextBusy) {
  busy = Boolean(nextBusy);
  installBtn.disabled = busy;
  playBtn.disabled = busy;
  usernameInput.disabled = busy;
  themeModeSelect.disabled = busy;
  ramGbSelect.disabled = busy;
  syncRuntimeIndicator();
}

function formatPublishedDate(isoText) {
  if (!isoText) {
    return "";
  }

  const date = new Date(isoText);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toLocaleDateString("fr-BE", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function renderReleaseInfo(info) {
  releaseInfo = info || null;
  if (!info) {
    changelogNode.textContent = "Changelog indisponible.";
    return;
  }

  const published = formatPublishedDate(info.publishedAt);
  const headerLines = [
    `Version locale: ${info.currentVersion || "inconnue"}`,
    `Derniere release: ${info.latestVersion || "inconnue"}`,
    info.releaseName ? `Titre: ${info.releaseName}` : "",
    published ? `Publiee le: ${published}` : "",
    info.releaseUrl ? `Lien: ${info.releaseUrl}` : "",
    "",
    "=== CHANGELOG ===",
    info.body || "Aucun changelog disponible.",
  ].filter(Boolean);

  changelogNode.textContent = headerLines.join("\n");

  if (info.error) {
    appendLog(`ERREUR UPDATE: ${info.error}`);
  }

  if (info.updateAvailable) {
    updateNoticeTextNode.textContent = `Mise a jour dispo: ${info.latestVersion}`;
    updateNoticeNode.classList.remove("hidden");
    tabChangelogBtn.textContent = "Changelog *";
    appendLog(`Mise a jour detectee: ${info.latestVersion} (actuel ${info.currentVersion}).`);
    setStatus("Mise a jour du launcher disponible", false);
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
    appendLog(`ERREUR UPDATE: ${error.message}`);
    changelogNode.textContent = "Impossible de charger le changelog GitHub.";
  }
}

if (!window.launcherAPI) {
  setStatus("Erreur: API Electron indisponible.", true);
  appendLog("ERREUR: API Electron indisponible.");
} else {
  window.launcherAPI.onLog((line) => appendLog(line));
  window.launcherAPI.onStatus((text) => setStatus(text, false));
  window.launcherAPI.onError((text) => {
    appendLog(`ERREUR: ${text}`);
    setStatus(text, true);
  });
  window.launcherAPI.onCrashReport((report) => {
    crashReportNode.textContent += `${report || ""}\n`;
    crashReportNode.scrollTop = crashReportNode.scrollHeight;
    setActiveTab("logs");
    appendLog("Crash report disponible dans l'onglet Logs.");
    setStatus("Crash report disponible", true);
  });
  window.launcherAPI.onBusy((value) => setBusy(value));
}

themeModeSelect.addEventListener("change", async () => {
  const nextTheme = themeModeSelect.value === "friendly" ? "friendly" : "tactical";
  appendLog(`Changement du theme vers ${nextTheme}...`);
  await persistSettings({ theme: nextTheme });
});

ramGbSelect.addEventListener("change", async () => {
  selectedRamGb = normalizeRamGb(ramGbSelect.value);
  appendLog(`RAM allouee mise a ${selectedRamGb}G.`);
  await persistSettings({ ramGb: selectedRamGb });
});

installBtn.addEventListener("click", () => {
  if (busy || !window.launcherAPI) {
    return;
  }

  appendLog("Demarrage de l'installation...");
  setStatus("Installation en cours...");
  window.launcherAPI.startInstall();
});

playBtn.addEventListener("click", () => {
  if (busy || !window.launcherAPI) {
    return;
  }

  const username = (usernameInput.value || "").trim() || "Player";
  crashReportNode.textContent = "";
  appendLog(`Demarrage du jeu pour ${username} avec ${selectedRamGb}G...`);
  setStatus("Lancement en cours...");
  window.launcherAPI.startLaunch(username, selectedRamGb);
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
    appendLog("ERREUR: impossible d'ouvrir la page release.");
  }
});

syncRuntimeIndicator();
appendLog("Interface prete.");
setBusy(false);
setActiveTab("console");
loadInitialSettings();
loadReleaseInfo();
