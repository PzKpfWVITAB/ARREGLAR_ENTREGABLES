"""Prueba integral del pipeline de detección de carátulas con PDFs sintéticos."""
import os
import sys
import unittest
from pathlib import Path
import numpy as np
import cv2
import pymupdf

# Añadir raíz al sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.network_io import NetworkIOHandler
from src.pdf_processor import PDFProcessor
from src.cover_matcher import CoverMatcher
from src.report_generator import ReportGenerator

class TestCoverDetectionPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = Path(__file__).resolve().parent / "mock_data"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        cls.cover_pdf = cls.test_dir / "modelo_caratula.pdf"
        cls.pdf_with_cover = cls.test_dir / "documento_con_caratula.pdf"
        cls.pdf_without_cover = cls.test_dir / "documento_sin_caratula.pdf"
        cls.pdf_corrupt = cls.test_dir / "documento_corrupto.pdf"

        # 1. Crear PDF Carátula de Referencia
        doc_cover = pymupdf.open()
        page = doc_cover.new_page(width=595, height=842) # A4
        # Dibujar elementos gráficos distintivos (membrete, logotipo geométrico y marco)
        page.draw_rect(pymupdf.Rect(50, 50, 545, 800), color=(0, 0.2, 0.6), width=3)
        page.draw_circle(pymupdf.Point(120, 120), 40, color=(0.8, 0.1, 0.1), fill=(0.9, 0.8, 0.2))
        page.draw_rect(pymupdf.Rect(200, 100, 500, 140), color=(0, 0, 0), fill=(0.2, 0.4, 0.8))
        page.insert_text(pymupdf.Point(150, 250), "GOBIERNO CORPORATIVO - CARATULA OFICIAL", fontsize=18, fontname="helv")
        page.insert_text(pymupdf.Point(220, 320), "CONTRATO MAESTRO DE SERVICIOS", fontsize=14, fontname="helv")
        doc_cover.save(cls.cover_pdf)
        doc_cover.close()

        # 2. Crear PDF con Carátula (Página 1 igual a la carátula + Página 2 texto de cuerpo)
        doc_with = pymupdf.open()
        p1 = doc_with.new_page(width=595, height=842)
        p1.draw_rect(pymupdf.Rect(50, 50, 545, 800), color=(0, 0.2, 0.6), width=3)
        p1.draw_circle(pymupdf.Point(120, 120), 40, color=(0.8, 0.1, 0.1), fill=(0.9, 0.8, 0.2))
        p1.draw_rect(pymupdf.Rect(200, 100, 500, 140), color=(0, 0, 0), fill=(0.2, 0.4, 0.8))
        p1.insert_text(pymupdf.Point(150, 250), "GOBIERNO CORPORATIVO - CARATULA OFICIAL", fontsize=18, fontname="helv")
        p1.insert_text(pymupdf.Point(220, 320), "CONTRATO MAESTRO DE SERVICIOS", fontsize=14, fontname="helv")
        
        p2 = doc_with.new_page(width=595, height=842)
        p2.insert_text(pymupdf.Point(60, 100), "Clausula Primera: El presente contrato estipula los terminos...", fontsize=12)
        doc_with.save(cls.pdf_with_cover)
        doc_with.close()

        # 3. Crear PDF Sin Carátula (solo texto plano sin los gráficos de la carátula)
        doc_without = pymupdf.open()
        pw = doc_without.new_page(width=595, height=842)
        pw.insert_text(pymupdf.Point(60, 100), "ANEXO TECNICO Y LIQUIDACION DE GASTOS", fontsize=16)
        pw.insert_text(pymupdf.Point(60, 140), "Detalle de operaciones bancarias y transferencias...", fontsize=12)
        doc_without.save(cls.pdf_without_cover)
        doc_without.close()

        # 4. Crear archivo corrupto (bytes aleatorios con extensión .pdf)
        with open(cls.pdf_corrupt, "wb") as f:
            f.write(b"%PDF-1.4 Corrupt File Data Testing Random Non-PDF Bytes 0123456789")

    def test_pipeline_execution(self):
        # 1. Probar inicialización del CoverMatcher desde el PDF de carátula
        matcher, err = CoverMatcher.from_pdf(self.cover_pdf)
        self.assertIsNone(err)
        self.assertIsNotNone(matcher)
        self.assertGreater(len(matcher.ref_kp), 20)

        # 2. Probar documento CON carátula
        proc = PDFProcessor()
        imgs_with, err = proc.render_pages_as_images(self.pdf_with_cover)
        self.assertIsNone(err)
        eval_with = matcher.check_document(imgs_with)
        print(f"\n[Test] Evaluación 'Con Carátula': {eval_with}")
        self.assertTrue(eval_with["has_cover"], "Debe detectar que el documento tiene carátula")
        self.assertGreater(eval_with["confidence"], 0.40)

        # 3. Probar documento SIN carátula
        imgs_without, err = proc.render_pages_as_images(self.pdf_without_cover)
        self.assertIsNone(err)
        eval_without = matcher.check_document(imgs_without)
        print(f"[Test] Evaluación 'Sin Carátula': {eval_without}")
        self.assertFalse(eval_without["has_cover"], "Debe determinar que no tiene la carátula")

        # 4. Probar archivo corrupto
        imgs_corrupt, err_corrupt = proc.render_pages_as_images(self.pdf_corrupt)
        self.assertIsNotNone(err_corrupt, "Debe reportar error para archivos corruptos")
        print(f"[Test] Manejo de archivo corrupto: {err_corrupt}")

        # 5. Probar generación de reporte HTML
        results = [
            {"filename": self.pdf_with_cover.name, "path": str(self.pdf_with_cover), "has_cover": True, "confidence": eval_with["confidence"], "matched_page": 1, "error": None, "details": eval_with["details"]},
            {"filename": self.pdf_without_cover.name, "path": str(self.pdf_without_cover), "has_cover": False, "confidence": eval_without["confidence"], "matched_page": 1, "error": None, "details": eval_without["details"]},
            {"filename": self.pdf_corrupt.name, "path": str(self.pdf_corrupt), "has_cover": False, "confidence": 0.0, "matched_page": None, "error": err_corrupt, "details": {}}
        ]
        reporter = ReportGenerator(reference_pdf_name=self.cover_pdf.name, network_dir=str(self.test_dir))
        out_html = self.test_dir / "test_report.html"
        generated_path = reporter.generate_html_report(results, out_html)
        self.assertTrue(generated_path.exists())
        self.assertGreater(generated_path.stat().st_size, 1000)
        print(f"[Test] Reporte HTML generado con éxito en: {generated_path}")

if __name__ == "__main__":
    unittest.main()
