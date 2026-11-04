@echo off
title Diagnostico e Instalacion (Ventana Permanente)
cd /d "%~dp0"

echo =======================================================================
echo    INICIANDO INSTALACION Y GENERANDO 'instalacion_log.txt'
echo    Esta ventana se mantendra abierta permanentemente.
echo =======================================================================
echo.

call :run_installer > "%~dp0instalacion_log.txt" 2>&1

:: Mostrar el log completo en la pantalla
type "%~dp0instalacion_log.txt"

echo.
echo =======================================================================
echo PROCESO FINALIZADO.
echo Todo el texto anterior se guardo en el archivo:
echo    "instalacion_log.txt"
echo.
echo Esta ventana NO se cerrara. Presiona cualquier tecla para abrir
echo el log en el Bloc de Notas.
echo =======================================================================
pause
start notepad.exe "%~dp0instalacion_log.txt"
cmd /k
exit /b 0

:run_installer
echo --- 1. VERIFICACION DE ENTORNOS ---
echo [PATH de Python]:
where python
python --version

echo.
echo [PATH de Node y NPM]:
where node
call node --version
where npm
call npm --version

echo.
echo --- 2. ENTORNO VIRTUAL PYTHON (.venv) ---
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual .venv...
    python -m venv .venv
) else (
    echo El entorno .venv ya existe.
)

echo.
echo --- 3. INSTALACION DE ELECTRON (NPM INSTALL) ---
echo Ejecutando 'npm install' para crear node_modules...
call npm install --verbose

echo.
echo --- 4. INSTALACION DE LIBRERIAS PYTHON (PIP INSTALL) ---
echo Actualizando pip...
call "%~dp0.venv\Scripts\python.exe" -m pip install --upgrade pip

echo Instalando librerias de Vision (requirements.txt)...
call "%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"

echo.
echo --- 5. COMPROBACION FINAL DE ARCHIVOS CREADOS ---
if exist "node_modules\.bin\electron.cmd" (
    echo [EXITO] Electron esta instalado correctamente en node_modules.
) else (
    echo [FALLO] No se encontro node_modules\.bin\electron.cmd.
)

if exist ".venv\Scripts\python.exe" (
    echo [EXITO] Python .venv esta instalado correctamente.
) else (
    echo [FALLO] No se encontro .venv\Scripts\python.exe.
)
exit /b 0
