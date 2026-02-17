#!/bin/bash

# ==========================================
# Build Script: YTMusicClient Release (Linux)
# ==========================================

echo "==========================================="
echo "  YTMusicClient - Build para Linux"
echo "==========================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Verificar que estamos en un entorno virtual
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Advertencia: No se detectó un entorno virtual activo${NC}"
    echo -e "${YELLOW}   Se recomienda activarlo primero: source .venv/bin/activate${NC}"
    read -p "¿Continuar de todos modos? (s/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

# Limpiar builds anteriores
echo -e "${YELLOW}🧹 Limpiando builds anteriores...${NC}"
rm -rf build dist release *.spec

# Crear directorio release
mkdir -p release

# Compilar ejecutable
echo -e "${CYAN}🔨 Compilando ejecutable Release...${NC}"

pyinstaller --onefile \
    --noconsole \
    --clean \
    --distpath release \
    --name "YTMusicClient" \
    --icon "icon.png" \
    --collect-datas yt_dlp \
    --collect-datas qtawesome \
    --collect-datas ytmusicapi \
    --hidden-import "PySide6.QtSvg" \
    app.py

# Verificar si la compilación fue exitosa
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Compilación completada exitosamente${NC}"
    echo -e "${GREEN}📦 Ejecutable disponible en: release/YTMusicClient${NC}"

    # Hacer el ejecutable... ejecutable
    chmod +x release/YTMusicClient

    # Mostrar información del archivo
    echo ""
    echo -e "${CYAN}Información del ejecutable:${NC}"
    ls -lh release/YTMusicClient
    file release/YTMusicClient

    # Crear un script de lanzamiento opcional
    echo -e "${CYAN}📝 Creando script de lanzamiento...${NC}"
    cat > release/run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
./YTMusicClient
EOF
    chmod +x release/run.sh
    echo -e "${GREEN}✅ Script de lanzamiento creado: release/run.sh${NC}"

else
    echo -e "${RED}❌ Error durante la compilación${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}==========================================="
echo -e "  🎉 Build completado"
echo -e "==========================================="${NC}