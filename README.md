# Verificador de Carátulas en Documentos PDF (Windows Forms Nativo)

Herramienta de escritorio para Windows con **Visión Artificial 100% Local** diseñada para auditar lotes masivos de archivos PDF en **carpetas de red (rutas UNC `\\servidor\recurso` o unidades mapeadas `Z:\`)**, detectando qué documentos tienen su carátula institucional y cuáles carecen de ella.

---

## Características Principales

1. **Interfaz Nativa de Windows (Sin Electron ni Node.js):**
   - Construida con formularios nativos de Windows (`tkinter` / `ttk`), arranque instantáneo, consumo mínimo de memoria y **únicamente requiere Python**.
2. **Optimización de Hardware al 90% y Soporte GPU NVIDIA:**
   - **Sección de Configuración:** Detecta automáticamente los núcleos lógicos/físicos del CPU, la memoria RAM total/disponible y la tarjeta gráfica dedicada (**NVIDIA GeForce / RTX / Quadro** o AMD/Intel con OpenCL).
   - **Procesamiento Paralelo:** Asigna por defecto el **90% de los hilos del procesador** y memoria mediante un pool de workers concurrentes, con control deslizante ajustable entre 50% y 100%.
3. **Tolerancia a Fallos en Rutas de Red (SMB / UNC):**
   - Manejo de rutas estilo `\\192.168.1.50\expedientes` o `Z:\contratos`.
   - Lectura mediante buffers temporales locales con reintentos automáticos para evitar bloqueos de archivos y caídas de red.
4. **Atajos Rápidos Integrados:**
   - **Doble clic** o **clic derecho** sobre cualquier fila de la tabla para abrir el PDF directamente, resaltarlo en el Explorador de Windows o copiar su ruta de red.
   - Botones de exportación a **CSV** y generación de **Reporte Interactivo HTML**.

---

## Estructura del Proyecto

```text
c:\laragon\www\ARREGLAR_ENTREGABLES\
│
├── app_gui.py                # Aplicación de Escritorio Windows Forms (Interfaz Principal)
├── run_checker.py            # Versión alternativa por línea de comandos (CLI)
├── config.py                 # Parámetros globales (DPI, umbrales ORB/RANSAC, red)
├── instalar.bat              # Instalador portátil de 1 clic (solo requiere Python)
├── ejecutar.bat              # Lanzador directo de la interfaz gráfica
├── requirements.txt          # Librerías (PyMuPDF, OpenCV, NumPy, psutil)
│
├── src/
│   ├── hardware_detector.py  # Auto-detección de CPU, RAM y GPU dedicada NVIDIA/OpenCL
│   ├── network_io.py         # Manejador robusto de rutas de red UNC y caché local
│   ├── pdf_processor.py      # Renderizado con PyMuPDF y mejora CLAHE en OpenCV
│   ├── cover_matcher.py      # Comparación geométrica visual (ORB + Lowe Ratio + RANSAC)
│   └── report_generator.py   # Acciones del sistema y generador de reporte HTML
│
└── tests/
    └── test_cover_pipeline.py# Suite de pruebas unitarias
```

---

## Instalación y Ejecución en Cualquier PC

1. **Requisito único:** Tener instalado **[Python 3.10+](https://www.python.org/downloads/)** (marcando la casilla *"Add python.exe to PATH"*). **Ya no se necesita Node.js ni npm.**
2. **Instalar (primera vez):**
   Haz doble clic en **`instalar.bat`**. Creará el entorno aislado `.venv` e instalará OpenCV, PyMuPDF y psutil.
3. **Ejecutar:**
   Haz doble clic en **`ejecutar.bat`**. Se abrirá directamente la ventana de Windows del verificador.
