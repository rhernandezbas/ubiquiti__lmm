#!/usr/bin/env python3
"""
Script de prueba para el servidor MCP de Ubiquiti LLM

Este script prueba que el servidor MCP puede comunicarse correctamente
con la API de Ubiquiti LLM.
"""

import asyncio
import httpx
import json

API_BASE_URL = "http://190.7.234.37:7444/api/v1"

async def test_api_connection():
    """
    Prueba la conexión con la API.
    """
    print("🔍 Probando conexión con la API...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL.replace('/api/v1', '')}/health")
            response.raise_for_status()
            data = response.json()
            print(f"✅ API respondiendo correctamente: {json.dumps(data, indent=2)}")
            return True
    except Exception as e:
        print(f"❌ Error conectando con la API: {e}")
        return False

async def test_device_info():
    """
    Prueba el endpoint de información de dispositivo.
    """
    print("\n🔍 Probando endpoint de información de dispositivo...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Usa una IP de ejemplo - ajusta según tu entorno
            response = await client.get(
                f"{API_BASE_URL}/device-info",
                params={"ip_address": "100.64.11.83"}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Información de dispositivo obtenida:")
                print(json.dumps(data, indent=2, ensure_ascii=False)[:500] + "...")
                return True
            else:
                print(f"⚠️  Respuesta: {response.status_code} - {response.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """
    Ejecuta todas las pruebas.
    """
    print("=" * 60)
    print("🧪 Pruebas del Servidor MCP de Ubiquiti LLM")
    print("=" * 60)
    
    # Test 1: Conexión con la API
    api_ok = await test_api_connection()
    
    if not api_ok:
        print("\n❌ La API no está disponible. Verifica que esté corriendo:")
        print("   docker compose ps")
        print("   curl http://190.7.234.37:7444/health")
        return
    
    # Test 2: Endpoint de información de dispositivo
    await test_device_info()
    
    print("\n" + "=" * 60)
    print("✅ Pruebas completadas!")
    print("=" * 60)
    print("\n📝 Próximos pasos:")
    print("1. Configura Claude Desktop con el archivo claude_desktop_config.example.json")
    print("2. Reinicia Claude Desktop")
    print("3. Prueba las herramientas en una conversación con Claude")
    print("\nEjemplo: 'Analiza el dispositivo con IP 100.64.11.83'")

if __name__ == "__main__":
    asyncio.run(main())
