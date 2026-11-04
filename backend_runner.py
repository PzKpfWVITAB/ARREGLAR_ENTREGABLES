"""Servicio backend en Python para integración en tiempo real con la interfaz Electron."""
import os
import sys
import json
import argparse
from pathlib import Path

# Asegurar flush inmediato para comunicación continua por pipe con Electron
def emit(event_type: str, data: dict = None):
    payload = {"type": event_type}
    if data:
        payload.update(data)
    print(json.dumps(payload, ensure_ascii=False), flush=True)

# Añadir ruta raíz al path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config
from src.network_io import NetworkIOHandler
from src.pdf_processor import PDFProcessor
from src.cover_matcher import CoverMatcher

def main():
    parser = argparse.ArgumentParser(description="Backend runner para Electron")
    parser.add_argument("--test-dir", help="Verifica conectividad y cuenta archivos")
    parser.add_argument("--dir", help="Directorio de red a procesar")
    parser.add_argument("--cover", help="Ruta de la carátula de referencia")
    parser.add_argument("--recursive", action="store_true", help="Escaneo recursivo")
    parser.add_argument("--pages", type=int, default=2, help="Páginas a verificar")
    args = parser.parse_args()

    # Modo de prueba rápida de conectividad
    if args.test_dir:
        dir_path = NetworkIOHandler.normalize_path(args.test_dir)
        ok, msg = NetworkIOHandler.test_connectivity(dir_path)
        if not ok:
            emit("test_result", {"ok": False, "message": msg, "count": 0})
            sys.exit(0)
        pdfs = NetworkIOHandler.list_pdf_files(dir_path, recursive=args.recursive)
        emit("test_result", {"ok": True, "message": msg, "count": len(pdfs)})
        sys.exit(0)

    if not args.dir or not args.cover:
        emit("error", {"message": "Se requieren los parámetros --dir y --cover"})
        sys.exit(1)

    work_dir = NetworkIOHandler.normalize_path(args.dir)
    cover_path = NetworkIOHandler.normalize_path(args.cover)

    # 1. Probar conectividad
    ok, msg = NetworkIOHandler.test_connectivity(work_dir)
    if not ok:
        emit("error", {"message": f"Error de acceso al directorio: {msg}"})
        sys.exit(1)

    if not cover_path.exists():
        emit("error", {"message": f"El archivo de carátula no existe: {cover_path}"})
        sys.exit(1)

    # 2. Listar archivos
    pdfs = NetworkIOHandler.list_pdf_files(work_dir, recursive=args.recursive)
    total_files = len(pdfs)
    emit("init", {"total_files": total_files, "work_dir": str(work_dir)})

    if total_files == 0:
        emit("finished", {
            "summary": {"total": 0, "with_cover": 0, "without_cover": 0, "errors": 0},
            "results": []
        })
        sys.exit(0)

    # 3. Inicializar comparador con la carátula
    emit("status", {"message": "Extrayendo rasgos visuales de la carátula..."})
    io_handler = NetworkIOHandler()
    local_cover, is_temp_cover = io_handler.get_local_accessible_file(cover_path)

    try:
        matcher, err = CoverMatcher.from_pdf(local_cover)
        if err or matcher is None:
            emit("error", {"message": f"No se pudo procesar la carátula: {err}"})
            sys.exit(1)
    finally:
        if is_temp_cover:
            io_handler.cleanup_temp(local_cover)

    emit("cover_ready", {"keypoints": len(matcher.ref_kp), "cover_name": cover_path.name})

    # 4. Procesamiento secuencial enviando eventos por cada PDF
    pdf_processor = PDFProcessor()
    results = []
    with_cover_count = 0
    without_cover_count = 0
    error_count = 0

    for idx, pdf in enumerate(pdfs, 1):
        # Omitir la propia carátula si está en la lista
        if pdf.resolve() == cover_path.resolve():
            continue

        emit("progress", {
            "current": idx,
            "total": total_files,
            "filename": pdf.name,
            "percent": round((idx / total_files) * 100, 1)
        })

        item_result = {
            "index": idx,
            "filename": pdf.name,
            "path": str(pdf),
            "has_cover": False,
            "confidence": 0.0,
            "matched_page": None,
            "error": None,
            "details": {}
        }

        try:
            local_proc_path, is_temp = io_handler.get_local_accessible_file(pdf)
        except Exception as e:
            item_result["error"] = f"Error de lectura en red: {e}"
            error_count += 1
            results.append(item_result)
            emit("item_done", {"item": item_result})
            continue

        try:
            pages_imgs, render_err = pdf_processor.render_pages_as_images(local_proc_path, max_pages=args.pages)
            if render_err:
                item_result["error"] = render_err
                error_count += 1
            else:
                doc_eval = matcher.check_document(pages_imgs)
                item_result["has_cover"] = doc_eval["has_cover"]
                item_result["confidence"] = doc_eval["confidence"]
                item_result["matched_page"] = doc_eval["matched_page"]
                item_result["details"] = doc_eval.get("details", {})
                
                if doc_eval["has_cover"]:
                    with_cover_count += 1
                else:
                    without_cover_count += 1
        except Exception as e:
            item_result["error"] = f"Excepción durante análisis: {e}"
            error_count += 1
        finally:
            if is_temp:
                io_handler.cleanup_temp(local_proc_path)

        results.append(item_result)
        emit("item_done", {"item": item_result})

    # 5. Emitir finalización
    emit("finished", {
        "summary": {
            "total": len(results),
            "with_cover": with_cover_count,
            "without_cover": without_cover_count,
            "errors": error_count
        },
        "results": results
    })

if __name__ == "__main__":
    main()
