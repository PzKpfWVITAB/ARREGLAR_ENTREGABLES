@echo off
setlocal
title Verificador de Caratulas PDF

cd /d "%~dp0"

:: Verificar si el entorno virtual o los módulos de Node faltan
if not exist ".venv\Scripts\python.exe" (
    echo [!] No se detecto el entorno virtual .venv de Python.
    echo [*] Iniciando instalacion automatica previa...
    call instalar.bat
    if %ERRORLEVEL% neq 0 exit /b 1
)

if not exist "node_modules\electron" (
    echo [!] No se detecto Electron instalado en node_modules.
    echo [*] Iniciando instalacion de dependencias...
    call instalar.bat
    if %ERRORLEVEL% neq 0 exit /b 1
)

:: Iniciar la aplicación Electron
echo [*] Iniciando Verificador de Caratulas en Electron...
start "" "%~dp0node_modules\.bin\electron.cmd" .
exit /b 0
