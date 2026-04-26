@echo off
setlocal

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] No se encontro el entorno virtual en .\venv
    echo Crea el entorno con: python -m venv venv
    pause
    exit /b 1
)

echo Iniciando aplicacion OCR PDF...
"venv\Scripts\python.exe" "main.py"

if errorlevel 1 (
    echo.
    echo La aplicacion finalizo con error.
    pause
)

endlocal
