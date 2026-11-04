# Verificador de Carátulas en Documentos PDF (100% Local)

Herramienta de Visión Artificial optimizada para auditar lotes masivos de documentos PDF ubicados en **carpetas de red (rutas UNC `\\servidor\recurso` o unidades mapeadas `Z:\`)**, identificando de forma precisa qué archivos cuentan con su carátula institucional/modelo y cuáles carecen de ella.

---

## Características Principales

1. **Modo 100% Local (Sin consumo ni dependencia de APIs externas):**
   - Utiliza **PyMuPDF 2.0** y **OpenCV** con aceleración matricial NumPy.
   - Algoritmo de comparación visual basado en **ORB (Oriented FAST and Rotated BRIEF)**, filtrado **Lowe's Ratio Test** y matriz de transformación homográfica con **RANSAC**.
   - Resistente a documentos degradados, borrosos, con fondos opacos o ligeras variaciones de resolución/escaneo.

2. **Diseñado para Rutas de Red (SMB / UNC / Shares):**
   - Manejo de rutas estilo `\\192.168.1.50\expedientes` o `Z:\contratos`.
   - Copia segura en buffer temporal (`tempfile`) con reintentos exponenciales para mitigar caídas de conexión, latencias de red y bloqueos de archivos abiertos.

3. **Resultados Claros y Atajos Rápidos:**
   - **Consola interactiva:** Selección por número para abrir el PDF al instante o revelarlo en el Explorador de Windows.
   - **Dashboard HTML interactivo:** Genera `reporte_caratulas.html` con estadísticas, filtros instantáneos (*Sin Carátula*, *Con Carátula*, *Errores*), enlaces directos de apertura y botón para copiar rutas al portapapeles.

---

## Estructura del Proyecto

```text
c:\laragon\www\ARREGLAR_ENTREGABLES\
│
├── config.py                 # Parámetros (DPI, umbrales de inliers, reintentos de red)
├── run_checker.py            # CLI interactivo principal
├── reporte_caratulas.html    # Reporte generado al finalizar cada análisis
│
├── src/
│   ├── network_io.py         # Manejador de rutas de red y tolerancia a fallos
│   ├── pdf_processor.py      # Renderizado de páginas con PyMuPDF y CLAHE OpenCV
│   ├── cover_matcher.py      # Motor de comparación geométrica y rasgos visuales
│   └── report_generator.py   # Generador de dashboard HTML y acciones del sistema
│
└── tests/
    └── test_cover_pipeline.py# Pruebas automatizadas con PDFs sintéticos
```

---

## Instrucciones de Instalación y Ejecución Portátil

Esta versión cuenta con una **interfaz gráfica moderna en Electron** y un entorno **100% portable** que no interfiere con librerías globales del sistema.

### 1. Para llevar a otra PC (Instalación en 1 Clic)
1. Copia la carpeta del proyecto a la nueva máquina.
2. Asegúrate de tener instalados **Python (3.10+)** y **Node.js (LTS)** en esa máquina.
3. Haz doble clic en el archivo:
   ```cmd
   instalar.bat
   ```
   *El instalador creará automáticamente un entorno virtual aislado (`.venv`), descargará las librerías de visión artificial (`requirements.txt`) e instalará Electron localmente.*

### 2. Para Iniciar la Aplicación
Simplemente haz doble clic en:
```cmd
ejecutar.bat
```
*(Si no se ha instalado previamente, `ejecutar.bat` detectará la falta de dependencias y lanzará el instalador por ti).*

---

## Características de la Interfaz Electron

- **Selector y Validador de Red:** Explora o pega rutas UNC (`\\servidor\carpeta`) con botón de verificación en vivo.
- **Selector de Carátula:** Elige el archivo PDF modelo con el diálogo nativo de Windows.
- **Monitoreo en Tiempo Real:** Barra de progreso con porcentaje, archivo actual y contador.
- **Tarjetas de Estadísticas Clicables:** Filtra al instante entre *Todos*, *Sin Carátula*, *Con Carátula* y *Errores*.
- **Atajos Directos por Fila:**
  - 📄 **Abrir:** Lanza el PDF en el visor predeterminado.
  - 📂 **Carpeta:** Abre el Explorador de Windows con el archivo exacto seleccionado.
  - 📋 **Copiar:** Copia la ruta de red directa al portapapeles.
- **Exportación:** Botón para exportar todos los hallazgos a archivo `.csv`.
- **Modo Consola Alternativo:** Aún puedes ejecutar `python run_checker.py` si deseas usar la versión puramente por terminal.

---

## Atajos de Teclado en Consola

Al terminar el análisis se mostrará el resumen y tendrás disponibles los siguientes comandos:

| Comando | Acción |
| :--- | :--- |
| `[número]` (ej. `3`) | Abre directamente el PDF `#3` en tu visor predeterminado de Windows. |
| `e [número]` (ej. `e 3`) | Abre el Explorador de Windows en la carpeta de red con el archivo `#3` seleccionado. |
| `s` | Filtra e imprime en pantalla únicamente los archivos **SIN CARÁTULA**. |
| `c` | Filtra e imprime en pantalla únicamente los archivos **CON CARÁTULA**. |
| `r` | Vuelve a abrir el reporte HTML interactivo en el navegador. |
| `q` | Salir del programa. |
