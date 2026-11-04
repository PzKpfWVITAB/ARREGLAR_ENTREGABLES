@echo off
setlocal enabledelayedexpansion
title Instalador - Verificador de Caratulas PDF (Portable)

echo =======================================================================
echo     INSTALADOR DEL SISTEMA - VERIFICADOR DE CARATULAS EN PDFS
echo     Entorno Portable: Python Venv + Electron Desktop
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
echo [+] Python activo:
!PYTHON_EXE! --version
if %ERRORLEVEL% neq 0 goto :error_exit

:: 2. Verificar Node.js y npm (¡IMPORTANTE: usar 'call' porque npm es npm.cmd en Windows!)
echo.
echo [*] Verificando instalacion de Node.js y npm...
call node --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se encontro 'node' en el sistema.
    echo Por favor instale Node.js LTS desde: https://nodejs.org/
    goto :error_exit
)

call npm --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se encontro 'npm' en el sistema.
    echo Por favor instale Node.js LTS desde: https://nodejs.org/
    goto :error_exit
)

echo [+] Node.js activo:
call node --version
echo [+] NPM activo:
call npm --version

:: 3. Crear entorno virtual local aislado (.venv)
echo.
echo [*] Configurando entorno virtual Python aislado (.venv)...
if not exist ".venv\Scripts\python.exe" (
    !PYTHON_EXE! -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Fallo al crear el entorno virtual .venv con !PYTHON_EXE!.
        goto :error_exit
    )
    echo [+] Entorno virtual .venv creado exitosamente.
) else (
    echo [+] El entorno virtual .venv ya existe.
)

:: 4. Actualizar pip e instalar dependencias de Python
echo.
echo [*] Instalando dependencias de Python en .venv (PyMuPDF, OpenCV, NumPy)...
call "%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip
call "%~dp0.venv\Scripts\python.exe" -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ADVERTENCIA] Si pip fallo buscando paquetes para Python 3.14:
    echo Intente instalar una version estable recomendada de Python (Python 3.11 o 3.12).
    goto :error_exit
)
echo [+] Dependencias de Python instaladas con exito.

:: 5. Instalar dependencias de Electron
echo.
echo [*] Instalando Electron y dependencias de escritorio (npm install)...
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo al instalar paquetes con npm install.
    goto :error_exit
)
echo [+] Electron instalado con exito en node_modules.

echo.
echo =======================================================================
echo    INSTALACION COMPLETADA CORRECTAMENTE
echo =======================================================================
echo Ya puedes iniciar la aplicacion ejecutando:
echo    "ejecutar.bat"
echo.
pause
exit /b 0

:error_exit
echo.
echo =======================================================================
echo [ERROR] La instalacion no pudo completarse debido al problema anterior.
echo La consola NO se cerrara para que puedas revisar el error arriba.
echo =======================================================================
echo.
pause
exit /b 1
