"""Script principal e interactivo para detección de carátulas en documentos PDF sobre rutas de red."""
import os
import sys
import argparse
from pathlib import Path
from tqdm import tqdm
from colorama import init, Fore, Style

# Inicializar colores en terminal Windows
init(autoreset=True)

# Asegurar que el directorio raíz esté en el PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config
from src.network_io import NetworkIOHandler
from src.pdf_processor import PDFProcessor
from src.cover_matcher import CoverMatcher
from src.report_generator import ReportGenerator

def print_banner():
    print(Fore.CYAN + "=" * 75)
    print(Fore.CYAN + "   VERIFICADOR DE CARÁTULAS EN DOCUMENTOS PDF (MODO 100% LOCAL)")
    print(Fore.CYAN + "   Optimizado para rutas de red (UNC / SMB / Unidades compartidas)")
    print(Fore.CYAN + "=" * 75 + Style.RESET_ALL)
    print("Modo de ejecución: " + Fore.GREEN + "Local (OpenCV + PyMuPDF)" + Style.RESET_ALL)
    print()

def ask_directory() -> Path:
    while True:
        raw_dir = input(Fore.YELLOW + ">> Ingrese la ruta del directorio de trabajo (ej. \\\\servidor\\docs o Z:\\archivos): " + Style.RESET_ALL).strip()
        if not raw_dir:
            print(Fore.RED + "[!] Por favor ingrese una ruta no vacía." + Style.RESET_ALL)
            continue
        
        norm_dir = NetworkIOHandler.normalize_path(raw_dir)
        print(f"[*] Verificando conectividad con: {norm_dir} ...")
        ok, msg = NetworkIOHandler.test_connectivity(norm_dir)
        if ok:
            print(Fore.GREEN + f"[+] {msg}" + Style.RESET_ALL)
            return norm_dir
        else:
            print(Fore.RED + f"[!] {msg}" + Style.RESET_ALL)
            retry = input("¿Desea reintentar con otra ruta? (s/n): ").strip().lower()
            if retry != 's':
                sys.exit(1)

def ask_cover_pdf(work_dir: Path, pdfs_list: list[Path]) -> Path:
    while True:
        print("\nOpciones para la carátula de referencia:")
        print("  1. Ingresar una ruta completa o de red del PDF de la carátula.")
        print("  2. Seleccionar uno de los PDFs encontrados en la carpeta actual.")
        choice = input(Fore.YELLOW + ">> Elija una opción (1 o 2): " + Style.RESET_ALL).strip()

        if choice == '1':
            raw_path = input(Fore.YELLOW + ">> Ingrese la ruta completa del PDF de la carátula modelo: " + Style.RESET_ALL).strip()
            cover_path = NetworkIOHandler.normalize_path(raw_path)
            if cover_path.exists() and cover_path.suffix.lower() == '.pdf':
                return cover_path
            else:
                print(Fore.RED + f"[!] Archivo no encontrado o no es un PDF válido: {cover_path}" + Style.RESET_ALL)
        
        elif choice == '2':
            if not pdfs_list:
                print(Fore.RED + "[!] No hay archivos PDF en la carpeta seleccionada." + Style.RESET_ALL)
                continue
            
            print(Fore.CYAN + "\nArchivos disponibles en la carpeta:" + Style.RESET_ALL)
            for idx, p in enumerate(pdfs_list[:15], 1):
                print(f"  [{idx}] {p.name}")
            if len(pdfs_list) > 15:
                print(f"  ... y {len(pdfs_list) - 15} archivos más.")
            
            sel = input(Fore.YELLOW + f">> Ingrese el número del archivo que servirá de carátula (1-{min(15, len(pdfs_list))}): " + Style.RESET_ALL).strip()
            if sel.isdigit() and 1 <= int(sel) <= min(15, len(pdfs_list)):
                return pdfs_list[int(sel) - 1]
            else:
                print(Fore.RED + "[!] Selección no válida." + Style.RESET_ALL)

def interactive_shortcuts_menu(results: list[dict], report_html_path: Path):
    """Bucle interactivo para abrir archivos o carpetas directamente mediante atajos."""
    while True:
        print("\n" + Fore.CYAN + "-" * 75 + Style.RESET_ALL)
        print(Fore.YELLOW + "ATAJOS RÁPIDOS DE ACCESO:" + Style.RESET_ALL)
        print(" • Ingrese el " + Fore.GREEN + "número del archivo" + Style.RESET_ALL + " para abrir el PDF directamente.")
        print(" • Ingrese " + Fore.GREEN + "'e [número]'" + Style.RESET_ALL + " para abrir la carpeta y seleccionarlo en el Explorador.")
        print(" • Ingrese " + Fore.GREEN + "'r'" + Style.RESET_ALL + " para reabrir el reporte HTML interactivo en el navegador.")
        print(" • Ingrese " + Fore.GREEN + "'s'" + Style.RESET_ALL + " para listar solo los archivos SIN carátula.")
        print(" • Ingrese " + Fore.GREEN + "'c'" + Style.RESET_ALL + " para listar solo los archivos CON carátula.")
        print(" • Ingrese " + Fore.GREEN + "'q'" + Style.RESET_ALL + " para salir.")
        
        cmd = input(Fore.CYAN + ">> Acción: " + Style.RESET_ALL).strip()
        if not cmd:
            continue

        if cmd.lower() == 'q':
            print("[*] Saliendo del programa.")
            break
        elif cmd.lower() == 'r':
            import webbrowser
            webbrowser.open(report_html_path.as_uri())
            print(f"[>] Abriendo reporte HTML: {report_html_path.name}")
        elif cmd.lower() == 's':
            print(Fore.RED + "\n=== ARCHIVOS SIN CARÁTULA ===" + Style.RESET_ALL)
            for i, r in enumerate(results, 1):
                if not r.get("has_cover") and not r.get("error"):
                    print(f"  [{i:03d}] {r['filename']} (Confianza: {int(r['confidence']*100)}%)")
        elif cmd.lower() == 'c':
            print(Fore.GREEN + "\n=== ARCHIVOS CON CARÁTULA ===" + Style.RESET_ALL)
            for i, r in enumerate(results, 1):
                if r.get("has_cover"):
                    print(f"  [{i:03d}] {r['filename']} (Confianza: {int(r['confidence']*100)}% - Pág {r.get('matched_page')})")
        elif cmd.lower().startswith("e "):
            num_part = cmd[2:].strip()
            if num_part.isdigit() and 1 <= int(num_part) <= len(results):
                target = Path(results[int(num_part) - 1]["path"])
                ReportGenerator.show_in_explorer(target)
            else:
                print(Fore.RED + "[!] Número fuera de rango." + Style.RESET_ALL)
        elif cmd.isdigit():
            idx = int(cmd)
            if 1 <= idx <= len(results):
                target = Path(results[idx - 1]["path"])
                ReportGenerator.open_file_in_viewer(target)
            else:
                print(Fore.RED + "[!] Número fuera de rango." + Style.RESET_ALL)
        else:
            print(Fore.RED + "[!] Comando no reconocido." + Style.RESET_ALL)

def main():
    parser = argparse.ArgumentParser(description="Verificador de carátulas de PDFs sobre red (Modo Local)")
    parser.add_argument("--dir", help="Directorio de red o local donde están los PDFs")
    parser.add_argument("--cover", help="Ruta del PDF con la carátula de referencia")
    parser.add_argument("--recursive", action="store_true", help="Buscar PDFs recursivamente en subdirectorios")
    args = parser.parse_args()

    print_banner()

    # 1. Obtención y validación de directorio de red
    if args.dir:
        work_dir = NetworkIOHandler.normalize_path(args.dir)
        ok, msg = NetworkIOHandler.test_connectivity(work_dir)
        if not ok:
            print(Fore.RED + f"[!] Error con directorio proporcionado: {msg}" + Style.RESET_ALL)
            sys.exit(1)
    else:
        work_dir = ask_directory()

    # 2. Enumerar archivos PDF
    print(f"\n[*] Escaneando archivos PDF en: {work_dir} ...")
    pdfs = NetworkIOHandler.list_pdf_files(work_dir, recursive=args.recursive)
    print(f"[+] Total de PDFs encontrados: {Fore.CYAN}{len(pdfs)}{Style.RESET_ALL}")
    
    if not pdfs:
        print(Fore.YELLOW + "[!] No se encontraron archivos PDF para procesar." + Style.RESET_ALL)
        sys.exit(0)

    # 3. Selección de la carátula de referencia
    if args.cover:
        cover_pdf_path = NetworkIOHandler.normalize_path(args.cover)
        if not cover_pdf_path.exists():
            print(Fore.RED + f"[!] Carátula especificada no existe: {cover_pdf_path}" + Style.RESET_ALL)
            sys.exit(1)
    else:
        cover_pdf_path = ask_cover_pdf(work_dir, pdfs)

    # 4. Inicializar motor de visión con la carátula modelo
    print(f"\n[*] Extrayendo características visuales de la carátula: {Fore.YELLOW}{cover_pdf_path.name}{Style.RESET_ALL} ...")
    io_handler = NetworkIOHandler()
    local_cover_path, is_temp_cover = io_handler.get_local_accessible_file(cover_pdf_path)
    
    try:
        matcher, err = CoverMatcher.from_pdf(local_cover_path)
        if err or matcher is None:
            print(Fore.RED + f"[!] Error al cargar carátula: {err}" + Style.RESET_ALL)
            sys.exit(1)
    finally:
        if is_temp_cover:
            io_handler.cleanup_temp(local_cover_path)

    print(Fore.GREEN + f"[+] Carátula procesada. Puntos clave de referencia extraídos: {len(matcher.ref_kp)}" + Style.RESET_ALL)

    # 5. Procesamiento por lote de todos los PDFs
    print(Fore.CYAN + f"\n[*] Iniciando análisis de {len(pdfs)} documentos..." + Style.RESET_ALL)
    
    pdf_processor = PDFProcessor()
    results = []

    progress_bar = tqdm(pdfs, desc="Procesando PDFs", unit="doc")
    for pdf_path in progress_bar:
        # Excluir la propia carátula de referencia si está en la lista para no redundar
        if pdf_path.resolve() == cover_pdf_path.resolve():
            continue

        item_result = {
            "filename": pdf_path.name,
            "path": str(pdf_path),
            "has_cover": False,
            "confidence": 0.0,
            "matched_page": None,
            "error": None,
            "details": {}
        }

        # Obtener archivo en buffer local para mitigar latencia y bloqueos de red
        try:
            local_proc_path, is_temp = io_handler.get_local_accessible_file(pdf_path)
        except Exception as e:
            item_result["error"] = str(e)
            results.append(item_result)
            continue

        try:
            # Renderizado seguro de las primeras páginas
            pages_imgs, render_err = pdf_processor.render_pages_as_images(local_proc_path)
            if render_err:
                item_result["error"] = render_err
            else:
                # Evaluación visual
                doc_eval = matcher.check_document(pages_imgs)
                item_result["has_cover"] = doc_eval["has_cover"]
                item_result["confidence"] = doc_eval["confidence"]
                item_result["matched_page"] = doc_eval["matched_page"]
                item_result["details"] = doc_eval.get("details", {})
        except Exception as e:
            item_result["error"] = f"Excepción durante análisis: {e}"
        finally:
            if is_temp:
                io_handler.cleanup_temp(local_proc_path)

        results.append(item_result)

    # 6. Generación de estadísticas y reporte
    sin_caratula = [r for r in results if not r.get("has_cover") and not r.get("error")]
    con_caratula = [r for r in results if r.get("has_cover") and not r.get("error")]
    errores = [r for r in results if r.get("error")]

    print("\n" + Fore.CYAN + "=" * 75 + Style.RESET_ALL)
    print(Fore.CYAN + "   RESUMEN FINAL DEL PROCESAMIENTO" + Style.RESET_ALL)
    print(Fore.CYAN + "=" * 75 + Style.RESET_ALL)
    print(f"Total analizados:     {Fore.WHITE}{len(results)}{Style.RESET_ALL}")
    print(f"❌ Sin Carátula:      {Fore.RED}{len(sin_caratula)}{Style.RESET_ALL}")
    print(f"✅ Con Carátula:      {Fore.GREEN}{len(con_caratula)}{Style.RESET_ALL}")
    if errores:
        print(f"⚠️  Errores / Dañados: {Fore.YELLOW}{len(errores)}{Style.RESET_ALL}")
    print(Fore.CYAN + "=" * 75 + Style.RESET_ALL)

    # 7. Generar reporte HTML
    reporter = ReportGenerator(reference_pdf_name=cover_pdf_path.name, network_dir=str(work_dir))
    report_html_path = Path(os.getcwd()) / "reporte_caratulas.html"
    reporter.generate_html_report(results, report_html_path)
    print(Fore.GREEN + f"\n[+] Reporte interactivo generado en: {report_html_path.resolve()}" + Style.RESET_ALL)

    # Abrir el reporte HTML automáticamente en el navegador
    import webbrowser
    webbrowser.open(report_html_path.as_uri())

    # 8. Menú interactivo de atajos
    interactive_shortcuts_menu(results, report_html_path)

if __name__ == "__main__":
    main()
