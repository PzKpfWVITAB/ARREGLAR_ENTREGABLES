// Lógica Frontend para Electron con soporte de Hardware al 90%
document.addEventListener("DOMContentLoaded", () => {
  // Elementos DOM de Hardware
  const hwCpuVal = document.getElementById("hwCpuVal");
  const hwCpuSub = document.getElementById("hwCpuSub");
  const hwRamVal = document.getElementById("hwRamVal");
  const hwRamSub = document.getElementById("hwRamSub");
  const hwGpuVal = document.getElementById("hwGpuVal");
  const hwGpuSub = document.getElementById("hwGpuSub");
  const hwGpuContainer = document.getElementById("hwGpuContainer");
  const badgeGpuInfo = document.getElementById("badgeGpuInfo");
  const badgeWorkersInfo = document.getElementById("badgeWorkersInfo");
  const resourceSlider = document.getElementById("resourceSlider");
  const sliderValDisplay = document.getElementById("sliderValDisplay");
  const workersCountDisplay = document.getElementById("workersCountDisplay");
  const chkGpuAccel = document.getElementById("chkGpuAccel");
  const btnRefreshHw = document.getElementById("btnRefreshHw");

  // Elementos DOM de Lote
  const workDirInput = document.getElementById("workDirInput");
  const coverPathInput = document.getElementById("coverPathInput");
  const btnBrowseDir = document.getElementById("btnBrowseDir");
  const btnBrowseCover = document.getElementById("btnBrowseCover");
  const btnTestConn = document.getElementById("btnTestConn");
  const btnStart = document.getElementById("btnStart");
  const btnCancel = document.getElementById("btnCancel");
  const chkRecursive = document.getElementById("chkRecursive");
  const selectPages = document.getElementById("selectPages");

  const dirFeedback = document.getElementById("dirFeedback");
  const coverFeedback = document.getElementById("coverFeedback");
  const systemStatus = document.getElementById("systemStatus");

  const progressSection = document.getElementById("progressSection");
  const progressBarFill = document.getElementById("progressBarFill");
  const progressStatusText = document.getElementById("progressStatusText");
  const progressCountText = document.getElementById("progressCountText");
  const currentFileName = document.getElementById("currentFileName");

  const statTotal = document.getElementById("statTotal");
  const statSinCaratula = document.getElementById("statSinCaratula");
  const statConCaratula = document.getElementById("statConCaratula");
  const statErrores = document.getElementById("statErrores");

  const tabCountAll = document.getElementById("tabCountAll");
  const tabCountSin = document.getElementById("tabCountSin");
  const tabCountCon = document.getElementById("tabCountCon");
  const tabCountErr = document.getElementById("tabCountErr");

  const tableBody = document.getElementById("tableBody");
  const searchInput = document.getElementById("searchInput");
  const btnExportCsv = document.getElementById("btnExportCsv");

  // Estado local
  let currentResults = [];
  let currentFilter = "all";
  let isAnalyzing = false;
  let detectedHw = null;
  let activeWorkers = 4;

  // 1. Detección Automática de Hardware (CPU, RAM, GPU NVIDIA)
  async function loadHardwareSpecs() {
    badgeGpuInfo.textContent = "🔍 Detectando...";
    try {
      const hw = await window.api.getHardwareInfo();
      if (!hw) {
        hwCpuVal.textContent = "Detectado estándar";
        hwRamVal.textContent = "Memoria estándar";
        hwGpuVal.textContent = "Modo CPU";
        return;
      }
      detectedHw = hw;

      // CPU
      const cpu = hw.cpu;
      hwCpuVal.textContent = `${cpu.logical_cores} Cores lógicos (${cpu.physical_cores} físicos)`;
      updateWorkersFromSlider();

      // RAM
      const ram = hw.ram;
      hwRamVal.textContent = `${ram.total_gb} GB (${ram.available_gb} GB Libres)`;
      hwRamSub.textContent = `Límite al 90%: ${ram.recommended_limit_gb} GB para buffer de visión`;

      // GPU
      const gpu = hw.gpu;
      if (gpu.detected) {
        const prim = gpu.primary;
        hwGpuVal.textContent = prim.name + (prim.vram_gb ? ` (${prim.vram_gb} GB VRAM)` : "");
        
        if (gpu.has_nvidia) {
          hwGpuContainer.className = "hw-item nvidia";
          hwGpuSub.textContent = "✓ Aceleración NVIDIA CUDA / Tensor Cores disponible";
          badgeGpuInfo.textContent = "🎮 NVIDIA Activa";
          badgeGpuInfo.style.borderColor = "var(--nvidia)";
          badgeGpuInfo.style.color = "#a3e635";
        } else if (gpu.opencl_acceleration) {
          hwGpuContainer.className = "hw-item highlight";
          hwGpuSub.textContent = "✓ Aceleración OpenCL de matriz gráfica activa";
          badgeGpuInfo.textContent = "⚡ GPU OpenCL";
        } else {
          hwGpuSub.textContent = "GPU detectada (renderizado estándar)";
          badgeGpuInfo.textContent = "GPU Detectada";
        }
      } else {
        hwGpuVal.textContent = "Gráficos Integrados";
        hwGpuSub.textContent = "Modo Multiproceso CPU de alto rendimiento";
        badgeGpuInfo.textContent = "CPU Multi-core";
      }

    } catch (err) {
      console.error("Error al cargar hardware:", err);
      badgeGpuInfo.textContent = "CPU Estándar";
    }
  }

  function updateWorkersFromSlider() {
    const percent = parseInt(resourceSlider.value, 10);
    sliderValDisplay.textContent = `${percent}%`;

    const totalCores = detectedHw?.cpu?.logical_cores || 4;
    activeWorkers = Math.max(1, Math.floor(totalCores * (percent / 100)));
    workersCountDisplay.textContent = activeWorkers;
    badgeWorkersInfo.textContent = `⚡ ${activeWorkers} Workers (${percent}%)`;
    hwCpuSub.textContent = `Asignación al ${percent}%: ${activeWorkers} workers paralelos`;
  }

  resourceSlider.addEventListener("input", updateWorkersFromSlider);
  btnRefreshHw.addEventListener("click", loadHardwareSpecs);

  // Iniciar detección de inmediato
  loadHardwareSpecs();

  // 2. Selección de Directorio de Red
  btnBrowseDir.addEventListener("click", async () => {
    const dir = await window.api.selectDirectory();
    if (dir) {
      workDirInput.value = dir;
      testDirectory(dir);
    }
  });

  // 3. Selección de Carátula Modelo
  btnBrowseCover.addEventListener("click", async () => {
    const file = await window.api.selectFile();
    if (file) {
      coverPathInput.value = file;
      coverFeedback.className = "field-feedback success";
      coverFeedback.textContent = "Carátula seleccionada: " + file.split(/[\/\\]/).pop();
    }
  });

  // 4. Probar Conexión con Ruta
  async function testDirectory(dir) {
    if (!dir) {
      dirFeedback.className = "field-feedback error";
      dirFeedback.textContent = "Por favor ingrese una ruta.";
      return;
    }
    dirFeedback.className = "field-feedback info";
    dirFeedback.textContent = "Verificando conectividad con la red...";
    const res = await window.api.testDirectory(dir);
    if (res.ok) {
      dirFeedback.className = "field-feedback success";
      dirFeedback.textContent = `✓ Conexión exitosa. Se encontraron ${res.count} archivos PDF.`;
    } else {
      dirFeedback.className = "field-feedback error";
      dirFeedback.textContent = `✗ ${res.message}`;
    }
  }

  btnTestConn.addEventListener("click", () => {
    testDirectory(workDirInput.value.trim());
  });

  // 5. Iniciar Análisis Masivo Acelerado
  btnStart.addEventListener("click", async () => {
    const workDir = workDirInput.value.trim();
    const coverPath = coverPathInput.value.trim();

    if (!workDir) {
      alert("Por favor indique el directorio de trabajo.");
      return;
    }
    if (!coverPath) {
      alert("Por favor seleccione el PDF de la carátula de referencia.");
      return;
    }

    // Reiniciar interfaz
    currentResults = [];
    renderTable();
    updateStats();

    isAnalyzing = true;
    btnStart.style.display = "none";
    btnCancel.style.display = "inline-flex";
    progressSection.style.display = "block";
    progressBarFill.style.width = "0%";
    progressStatusText.textContent = `Iniciando con ${activeWorkers} workers paralelos al ${resourceSlider.value}%...`;
    systemStatus.textContent = "Analizando...";
    systemStatus.style.color = "var(--primary)";

    const res = await window.api.startAnalysis({
      workDir,
      coverPath,
      recursive: chkRecursive.checked,
      maxPages: parseInt(selectPages.value, 10),
      workers: activeWorkers,
      useGpu: chkGpuAccel.checked
    });

    if (!res.ok) {
      alert(res.message);
      resetUI();
    }
  });

  // 6. Cancelar Análisis
  btnCancel.addEventListener("click", async () => {
    if (confirm("¿Desea cancelar el análisis en curso?")) {
      await window.api.cancelAnalysis();
      progressStatusText.textContent = "Cancelado por el usuario.";
      resetUI();
    }
  });

  function resetUI() {
    isAnalyzing = false;
    btnStart.style.display = "inline-flex";
    btnCancel.style.display = "none";
    systemStatus.textContent = "Listo";
    systemStatus.style.color = "var(--success)";
  }

  // 7. Escucha de Eventos Backend
  window.api.onStatus((msg) => {
    progressStatusText.textContent = msg;
  });

  window.api.onCoverReady((data) => {
    progressStatusText.textContent = `Carátula lista (${data.keypoints} rasgos extraídos). Procesando con ${activeWorkers} workers...`;
  });

  window.api.onProgress((data) => {
    progressBarFill.style.width = `${data.percent}%`;
    progressCountText.textContent = `${data.current} / ${data.total} (${data.percent}%)`;
    currentFileName.textContent = `Examinando: ${data.filename}`;
  });

  window.api.onItemDone((item) => {
    currentResults.push(item);
    updateStats();
    appendTableRow(item);
  });

  window.api.onFinished((data) => {
    resetUI();
    progressBarFill.style.width = "100%";
    progressStatusText.textContent = "¡Análisis Completado!";
    currentFileName.textContent = `Total: ${data.summary.total} | Con Carátula: ${data.summary.with_cover} | Sin Carátula: ${data.summary.without_cover}`;
  });

  window.api.onError((msg) => {
    alert("Error durante el proceso: " + msg);
    resetUI();
  });

  // 8. Actualización de Estadísticas
  function updateStats() {
    const total = currentResults.length;
    const sin = currentResults.filter(r => !r.has_cover && !r.error).length;
    const con = currentResults.filter(r => r.has_cover && !r.error).length;
    const err = currentResults.filter(r => r.error).length;

    statTotal.textContent = total;
    statSinCaratula.textContent = sin;
    statConCaratula.textContent = con;
    statErrores.textContent = err;

    tabCountAll.textContent = total;
    tabCountSin.textContent = sin;
    tabCountCon.textContent = con;
    tabCountErr.textContent = err;
  }

  // 9. Renderizado de Filas y Tabla
  function renderTable() {
    tableBody.innerHTML = "";
    const term = searchInput.value.toLowerCase().trim();

    const filtered = currentResults.filter(item => {
      let matchTab = true;
      if (currentFilter === "sin_caratula") matchTab = (!item.has_cover && !item.error);
      else if (currentFilter === "con_caratula") matchTab = (item.has_cover && !item.error);
      else if (currentFilter === "error") matchTab = Boolean(item.error);

      const matchSearch = term === "" || item.filename.toLowerCase().includes(term);
      return matchTab && matchSearch;
    });

    if (filtered.length === 0) {
      tableBody.innerHTML = `<tr class="empty-row"><td colspan="6">${currentResults.length === 0 ? "No hay documentos procesados aún." : "No hay archivos que coincidan con el filtro actual."}</td></tr>`;
      return;
    }

    filtered.forEach(item => appendTableRow(item));
  }

  function appendTableRow(item) {
    const empty = tableBody.querySelector(".empty-row");
    if (empty) empty.remove();

    const term = searchInput.value.toLowerCase().trim();
    if (currentFilter === "sin_caratula" && (item.has_cover || item.error)) return;
    if (currentFilter === "con_caratula" && (!item.has_cover || item.error)) return;
    if (currentFilter === "error" && !item.error) return;
    if (term && !item.filename.toLowerCase().includes(term)) return;

    const tr = document.createElement("tr");

    let badgeHtml = "";
    let confText = "-";
    let detailsText = "-";

    if (item.error) {
      badgeHtml = `<span class="status-badge error">⚠️ ERROR</span>`;
      detailsText = `<span style="color:var(--danger)">${item.error}</span>`;
    } else if (item.has_cover) {
      badgeHtml = `<span class="status-badge has-cover">✅ CON CARÁTULA</span>`;
      confText = `<strong>${Math.round(item.confidence * 100)}%</strong>`;
      detailsText = `Pág ${item.matched_page || 1} (${item.details?.inliers || 0} puntos)`;
    } else {
      badgeHtml = `<span class="status-badge no-cover">❌ SIN CARÁTULA</span>`;
      confText = `${Math.round(item.confidence * 100)}%`;
      detailsText = `Sin coincidencia visual`;
    }

    tr.innerHTML = `
      <td>${item.index || tableBody.children.length + 1}</td>
      <td>${badgeHtml}</td>
      <td>
        <div class="file-info">
          <span class="file-name">${escapeHtml(item.filename)}</span>
          <span class="file-path">${escapeHtml(item.path)}</span>
        </div>
      </td>
      <td>${confText}</td>
      <td style="color:var(--text-muted); font-size:12px;">${detailsText}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-secondary btn-sm btn-open-pdf">📄 Abrir</button>
          <button class="btn btn-secondary btn-sm btn-show-folder">📂 Carpeta</button>
          <button class="btn btn-outline btn-sm btn-copy-path">📋 Copiar</button>
        </div>
      </td>
    `;

    tr.querySelector(".btn-open-pdf").addEventListener("click", () => {
      window.api.openFile(item.path);
    });

    tr.querySelector(".btn-show-folder").addEventListener("click", () => {
      window.api.showInFolder(item.path);
    });

    tr.querySelector(".btn-copy-path").addEventListener("click", (e) => {
      window.api.copyToClipboard(item.path);
      const btn = e.target;
      btn.textContent = "✓ Copiado";
      setTimeout(() => btn.textContent = "📋 Copiar", 1500);
    });

    tableBody.appendChild(tr);
  }

  // 10. Filtros por Pestañas
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      renderTable();
    });
  });

  document.querySelectorAll(".stat-card").forEach(card => {
    card.addEventListener("click", () => {
      const f = card.dataset.filter;
      const targetTab = document.querySelector(`.tab-btn[data-filter="${f}"]`);
      if (targetTab) targetTab.click();
    });
  });

  searchInput.addEventListener("input", () => {
    renderTable();
  });

  // 11. Exportar a CSV
  btnExportCsv.addEventListener("click", () => {
    if (currentResults.length === 0) {
      alert("No hay resultados para exportar.");
      return;
    }

    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Index,Estado,Nombre,Ruta,Confianza,Pagina,Detalles\n";

    currentResults.forEach(r => {
      const status = r.error ? "ERROR" : (r.has_cover ? "CON_CARATULA" : "SIN_CARATULA");
      const cleanPath = `"${r.path.replace(/"/g, '""')}"`;
      const cleanName = `"${r.filename.replace(/"/g, '""')}"`;
      const details = `"${(r.error || r.details?.reason || '').replace(/"/g, '""')}"`;
      csvContent += `${r.index || 0},${status},${cleanName},${cleanPath},${r.confidence || 0},${r.matched_page || ''},${details}\n`;
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `reporte_caratulas_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });

  function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/[&<>"']/g, function(m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
    });
  }
});
