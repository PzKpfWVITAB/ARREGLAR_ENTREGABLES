@echo off
setlocal enabledelayedexpansion
title Instalador - Verificador de Caratulas PDF (Portable)

echo =======================================================================
echo     INSTALADOR DEL SISTEMA - VERIFICADOR DE CARATULAS EN PDFS
echo     Entorno Portable: Python Venv + Electron Desktop
echo =======================================================================
echo.

cd /d "%~dp0"

:: 1. Verificar Python (prueba 'python' y luego el lanzador de Windows 'py')
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
        echo.
        pause
        exit /b 1
    )
)
for /f "tokens=*" %%i in ('!PYTHON_EXE! --version') do echo [+] %%i detectado.

:: 2. Verificar Node.js y npm
echo [*] Verificando instalacion de Node.js / NPM...
npm --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] No se encontro Node.js / npm en el sistema.
    echo Por favor descargue e instale Node.js (version LTS) desde: https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do echo [+] Node.js %%i detectado.
for /f "tokens=*" %%i in ('npm --version') do echo [+] NPM v%%i detectado.

:: 3. Crear entorno virtual local aislado (.venv)
echo.
echo [*] Configurando entorno virtual Python aislado (.venv)...
if not exist ".venv\Scripts\python.exe" (
    !PYTHON_EXE! -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Fallo al crear el entorno virtual .venv.
        pause
        exit /b 1
    )
    echo [+] Entorno virtual creado exitosamente.
) else (
    echo [+] El entorno virtual .venv ya existe.
)

:: 4. Actualizar pip e instalar dependencias de Python
echo.
echo [*] Instalando dependencias de Vision Artificial (PyMuPDF, OpenCV, NumPy)...
call .venv\Scripts\python.exe -m pip install --upgrade pip
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo al instalar librerias en requirements.txt.
    pause
    exit /b 1
)
echo [+] Dependencias de Python instaladas con exito.

:: 5. Instalar dependencias de Electron
echo.
echo [*] Instalando Electron y dependencias de escritorio (npm install)...
call npm install
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Fallo al instalar paquetes con npm.
    pause
    exit /b 1
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
