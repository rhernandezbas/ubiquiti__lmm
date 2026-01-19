#!/usr/bin/env python3
"""
MCP Server for Ubiquiti LLM Diagnostic Service

This server exposes the Ubiquiti LLM API functionality as MCP tools
that can be used by AI assistants like Claude.
"""

import asyncio
import httpx
import json
from typing import Any, Optional
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from pydantic import AnyUrl

# API Configuration
API_BASE_URL = "http://190.7.234.37:7444/api/v1"
API_TIMEOUT = 300.0  # 5 minutes for long-running operations

# Create MCP server instance
server = Server("ubiquiti-llm-diagnostic")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    List all available tools for Ubiquiti device diagnostics.
    """
    return [
        Tool(
            name="analyze_device_complete",
            description=(
                "Realiza un análisis completo de un dispositivo Ubiquiti. "
                "Incluye: búsqueda en UISP, configuración de frecuencias, "
                "site survey, diagnóstico completo y recomendaciones con IA. "
                "Requiere IP o MAC del dispositivo."
            ),
            inputSchema={
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
            },
        ),
        Tool(
            name="get_device_info",
            description=(
                "Obtiene información básica de un dispositivo desde UISP. "
                "Busca por IP o MAC y retorna datos del dispositivo, modelo, ubicación, etc."
            ),
            inputSchema={
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
            },
        ),
        Tool(
            name="site_survey",
            description=(
                "Realiza un site survey (escaneo de APs) en un dispositivo Ubiquiti. "
                "Retorna lista de APs disponibles con señal, frecuencia y calidad. "
                "Útil para encontrar el mejor AP para conectarse."
            ),
            inputSchema={
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
            },
        ),
        Tool(
            name="configure_frequencies",
            description=(
                "Configura automáticamente todas las frecuencias disponibles "
                "en un dispositivo Ubiquiti (LiteBeam AC, NanoBeam, etc.). "
                "Habilita el rango completo de frecuencias para mejorar la conectividad."
            ),
            inputSchema={
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
            },
        ),
        Tool(
            name="ping_device",
            description=(
                "Realiza un ping a un dispositivo para verificar conectividad. "
                "Retorna latencia promedio, pérdida de paquetes y estado de alcanzabilidad."
            ),
            inputSchema={
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
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool execution requests.
    """
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
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [
            TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "success": False
                }, indent=2)
            )
        ]


async def analyze_device_complete(args: dict) -> dict[str, Any]:
    """
    Realiza análisis completo de un dispositivo.
    """
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
    """
    Obtiene información de un dispositivo desde UISP.
    """
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
    """
    Realiza site survey en un dispositivo.
    """
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
    """
    Configura frecuencias en un dispositivo.
    """
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
    """
    Hace ping a un dispositivo.
    """
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


async def main():
    """
    Main entry point for the MCP server.
    """
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="ubiquiti-llm-diagnostic",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
