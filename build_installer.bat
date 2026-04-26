@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

set "VENV_PY=venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo [ERROR] No se encontro el entorno virtual en .\venv
    echo Crea el entorno con: python -m venv venv
    exit /b 1
)

set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" (
    echo [ERROR] No se encontro Inno Setup en:
    echo !ISCC_PATH!
    echo Instala Inno Setup 6 para compilar el instalador.
    exit /b 1
)

echo [1/4] Limpiando carpetas de build...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "installer_output" rmdir /s /q "installer_output"

echo [2/4] Instalando/actualizando PyInstaller...
"%VENV_PY%" -m pip install --upgrade pyinstaller
if errorlevel 1 exit /b 1

echo [3/4] Generando ejecutable con PyInstaller...
"%VENV_PY%" -m PyInstaller --clean "telita_ocr.spec"
if errorlevel 1 exit /b 1

echo [4/4] Compilando instalador con Inno Setup...
"%ISCC_PATH%" "installer\telita_ocr.iss"
if errorlevel 1 exit /b 1

echo.
echo Build finalizado.
echo Instalador generado en: installer_output\
endlocal
