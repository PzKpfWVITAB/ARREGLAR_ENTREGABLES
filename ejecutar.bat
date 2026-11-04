@echo off
title Verificador de Caratulas PDF
cd /d "%~dp0"

echo =======================================================================
echo    INICIANDO VERIFICADOR DE CARATULAS EN PDFS
echo =======================================================================
echo.

:: Asegurar que Node.js y Python esten en PATH para Explorer
set "PATH=%PATH%;C:\Program Files\nodejs;%APPDATA%\npm;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python314;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python314\Scripts;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311"

:: Iniciar la aplicacion directamente con npm start
echo [*] Abriendo la aplicacion de escritorio...
call npm start

if %ERRORLEVEL% neq 0 (
    echo.
    echo =======================================================================
    echo [ERROR] No se pudo iniciar la aplicacion con npm start.
    echo Codigo de salida: %ERRORLEVEL%
    echo =======================================================================
    pause
    exit /b %ERRORLEVEL%
)

exit /b 0
