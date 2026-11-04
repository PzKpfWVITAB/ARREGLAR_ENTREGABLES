"""Configuración central para el procesador de documentos y detector de carátulas."""
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

@dataclass
class AppConfig:
    # Modo de ejecución (100% local por defecto, sin requerir APIs externas)
    USE_LOCAL_TOOLS_ONLY: bool = True
    
    # Parámetros de renderizado de visión
    RENDER_DPI: int = 150  # 150 DPI ofrece un balance óptimo entre velocidad y detalle de keypoints
    MAX_PAGES_TO_CHECK: int = 2  # Revisa página 1 y 2 por si hay hojas de guarda/blanco
    
    # Umbrales para comparación visual de carátulas
    # Se utiliza Feature Matching (ORB/SIFT) + SSIM / Perceptual Hash
    ORB_N_FEATURES: int = 2000
    ORB_MIN_GOOD_MATCHES: int = 25      # Mínimo de puntos de coincidencia de alta calidad
    MIN_INLIER_RATIO: float = 0.22      # Porcentaje mínimo de inliers tras RANSAC
    SSIM_FALLBACK_THRESHOLD: float = 0.60 # Similitud estructural complementaria
    
    # Manejo de Rutas de Red (SMB / UNC / Unidades compartidas)
    NETWORK_MAX_RETRIES: int = 3
    NETWORK_RETRY_DELAY_SEC: float = 1.5
    COPY_TO_LOCAL_BUFFER: bool = True   # Copia temporal a RAM/SSD para evitar cuellos de botella de red
    LOCAL_CACHE_DIR: Path = Path(tempfile.gettempdir()) / "doc_cover_checker_cache"

config = AppConfig()
