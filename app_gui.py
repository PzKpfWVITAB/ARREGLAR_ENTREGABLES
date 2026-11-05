"""Aplicación de Escritorio Nativa para Windows (Tkinter / ttk) - Verificador de Carátulas PDF."""
import os
import sys
import csv
import queue
import threading
import subprocess
import concurrent.futures
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Asegurar que el directorio raíz esté en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2
from config import config
from src.network_io import NetworkIOHandler
from src.pdf_processor import PDFProcessor
from src.cover_matcher import CoverMatcher
from src.hardware_detector import HardwareDetector
from src.report_generator import ReportGenerator


class CoverCheckerWinApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Verificador de Carátulas en PDFs - Windows Forms (Alto Rendimiento)")
        self.root.geometry("1220x820")
        self.root.minsize(980, 680)

        # Estado de la aplicación
        self.hw_info = None
        self.active_workers = 4
        self.is_running = False
        self.cancel_requested = False
        self.results = []
        self.current_filter = "all"
        self.msg_queue = queue.Queue()

        # Variables de Tkinter
        self.var_work_dir = tk.StringVar()
        self.var_cover_pdf = tk.StringVar()
        self.var_recursive = tk.BooleanVar(value=True)
        self.var_max_pages = tk.StringVar(value="2")
        self.var_resource_pct = tk.IntVar(value=90)
        self.var_use_gpu = tk.BooleanVar(value=True)
        self.var_search = tk.StringVar()
        self.var_dir_status = tk.StringVar(value="Seleccione o pegue una ruta de red (ej. \\\\servidor\\carpeta)")
        self.var_progress_text = tk.StringVar(value="Listo para iniciar.")
        self.var_progress_count = tk.StringVar(value="0 / 0 (0%)")

        # Configurar estilo visual nativo de Windows
        self._setup_styles()
        self._build_ui()

        # Detectar hardware al arrancar
        self.root.after(100, self.detect_hardware)
        # Bucle de lectura de cola para actualizar la interfaz sin congelarla
        self.root.after(100, self._process_queue)

    def _setup_styles(self):
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        elif "xpnative" in style.theme_names():
            style.theme_use("xpnative")
        else:
            style.theme_use("clam")

        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9), foreground="#555555")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"), foreground="#003366")
        style.configure("Bold.TLabel", font=("Segoe UI", 9, "bold"))
        style.configure("Success.TLabel", font=("Segoe UI", 9, "bold"), foreground="#107c10")
        style.configure("Danger.TLabel", font=("Segoe UI", 9, "bold"), foreground="#c50f1f")
        style.configure("Nvidia.TLabel", font=("Segoe UI", 9, "bold"), foreground="#2b7a0b")
        style.configure("StatNum.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("StatTitle.TLabel", font=("Segoe UI", 9), foreground="#444444")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 6))
        style.configure("Action.TButton", font=("Segoe UI", 9), padding=(8, 4))
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=26)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding=12)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Encabezado
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 8))

        title_box = ttk.Frame(header_frame)
        title_box.pack(side=tk.LEFT)
        ttk.Label(title_box, text="Verificador de Carátulas en Documentos PDF", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            title_box,
            text="Modo 100% Local (OpenCV + PyMuPDF) | Optimizado para carpetas de red y multiprocesamiento al 90%",
            style="Subtitle.TLabel"
        ).pack(anchor=tk.W)

        self.lbl_top_badge = ttk.Label(header_frame, text="Detectando hardware...", style="Bold.TLabel")
        self.lbl_top_badge.pack(side=tk.RIGHT, padx=8)

        # 2. Sección de Configuración de Hardware y Recursos (90%)
        hw_frame = ttk.LabelFrame(main_frame, text=" Configuración de Hardware y Recursos del Equipo (Auto 90%) ", style="Section.TLabelframe", padding=10)
        hw_frame.pack(fill=tk.X, pady=(0, 8))

        hw_info_row = ttk.Frame(hw_frame)
        hw_info_row.pack(fill=tk.X, pady=(0, 8))
        hw_info_row.columnconfigure(0, weight=1)
        hw_info_row.columnconfigure(1, weight=1)
        hw_info_row.columnconfigure(2, weight=1)

        # CPU Box
        cpu_box = ttk.Frame(hw_info_row)
        cpu_box.grid(row=0, column=0, sticky="w", padx=4)
        ttk.Label(cpu_box, text="Procesador (CPU):", style="Bold.TLabel").pack(anchor=tk.W)
        self.lbl_cpu_val = ttk.Label(cpu_box, text="Detectando núcleos...")
        self.lbl_cpu_val.pack(anchor=tk.W)

        # RAM Box
        ram_box = ttk.Frame(hw_info_row)
        ram_box.grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(ram_box, text="Memoria RAM:", style="Bold.TLabel").pack(anchor=tk.W)
        self.lbl_ram_val = ttk.Label(ram_box, text="Detectando memoria...")
        self.lbl_ram_val.pack(anchor=tk.W)

        # GPU Box
        gpu_box = ttk.Frame(hw_info_row)
        gpu_box.grid(row=0, column=2, sticky="w", padx=4)
        ttk.Label(gpu_box, text="Tarjeta Gráfica (GPU):", style="Bold.TLabel").pack(anchor=tk.W)
        self.lbl_gpu_val = ttk.Label(gpu_box, text="Buscando GPU dedicada...", style="Bold.TLabel")
        self.lbl_gpu_val.pack(anchor=tk.W)

        ttk.Separator(hw_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        # Controles de porcentaje de recursos y GPU
        hw_ctrl_row = ttk.Frame(hw_frame)
        hw_ctrl_row.pack(fill=tk.X)

        ttk.Label(hw_ctrl_row, text="Uso de CPU / RAM asignado:").pack(side=tk.LEFT, padx=(0, 6))
        self.lbl_workers_calc = ttk.Label(hw_ctrl_row, text="90% (Calculando workers...)", style="Bold.TLabel")
        self.scale_resources = ttk.Scale(
            hw_ctrl_row, from_=50, to=100, orient=tk.HORIZONTAL, length=180,
            command=self._on_slider_change
        )
        self.scale_resources.pack(side=tk.LEFT, padx=(0, 8))
        self.lbl_workers_calc.pack(side=tk.LEFT, padx=(0, 20))
        self.scale_resources.set(90)

        self.chk_gpu = ttk.Checkbutton(
            hw_ctrl_row,
            text="Utilizar aceleración por GPU (NVIDIA CUDA / OpenCL si está disponible)",
            variable=self.var_use_gpu
        )
        self.chk_gpu.pack(side=tk.LEFT, padx=(0, 12))

        ttk.Button(hw_ctrl_row, text="Re-detectar Equipo", command=self.detect_hardware).pack(side=tk.RIGHT)

        # 3. Sección de Selección de Directorio de Red y Carátula
        cfg_frame = ttk.LabelFrame(main_frame, text=" Parámetros de Búsqueda y Archivos ", style="Section.TLabelframe", padding=10)
        cfg_frame.pack(fill=tk.X, pady=(0, 8))

        # Fila Directorio de Red
        dir_row = ttk.Frame(cfg_frame)
        dir_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(dir_row, text="Directorio de Red / Carpeta:", width=24, anchor=tk.W, style="Bold.TLabel").pack(side=tk.LEFT)
        self.entry_dir = ttk.Entry(dir_row, textvariable=self.var_work_dir)
        self.entry_dir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(dir_row, text="Examinar Carpeta...", command=self.browse_directory).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(dir_row, text="Probar Conexión", command=self.test_network_dir).pack(side=tk.LEFT)

        self.lbl_dir_feedback = ttk.Label(cfg_frame, textvariable=self.var_dir_status, foreground="#555555")
        self.lbl_dir_feedback.pack(anchor=tk.W, padx=(170, 0), pady=(0, 6))

        # Fila Carátula Modelo
        cover_row = ttk.Frame(cfg_frame)
        cover_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(cover_row, text="PDF Carátula de Referencia:", width=24, anchor=tk.W, style="Bold.TLabel").pack(side=tk.LEFT)
        self.entry_cover = ttk.Entry(cover_row, textvariable=self.var_cover_pdf)
        self.entry_cover.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(cover_row, text="Seleccionar PDF...", command=self.browse_cover_pdf).pack(side=tk.LEFT)

        # Fila de opciones y botones de inicio
        opt_row = ttk.Frame(cfg_frame)
        opt_row.pack(fill=tk.X, pady=(4, 0))

        ttk.Checkbutton(opt_row, text="Incluir subcarpetas recursivamente", variable=self.var_recursive).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(opt_row, text="Páginas iniciales a revisar por PDF:").pack(side=tk.LEFT, padx=(0, 6))
        cmb_pages = ttk.Combobox(opt_row, textvariable=self.var_max_pages, values=["1", "2", "3", "4"], width=5, state="readonly")
        cmb_pages.pack(side=tk.LEFT)

        self.btn_cancel = ttk.Button(opt_row, text="Detener Proceso", command=self.cancel_analysis, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_start = ttk.Button(opt_row, text="Iniciar Verificación de Carátulas", style="Primary.TButton", command=self.start_analysis)
        self.btn_start.pack(side=tk.RIGHT)

        # 4. Barra de progreso
        prog_frame = ttk.Frame(main_frame)
        prog_frame.pack(fill=tk.X, pady=(0, 8))

        prog_labels = ttk.Frame(prog_frame)
        prog_labels.pack(fill=tk.X)
        ttk.Label(prog_labels, textvariable=self.var_progress_text, style="Bold.TLabel").pack(side=tk.LEFT)
        ttk.Label(prog_labels, textvariable=self.var_progress_count, style="Bold.TLabel").pack(side=tk.RIGHT)

        self.progress_bar = ttk.Progressbar(prog_frame, orient=tk.HORIZONTAL, mode="determinate", maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(4, 0))

        # 5. Contadores Rápidos y Barra de Filtros
        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_filter_all = ttk.Button(stats_frame, text="Todos (0)", command=lambda: self.set_filter("all"))
        self.btn_filter_all.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_filter_no_cover = ttk.Button(stats_frame, text="❌ Sin Carátula (0)", command=lambda: self.set_filter("sin_caratula"))
        self.btn_filter_no_cover.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_filter_has_cover = ttk.Button(stats_frame, text="✅ Con Carátula (0)", command=lambda: self.set_filter("con_caratula"))
        self.btn_filter_has_cover.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_filter_err = ttk.Button(stats_frame, text="⚠️ Errores / Dañados (0)", command=lambda: self.set_filter("error"))
        self.btn_filter_err.pack(side=tk.LEFT, padx=(0, 16))

        # Buscador a la derecha
        ttk.Button(stats_frame, text="Exportar CSV", command=self.export_csv).pack(side=tk.RIGHT, padx=(6, 0))
        ttk.Button(stats_frame, text="Abrir Reporte HTML", command=self.export_and_open_html).pack(side=tk.RIGHT, padx=(6, 0))

        search_entry = ttk.Entry(stats_frame, textvariable=self.var_search, width=28)
        search_entry.pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Label(stats_frame, text="Buscar archivo:").pack(side=tk.RIGHT)
        self.var_search.trace_add("write", lambda *_: self.refresh_table())

        # 6. Tabla de Resultados (Treeview)
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("idx", "status", "filename", "confidence", "details", "path")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("idx", text="#")
        self.tree.heading("status", text="Estado")
        self.tree.heading("filename", text="Archivo PDF")
        self.tree.heading("confidence", text="Confianza")
        self.tree.heading("details", text="Página / Puntos")
        self.tree.heading("path", text="Ruta Completa en Red")

        self.tree.column("idx", width=50, anchor=tk.CENTER, stretch=False)
        self.tree.column("status", width=145, anchor=tk.CENTER, stretch=False)
        self.tree.column("filename", width=260, anchor=tk.W)
        self.tree.column("confidence", width=95, anchor=tk.CENTER, stretch=False)
        self.tree.column("details", width=180, anchor=tk.W, stretch=False)
        self.tree.column("path", width=420, anchor=tk.W)

        # Colores por etiqueta
        self.tree.tag_configure("con_caratula", background="#e6f4ea", foreground="#0d652d")
        self.tree.tag_configure("sin_caratula", background="#fce8e6", foreground="#a50e0e")
        self.tree.tag_configure("error", background="#fef7e0", foreground="#b06000")

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Eventos de doble clic y clic derecho
        self.tree.bind("<Double-1>", lambda e: self.open_selected_pdf())
        self.tree.bind("<Button-3>", self._show_context_menu)

        # Menú contextual (Clic derecho)
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📄 Abrir PDF en visor predeterminado", command=self.open_selected_pdf)
        self.context_menu.add_command(label="📂 Mostrar archivo en el Explorador de Windows", command=self.show_selected_in_explorer)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copiar ruta completa al portapapeles", command=self.copy_selected_path)

        # 7. Barra inferior de Atajos Rápidos para el archivo seleccionado
        shortcut_bar = ttk.LabelFrame(main_frame, text=" Atajos Rápidos para el Archivo Seleccionado (o Doble Clic / Clic Derecho en la tabla) ", padding=8)
        shortcut_bar.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(shortcut_bar, text="📄 Abrir PDF Seleccionado", style="Action.TButton", command=self.open_selected_pdf).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(shortcut_bar, text="📂 Abrir Carpeta y Resaltar Archivo", style="Action.TButton", command=self.show_selected_in_explorer).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(shortcut_bar, text="📋 Copiar Ruta de Red", style="Action.TButton", command=self.copy_selected_path).pack(side=tk.LEFT)

        self.lbl_shortcut_hint = ttk.Label(shortcut_bar, text="Tip: Haz doble clic sobre cualquier fila para abrir el PDF al instante.", style="Subtitle.TLabel")
        self.lbl_shortcut_hint.pack(side=tk.RIGHT)

    # =========================================================================
    # DETECCIÓN DE HARDWARE Y AJUSTE AL 90%
    # =========================================================================
    def detect_hardware(self):
        try:
            self.hw_info = HardwareDetector.detect()
            cpu = self.hw_info["cpu"]
            ram = self.hw_info["ram"]
            gpu = self.hw_info["gpu"]

            self._update_workers_from_slider()

            self.lbl_cpu_val.configure(
                text=f"{cpu['logical_cores']} hilos lógicos ({cpu['physical_cores']} núcleos físicos)"
            )
            self.lbl_ram_val.configure(
                text=f"{ram['total_gb']} GB Total ({ram['available_gb']} GB disponibles)"
            )

            prim_gpu = gpu["primary"]
            gpu_name = prim_gpu.get("name", "Integrada")
            vram_txt = f" ({prim_gpu['vram_gb']} GB VRAM)" if prim_gpu.get("vram_gb") else ""

            if gpu["has_nvidia"]:
                self.lbl_gpu_val.configure(text=f"NVIDIA: {gpu_name}{vram_txt} [Activa]", style="Nvidia.TLabel")
                self.lbl_top_badge.configure(text=f"🎮 GPU NVIDIA Activa | ⚡ {self.active_workers} Workers (90%)", style="Nvidia.TLabel")
            elif gpu["opencl_acceleration"]:
                self.lbl_gpu_val.configure(text=f"{gpu_name}{vram_txt} [OpenCL Activo]", style="Success.TLabel")
                self.lbl_top_badge.configure(text=f"⚡ GPU OpenCL Activo | {self.active_workers} Workers", style="Success.TLabel")
            else:
                self.lbl_gpu_val.configure(text=f"{gpu_name} (Modo CPU Multiproceso)", style="Bold.TLabel")
                self.lbl_top_badge.configure(text=f"⚡ CPU Multiproceso: {self.active_workers} Workers", style="Bold.TLabel")

        except Exception as e:
            self.lbl_cpu_val.configure(text=f"Error al detectar: {e}")

    def _on_slider_change(self, val):
        pct = int(float(val))
        self.var_resource_pct.set(pct)
        self._update_workers_from_slider()

    def _update_workers_from_slider(self):
        pct = self.var_resource_pct.get()
        logical_cores = self.hw_info["cpu"]["logical_cores"] if self.hw_info else (os.cpu_count() or 4)
        total_ram = self.hw_info["ram"]["total_gb"] if self.hw_info else 8.0

        self.active_workers = max(1, int(logical_cores * (pct / 100.0)))
        ram_limit = round(total_ram * (pct / 100.0), 1)
        self.lbl_workers_calc.configure(text=f"{pct}%  →  {self.active_workers} Workers en paralelo | Límite RAM: {ram_limit} GB")

    # =========================================================================
    # DIÁLOGOS Y PRUEBA DE RED
    # =========================================================================
    def browse_directory(self):
        selected = filedialog.askdirectory(title="Seleccionar Directorio de Red o Carpeta de PDFs")
        if selected:
            norm = str(NetworkIOHandler.normalize_path(selected))
            self.var_work_dir.set(norm)
            self.test_network_dir()

    def browse_cover_pdf(self):
        selected = filedialog.askopenfilename(
            title="Seleccionar PDF de la Carátula de Referencia",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if selected:
            norm = str(NetworkIOHandler.normalize_path(selected))
            self.var_cover_pdf.set(norm)

    def test_network_dir(self):
        raw_dir = self.var_work_dir.get().strip()
        if not raw_dir:
            self.var_dir_status.set("⚠️ Ingrese una ruta primero.")
            self.lbl_dir_feedback.configure(foreground="#b06000")
            return

        dir_path = NetworkIOHandler.normalize_path(raw_dir)
        self.var_dir_status.set("Verificando conectividad con la ruta de red...")
        self.root.update_idletasks()

        ok, msg = NetworkIOHandler.test_connectivity(dir_path)
        if ok:
            pdfs = NetworkIOHandler.list_pdf_files(dir_path, recursive=self.var_recursive.get())
            self.var_dir_status.set(f"✅ {msg} Se encontraron {len(pdfs)} archivos PDF.")
            self.lbl_dir_feedback.configure(foreground="#107c10")
        else:
            self.var_dir_status.set(f"❌ {msg}")
            self.lbl_dir_feedback.configure(foreground="#c50f1f")

    # =========================================================================
    # PROCESAMIENTO PARALELO EN SEGUNDO PLANO
    # =========================================================================
    def start_analysis(self):
        if self.is_running:
            return

        raw_dir = self.var_work_dir.get().strip()
        raw_cover = self.var_cover_pdf.get().strip()

        if not raw_dir:
            messagebox.showwarning("Falta Directorio", "Por favor seleccione o ingrese el directorio de red a analizar.")
            return
        if not raw_cover:
            messagebox.showwarning("Falta Carátula", "Por favor seleccione el archivo PDF que contiene la carátula modelo.")
            return

        work_dir = NetworkIOHandler.normalize_path(raw_dir)
        cover_path = NetworkIOHandler.normalize_path(raw_cover)

        ok, msg = NetworkIOHandler.test_connectivity(work_dir)
        if not ok:
            messagebox.showerror("Error de Red", msg)
            return

        if not cover_path.exists():
            messagebox.showerror("Carátula no encontrada", f"No existe el archivo de carátula:\n{cover_path}")
            return

        # Reiniciar estado
        self.results.clear()
        self.refresh_table()
        self._update_counters()

        self.is_running = True
        self.cancel_requested = False
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_cancel.configure(state=tk.NORMAL)
        self.progress_bar["value"] = 0
        self.var_progress_text.set("Preparando motor de visión artificial y carátula modelo...")
        self.var_progress_count.set("0 / 0 (0%)")

        max_pages = int(self.var_max_pages.get() or 2)
        recursive = self.var_recursive.get()
        workers = self.active_workers
        use_gpu = self.var_use_gpu.get()

        thread = threading.Thread(
            target=self._worker_thread,
            args=(work_dir, cover_path, recursive, max_pages, workers, use_gpu),
            daemon=True
        )
        thread.start()

    def cancel_analysis(self):
        if self.is_running:
            self.cancel_requested = True
            self.var_progress_text.set("Cancelando proceso, esperando cierre de hilos activos...")

    def _worker_thread(self, work_dir: Path, cover_path: Path, recursive: bool, max_pages: int, workers: int, use_gpu: bool):
        try:
            if use_gpu and cv2.ocl.haveOpenCL():
                cv2.ocl.setUseOpenCL(True)
            else:
                cv2.ocl.setUseOpenCL(False)

            all_pdfs = NetworkIOHandler.list_pdf_files(work_dir, recursive=recursive)
            target_pdfs = [p for p in all_pdfs if p.resolve() != cover_path.resolve()]
            total_files = len(target_pdfs)

            if total_files == 0:
                self.msg_queue.put(("done", "No se encontraron otros archivos PDF para comparar."))
                return

            io_handler = NetworkIOHandler()
            local_cover, is_temp_cover = io_handler.get_local_accessible_file(cover_path)
            try:
                matcher, err = CoverMatcher.from_pdf(local_cover)
                if err or matcher is None:
                    self.msg_queue.put(("error", f"No se pudo cargar la carátula de referencia:\n{err}"))
                    return
            finally:
                if is_temp_cover:
                    io_handler.cleanup_temp(local_cover)

            self.msg_queue.put(("status", f"Analizando {total_files} PDFs con {workers} workers paralelos ({len(matcher.ref_kp)} rasgos)..."))

            pdf_processor = PDFProcessor()
            indexed_files = list(enumerate(target_pdfs, 1))
            completed = 0

            def evaluate_one(item_tuple):
                idx, pdf = item_tuple
                res = {
                    "index": idx,
                    "filename": pdf.name,
                    "path": str(pdf),
                    "has_cover": False,
                    "confidence": 0.0,
                    "matched_page": None,
                    "error": None,
                    "details": {}
                }
                if self.cancel_requested:
                    res["error"] = "Cancelado"
                    return res

                try:
                    local_proc_path, is_temp = io_handler.get_local_accessible_file(pdf)
                except Exception as e:
                    res["error"] = f"Error de lectura en red: {e}"
                    return res

                try:
                    pages_imgs, render_err = pdf_processor.render_pages_as_images(local_proc_path, max_pages=max_pages)
                    if render_err:
                        res["error"] = render_err
                    else:
                        doc_eval = matcher.check_document(pages_imgs)
                        res["has_cover"] = doc_eval["has_cover"]
                        res["confidence"] = doc_eval["confidence"]
                        res["matched_page"] = doc_eval["matched_page"]
                        res["details"] = doc_eval.get("details", {})
                except Exception as e:
                    res["error"] = f"Error de análisis: {e}"
                finally:
                    if is_temp:
                        io_handler.cleanup_temp(local_proc_path)

                return res

            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(evaluate_one, item): item for item in indexed_files}
                for future in concurrent.futures.as_completed(futures):
                    if self.cancel_requested:
                        break
                    item_res = future.result()
                    completed += 1
                    pct = round((completed / total_files) * 100, 1)
                    self.msg_queue.put(("item", (item_res, completed, total_files, pct)))

            if self.cancel_requested:
                self.msg_queue.put(("done", "Proceso cancelado por el usuario."))
            else:
                self.msg_queue.put(("done", f"¡Análisis finalizado! ({completed} archivos procesados)"))

        except Exception as e:
            self.msg_queue.put(("error", f"Error inesperado en el motor:\n{e}"))

    def _process_queue(self):
        try:
            while True:
                msg_type, payload = self.msg_queue.get_nowait()
                if msg_type == "status":
                    self.var_progress_text.set(payload)
                elif msg_type == "item":
                    item_res, completed, total_files, pct = payload
                    self.results.append(item_res)
                    self.progress_bar["value"] = pct
                    self.var_progress_text.set(f"Procesando: {item_res['filename']}")
                    self.var_progress_count.set(f"{completed} / {total_files} ({pct}%)")
                    self._update_counters()
                    self._insert_row_if_matches_filter(item_res)
                elif msg_type == "error":
                    self.is_running = False
                    self.btn_start.configure(state=tk.NORMAL)
                    self.btn_cancel.configure(state=tk.DISABLED)
                    self.var_progress_text.set("Error en el proceso.")
                    messagebox.showerror("Error", payload)
                elif msg_type == "done":
                    self.is_running = False
                    self.btn_start.configure(state=tk.NORMAL)
                    self.btn_cancel.configure(state=tk.DISABLED)
                    self.results.sort(key=lambda x: x["index"])
                    self.refresh_table()
                    self.var_progress_text.set(payload)
        except queue.Empty:
            pass
        finally:
            self.root.after(80, self._process_queue)

    # =========================================================================
    # TABLA, FILTROS Y ATAJOS RÁPIDOS
    # =========================================================================
    def _update_counters(self):
        total = len(self.results)
        sin_c = sum(1 for r in self.results if not r["has_cover"] and not r["error"])
        con_c = sum(1 for r in self.results if r["has_cover"] and not r["error"])
        err_c = sum(1 for r in self.results if r["error"])

        self.btn_filter_all.configure(text=f"Todos ({total})")
        self.btn_filter_no_cover.configure(text=f"❌ Sin Carátula ({sin_c})")
        self.btn_filter_has_cover.configure(text=f"✅ Con Carátula ({con_c})")
        self.btn_filter_err.configure(text=f"⚠️ Errores / Dañados ({err_c})")

    def set_filter(self, filter_name: str):
        self.current_filter = filter_name
        self.refresh_table()

    def _matches_filter(self, item: dict) -> bool:
        if self.current_filter == "sin_caratula" and (item["has_cover"] or item["error"]):
            return False
        if self.current_filter == "con_caratula" and (not item["has_cover"] or item["error"]):
            return False
        if self.current_filter == "error" and not item["error"]:
            return False

        term = self.var_search.get().strip().lower()
        if term and term not in item["filename"].lower():
            return False
        return True

    def _insert_row_if_matches_filter(self, item: dict):
        if not self._matches_filter(item):
            return

        if item["error"]:
            status_txt = "⚠️ ERROR"
            conf_txt = "-"
            det_txt = item["error"]
            tag = "error"
        elif item["has_cover"]:
            status_txt = "✅ CON CARÁTULA"
            conf_txt = f"{int(item['confidence'] * 100)}%"
            det_txt = f"Pág {item.get('matched_page') or 1} ({item.get('details', {}).get('inliers', 0)} pts)"
            tag = "con_caratula"
        else:
            status_txt = "❌ SIN CARÁTULA"
            conf_txt = f"{int(item['confidence'] * 100)}%"
            det_txt = "Sin coincidencia visual"
            tag = "sin_caratula"

        self.tree.insert(
            "", tk.END,
            values=(item["index"], status_txt, item["filename"], conf_txt, det_txt, item["path"]),
            tags=(tag,)
        )

    def refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for item in self.results:
            self._insert_row_if_matches_filter(item)

    def _get_selected_path(self) -> Path | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Seleccione un archivo", "Seleccione primero una fila en la tabla de resultados.")
            return None
        values = self.tree.item(sel[0], "values")
        if not values or len(values) < 6:
            return None
        return Path(values[5])

    def open_selected_pdf(self):
        p = self._get_selected_path()
        if p:
            ReportGenerator.open_file_in_viewer(p)

    def show_selected_in_explorer(self):
        p = self._get_selected_path()
        if p:
            ReportGenerator.show_in_explorer(p)

    def copy_selected_path(self):
        p = self._get_selected_path()
        if p:
            self.root.clipboard_clear()
            self.root.clipboard_append(str(p))
            self.lbl_shortcut_hint.configure(text=f"✓ Ruta copiada: {p.name}")

    def _show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    # =========================================================================
    # EXPORTACIÓN DE REPORTES (CSV Y HTML)
    # =========================================================================
    def export_csv(self):
        if not self.results:
            messagebox.showinfo("Sin datos", "No hay resultados para exportar.")
            return

        out_file = filedialog.asksaveasfilename(
            title="Guardar Reporte CSV",
            defaultextension=".csv",
            initialfile=f"reporte_caratulas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("Archivo CSV", "*.csv")]
        )
        if not out_file:
            return

        try:
            with open(out_file, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["#", "Estado", "Archivo", "Confianza", "Pagina", "Detalles", "Ruta Completa"])
                for r in self.results:
                    estado = "ERROR" if r["error"] else ("CON_CARATULA" if r["has_cover"] else "SIN_CARATULA")
                    det = r["error"] or r.get("details", {}).get("reason", "")
                    writer.writerow([
                        r["index"], estado, r["filename"],
                        f"{int(r['confidence'] * 100)}%",
                        r.get("matched_page") or "",
                        det, r["path"]
                    ])
            messagebox.showinfo("Exportación Exitosa", f"Archivo CSV guardado en:\n{out_file}")
        except Exception as e:
            messagebox.showerror("Error al guardar CSV", str(e))

    def export_and_open_html(self):
        if not self.results:
            messagebox.showinfo("Sin datos", "No hay resultados para generar el reporte.")
            return

        try:
            cover_name = Path(self.var_cover_pdf.get()).name if self.var_cover_pdf.get() else "Caratula.pdf"
            reporter = ReportGenerator(reference_pdf_name=cover_name, network_dir=self.var_work_dir.get())
            report_path = Path(os.getcwd()) / "reporte_caratulas.html"
            reporter.generate_html_report(self.results, report_path)
            os.startfile(str(report_path))
        except Exception as e:
            messagebox.showerror("Error al generar HTML", str(e))


def main():
    root = tk.Tk()
    app = CoverCheckerWinApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
