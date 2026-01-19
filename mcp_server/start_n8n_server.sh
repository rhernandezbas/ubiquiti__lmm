#!/bin/bash

# Script para iniciar el servidor MCP HTTP/SSE para n8n

set -e

echo "🚀 Iniciando Ubiquiti LLM MCP Server para n8n..."
echo ""

# Verificar que Python esté instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado"
    exit 1
fi

# Verificar que las dependencias estén instaladas
echo "🔍 Verificando dependencias..."
python3 -c "import fastapi, uvicorn, httpx" 2>/dev/null || {
    echo "⚠️  Dependencias no encontradas. Instalando..."
    pip install fastapi uvicorn[standard] httpx pydantic
}

echo "✅ Dependencias verificadas"
echo ""

# Verificar que la API esté corriendo
echo "🔍 Verificando conexión con la API..."
if curl -s http://190.7.234.37:7444/health > /dev/null 2>&1; then
    echo "✅ API de Ubiquiti LLM está corriendo"
else
    echo "⚠️  Advertencia: No se pudo conectar con la API en http://190.7.234.37:7444"
    echo "   El servidor MCP se iniciará de todos modos, pero las herramientas no funcionarán."
fi

echo ""
echo "🌐 Iniciando servidor HTTP/SSE en http://0.0.0.0:3000"
echo "🔌 SSE Endpoint para n8n: http://localhost:3000/sse"
echo ""
echo "📝 Para usar en n8n:"
echo "   1. Agrega un nodo 'MCP Client'"
echo "   2. Configura SSE Endpoint: http://localhost:3000/sse"
echo "   3. Conecta a un AI Agent"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo ""

# Iniciar el servidor
python3 server_http.py
