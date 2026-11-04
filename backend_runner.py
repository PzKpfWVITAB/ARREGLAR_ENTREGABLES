"""Servicio backend en Python para integración en tiempo real con la interfaz Electron."""
import os
import sys
import json
import argparse
import concurrent.futures
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
from src.hardware_detector import HardwareDetector
import cv2

def main():
    parser = argparse.ArgumentParser(description="Backend runner para Electron")
    parser.add_argument("--detect-hw", action="store_true", help="Detecta y devuelve las capacidades de hardware")
    parser.add_argument("--test-dir", help="Verifica conectividad y cuenta archivos")
    parser.add_argument("--dir", help="Directorio de red a procesar")
    parser.add_argument("--cover", help="Ruta de la carátula de referencia")
    parser.add_argument("--recursive", action="store_true", help="Escaneo recursivo")
    parser.add_argument("--pages", type=int, default=2, help="Páginas a verificar")
    parser.add_argument("--workers", type=int, default=None, help="Número de hilos/workers paralelos")
    parser.add_argument("--use-gpu", action="store_true", default=True, help="Habilitar aceleración por GPU")
    args = parser.parse_args()

    # Modo de detección de Hardware
    if args.detect_hw:
        hw_info = HardwareDetector.detect()
        emit("hw_info", {"data": hw_info})
        sys.exit(0)

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

    # Detección de hardware y asignación de recursos al 90%
    hw = HardwareDetector.detect()
    workers = args.workers or hw["cpu"]["recommended_workers"]
    
    if args.use_gpu and cv2.ocl.haveOpenCL():
        cv2.ocl.setUseOpenCL(True)

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
    # Excluir la propia carátula del lote
    target_pdfs = [p for p in pdfs if p.resolve() != cover_path.resolve()]
    total_files = len(target_pdfs)
    
    emit("init", {
        "total_files": total_files,
        "work_dir": str(work_dir),
        "workers_active": workers,
        "gpu_accelerated": args.use_gpu and hw["gpu"]["acceleration_active"],
        "gpu_name": hw["gpu"]["primary"]["name"]
    })

    if total_files == 0:
        emit("finished", {
            "summary": {"total": 0, "with_cover": 0, "without_cover": 0, "errors": 0},
            "results": []
        })
        sys.exit(0)

    # 3. Inicializar comparador con la carátula
    emit("status", {"message": f"Extrayendo rasgos de carátula y configurando {workers} workers paralelos (90% CPU)..."})
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

    # 4. Procesamiento Paralelo Masivo
    pdf_processor = PDFProcessor()
    results = []
    processed_count = 0
    with_cover_count = 0
    without_cover_count = 0
    error_count = 0

    def evaluate_single_file(item_info):
        idx, pdf = item_info
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

        try:
            local_proc_path, is_temp = io_handler.get_local_accessible_file(pdf)
        except Exception as e:
            res["error"] = f"Error de lectura en red: {e}"
            return res

        try:
            pages_imgs, render_err = pdf_processor.render_pages_as_images(local_proc_path, max_pages=args.pages)
            if render_err:
                res["error"] = render_err
            else:
                doc_eval = matcher.check_document(pages_imgs)
                res["has_cover"] = doc_eval["has_cover"]
                res["confidence"] = doc_eval["confidence"]
                res["matched_page"] = doc_eval["matched_page"]
                res["details"] = doc_eval.get("details", {})
        except Exception as e:
            res["error"] = f"Excepción durante análisis: {e}"
        finally:
            if is_temp:
                io_handler.cleanup_temp(local_proc_path)

        return res

    indexed_files = list(enumerate(target_pdfs, 1))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_pdf = {executor.submit(evaluate_single_file, item): item for item in indexed_files}
        
        for future in concurrent.futures.as_completed(future_to_pdf):
            item_result = future.result()
            processed_count += 1
            
            if item_result["error"]:
                error_count += 1
            elif item_result["has_cover"]:
                with_cover_count += 1
            else:
                without_cover_count += 1

            results.append(item_result)

            emit("progress", {
                "current": processed_count,
                "total": total_files,
                "filename": item_result["filename"],
                "percent": round((processed_count / total_files) * 100, 1)
            })
            emit("item_done", {"item": item_result})

    # Ordenar por índice para que aparezcan en orden secuencial en el reporte final
    results.sort(key=lambda x: x["index"])

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
