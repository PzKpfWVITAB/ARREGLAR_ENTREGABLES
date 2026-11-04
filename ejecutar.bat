@echo off
setlocal enabledelayedexpansion
title Verificador de Caratulas PDF

cd /d "%~dp0"

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
set "ELECTRON_BIN=%~dp0node_modules\.bin\electron.cmd"

:: 1. Verificar si faltan los componentes esenciales
set "NEED_INSTALL=0"
if not exist "!VENV_PYTHON!" (
    echo [!] No se encontro el entorno virtual de Python (.venv).
    set "NEED_INSTALL=1"
)
if not exist "!ELECTRON_BIN!" (
    echo [!] No se encontraron los modulos de Electron (node_modules).
    set "NEED_INSTALL=1"
)

:: 2. Si falta algo, invocar la instalación
if "!NEED_INSTALL!"=="1" (
    echo [*] Es la primera vez que se ejecuta o faltan dependencias.
    echo [*] Iniciando instalador automatico...
    echo.
    call "%~dp0instalar.bat"
    
    :: Volver a comprobar tras la instalación
    if not exist "!VENV_PYTHON!" (
        echo.
        echo =======================================================================
        echo [ERROR] No se pudo inicializar el entorno virtual de Python.
        echo Asegurate de tener Python instalado y accesible en la terminal (PATH).
        echo Descargalo desde: https://www.python.org/
        echo =======================================================================
        pause
        exit /b 1
    )
    if not exist "!ELECTRON_BIN!" (
        echo.
        echo =======================================================================
        echo [ERROR] No se pudo instalar Electron.
        echo Asegurate de tener Node.js instalado (incluye npm).
        echo Descargalo desde: https://nodejs.org/ (Version LTS)
        echo =======================================================================
        pause
        exit /b 1
    )
)

:: 3. Iniciar la aplicación Electron
echo [*] Iniciando Verificador de Caratulas en Electron...
call npm start
if %ERRORLEVEL% neq 0 (
    echo [!] npm start retorno codigo de error. Probando lanzamiento directo...
    start "" "!ELECTRON_BIN!" .
)
exit /b 0
