# Configuración del Servidor MCP en n8n

Esta guía te ayudará a integrar el servidor MCP de Ubiquiti LLM con n8n.

## 📋 Requisitos Previos

1. ✅ API de Ubiquiti LLM corriendo en `http://190.7.234.37:7444`
2. ✅ n8n instalado y corriendo
3. ✅ Python 3.10+ instalado

## 🚀 Instalación

### 1. Instalar Dependencias

```bash
cd mcp_server
pip install fastapi uvicorn httpx pydantic
```

O con el script de instalación:

```bash
./install.sh
```

### 2. Iniciar el Servidor HTTP/SSE

```bash
python server_http.py
```

El servidor se iniciará en `http://localhost:3000` con los siguientes endpoints:

- **SSE Endpoint**: `http://localhost:3000/sse` (para n8n)
- **Tools List**: `http://localhost:3000/tools`
- **Health Check**: `http://localhost:3000/health`

## 🔧 Configuración en n8n

### Paso 1: Agregar Nodo MCP Client

1. En tu workflow de n8n, agrega un nodo **"MCP Client"**
2. Conecta el nodo a un AI Agent (como OpenAI, Anthropic, etc.)

### Paso 2: Configurar el SSE Endpoint

En el nodo MCP Client, configura:

```
SSE Endpoint: http://localhost:3000/sse
Authentication: None
Tools to Include: All
```

Si el servidor MCP está en otro servidor, usa la IP correspondiente:

```
SSE Endpoint: http://190.7.234.37:3000/sse
```

### Paso 3: Conectar a un AI Agent

El nodo MCP Client debe estar conectado a un nodo de AI Agent. El flujo típico es:

```
[Trigger] → [AI Agent] → [MCP Client] → [Output]
```

## 🛠️ Herramientas Disponibles

Una vez configurado, el AI Agent tendrá acceso a estas herramientas:

### 1. analyze_device_complete
Análisis completo de un dispositivo Ubiquiti.

**Parámetros:**
- `ip_address` (opcional): IP del dispositivo
- `mac_address` (opcional): MAC del dispositivo
- `ssh_username` (opcional): Usuario SSH
- `ssh_password` (opcional): Contraseña SSH

**Ejemplo de uso en n8n:**
```
User: "Analiza el dispositivo con IP 100.64.11.83"
```

### 2. get_device_info
Obtiene información básica desde UISP.

**Parámetros:**
- `ip_address` o `mac_address`

### 3. site_survey
Escaneo de APs disponibles.

**Parámetros:**
- `ip_address`: IP del dispositivo
- `ssh_username` (opcional)
- `ssh_password` (opcional)

### 4. configure_frequencies
Configuración automática de frecuencias.

**Parámetros:**
- `ip_address`: IP del dispositivo
- `ssh_username` (opcional)
- `ssh_password` (opcional)

### 5. ping_device
Verificación de conectividad.

**Parámetros:**
- `ip_address`: IP del dispositivo
- `count` (opcional): Número de paquetes (default: 5)

## 📊 Ejemplo de Workflow en n8n

### Workflow Básico: Diagnóstico de Dispositivo

```
1. [Webhook Trigger]
   ↓
2. [AI Agent - OpenAI/Anthropic]
   ↓
3. [MCP Client - Ubiquiti LLM]
   ↓
4. [Response]
```

**Configuración del AI Agent:**
- Model: gpt-4 o claude-3-sonnet
- System Prompt: "Eres un asistente técnico especializado en dispositivos Ubiquiti. Usa las herramientas disponibles para diagnosticar y resolver problemas."

**Ejemplo de entrada:**
```json
{
  "message": "El cliente reporta mala señal en el dispositivo 100.64.11.83. Analiza el dispositivo y recomienda una solución."
}
```

**El AI Agent automáticamente:**
1. Llamará a `analyze_device_complete` con la IP
2. Analizará los resultados
3. Proporcionará recomendaciones basadas en el diagnóstico

## 🔒 Desplegar en Producción

### Opción 1: Servidor Local

Si n8n está en el mismo servidor que la API:

```bash
# Iniciar el servidor MCP en background
nohup python server_http.py > mcp_server.log 2>&1 &
```

### Opción 2: Docker

Crear un `Dockerfile` para el servidor MCP:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY server_http.py .
RUN pip install fastapi uvicorn httpx pydantic

EXPOSE 3000

CMD ["python", "server_http.py"]
```

Construir y ejecutar:

```bash
docker build -t ubiquiti-mcp-server .
docker run -d -p 3000:3000 ubiquiti-mcp-server
```

### Opción 3: Systemd Service

Crear `/etc/systemd/system/ubiquiti-mcp.service`:

```ini
[Unit]
Description=Ubiquiti LLM MCP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ubiquiti-llm/mcp_server
ExecStart=/usr/bin/python3 /opt/ubiquiti-llm/mcp_server/server_http.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Habilitar y iniciar:

```bash
sudo systemctl enable ubiquiti-mcp
sudo systemctl start ubiquiti-mcp
sudo systemctl status ubiquiti-mcp
```

## 🧪 Pruebas

### Verificar que el servidor está corriendo

```bash
curl http://localhost:3000/health
```

Respuesta esperada:
```json
{
  "status": "healthy",
  "mcp_server": "running",
  "api_connection": "ok"
}
```

### Listar herramientas disponibles

```bash
curl http://localhost:3000/tools
```

### Probar el endpoint SSE

```bash
curl -X POST http://localhost:3000/sse \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/list"
  }'
```

## 🔍 Troubleshooting

### El nodo MCP Client no se conecta

1. Verifica que el servidor MCP esté corriendo:
   ```bash
   curl http://localhost:3000/health
   ```

2. Verifica que la URL del SSE Endpoint sea correcta en n8n

3. Revisa los logs del servidor MCP

### Timeouts en operaciones largas

El servidor está configurado con un timeout de 5 minutos. Si necesitas más tiempo, edita `API_TIMEOUT` en `server_http.py`:

```python
API_TIMEOUT = 600.0  # 10 minutos
```

### Error de conexión a la API

Verifica que la API de Ubiquiti LLM esté corriendo:

```bash
curl http://190.7.234.37:7444/health
```

Si la API está en otra URL, actualiza `API_BASE_URL` en `server_http.py`.

## 📚 Recursos Adicionales

- [Documentación de n8n MCP](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.mcpclient/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [API Endpoints de Ubiquiti LLM](../API_ENDPOINTS.md)

## 💡 Casos de Uso

### 1. Chatbot de Soporte Técnico

Crea un chatbot en n8n que:
- Recibe consultas de clientes vía Telegram/WhatsApp
- Usa el AI Agent con MCP para diagnosticar dispositivos
- Responde automáticamente con soluciones

### 2. Monitoreo Proactivo

Workflow que:
- Se ejecuta cada hora
- Analiza dispositivos críticos
- Envía alertas si detecta problemas

### 3. Portal de Auto-Servicio

API que permite a clientes:
- Consultar estado de su dispositivo
- Obtener recomendaciones de mejora
- Ver APs disponibles para cambio

## 🤝 Contribuir

Para agregar nuevas herramientas:

1. Agrega la definición en `TOOLS` en `server_http.py`
2. Implementa la función handler en `call_tool()`
3. Crea la función async que llama al endpoint de la API
4. Actualiza esta documentación

---

¿Necesitas ayuda? Revisa los logs del servidor o contacta al equipo de desarrollo.
