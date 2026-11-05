@echo off
setlocal enabledelayedexpansion
title Instalador - Verificador de Caratulas PDF (Windows Forms)

echo =======================================================================
echo     INSTALADOR DEL SISTEMA - VERIFICADOR DE CARATULAS EN PDFS
echo     Interfaz Nativa de Windows (Sin Node.js / Sin Electron)
echo =======================================================================
echo.

cd /d "%~dp0"

:: 1. Verificar Python
echo [*] Verificando instalacion de Python...
set "PYTHON_EXE=python"
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    py -3 --version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=py -3"
        echo [+] Detectado lanzador de Windows 'py'.
    ) else (
        echo [ERROR] No se encontro Python en el sistema.
        echo Por favor descargue e instale Python 3.10 o superior desde: https://www.python.org/
        echo IMPORTANTE: Marque la casilla "Add python.exe to PATH" durante la instalacion.
        goto :error_exit
    )
)
echo [+] Python detectado:
!PYTHON_EXE! --version
if %ERRORLEVEL% neq 0 goto :error_exit

:: 2. Crear entorno virtual local aislado (.venv)
echo.
echo [*] Configurando entorno virtual Python aislado (.venv)...
if not exist ".venv\Scripts\python.exe" (
    !PYTHON_EXE! -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Fallo al crear el entorno virtual .venv.
        goto :error_exit
    )
    echo [+] Entorno virtual .venv creado exitosamente.
) else (
    echo [+] El entorno virtual .venv ya existe.
)

:: 3. Actualizar pip e instalar dependencias de Python
echo.
echo [*] Instalando librerias de Vision Artificial (PyMuPDF, OpenCV, NumPy, psutil)...
call "%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
call "%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo al instalar las librerias de requirements.txt.
    goto :error_exit
)

echo.
echo =======================================================================
echo    INSTALACION COMPLETADA CORRECTAMENTE
echo =======================================================================
echo Ya puedes abrir la aplicacion haciendo doble clic en:
echo    "ejecutar.bat"
echo.
pause
exit /b 0

:error_exit
echo.
echo =======================================================================
echo [ERROR] La instalacion se detuvo debido al problema anterior.
echo La ventana NO se cerrara sola para que puedas revisar el mensaje.
echo =======================================================================
echo.
pause
exit /b 1
