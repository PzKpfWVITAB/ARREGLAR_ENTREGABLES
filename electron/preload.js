const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  selectDirectory: () => ipcRenderer.invoke("dialog:select-directory"),
  selectFile: () => ipcRenderer.invoke("dialog:select-file"),
  testDirectory: (path) => ipcRenderer.invoke("backend:test-directory", path),
  startAnalysis: (params) => ipcRenderer.invoke("backend:start-analysis", params),
  cancelAnalysis: () => ipcRenderer.invoke("backend:cancel-analysis"),
  
  openFile: (filePath) => ipcRenderer.invoke("system:open-file", filePath),
  showInFolder: (filePath) => ipcRenderer.invoke("system:show-in-folder", filePath),
  copyToClipboard: (text) => ipcRenderer.invoke("system:copy-clipboard", text),

  // Eventos reactivos desde Python hacia la UI
  onProgress: (callback) => ipcRenderer.on("py:progress", (event, data) => callback(data)),
  onItemDone: (callback) => ipcRenderer.on("py:item-done", (event, data) => callback(data)),
  onStatus: (callback) => ipcRenderer.on("py:status", (event, data) => callback(data)),
  onCoverReady: (callback) => ipcRenderer.on("py:cover-ready", (event, data) => callback(data)),
  onFinished: (callback) => ipcRenderer.on("py:finished", (event, data) => callback(data)),
  onError: (callback) => ipcRenderer.on("py:error", (event, data) => callback(data)),
  removeListeners: () => {
    ipcRenderer.removeAllListeners("py:progress");
    ipcRenderer.removeAllListeners("py:item-done");
    ipcRenderer.removeAllListeners("py:status");
    ipcRenderer.removeAllListeners("py:cover-ready");
    ipcRenderer.removeAllListeners("py:finished");
    ipcRenderer.removeAllListeners("py:error");
  }
});
