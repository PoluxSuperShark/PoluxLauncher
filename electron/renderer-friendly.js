const usernameInput = document.getElementById("username");
const installBtn = document.getElementById("installBtn");
const playBtn = document.getElementById("playBtn");
const clearBtn = document.getElementById("clearBtn");
const statusNode = document.getElementById("status");
const consoleNode = document.getElementById("console");
const runState = document.getElementById("runState");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");

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

function setBusy(nextBusy) {
  busy = Boolean(nextBusy);
  installBtn.disabled = busy;
  playBtn.disabled = busy;
  usernameInput.disabled = busy;

  if (busy) {
    runState.textContent = "Working";
    runState.classList.add("busy");
  } else {
    runState.textContent = "Idle";
    runState.classList.remove("busy");
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
  appendLog(`Starting game for ${username}...`);
  setStatus("Launching Minecraft...");
  window.launcherAPI.startLaunch(username);
});

clearBtn.addEventListener("click", () => {
  consoleNode.textContent = "";
});

appendLog("Interface ready.");
setBusy(false);
