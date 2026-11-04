"""Módulo de Visión Artificial para comparación y detección de carátulas de documentos."""
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import numpy as np
import cv2
from config import config
from src.pdf_processor import PDFProcessor

class CoverMatcher:
    def __init__(self, reference_cover_img: np.ndarray):
        """
        Inicializa el comparador extrayendo características de la carátula de referencia.
        """
        self.processor = PDFProcessor()
        self.reference_img = reference_cover_img
        self.reference_enhanced = self.processor.preprocess_image_for_matching(reference_cover_img)
        
        # Detector ORB para detección de puntos clave robustos
        self.orb = cv2.ORB_create(
            nfeatures=config.ORB_N_FEATURES,
            scaleFactor=1.2,
            nlevels=8,
            edgeThreshold=31,
            firstLevel=0,
            WTA_K=2,
            scoreType=cv2.ORB_HARRIS_SCORE,
            patchSize=31,
            fastThreshold=20
        )
        
        # Extraer puntos y descriptores de la carátula de referencia
        self.ref_kp, self.ref_des = self.orb.detectAndCompute(self.reference_enhanced, None)
        
        # Matcher BF con distancia Hamming para descriptores binarios ORB
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    @classmethod
    def from_pdf(cls, reference_pdf_path: Path) -> Tuple[Optional["CoverMatcher"], Optional[str]]:
        """Construye el comparador a partir de la primera página del PDF modelo de carátula."""
        proc = PDFProcessor()
        images, err = proc.render_pages_as_images(reference_pdf_path, max_pages=1)
        if err or not images:
            return None, f"No se pudo cargar la carátula del PDF de referencia: {err}"
        
        return cls(images[0]), None

    def _calculate_ssim(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Calcula el índice de similitud estructural (SSIM) simplificado de forma nativa con OpenCV."""
        h1, w1 = img1.shape[:2]
        h2, w2 = img2.shape[:2]
        # Redimensionar a una escala común fija para comparar layout estructural
        target_size = (300, 420)
        i1 = cv2.resize(img1, target_size, interpolation=cv2.INTER_AREA).astype(np.float64)
        i2 = cv2.resize(img2, target_size, interpolation=cv2.INTER_AREA).astype(np.float64)

        c1 = (0.01 * 255) ** 2
        c2 = (0.03 * 255) ** 2

        mu1 = cv2.GaussianBlur(i1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(i2, (11, 11), 1.5)

        mu1_sq = mu1 * mu1
        mu2_sq = mu2 * mu2
        mu1_mu2 = mu1 * mu2

        sigma1_sq = cv2.GaussianBlur(i1 * i1, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(i2 * i2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(i1 * i2, (11, 11), 1.5) - mu1_mu2

        ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / ((mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2))
        return float(np.mean(ssim_map))

    def evaluate_page(self, page_img: np.ndarray) -> Dict[str, Any]:
        """
        Evalúa una página candidata contra la carátula de referencia.
        Utiliza Lowe's Ratio Test + RANSAC Homography + SSIM.
        """
        page_enhanced = self.processor.preprocess_image_for_matching(page_img)
        cand_kp, cand_des = self.orb.detectAndCompute(page_enhanced, None)

        if self.ref_des is None or cand_des is None or len(cand_des) < 10:
            return {
                "has_cover": False,
                "confidence": 0.0,
                "good_matches": 0,
                "inliers": 0,
                "inlier_ratio": 0.0,
                "ssim": 0.0,
                "reason": "Descriptores insuficientes para análisis visual."
            }

        # Búsqueda de los 2 mejores vecinos (k-NN)
        try:
            raw_matches = self.matcher.knnMatch(self.ref_des, cand_des, k=2)
        except cv2.error:
            return {
                "has_cover": False,
                "confidence": 0.0,
                "good_matches": 0,
                "inliers": 0,
                "inlier_ratio": 0.0,
                "ssim": 0.0,
                "reason": "Error en comparación de vectores de características."
            }

        # Filtrar mediante Lowe's Ratio Test (más estricto: 0.70)
        good_matches = []
        for pair in raw_matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < 0.70 * n.distance:
                    good_matches.append(m)

        inliers_count = 0
        inlier_ratio = 0.0
        valid_homography = False

        if len(good_matches) >= config.ORB_MIN_GOOD_MATCHES:
            src_pts = np.float32([self.ref_kp[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([cand_kp[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            # Homografía con RANSAC
            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 4.0)
            if mask is not None and H is not None:
                inliers_count = int(np.sum(mask))
                inlier_ratio = inliers_count / len(good_matches)
                
                # Validación geométrica de la homografía (evitar transformaciones degeneradas o invertidas)
                det = np.linalg.det(H[:2, :2])
                if 0.2 < abs(det) < 5.0:  # Escala razonable entre documentos (0.5x a 2.2x)
                    valid_homography = True

        # Cobertura de puntos clave con respecto a la carátula de referencia
        total_ref_kp = max(1, len(self.ref_kp))
        template_coverage = inliers_count / total_ref_kp

        # Similitud estructural complementaria (solo decisiva si es muy alta >= 0.88 para compensar fondos)
        ssim_score = self._calculate_ssim(self.reference_enhanced, page_enhanced)

        # Regla de decisión:
        # 1. Homografía válida + alto número de inliers (>= 80) + buena cobertura del template (>= 8%)
        # O 2. SSIM extremadamente alto (>= 0.88) junto con coincidencia de rasgos
        has_feature_match = (
            valid_homography and 
            inliers_count >= 80 and 
            template_coverage >= 0.08 and
            inlier_ratio >= config.MIN_INLIER_RATIO
        )
        has_identical_ssim = ssim_score >= 0.90 and inliers_count >= 40

        has_cover = has_feature_match or has_identical_ssim
        
        # Puntuación de confianza normalizada (0.0 a 1.0)
        conf_score = min(1.0, (inliers_count / 150.0) * 0.6 + (template_coverage / 0.25) * 0.4)
        if not has_cover:
            conf_score = min(0.35, conf_score)

        return {
            "has_cover": bool(has_cover),
            "confidence": round(float(conf_score if has_cover else max(0.0, conf_score * 0.5)), 3),
            "good_matches": len(good_matches),
            "inliers": inliers_count,
            "inlier_ratio": round(float(inlier_ratio), 3),
            "template_coverage": round(float(template_coverage), 3),
            "ssim": round(float(ssim_score), 3),
            "reason": "Coincidencia geométrica de carátula confirmada." if has_cover else "No coincide con el patrón visual de la carátula."
        }

    def check_document(self, pages_images: list[np.ndarray]) -> Dict[str, Any]:
        """
        Revisa las páginas del documento. Si cualquiera de las primeras N páginas
        cumple con el patrón de la carátula, se clasifica como CON CARÁTULA.
        """
        best_result = {
            "has_cover": False,
            "confidence": 0.0,
            "matched_page": None,
            "details": {}
        }

        for idx, page_img in enumerate(pages_images):
            page_eval = self.evaluate_page(page_img)
            if page_eval["has_cover"] and page_eval["confidence"] > best_result["confidence"]:
                best_result["has_cover"] = True
                best_result["confidence"] = page_eval["confidence"]
                best_result["matched_page"] = idx + 1
                best_result["details"] = page_eval

        # Si ninguna cumplió, guardar los detalles de la mejor aproximación para depuración
        if not best_result["has_cover"] and pages_images:
            eval_p1 = self.evaluate_page(pages_images[0])
            best_result["confidence"] = eval_p1["confidence"]
            best_result["matched_page"] = 1
            best_result["details"] = eval_p1

        return best_result
