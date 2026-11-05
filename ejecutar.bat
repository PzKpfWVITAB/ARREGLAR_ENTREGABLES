@echo off
setlocal enabledelayedexpansion
title Verificador de Caratulas PDF - Windows Forms

cd /d "%~dp0"

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

:: 1. Verificar si existe el entorno virtual .venv
if not exist "!VENV_PYTHON!" (
    echo [!] No se detecto el entorno virtual .venv.
    echo [*] Iniciando instalacion automatica...
    echo.
    call "%~dp0instalar.bat"
    if not exist "!VENV_PYTHON!" goto :error_exit
)

:: 2. Iniciar la interfaz nativa de Windows Forms (Tkinter/ttk)
echo [*] Abriendo interfaz grafica de Windows...
"!VENV_PYTHON!" "%~dp0app_gui.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] La aplicacion finalizo con codigo de error: %ERRORLEVEL%
    goto :error_exit
)

exit /b 0

:error_exit
echo.
echo =======================================================================
echo [ERROR] Ocurrio un problema al ejecutar la aplicacion.
echo La consola NO se cerrara sola para que puedas leer el detalle arriba.
echo =======================================================================
echo.
pause
exit /b 1
