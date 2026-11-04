@echo off
setlocal enabledelayedexpansion
title Verificador de Caratulas PDF

cd /d "%~dp0"

echo =======================================================================
echo    INICIANDO VERIFICADOR DE CARATULAS EN PDFS
echo =======================================================================
echo.

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
set "ELECTRON_BIN=%~dp0node_modules\.bin\electron.cmd"

:: 1. Verificar si Node.js / npm está instalado en el sistema
call npm --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR CRITICO] No se encontro 'npm' ni Node.js en este equipo.
    echo La interfaz de escritorio (Electron) necesita Node.js.
    echo.
    echo Por favor descargue e instale Node.js LTS desde:
    echo    https://nodejs.org/
    echo.
    echo (Una vez instalado, vuelva a ejecutar este archivo).
    goto :error_exit
)

:: 2. Verificar si falta instalar Electron o Python .venv
if not exist "!ELECTRON_BIN!" (
    echo [!] No se detecto Electron en la carpeta 'node_modules'.
    echo [*] Iniciando instalacion de paquetes requeridos...
    echo.
    call "%~dp0instalar.bat"
    if not exist "!ELECTRON_BIN!" goto :error_exit
)

if not exist "!VENV_PYTHON!" (
    echo [!] No se detecto el entorno virtual de Python (.venv).
    echo [*] Iniciando instalacion de paquetes requeridos...
    echo.
    call "%~dp0instalar.bat"
    if not exist "!VENV_PYTHON!" goto :error_exit
)

:: 3. Lanzar la aplicación y mantener la consola en caso de fallo
echo [*] Iniciando aplicacion de escritorio con Electron...
call npm start

if %ERRORLEVEL% neq 0 (
    echo.
    echo [!] La aplicacion se cerro con codigo de error: %ERRORLEVEL%
    goto :error_exit
)

exit /b 0

:error_exit
echo.
echo =======================================================================
echo [ERROR] No se pudo iniciar la aplicacion.
echo La consola NO se cerrara para que puedas revisar el error anterior.
echo =======================================================================
echo.
pause
exit /b 1
