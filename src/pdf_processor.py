"""Módulo para lectura, renderizado y preprocesamiento de páginas PDF con PyMuPDF y OpenCV."""
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
import cv2
import pymupdf  # PyMuPDF 2.0
from config import config

class PDFProcessor:
    def __init__(self, dpi: int = config.RENDER_DPI):
        self.dpi = dpi
        # Factor de escala (72 puntos por pulgada base en PDF)
        self.zoom = dpi / 72.0
        self.matrix = pymupdf.Matrix(self.zoom, self.zoom)

    def render_pages_as_images(
        self, 
        pdf_path: Path, 
        max_pages: int = config.MAX_PAGES_TO_CHECK
    ) -> Tuple[List[np.ndarray], Optional[str]]:
        """
        Renderiza las primeras N páginas de un PDF a imágenes BGR (OpenCV).
        Retorna (lista_de_imagenes, mensaje_error_si_hubo).
        """
        images: List[np.ndarray] = []
        try:
            doc = pymupdf.open(pdf_path)
            if doc.is_encrypted:
                return [], "PDF protegido con contraseña."
            
            total_pages = len(doc)
            if total_pages == 0:
                return [], "PDF vacío (0 páginas)."

            pages_to_process = min(total_pages, max_pages)
            for page_idx in range(pages_to_process):
                page = doc.load_page(page_idx)
                pix = page.get_pixmap(matrix=self.matrix, alpha=False)
                
                # Convertir buffer de PyMuPDF a array NumPy BGR
                img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
                if pix.n == 3:
                    # RGB a BGR para OpenCV
                    bgr_img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
                elif pix.n == 1:
                    # Escala de grises a BGR
                    bgr_img = cv2.cvtColor(img_data, cv2.COLOR_GRAY2BGR)
                else:
                    bgr_img = img_data[:, :, :3]
                
                images.append(bgr_img)
            
            doc.close()
            return images, None

        except pymupdf.FileDataError:
            return [], "Archivo PDF dañado o formato no válido."
        except Exception as e:
            return [], f"Error al procesar PDF: {str(e)}"

    @staticmethod
    def preprocess_image_for_matching(img_bgr: np.ndarray) -> np.ndarray:
        """
        Aplica escala de grises y CLAHE para resaltar elementos y logos
        en documentos con fondos opacos o desvanecidos.
        """
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return enhanced

    @staticmethod
    def create_thumbnail(img_bgr: np.ndarray, max_width: int = 300) -> np.ndarray:
        """Genera una miniatura pequeña para previsualizaciones rápidas."""
        h, w = img_bgr.shape[:2]
        if w <= max_width:
            return img_bgr
        scale = max_width / float(w)
        new_w = max_width
        new_h = int(h * scale)
        return cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)
