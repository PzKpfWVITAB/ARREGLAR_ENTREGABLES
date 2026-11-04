"""Módulo para acceso robusto a archivos en rutas de red locales y remotas (UNC / SMB)."""
import os
import time
import shutil
import tempfile
from pathlib import Path
from typing import List, Generator, Optional
from config import config

class NetworkIOHandler:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or config.LOCAL_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_path(path_str: str) -> Path:
        """Limpia comillas y normaliza la ruta para Windows (incluyendo rutas UNC \\servidor\\...)."""
        clean = path_str.strip().strip('"').strip("'")
        return Path(os.path.abspath(clean))

    @staticmethod
    def test_connectivity(directory_path: Path) -> tuple[bool, str]:
        """Verifica si la ruta de red es alcanzable y legible."""
        if not directory_path.exists():
            return False, f"La ruta '{directory_path}' no existe o no es accesible por la red."
        if not directory_path.is_dir():
            return False, f"La ruta especificada no es un directorio válido: '{directory_path}'."
        
        try:
            # Intento de lectura exploratoria
            _ = next(directory_path.iterdir(), None)
            return True, "Conexión a ruta de red verificada exitosamente."
        except PermissionError:
            return False, f"Permiso denegado para acceder a '{directory_path}'. Verifica credenciales de red."
        except OSError as e:
            return False, f"Error del sistema de archivos de red: {e}"

    @classmethod
    def list_pdf_files(cls, directory_path: Path, recursive: bool = False) -> List[Path]:
        """Lista todos los archivos PDF en el directorio de red con manejo de excepciones."""
        pdfs: List[Path] = []
        try:
            iterator = directory_path.rglob("*.pdf") if recursive else directory_path.glob("*.pdf")
            for item in iterator:
                try:
                    if item.is_file() and not item.name.startswith("._") and not item.name.startswith("~$"):
                        pdfs.append(item)
                except OSError:
                    continue
        except OSError as e:
            print(f"[!] Advertencia al enumerar archivos en red: {e}")
        return sorted(pdfs)

    def get_local_accessible_file(self, network_file_path: Path) -> tuple[Path, bool]:
        """
        Garantiza que el archivo esté listo para PyMuPDF.
        Si COPY_TO_LOCAL_BUFFER es True, copia a cache local para evitar
        latencias de I/O de red continuas y bloqueos de archivo.
        Devuelve (ruta_procesable, es_temporal).
        """
        if not config.COPY_TO_LOCAL_BUFFER:
            return network_file_path, False

        local_temp = self.cache_dir / f"proc_{os.getpid()}_{network_file_path.name}"
        
        last_error = None
        for attempt in range(1, config.NETWORK_MAX_RETRIES + 1):
            try:
                # Copia en chunks protegiendo ante desconexiones transitorias
                with open(network_file_path, "rb") as fsrc, open(local_temp, "wb") as fdst:
                    shutil.copyfileobj(fsrc, fdst, length=64 * 1024)
                return local_temp, True
            except (OSError, IOError) as e:
                last_error = e
                time.sleep(config.NETWORK_RETRY_DELAY_SEC * attempt)
        
        raise IOError(f"No fue posible leer el archivo de red tras {config.NETWORK_MAX_RETRIES} intentos: {network_file_path}. Detalle: {last_error}")

    def cleanup_temp(self, temp_path: Path):
        """Elimina archivo temporal generado."""
        try:
            if temp_path.exists() and temp_path.parent == self.cache_dir:
                temp_path.unlink(missing_ok=True)
        except OSError:
            pass

    def clear_cache(self):
        """Limpia todo el directorio de caché temporal."""
        try:
            shutil.rmtree(self.cache_dir, ignore_errors=True)
        except OSError:
            pass
