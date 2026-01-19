# API Endpoints - Ubiquiti LLM System

## Base URL
```
http://190.7.234.37:7444/api/v1
```

## 📚 Device Analysis Complete

### Analyze Device Complete
```bash
GET /analyze-device-complete?ip_address={ip}
```
**Descripción**: Análisis completo del dispositivo con IA, site survey, frecuencias, etc.

**Parámetros**:
- `ip_address` (required): IP del dispositivo

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/analyze-device-complete?ip_address=100.64.12.173"
```

---

## 📚 Device Overview

### Find Device Data
```bash
GET /find-device-data?query={query}
```
**Descripción**: Busca dispositivo y devuelve toda la data completa desde UISP

**Parámetros**:
- `query` (required): IP, nombre o MAC del dispositivo

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/find-device-data?query=100.64.12.173"
```

### Debug Device Overview
```bash
GET /debug-device-overview?ip_address={ip}
```
**Descripción**: Obtiene el overview completo del dispositivo desde UISP API

**Parámetros**:
- `ip_address` (required): IP del dispositivo

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/debug-device-overview?ip_address=100.64.12.173"
```

### Debug Device Overview by ID
```bash
GET /debug-device-overview/{device_id}
```
**Descripción**: Obtiene el overview completo por ID de dispositivo

**Parámetros**:
- `device_id` (required): ID del dispositivo en UISP

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/debug-device-overview/abc123"
```

### Search Devices
```bash
GET /search-devices?query={query}
```
**Descripción**: Busca dispositivos por IP, nombre o MAC

**Parámetros**:
- `query` (required): Término de búsqueda

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/search-devices?query=100.64"
```

---

## 📚 AP Clients

### AP Info with Clients
```bash
GET /ap-info-with-clients?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Obtiene información del AP actual y sus clientes conectados

**Parámetros**:
- `ip_address` (required): IP del dispositivo
- `ssh_username` (optional): Usuario SSH
- `ssh_password` (optional): Contraseña SSH

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/ap-info-with-clients?ip_address=100.64.12.173"
```

### AP Clients Only
```bash
GET /ap-clients-only?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Obtiene solo los clientes conectados al AP actual

**Parámetros**:
- `ip_address` (required): IP del dispositivo
- `ssh_username` (optional): Usuario SSH
- `ssh_password` (optional): Contraseña SSH

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/ap-clients-only?ip_address=100.64.12.173"
```

---

## 📚 Remote AP Clients

### List All APs
```bash
GET /list-all-aps
```
**Descripción**: Lista todos los APs encontrados en UISP para debug

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/list-all-aps"
```

### Get AP Clients by BSSID
```bash
GET /get-ap-clients-by-bssid?bssid={bssid}&ssid={ssid}
```
**Descripción**: Obtiene los clientes de un AP usando su BSSID desde UISP

**Parámetros**:
- `bssid` (required): BSSID del AP (ej: 802AA8249E26)
- `ssid` (optional): SSID del AP (ayuda a buscar)

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/get-ap-clients-by-bssid?bssid=802AA8249E26&ssid=Merc_Hipico_Panel2"
```

### Get AP Clients from Survey
```bash
GET /get-ap-clients-from-survey?station_ip={ip}
```
**Descripción**: Obtiene los clientes del mejor AP encontrado en el site survey

**Parámetros**:
- `station_ip` (required): IP de la estación que hizo el site survey

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/get-ap-clients-from-survey?station_ip=100.64.12.173"
```

---

## 📚 Debug SSH

### Debug SSH Commands
```bash
GET /debug-ssh-commands?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Endpoint para debug de comandos SSH y ver qué devuelven

**Parámetros**:
- `ip_address` (required): IP del dispositivo
- `ssh_username` (optional): Usuario SSH
- `ssh_password` (optional): Contraseña SSH

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/debug-ssh-commands?ip_address=100.64.12.173"
```

### Debug Station Info
```bash
GET /debug-station-info?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Verifica si el dispositivo es estación o AP

**Parámetros**:
- `ip_address` (required): IP del dispositivo
- `ssh_username` (optional): Usuario SSH
- `ssh_password` (optional): Contraseña SSH

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/debug-station-info?ip_address=100.64.12.173"
```

---

## 📚 Devices

### Get All Devices
```bash
GET /devices
```
**Descripción**: Obtiene todos los dispositivos

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/devices"
```

### Get Device by ID
```bash
GET /devices/{device_id}
```
**Descripción**: Obtiene un dispositivo específico por ID

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/devices/abc123"
```

---

## 📚 Diagnostics

### Diagnose Device by IP
```bash
POST /diagnostics/by-ip?ip_address={ip}&use_patterns={true/false}
```
**Descripción**: Diagnostica dispositivo por IP

**Parámetros**:
- `ip_address` (required): IP del dispositivo
- `use_patterns` (optional): Usar patrones predefinidos

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/diagnostics/by-ip?ip_address=100.64.12.173&use_patterns=true"
```

### Diagnose Device by ID
```bash
POST /diagnostics/{device_id}?use_patterns={true/false}
```
**Descripción**: Diagnostica dispositivo por ID

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/diagnostics/abc123?use_patterns=true"
```

### Scan Nearby APs
```bash
POST /diagnostics/scan-aps/by-ip?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Escanea APs cercanos desde el dispositivo

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/diagnostics/scan-aps/by-ip?ip_address=100.64.12.173"
```

### Analyze Complete by IP
```bash
POST /diagnostics/analyze-complete/by-ip?ip_address={ip}&use_ai={true/false}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Análisis completo por IP (similar a /analyze-device-complete)

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/diagnostics/analyze-complete/by-ip?ip_address=100.64.12.173&use_ai=true"
```

---

## 📚 AP Optimization

### Change Frequency Test by IP
```bash
POST /ap-optimization/change-frequency-test/by-ip?ip_address={ip}&frequency_mhz={freq}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Cambia frecuencia de prueba

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/ap-optimization/change-frequency-test/by-ip?ip_address=100.64.12.173&frequency_mhz=5840"
```

### Confirm Test Mode by IP
```bash
POST /ap-optimization/confirm-test-mode/by-ip?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Confirma modo de prueba

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/ap-optimization/confirm-test-mode/by-ip?ip_address=100.64.12.173"
```

### Cancel Test Mode by IP
```bash
POST /ap-optimization/cancel-test-mode/by-ip?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Cancela modo de prueba

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/ap-optimization/cancel-test-mode/by-ip?ip_address=100.64.12.173"
```

### Enable LiteBeam Frequencies by IP
```bash
POST /ap-optimization/enable-litebeam-frequencies/by-ip?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Habilita frecuencias LiteBeam

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/ap-optimization/enable-litebeam-frequencies/by-ip?ip_address=100.64.12.173"
```

### Debug Frequency Fields by IP
```bash
POST /ap-optimization/debug-frequency-fields/by-ip?ip_address={ip}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Debug de campos de frecuencia

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/ap-optimization/debug-frequency-fields/by-ip?ip_address=100.64.12.173"
```

### Change Frequency by IP
```bash
POST /ap-optimization/change-frequency/by-ip?ip_address={ip}&frequency_mhz={freq}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Cambia frecuencia

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/ap-optimization/change-frequency/by-ip?ip_address=100.64.12.173&frequency_mhz=5840"
```

### Enable All Frequencies by IP
```bash
POST /ap-optimization/enable-all-frequencies/by-ip?ip_address={ip}&use_ssh={true/false}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Habilita todas las frecuencias

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/ap-optimization/enable-all-frequencies/by-ip?ip_address=100.64.12.173&use_ssh=true"
```

### Optimize by IP
```bash
POST /ap-optimization/optimize-by-ip?ip_address={ip}&auto_apply={true/false}&ssh_username={user}&ssh_password={pass}
```
**Descripción**: Optimiza AP automáticamente

**Ejemplo**:
```bash
curl -X POST "http://190.7.234.37:7444/api/v1/ap-optimization/optimize-by-ip?ip_address=100.64.12.173&auto_apply=false"
```

---

## 📚 Logs

### Get Logs
```bash
GET /logs?log_type={app|error}&limit={number}&since={date}
```
**Descripción**: Obtiene logs del sistema

**Parámetros**:
- `log_type` (optional): "app" o "error"
- `limit` (optional): Número de líneas
- `since` (optional): Fecha desde cuando

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/logs?log_type=app&limit=50"
```

### Get Logs Stats
```bash
GET /logs/stats
```
**Descripción**: Obtiene estadísticas de los archivos de logs

**Ejemplo**:
```bash
curl "http://190.7.234.37:7444/api/v1/logs/stats"
```

### Clear Logs
```bash
DELETE /logs?log_type={app|error|all}
```
**Descripción**: Limpia logs

**Parámetros**:
- `log_type` (optional): "app", "error" o "all"

**Ejemplo**:
```bash
curl -X DELETE "http://190.7.234.37:7444/api/v1/logs?log_type=error"
```

---

## 🏷️ Tags de Endpoints

- **Device Analysis Complete**: Análisis completo con IA
- **Device Overview**: Información desde UISP
- **AP Clients**: Clientes via SSH
- **Remote AP Clients**: Clientes via UISP
- **Debug SSH**: Debug de comandos SSH
- **Devices**: Gestión de dispositivos
- **Diagnostics**: Diagnósticos varios
- **AP Optimization**: Optimización de APs
- **Logs**: Gestión de logs

---

## 🔧 Autenticación SSH

Para endpoints que requieren SSH, si no se proporcionan `ssh_username` y `ssh_password`, se usan los valores por defecto del archivo de configuración.

---

## 📊 Respuestas Típicas

### Análisis Completo
```json
{
    "success": true,
    "device": {"name": "DeviceName", "model": "Loco5AC", "ip": "100.64.12.173"},
    "analysis": {
        "llm_summary": "Resumen del análisis...",
        "ping": {"reachable": true, "avg_latency_ms": 14.9},
        "metrics": {...},
        "frequency_check": {...},
        "current_ap_info": {...},
        "site_survey": {...}
    }
}
```

### Información de AP
```json
{
    "success": true,
    "ap_info": {
        "device_id": "abc123",
        "name": "AP Name",
        "ip_address": "100.64.11.55",
        "clients_count": 29
    }
}
```

---

## 🚀 Uso Rápido

### 1. Analizar dispositivo completo
```bash
curl "http://190.7.234.37:7444/api/v1/analyze-device-complete?ip_address=100.64.12.173"
```

### 2. Buscar dispositivo
```bash
curl "http://190.7.234.37:7444/api/v1/find-device-data?query=100.64.12.173"
```

### 3. Ver clientes del AP actual
```bash
curl "http://190.7.234.37:7444/api/v1/ap-info-with-clients?ip_address=100.64.12.173"
```

### 4. Listar todos los APs
```bash
curl "http://190.7.234.37:7444/api/v1/list-all-aps"
```

### 5. Obtener clientes de AP remoto
```bash
curl "http://190.7.234.37:7444/api/v1/get-ap-clients-by-bssid?bssid=802AA8249E26"
```

---

*Última actualización: Enero 2026*
