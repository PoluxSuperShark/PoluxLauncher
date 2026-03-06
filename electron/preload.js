const { contextBridge, ipcRenderer } = require("electron");

function subscribe(channel, callback) {
  const listener = (_event, payload) => callback(payload);
  ipcRenderer.on(channel, listener);
  return () => ipcRenderer.removeListener(channel, listener);
}

contextBridge.exposeInMainWorld("launcherAPI", {
  startInstall: () => ipcRenderer.send("launcher:start", { action: "install" }),
  startLaunch: (username, ramGb, accountMode) =>
    ipcRenderer.send("launcher:start", { action: "launch", username, ramGb, accountMode }),
  getSettings: () => ipcRenderer.invoke("launcher:get-settings"),
  authStatus: () => ipcRenderer.invoke("launcher:auth-status"),
  authStart: () => ipcRenderer.invoke("launcher:auth-start"),
  authComplete: (redirectUrl) => ipcRenderer.invoke("launcher:auth-complete", { redirectUrl }),
  authLogout: () => ipcRenderer.invoke("launcher:auth-logout"),
  getReleaseInfo: () => ipcRenderer.invoke("launcher:get-release-info"),
  openExternal: (url) => ipcRenderer.invoke("launcher:open-external", url),
  updateSettings: (updates) => ipcRenderer.invoke("launcher:update-settings", updates),
  onLog: (callback) => subscribe("launcher:log", callback),
  onStatus: (callback) => subscribe("launcher:status", callback),
  onError: (callback) => subscribe("launcher:error", callback),
  onCrashReport: (callback) => subscribe("launcher:crash-report", callback),
  onBusy: (callback) => subscribe("launcher:busy", callback),
});
