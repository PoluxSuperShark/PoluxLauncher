const { contextBridge, ipcRenderer } = require("electron");

function subscribe(channel, callback) {
  const listener = (_event, payload) => callback(payload);
  ipcRenderer.on(channel, listener);
  return () => ipcRenderer.removeListener(channel, listener);
}

contextBridge.exposeInMainWorld("launcherAPI", {
  startInstall: () => ipcRenderer.send("launcher:start", { action: "install" }),
  startLaunch: (username) => ipcRenderer.send("launcher:start", { action: "launch", username }),
  onLog: (callback) => subscribe("launcher:log", callback),
  onStatus: (callback) => subscribe("launcher:status", callback),
  onError: (callback) => subscribe("launcher:error", callback),
  onBusy: (callback) => subscribe("launcher:busy", callback),
});
