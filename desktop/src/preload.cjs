const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopAPI", {
  retryConnection: () => ipcRenderer.invoke("connection:retry"),
});