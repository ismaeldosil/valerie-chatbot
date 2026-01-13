#!/bin/bash
#
# Valerie Supplier Chatbot - Instalación Automática
# Ejecutar con: bash install.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║         VALERIE SUPPLIER CHATBOT - INSTALACIÓN               ║"
echo "║                      Versión 2.0.0                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Detectar Python
echo -e "${YELLOW}[1/6] Detectando Python...${NC}"
PYTHON_CMD=""

if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Error: Python no encontrado${NC}"
    echo "Por favor instala Python 3.11+ desde https://www.python.org/downloads/"
    exit 1
fi

VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✓ Encontrado: $PYTHON_CMD (versión $VERSION)${NC}"

# Verificar versión mínima
MAJOR=$(echo $VERSION | cut -d. -f1)
MINOR=$(echo $VERSION | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 11 ]); then
    echo -e "${RED}Error: Se requiere Python 3.11+. Encontrado: $VERSION${NC}"
    exit 1
fi

# 2. Crear entorno virtual
echo -e "${YELLOW}[2/6] Creando entorno virtual...${NC}"
if [ -d "venv" ]; then
    echo "Eliminando entorno virtual existente..."
    rm -rf venv
fi
$PYTHON_CMD -m venv venv
echo -e "${GREEN}✓ Entorno virtual creado${NC}"

# 3. Activar entorno
echo -e "${YELLOW}[3/6] Activando entorno virtual...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Entorno activado${NC}"

# 4. Actualizar pip e instalar dependencias
echo -e "${YELLOW}[4/6] Instalando dependencias...${NC}"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# 5. Configurar .env
echo -e "${YELLOW}[5/6] Configurando entorno...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Archivo .env creado${NC}"
else
    echo -e "${GREEN}✓ Archivo .env ya existe${NC}"
fi

# 6. Verificar instalación
echo -e "${YELLOW}[6/6] Verificando instalación...${NC}"
$PYTHON_CMD -c "
import sys
sys.path.insert(0, 'src')
from valerie_supplier_chatbot.graph.builder import build_graph
graph = build_graph()
print(f'✓ Grafo LangGraph compilado ({len(graph.nodes)} nodos)')
"

echo ""
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 ¡INSTALACIÓN COMPLETADA!                     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo -e "${BLUE}Para usar el chatbot:${NC}"
echo ""
echo "  1. Activa el entorno virtual:"
echo -e "     ${GREEN}source venv/bin/activate${NC}"
echo ""
echo "  2. Configura tu API key en .env:"
echo -e "     ${GREEN}VALERIE_ANTHROPIC_API_KEY=tu-api-key${NC}"
echo ""
echo "  3. Ejecuta el chatbot:"
echo -e "     ${GREEN}python3 scripts/run.py chat${NC}"
echo ""
echo "  4. O prueba sin API key:"
echo -e "     ${GREEN}python3 scripts/run.py test-graph${NC}"
echo ""
