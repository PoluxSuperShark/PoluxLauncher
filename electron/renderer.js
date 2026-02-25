const usernameInput = document.getElementById("username");
const installBtn = document.getElementById("installBtn");
const playBtn = document.getElementById("playBtn");
const statusNode = document.getElementById("status");
const consoleNode = document.getElementById("console");
const runtimeText = document.getElementById("runtime-text");
const runtimeDot = document.getElementById("runtime-dot");

let busy = false;

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

function setBusy(nextBusy) {
  busy = Boolean(nextBusy);
  installBtn.disabled = busy;
  playBtn.disabled = busy;
  usernameInput.disabled = busy;
  syncRuntimeIndicator();
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
  window.launcherAPI.onBusy((value) => setBusy(value));
}

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
  appendLog(`Demarrage du jeu pour ${username}...`);
  setStatus("Lancement en cours...");
  window.launcherAPI.startLaunch(username);
});

syncRuntimeIndicator();
appendLog("Interface prete.");
