"""Generador de reportes en consola interactiva y dashboard HTML con atajos rápidos a archivos."""
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any
import webbrowser

class ReportGenerator:
    def __init__(self, reference_pdf_name: str, network_dir: str):
        self.reference_pdf_name = reference_pdf_name
        self.network_dir = network_dir

    @staticmethod
    def open_file_in_viewer(file_path: Path):
        """Abre el archivo PDF en el visor predeterminado del sistema operativo."""
        try:
            os.startfile(str(file_path))
            print(f"[>] Abriendo archivo: {file_path.name}")
        except Exception as e:
            print(f"[!] Error al abrir el archivo: {e}")

    @staticmethod
    def show_in_explorer(file_path: Path):
        """Abre el explorador de Windows seleccionando y resaltando el archivo exacto."""
        try:
            norm = os.path.normpath(str(file_path))
            subprocess.run(["explorer.exe", f"/select,{norm}"])
            print(f"[>] Carpeta abierta con archivo seleccionado: {file_path.name}")
        except Exception as e:
            print(f"[!] Error al abrir el Explorador de Windows: {e}")

    def generate_html_report(self, results: List[Dict[str, Any]], output_path: Path) -> Path:
        """
        Genera un dashboard HTML autónomo, interactivo y estilizado
        con filtros y enlaces directos a los archivos.
        """
        total = len(results)
        sin_caratula = [r for r in results if not r.get("has_cover") and not r.get("error")]
        con_caratula = [r for r in results if r.get("has_cover") and not r.get("error")]
        errores = [r for r in results if r.get("error")]

        html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Detección de Carátulas</title>
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
            --accent: #38bdf8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{ background-color: var(--bg-primary); color: var(--text-main); padding: 24px; }}
        header {{ margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--bg-card); }}
        h1 {{ font-size: 24px; color: var(--accent); margin-bottom: 8px; }}
        .meta {{ color: var(--text-muted); font-size: 14px; }}
        
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .stat-card {{ background: var(--bg-secondary); border-radius: 8px; padding: 16px; border-left: 4px solid var(--accent); }}
        .stat-card.danger {{ border-left-color: var(--danger); }}
        .stat-card.success {{ border-left-color: var(--success); }}
        .stat-card.warning {{ border-left-color: var(--warning); }}
        .stat-title {{ font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
        .stat-num {{ font-size: 32px; font-weight: bold; margin-top: 4px; }}

        .filter-bar {{ display: flex; gap: 10px; margin-bottom: 16px; }}
        .filter-btn {{ background: var(--bg-secondary); border: 1px solid var(--bg-card); color: var(--text-main); padding: 8px 16px; border-radius: 6px; cursor: pointer; transition: 0.2s; font-size: 14px; }}
        .filter-btn.active, .filter-btn:hover {{ background: var(--accent); color: #000; font-weight: 600; }}

        .table-container {{ background: var(--bg-secondary); border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        th {{ background: #182234; padding: 12px 16px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 12px; }}
        td {{ padding: 14px 16px; border-bottom: 1px solid var(--bg-card); vertical-align: middle; }}
        tr:hover {{ background: rgba(56, 189, 248, 0.05); }}

        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: bold; text-align: center; }}
        .badge.danger {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid var(--danger); }}
        .badge.success {{ background: rgba(34, 197, 94, 0.2); color: #86efac; border: 1px solid var(--success); }}
        .badge.warning {{ background: rgba(245, 158, 11, 0.2); color: #fde68a; border: 1px solid var(--warning); }}

        .file-name {{ font-weight: 600; color: #fff; display: block; }}
        .file-path {{ font-size: 12px; color: var(--text-muted); word-break: break-all; margin-top: 2px; }}

        .actions {{ display: flex; gap: 8px; }}
        .action-link {{ background: #2563eb; color: #fff; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 12px; font-weight: 500; display: inline-block; }}
        .action-link:hover {{ background: #1d4ed8; }}
        .action-btn-copy {{ background: var(--bg-card); color: var(--text-main); border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }}
        .action-btn-copy:hover {{ background: #475569; }}
    </style>
</head>
<body>
    <header>
        <h1>Reporte de Verificación de Carátulas</h1>
        <div class="meta">
            <span>Directorio de Red: <strong>{self.network_dir}</strong></span> | 
            <span>Carátula Modelo: <strong>{self.reference_pdf_name}</strong></span>
        </div>
    </header>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-title">Total Procesados</div>
            <div class="stat-num">{total}</div>
        </div>
        <div class="stat-card danger">
            <div class="stat-title">❌ Sin Carátula</div>
            <div class="stat-num">{len(sin_caratula)}</div>
        </div>
        <div class="stat-card success">
            <div class="stat-title">✅ Con Carátula</div>
            <div class="stat-num">{len(con_caratula)}</div>
        </div>
        <div class="stat-card warning">
            <div class="stat-title">⚠️ Errores / Corruptos</div>
            <div class="stat-num">{len(errores)}</div>
        </div>
    </div>

    <div class="filter-bar">
        <button class="filter-btn active" onclick="filterTable('all')">Todos ({total})</button>
        <button class="filter-btn" onclick="filterTable('sin_caratula')">Solo Sin Carátula ({len(sin_caratula)})</button>
        <button class="filter-btn" onclick="filterTable('con_caratula')">Solo Con Carátula ({len(con_caratula)})</button>
        <button class="filter-btn" onclick="filterTable('error')">Solo Errores ({len(errores)})</button>
    </div>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">#</th>
                    <th>Estado</th>
                    <th>Archivo y Ubicación</th>
                    <th>Confianza</th>
                    <th>Detalles / Pág</th>
                    <th>Acciones Rápidas</th>
                </tr>
            </thead>
            <tbody id="resultsTable">
"""
        for i, item in enumerate(results, 1):
            path_obj = Path(item["path"])
            file_url = path_obj.as_uri()
            clean_path = str(path_obj).replace("\\", "\\\\")

            if item.get("error"):
                status_class = "error"
                badge_html = '<span class="badge warning">⚠️ ERROR</span>'
                status_text = item["error"]
                conf_text = "-"
                details_text = "-"
            elif item["has_cover"]:
                status_class = "con_caratula"
                badge_html = '<span class="badge success">✅ CON CARÁTULA</span>'
                conf_text = f"{int(item['confidence'] * 100)}%"
                details_text = f"Pág {item.get('matched_page', 1)} ({item.get('details', {}).get('inliers', 0)} puntos)"
            else:
                status_class = "sin_caratula"
                badge_html = '<span class="badge danger">❌ SIN CARÁTULA</span>'
                conf_text = f"{int(item['confidence'] * 100)}%"
                details_text = "No hubo coincidencia visual"

            html_template += f"""
                <tr class="row-item {status_class}">
                    <td>{i}</td>
                    <td>{badge_html}</td>
                    <td>
                        <span class="file-name">{item["filename"]}</span>
                        <span class="file-path">{item["path"]}</span>
                    </td>
                    <td><strong>{conf_text}</strong></td>
                    <td style="color: var(--text-muted); font-size: 13px;">{details_text}</td>
                    <td>
                        <div class="actions">
                            <a class="action-link" href="{file_url}" target="_blank">Abrir PDF</a>
                            <button class="action-btn-copy" onclick="copyPath('{clean_path}')">Copiar Ruta</button>
                        </div>
                    </td>
                </tr>
"""

        html_template += """
            </tbody>
        </table>
    </div>

    <script>
        function filterTable(type) {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');

            const rows = document.querySelectorAll('.row-item');
            rows.forEach(r => {
                if (type === 'all' || r.classList.contains(type)) {
                    r.style.display = '';
                } else {
                    r.style.display = 'none';
                }
            });
        }

        function copyPath(path) {
            navigator.clipboard.writeText(path).then(() => {
                alert('Ruta copiada al portapapeles: ' + path);
            }).catch(() => {
                prompt('Copia la ruta:', path);
            });
        }
    </script>
</body>
</html>
"""
        output_path.write_text(html_template, encoding="utf-8")
        return output_path
