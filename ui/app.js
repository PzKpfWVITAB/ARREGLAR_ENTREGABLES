// Lógica Frontend para Electron
document.addEventListener("DOMContentLoaded", () => {
  // Elementos DOM
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

  // 1. Selección de Directorio
  btnBrowseDir.addEventListener("click", async () => {
    const dir = await window.api.selectDirectory();
    if (dir) {
      workDirInput.value = dir;
      testDirectory(dir);
    }
  });

  // 2. Selección de Carátula Modelo
  btnBrowseCover.addEventListener("click", async () => {
    const file = await window.api.selectFile();
    if (file) {
      coverPathInput.value = file;
      coverFeedback.className = "field-feedback success";
      coverFeedback.textContent = "Carátula seleccionada: " + file.split(/[\/\\]/).pop();
    }
  });

  // 3. Probar Conexión con Ruta
  async function testDirectory(dir) {
    if (!dir) {
      dirFeedback.className = "field-feedback error";
      dirFeedback.textContent = "Por favor ingrese una ruta.";
      return;
    }
    dirFeedback.className = "field-feedback info";
    dirFeedback.textContent = "Verificando conectividad...";
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

  // 4. Iniciar Análisis
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
    progressStatusText.textContent = "Iniciando proceso en lote...";
    systemStatus.textContent = "Analizando...";
    systemStatus.style.color = "var(--primary)";

    const res = await window.api.startAnalysis({
      workDir,
      coverPath,
      recursive: chkRecursive.checked,
      maxPages: parseInt(selectPages.value, 10)
    });

    if (!res.ok) {
      alert(res.message);
      resetUI();
    }
  });

  // 5. Cancelar Análisis
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

  // 6. Escucha de Eventos Backend
  window.api.onStatus((msg) => {
    progressStatusText.textContent = msg;
  });

  window.api.onCoverReady((data) => {
    progressStatusText.textContent = `Carátula lista (${data.keypoints} rasgos extraídos). Analizando lote...`;
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

  // 7. Actualización de Estadísticas
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

  // 8. Renderizado de Filas y Tabla
  function renderTable() {
    tableBody.innerHTML = "";
    const term = searchInput.value.toLowerCase().trim();

    const filtered = currentResults.filter(item => {
      // Filtro por pestaña
      let matchTab = true;
      if (currentFilter === "sin_caratula") matchTab = (!item.has_cover && !item.error);
      else if (currentFilter === "con_caratula") matchTab = (item.has_cover && !item.error);
      else if (currentFilter === "error") matchTab = Boolean(item.error);

      // Filtro por búsqueda
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
    // Si la tabla estaba vacía, limpiar mensaje
    const empty = tableBody.querySelector(".empty-row");
    if (empty) empty.remove();

    // Comprobar si cumple con filtro actual
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

    // Asignar eventos directos a los botones de atajo
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

  // 9. Filtros por Pestañas
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      renderTable();
    });
  });

  // Filtros desde las tarjetas superiores de estadísticas
  document.querySelectorAll(".stat-card").forEach(card => {
    card.addEventListener("click", () => {
      const f = card.dataset.filter;
      const targetTab = document.querySelector(`.tab-btn[data-filter="${f}"]`);
      if (targetTab) targetTab.click();
    });
  });

  // Búsqueda en vivo
  searchInput.addEventListener("input", () => {
    renderTable();
  });

  // 10. Exportar a CSV
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
