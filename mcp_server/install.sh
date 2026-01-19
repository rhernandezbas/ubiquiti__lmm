#!/bin/bash

# Script de instalación para Ubiquiti LLM MCP Server

set -e

echo "🚀 Instalando Ubiquiti LLM MCP Server..."

# Verificar que Python esté instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Instalar dependencias
echo "📦 Instalando dependencias..."
pip install mcp httpx pydantic

echo ""
echo "✅ Instalación completada!"
echo ""
echo "📝 Próximos pasos:"
echo ""
echo "1. Edita tu archivo de configuración de Claude Desktop:"
echo "   macOS: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo "   Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
echo ""
echo "2. Agrega esta configuración:"
echo ""
cat claude_desktop_config.example.json
echo ""
echo "3. Reinicia Claude Desktop"
echo ""
echo "4. Verifica que la API esté corriendo:"
echo "   curl http://190.7.234.37:7444/health"
echo ""
echo "🎉 ¡Listo! Ahora puedes usar las herramientas de Ubiquiti en Claude."
