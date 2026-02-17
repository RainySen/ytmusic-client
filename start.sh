#!/bin/bash

# ===========================================
# YTMusic Client - Script de Inicio
# ===========================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "==========================================="
echo "  🎵 YTMusic Client"
echo "==========================================="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 no está instalado${NC}"
    echo "Por favor instala Python 3.8 o superior"
    exit 1
fi

# Verificar VLC
if ! command -v vlc &> /dev/null; then
    echo -e "${YELLOW}⚠️  VLC no está instalado o no está en el PATH${NC}"
    echo "La aplicación puede no funcionar correctamente sin VLC"
    echo "Instala VLC desde tu gestor de paquetes"
    echo ""
fi

# Verificar si existe el entorno virtual
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  No se encontró entorno virtual${NC}"
    echo "Creando entorno virtual..."
    python3 -m venv .venv

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error al crear entorno virtual${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Entorno virtual creado${NC}"
fi

# Activar entorno virtual
source .venv/bin/activate

# Verificar dependencias
if [ ! -f ".venv/lib/python*/site-packages/PySide6/__init__.py" ]; then
    echo -e "${YELLOW}⚠️  Instalando dependencias...${NC}"
    pip install -r requirements.txt

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Error al instalar dependencias${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ Dependencias instaladas${NC}"
fi

# Ejecutar aplicación
echo ""
echo -e "${GREEN}🚀 Iniciando YTMusic Client...${NC}"
echo ""

python app.py

# Desactivar entorno virtual al salir
deactivate