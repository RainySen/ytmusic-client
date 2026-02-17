@echo off
REM ===========================================
REM YTMusic Client - Script de Inicio (Windows)
REM ===========================================

echo ===========================================
echo   YTMusic Client
echo ===========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Por favor instala Python 3.8 o superior desde python.org
    pause
    exit /b 1
)

REM Verificar VLC
where vlc >nul 2>&1
if %errorlevel% neq 0 (
    echo ADVERTENCIA: VLC no esta instalado o no esta en el PATH
    echo La aplicacion puede no funcionar correctamente sin VLC
    echo Instala VLC desde videolan.org
    echo.
)

REM Verificar si existe el entorno virtual
if not exist ".venv\" (
    echo No se encontro entorno virtual
    echo Creando entorno virtual...
    python -m venv .venv

    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear el entorno virtual
        pause
        exit /b 1
    )

    echo Entorno virtual creado
)

REM Activar entorno virtual
call .venv\Scripts\activate.bat

REM Verificar dependencias
if not exist ".venv\Lib\site-packages\PySide6\" (
    echo Instalando dependencias...
    pip install -r requirements.txt

    if %errorlevel% neq 0 (
        echo ERROR: No se pudieron instalar las dependencias
        pause
        exit /b 1
    )

    echo Dependencias instaladas
)

REM Ejecutar aplicación
echo.
echo Iniciando YTMusic Client...
echo.

python app.py

REM Desactivar entorno virtual al salir
deactivate