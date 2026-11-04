"""Módulo para detección automática de especificaciones de hardware y asignación del 90% de recursos."""
import os
import sys
import subprocess
import json
import psutil
import cv2

class HardwareDetector:
    @staticmethod
    def detect() -> dict:
        """
        Detecta procesador, memoria RAM y GPU dedicada (con énfasis en NVIDIA).
        Calcula la asignación recomendada al 90% de los recursos.
        """
        # 1. CPU
        cpu_count_logical = psutil.cpu_count(logical=True) or 4
        cpu_count_physical = psutil.cpu_count(logical=False) or max(1, cpu_count_logical // 2)
        recommended_cpu_workers = max(1, int(cpu_count_logical * 0.90))

        # 2. RAM
        mem = psutil.virtual_memory()
        total_ram_gb = round(mem.total / (1024 ** 3), 2)
        avail_ram_gb = round(mem.available / (1024 ** 3), 2)
        recommended_ram_limit_gb = round(total_ram_gb * 0.90, 2)

        # 3. GPU (NVIDIA y genérica)
        gpus = HardwareDetector._detect_gpus()
        has_nvidia = any("nvidia" in g.get("name", "").lower() for g in gpus)
        nvidia_gpu = next((g for g in gpus if "nvidia" in g.get("name", "").lower()), None)
        
        # Soporte de aceleración OpenCL en OpenCV
        has_opencl = cv2.ocl.haveOpenCL()
        if has_opencl:
            cv2.ocl.setUseOpenCL(True)

        return {
            "cpu": {
                "logical_cores": cpu_count_logical,
                "physical_cores": cpu_count_physical,
                "usage_target_percent": 90,
                "recommended_workers": recommended_cpu_workers
            },
            "ram": {
                "total_gb": total_ram_gb,
                "available_gb": avail_ram_gb,
                "usage_target_percent": 90,
                "recommended_limit_gb": recommended_ram_limit_gb
            },
            "gpu": {
                "detected": len(gpus) > 0,
                "has_nvidia": has_nvidia,
                "primary": nvidia_gpu or (gpus[0] if gpus else {"name": "No detectada", "vram_gb": 0}),
                "all_gpus": gpus,
                "opencl_acceleration": has_opencl,
                "acceleration_active": has_nvidia or has_opencl
            }
        }

    @staticmethod
    def _detect_gpus() -> list:
        gpus = []
        
        # Intento 1: Consultar nvidia-smi directamente
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().split("\n"):
                    parts = [p.strip() for p in line.split(",")]
                    name = parts[0]
                    vram_mb = float(parts[1]) if len(parts) > 1 and parts[1].replace(".", "").isdigit() else 0
                    gpus.append({
                        "name": name,
                        "vram_gb": round(vram_mb / 1024.0, 2),
                        "is_nvidia": True,
                        "source": "nvidia-smi"
                    })
                if gpus:
                    return gpus
        except Exception:
            pass

        # Intento 2: PowerShell Win32_VideoController (detecta cualquier GPU dedicada en Windows)
        try:
            cmd = "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | ConvertTo-Json"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = item.get("Name", "GPU Desconocida")
                    # Descartar adaptadores virtuales o básicos
                    if "virtual" in name.lower() or "basic render" in name.lower():
                        continue
                    vram_bytes = item.get("AdapterRAM") or 0
                    vram_gb = round(vram_bytes / (1024 ** 3), 2)
                    is_nvidia = "nvidia" in name.lower()
                    gpus.append({
                        "name": name,
                        "vram_gb": vram_gb,
                        "is_nvidia": is_nvidia,
                        "source": "Win32_VideoController"
                    })
        except Exception:
            pass

        return gpus

if __name__ == "__main__":
    hw = HardwareDetector.detect()
    print(json.dumps(hw, indent=2))
