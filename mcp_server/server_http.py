#!/usr/bin/env python3
"""
MCP HTTP/SSE Server for Ubiquiti LLM Diagnostic Service

This server exposes the MCP functionality via HTTP with SSE (Server-Sent Events)
for integration with n8n and other HTTP-based clients.
"""

import asyncio
import json
import httpx
from typing import Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# API Configuration
API_BASE_URL = "http://190.7.234.37:7444/api/v1"
API_TIMEOUT = 300.0  # 5 minutes for long-running operations

# Create FastAPI app
app = FastAPI(
    title="Ubiquiti LLM MCP Server",
    description="MCP Server for Ubiquiti device diagnostics via HTTP/SSE",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# MCP Tools Definition
TOOLS = [
    {
        "name": "analyze_device_complete",
        "description": (
            "Realiza un análisis completo de un dispositivo Ubiquiti. "
            "Incluye: búsqueda en UISP, configuración de frecuencias, "
            "site survey, diagnóstico completo y recomendaciones con IA. "
            "Requiere IP o MAC del dispositivo."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP del dispositivo (PPPoE o management). Ejemplo: 100.64.11.83"
                },
                "mac_address": {
                    "type": "string",
                    "description": "MAC address del dispositivo. Ejemplo: 80:2a:a8:64:7f:d4"
                },
                "ssh_username": {
                    "type": "string",
                    "description": "Usuario SSH (opcional, usa default si no se proporciona)"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "Contraseña SSH (opcional, usa default si no se proporciona)"
                }
            },
            "oneOf": [
                {"required": ["ip_address"]},
                {"required": ["mac_address"]}
            ]
        }
    },
    {
        "name": "get_device_info",
        "description": (
            "Obtiene información básica de un dispositivo desde UISP. "
            "Busca por IP o MAC y retorna datos del dispositivo, modelo, ubicación, etc."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP del dispositivo"
                },
                "mac_address": {
                    "type": "string",
                    "description": "MAC address del dispositivo"
                }
            },
            "oneOf": [
                {"required": ["ip_address"]},
                {"required": ["mac_address"]}
            ]
        }
    },
    {
        "name": "site_survey",
        "description": (
            "Realiza un site survey (escaneo de APs) en un dispositivo Ubiquiti. "
            "Retorna lista de APs disponibles con señal, frecuencia y calidad. "
            "Útil para encontrar el mejor AP para conectarse."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP del dispositivo"
                },
                "ssh_username": {
                    "type": "string",
                    "description": "Usuario SSH (opcional)"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "Contraseña SSH (opcional)"
                }
            },
            "required": ["ip_address"]
        }
    },
    {
        "name": "configure_frequencies",
        "description": (
            "Configura automáticamente todas las frecuencias disponibles "
            "en un dispositivo Ubiquiti (LiteBeam AC, NanoBeam, etc.). "
            "Habilita el rango completo de frecuencias para mejorar la conectividad."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP del dispositivo"
                },
                "ssh_username": {
                    "type": "string",
                    "description": "Usuario SSH (opcional)"
                },
                "ssh_password": {
                    "type": "string",
                    "description": "Contraseña SSH (opcional)"
                }
            },
            "required": ["ip_address"]
        }
    },
    {
        "name": "ping_device",
        "description": (
            "Realiza un ping a un dispositivo para verificar conectividad. "
            "Retorna latencia promedio, pérdida de paquetes y estado de alcanzabilidad."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ip_address": {
                    "type": "string",
                    "description": "IP del dispositivo a hacer ping"
                },
                "count": {
                    "type": "integer",
                    "description": "Número de paquetes a enviar (default: 5)",
                    "default": 5
                }
            },
            "required": ["ip_address"]
        }
    },
    {
        "name": "get_logs",
        "description": (
            "Obtiene los logs de la aplicación Ubiquiti LLM. "
            "Permite consultar logs generales (app) o logs de errores (error). "
            "Útil para debugging y monitoreo del sistema."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "log_type": {
                    "type": "string",
                    "enum": ["app", "error"],
                    "description": "Tipo de log: 'app' para logs generales, 'error' para logs de errores",
                    "default": "app"
                },
                "lines": {
                    "type": "integer",
                    "description": "Número de líneas a retornar (últimas N líneas)",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 10000
                },
                "search": {
                    "type": "string",
                    "description": "Texto opcional para filtrar logs (case-insensitive)"
                }
            }
        }
    }
]


@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "Ubiquiti LLM MCP Server",
        "version": "1.0.0",
        "description": "MCP Server for Ubiquiti device diagnostics",
        "endpoints": {
            "sse": "/sse",
            "tools": "/tools",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL.replace('/api/v1', '')}/health")
            api_healthy = response.status_code == 200
    except:
        api_healthy = False
    
    return {
        "status": "healthy" if api_healthy else "degraded",
        "mcp_server": "running",
        "api_connection": "ok" if api_healthy else "error"
    }


@app.get("/tools")
async def list_tools():
    """List all available MCP tools."""
    return {
        "tools": TOOLS
    }


@app.post("/sse")
async def sse_endpoint(request: Request):
    """
    SSE endpoint for MCP communication.
    This is the endpoint that n8n will connect to.
    """
    async def event_generator():
        try:
            body = await request.json()
            method = body.get("method")
            params = body.get("params", {})
            
            # Handle different MCP methods
            if method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await call_tool(tool_name, arguments)
            else:
                result = {"error": f"Unknown method: {method}"}
            
            # Send result as SSE
            yield f"data: {json.dumps(result)}\n\n"
            
        except Exception as e:
            error_result = {"error": str(e)}
            yield f"data: {json.dumps(error_result)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


async def call_tool(name: str, arguments: dict) -> dict[str, Any]:
    """Execute a tool and return the result."""
    try:
        if name == "analyze_device_complete":
            result = await analyze_device_complete(arguments)
        elif name == "get_device_info":
            result = await get_device_info(arguments)
        elif name == "site_survey":
            result = await site_survey(arguments)
        elif name == "configure_frequencies":
            result = await configure_frequencies(arguments)
        elif name == "ping_device":
            result = await ping_device(arguments)
        elif name == "get_logs":
            result = await get_logs(arguments)
        else:
            return {"error": f"Unknown tool: {name}", "success": False}
        
        return {"result": result, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


async def analyze_device_complete(args: dict) -> dict[str, Any]:
    """Realiza análisis completo de un dispositivo."""
    params = {}
    if "ip_address" in args:
        params["ip_address"] = args["ip_address"]
    if "mac_address" in args:
        params["mac_address"] = args["mac_address"]
    if "ssh_username" in args:
        params["ssh_username"] = args["ssh_username"]
    if "ssh_password" in args:
        params["ssh_password"] = args["ssh_password"]

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE_URL}/analyze-device-complete",
            params=params
        )
        response.raise_for_status()
        return response.json()


async def get_device_info(args: dict) -> dict[str, Any]:
    """Obtiene información de un dispositivo desde UISP."""
    params = {}
    if "ip_address" in args:
        params["ip_address"] = args["ip_address"]
    if "mac_address" in args:
        params["mac_address"] = args["mac_address"]

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.get(
            f"{API_BASE_URL}/device-info",
            params=params
        )
        response.raise_for_status()
        return response.json()


async def site_survey(args: dict) -> dict[str, Any]:
    """Realiza site survey en un dispositivo."""
    params = {
        "ip_address": args["ip_address"]
    }
    if "ssh_username" in args:
        params["ssh_username"] = args["ssh_username"]
    if "ssh_password" in args:
        params["ssh_password"] = args["ssh_password"]

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE_URL}/site-survey",
            params=params
        )
        response.raise_for_status()
        return response.json()


async def configure_frequencies(args: dict) -> dict[str, Any]:
    """Configura frecuencias en un dispositivo."""
    params = {
        "ip_address": args["ip_address"]
    }
    if "ssh_username" in args:
        params["ssh_username"] = args["ssh_username"]
    if "ssh_password" in args:
        params["ssh_password"] = args["ssh_password"]

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE_URL}/configure-frequencies",
            params=params
        )
        response.raise_for_status()
        return response.json()


async def ping_device(args: dict) -> dict[str, Any]:
    """Hace ping a un dispositivo."""
    params = {
        "ip_address": args["ip_address"],
        "count": args.get("count", 5)
    }

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.post(
            f"{API_BASE_URL}/ping",
            params=params
        )
        response.raise_for_status()
        return response.json()


async def get_logs(args: dict) -> dict[str, Any]:
    """Obtiene los logs de la aplicación."""
    params = {
        "log_type": args.get("log_type", "app"),
        "lines": args.get("lines", 100)
    }
    if "search" in args:
        params["search"] = args["search"]

    async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
        response = await client.get(
            f"{API_BASE_URL}/logs",
            params=params
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    print("🚀 Iniciando Ubiquiti LLM MCP Server (HTTP/SSE)...")
    print(f"📡 API Base URL: {API_BASE_URL}")
    print(f"🌐 Server URL: http://localhost:3000")
    print(f"🔌 SSE Endpoint: http://localhost:3000/sse")
    print(f"🛠️  Tools: http://localhost:3000/tools")
    print(f"💚 Health: http://localhost:3000/health")
    print("\n✅ Servidor listo para n8n!")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=3000,
        log_level="info"
    )
