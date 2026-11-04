const { app, BrowserWindow, ipcMain, dialog, shell, clipboard } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

let mainWindow = null;
let pythonProcess = null;

function getPythonExecutable() {
  const rootDir = path.resolve(__dirname, "..");
  // Verificar si existe el entorno virtual portátil .venv
  const venvPython = path.join(rootDir, ".venv", "Scripts", "python.exe");
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }
  // Si no, recurrir al python del sistema
  return "python";
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1250,
    height: 850,
    minWidth: 1000,
    minHeight: 650,
    title: "Verificador de Carátulas en PDFs - Visión Artificial",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    },
    autoHideMenuBar: true,
    backgroundColor: "#0b1329"
  });

  mainWindow.loadFile(path.join(__dirname, "..", "ui", "index.html"));

  mainWindow.on("closed", () => {
    if (pythonProcess) {
      pythonProcess.kill();
      pythonProcess = null;
    }
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// IPC: Selección de Directorio de Red
ipcMain.handle("dialog:select-directory", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openDirectory"],
    title: "Seleccionar Carpeta de Red o Directorio de Trabajo"
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

// IPC: Selección de Archivo PDF Carátula
ipcMain.handle("dialog:select-file", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile"],
    filters: [{ name: "Archivos PDF", extensions: ["pdf"] }],
    title: "Seleccionar PDF de la Carátula de Referencia"
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

// IPC: Test rápido de Conectividad con la Ruta
ipcMain.handle("backend:test-directory", async (event, dirPath) => {
  return new Promise((resolve) => {
    const pythonExe = getPythonExecutable();
    const runnerScript = path.join(__dirname, "..", "backend_runner.py");
    const proc = spawn(pythonExe, ["-u", runnerScript, "--test-dir", dirPath]);

    let output = "";
    proc.stdout.on("data", (data) => {
      output += data.toString("utf-8");
    });

    proc.on("close", () => {
      try {
        const lines = output.trim().split("\n");
        for (const line of lines) {
          if (line.trim().startsWith("{")) {
            const parsed = JSON.parse(line.trim());
            if (parsed.type === "test_result") {
              return resolve(parsed);
            }
          }
        }
        resolve({ ok: false, message: "Respuesta no estructurada del proceso de prueba." });
      } catch (err) {
        resolve({ ok: false, message: `Error al verificar: ${err.message}` });
      }
    });

    proc.on("error", (err) => {
      resolve({ ok: false, message: `No se pudo ejecutar Python: ${err.message}` });
    });
  });
});

// IPC: Iniciar Análisis Masivo
ipcMain.handle("backend:start-analysis", async (event, params) => {
  if (pythonProcess) {
    return { ok: false, message: "Ya hay un proceso en ejecución." };
  }

  const { workDir, coverPath, recursive, maxPages } = params;
  const pythonExe = getPythonExecutable();
  const runnerScript = path.join(__dirname, "..", "backend_runner.py");

  const args = ["-u", runnerScript, "--dir", workDir, "--cover", coverPath, "--pages", String(maxPages || 2)];
  if (recursive) {
    args.push("--recursive");
  }

  pythonProcess = spawn(pythonExe, args, {
    cwd: path.resolve(__dirname, "..")
  });

  let buffer = "";

  pythonProcess.stdout.on("data", (data) => {
    buffer += data.toString("utf-8");
    const lines = buffer.split("\n");
    buffer = lines.pop(); // Mantener el último segmento incompleto

    for (const line of lines) {
      const clean = line.trim();
      if (!clean) continue;
      try {
        const msg = JSON.parse(clean);
        if (mainWindow && !mainWindow.isDestroyed()) {
          switch (msg.type) {
            case "progress":
              mainWindow.webContents.send("py:progress", msg);
              break;
            case "item_done":
              mainWindow.webContents.send("py:item-done", msg.item);
              break;
            case "status":
              mainWindow.webContents.send("py:status", msg.message);
              break;
            case "cover_ready":
              mainWindow.webContents.send("py:cover-ready", msg);
              break;
            case "finished":
              mainWindow.webContents.send("py:finished", msg);
              break;
            case "error":
              mainWindow.webContents.send("py:error", msg.message);
              break;
          }
        }
      } catch (e) {
        // Ignorar líneas no JSON (ej. advertencias o logs)
      }
    }
  });

  pythonProcess.stderr.on("data", (data) => {
    console.error("Python Stderr:", data.toString("utf-8"));
  });

  pythonProcess.on("close", (code) => {
    pythonProcess = null;
  });

  return { ok: true };
});

// IPC: Cancelar Proceso
ipcMain.handle("backend:cancel-analysis", () => {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
    return true;
  }
  return false;
});

// IPC: Acciones Rápidas del Sistema
ipcMain.handle("system:open-file", async (event, filePath) => {
  try {
    const error = await shell.openPath(filePath);
    return { ok: !error, error };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

ipcMain.handle("system:show-in-folder", (event, filePath) => {
  try {
    shell.showItemInFolder(filePath);
    return true;
  } catch (err) {
    return false;
  }
});

ipcMain.handle("system:copy-clipboard", (event, text) => {
  clipboard.writeText(text);
  return true;
});
