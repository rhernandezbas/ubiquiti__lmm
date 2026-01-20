# Ubiquiti LLM MCP Server

Servidor MCP (Model Context Protocol) para el servicio de diagnóstico de dispositivos Ubiquiti.

## 🎯 Descripción

Este servidor MCP expone las funcionalidades de la API de Ubiquiti LLM como herramientas que pueden ser utilizadas por asistentes de IA como Claude. Permite realizar diagnósticos completos, site surveys, configuración de frecuencias y más, directamente desde una conversación con un LLM.

## 🛠️ Herramientas Disponibles

### 1. `analyze_device_complete`
Realiza un análisis completo de un dispositivo Ubiquiti:
- Búsqueda en UISP por IP o MAC
- Configuración automática de frecuencias
- Site survey con señal en dBm
- Análisis de mejor AP disponible
- Diagnóstico completo (LAN, Ethernet, throughput, uptime)
- Recomendaciones con IA

**Parámetros:**
- `ip_address` (opcional): IP del dispositivo
- `mac_address` (opcional): MAC del dispositivo
- `ssh_username` (opcional): Usuario SSH
- `ssh_password` (opcional): Contraseña SSH

**Ejemplo:**
```json
{
  "ip_address": "100.64.11.83"
}
```

### 2. `get_device_info`
Obtiene información básica de un dispositivo desde UISP.

**Parámetros:**
- `ip_address` o `mac_address`

### 3. `site_survey`
Realiza un escaneo de APs disponibles.

**Parámetros:**
- `ip_address`: IP del dispositivo
- `ssh_username` (opcional)
- `ssh_password` (opcional)

### 4. `configure_frequencies`
Configura automáticamente todas las frecuencias disponibles en el dispositivo.

**Parámetros:**
- `ip_address`: IP del dispositivo
- `ssh_username` (opcional)
- `ssh_password` (opcional)

### 5. `ping_device`
Verifica conectividad con un dispositivo.

**Parámetros:**
- `ip_address`: IP del dispositivo
- `count` (opcional): Número de paquetes (default: 5)

## 📦 Instalación

### Opción 1: Usando Poetry

```bash
cd mcp_server
poetry install
```

### Opción 2: Usando pip

```bash
cd mcp_server
pip install mcp httpx pydantic
```

## 🚀 Uso

### Opción 1n: Integración con n8n

Para usar el servidor MCP con n8n, consulta la guía completa en [N8N_SETUP.md](N8N_SETUP.md).

**Inicio rápido:**

```bash
# Iniciar servidor HTTP/SSE para n8n
./start_n8n_server.sh
```

El servidor se iniciará en `http://localhost:3000/sse` y estará listo para conectarse desde n8n.

En n8n:
1. Agrega un nodo **"MCP Client"**
2. Configura **SSE Endpoint**: `http://localhost:3000/sse`
3. Conecta a un **AI Agent** (OpenAI, Anthropic, etc.)

### Opción 2: Configuración en Claude Desktop

1. Edita el archivo de configuración de Claude Desktop:

**macOS:**
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
code %APPDATA%\Claude\claude_desktop_config.json
```

2. Agrega la configuración del servidor MCP:

```json
{
  "mcpServers": {
    "ubiquiti-llm-diagnostic": {
      "command": "python",
      "args": [
        "/Users/rhernandezba/PycharmProjects/ubiquiti_llm/mcp_server/server.py"
      ]
    }
  }
}
```

3. Reinicia Claude Desktop.

### Uso desde la línea de comandos

```bash
python server.py
```

## 🔧 Configuración

El servidor está configurado para conectarse a la API en:
```
http://190.7.234.37:7444/api/v1
```

Si necesitas cambiar la URL de la API, edita la variable `API_BASE_URL` en `server.py`:

```python
API_BASE_URL = "http://tu-servidor:puerto/api/v1"
```

## 📝 Ejemplos de Uso en Claude

Una vez configurado, puedes usar las herramientas en Claude:

**Ejemplo 1: Análisis completo**
```
Analiza el dispositivo con IP 100.64.11.83
```

**Ejemplo 2: Site survey**
```
Haz un site survey del dispositivo 100.64.11.83 para ver qué APs están disponibles
```

**Ejemplo 3: Configurar frecuencias**
```
Configura todas las frecuencias disponibles en el dispositivo 100.64.11.83
```

**Ejemplo 4: Ping**
```
Verifica la conectividad del dispositivo 100.64.11.83
```

## 🔍 Troubleshooting

### El servidor no aparece en Claude Desktop

1. Verifica que la ruta en `claude_desktop_config.json` sea correcta
2. Asegúrate de que Python esté en el PATH
3. Reinicia Claude Desktop completamente
4. Revisa los logs de Claude Desktop

### Error de conexión a la API

1. Verifica que la API esté corriendo: `curl http://190.7.234.37:7444/health`
2. Verifica que la URL en `API_BASE_URL` sea correcta
3. Asegúrate de que no haya firewall bloqueando la conexión

### Timeouts

Las operaciones pueden tardar hasta 5 minutos (especialmente el análisis completo). Si necesitas más tiempo, ajusta `API_TIMEOUT` en `server.py`.

## 📚 Documentación de la API

Para más detalles sobre los endpoints y respuestas, consulta:
- `API_ENDPOINTS.md` en el directorio raíz del proyecto
- Documentación interactiva: http://190.7.234.37:7444/docs

## 🤝 Contribuir

Para agregar nuevas herramientas al servidor MCP:

1. Agrega la definición de la herramienta en `handle_list_tools()`
2. Implementa la función handler en `handle_call_tool()`
3. Crea la función async que llama al endpoint de la API
4. Actualiza esta documentación

## 📄 Licencia

Este proyecto es parte del sistema Ubiquiti LLM Diagnostic Service.
