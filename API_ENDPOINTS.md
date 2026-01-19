# API Endpoints - Ubiquiti LLM System

## Base URLl
```
http://localhost:8000/api/v1
```

---

## 🎯 Análisis Unificado (PRINCIPAL)

### 1. Análisis Completo Unificado
**Endpoint:** `POST /analyze-unified`

**Descripción:** Flujo completo automatizado que incluye:
1. ✅ Búsqueda por IP o MAC en UISP
2. ✅ Obtención de IP PPPoE si se busca por MAC
3. ✅ Configuración automática de frecuencias (AC/M5) si no están configuradas
4. ✅ Site survey con señal en dBm
5. ✅ Análisis de mejor AP disponible
6. ✅ Diagnóstico completo (LAN, Ethernet, throughput, uptime)
7. ✅ Recomendación con IA

**Query Parameters:**
- `ip_address` (string, opcional): IP del dispositivo (PPPoE o management)
- `mac_address` (string, opcional): MAC address del dispositivo
- `ssh_username` (string, opcional): Usuario SSH
- `ssh_password` (string, opcional): Contraseña SSH

**Nota:** Debe proporcionar `ip_address` O `mac_address`

**Ejemplo por IP:**
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-unified?ip_address=100.64.11.83"
```

**Ejemplo por MAC:**
```bash
curl -X POST "http://localhost:8000/api/v1/analyze-unified?mac_address=80:2a:a8:64:7f:d4"
```

**Respuesta:**
```json
{
  "success": true,
  "device_info": {
    "device_id": "xxx",
    "device_name": "Andy",
    "device_model": "LBE-5AC-23",
    "ip_address": "100.64.11.83",
    "uptime_seconds": 86400
  },
  "frequency_configuration": {
    "configured": true,
    "device_type": "AC",
    "frequencies_before": 2,
    "frequencies_after": 237,
    "frequencies_added": 235
  },
  "site_survey": {
    "total_aps": 55,
    "best_ap": {
      "ssid": "ubntsilva",
      "bssid": "80:2a:a8:64:7f:d4",
      "signal_dbm": -54,
      "frequency_mhz": 5745,
      "quality_percent": 78
    },
    "aps_top_5": [...]
  },
  "current_status": {
    "signal_dbm": -68,
    "frequency_mhz": 5180,
    "uptime_seconds": 86400
  },
  "diagnostic": {
    "status": "healthy",
    "issues": [],
    "recommendations": [],
    "confidence": 0.95
  },
  "recommendation": {
    "cambiar_ap": true,
    "razon": "Mejor AP disponible con 14 dBm más de señal",
    "ap_recomendado": "ubntsilva",
    "frecuencia_recomendada": 5745,
    "señal_actual": -68,
    "señal_recomendada": -54,
    "mejora_dbm": 14
  },
  "analysis_summary": {
    "device_healthy": true,
    "signal_quality": "débil",
    "should_change_ap": true,
    "frequencies_configured": true
  }
}
```

---

## 📊 Diagnósticos

### 1. Diagnóstico Completo por IP
**Endpoint:** `POST /diagnostics/analyze-complete/by-ip`

**Descripción:** Análisis completo del dispositivo con IA, incluyendo diagnóstico, site survey automático y recomendaciones de AP.

**Query Parameters:**
- `ip_address` (string, requerido): IP del dispositivo
- `use_patterns` (boolean, opcional): Usar patrones de diagnóstico (default: true)

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/diagnostics/analyze-complete/by-ip?ip_address=100.64.70.131"
```

**Respuesta:**
```json
{
  "device_id": "xxx",
  "device_name": "JulioTCh",
  "diagnostic": {
    "status": "healthy",
    "issues": [],
    "recommendations": []
  },
  "ap_scan": {
    "total_aps": 15,
    "best_ap": {
      "ssid": "AP-Principal",
      "signal": -45,
      "frequency": 5745
    }
  },
  "ai_recommendation": {
    "cambiar_ap": true,
    "ap_recomendado": "AP-Principal",
    "razon": "Mejor señal y menor interferencia"
  }
}
```

---

### 2. Escaneo de APs por IP
**Endpoint:** `POST /diagnostics/scan-aps/by-ip`

**Descripción:** Ejecuta site survey y escanea APs disponibles.

**Query Parameters:**
- `ip_address` (string, requerido): IP del di-11spositivo

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/diagnostics/scan-aps/by-ip?ip_address=100.64.70.131"
```

---

### 3. Diagnóstico por Device ID
**Endpoint:** `POST /diagnostics/{device_id}`

**Descripción:** Diagnóstico tradicional por ID de dispositivo.

**Path Parameters:**
- `device_id` (string, requerido): ID del dispositivo en UISP

**Query Parameters:**
- `use_patterns` (boolean, opcional): Usar patrones de diagnóstico

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/diagnostics/abc123?use_patterns=true"
```

---

## 🔧 Optimización de AP

### 4. Cambiar Frecuencia en Test Mode (con Rollback)
**Endpoint:** `POST /ap-optimization/change-frequency-test/by-ip`

**Descripción:** Cambia la frecuencia del dispositivo en Test Mode con rollback automático. Si no confirmas en el tiempo especificado, revierte automáticamente.

**Query Parameters:**
- `ip_address` (string, requerido): IP del dispositivo
- `frequency_mhz` (integer, requerido): Frecuencia en MHz (ej: 5840)
- `rollback_seconds` (integer, opcional): Segundos antes de revertir (default: 300)
- `interface` (string, opcional): Interfaz wireless (default: ath0)
- `ssh_username` (string, opcional): Usuario SSH
- `ssh_password` (string, opcional): Contraseña SSH

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/ap-optimization/change-frequency-test/by-ip?ip_address=100.64.11.83&frequency_mhz=5840&rollback_seconds=300"
```

**Respuesta:**
```json
{
  "success": true,
  "message": "✅ Frecuencia cambiada exitosamente de 5115 MHz a 5840 MHz. Scan list actualizada de [4930,5115] a [5840].",
  "frequency_mhz": 5840,
  "rollback_seconds": 300,
  "test_mode_active": true,
  "validation": {
    "scan_list_antes": "4930,5115",
    "frecuencia_antes": "5115",
    "frecuencia_solicitada": "5840",
    "scan_list_despues": "5840",
    "frecuencia_aplicada": "5840",
    "cambio_aplicado_exitoso": true
  },
  "instrucciones": {
    "confirmar": "POST /confirm-test-mode/by-ip?ip_address=100.64.11.83",
    "cancelar": "POST /cancel-test-mode/by-ip?ip_address=100.64.11.83",
    "automatico": "Si no haces nada, en 300 segundos se revertirá automáticamente CON REINICIO"
  }
}
```

---

### 5. Confirmar Test Mode
**Endpoint:** `POST /ap-optimization/confirm-test-mode/by-ip`

**Descripción:** Confirma los cambios realizados en Test Mode y desactiva el rollback automático.

**Query Parameters:**
- `ip_address` (string, requerido): IP del dispositivo
- `ssh_username` (string, opcional): Usuario SSH
- `ssh_password` (string, opcional): Contraseña SSH

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/ap-optimization/confirm-test-mode/by-ip?ip_address=100.64.11.83"
```

---

### 6. Cancelar Test Mode
**Endpoint:** `POST /ap-optimization/cancel-test-mode/by-ip`

**Descripción:** Cancela Test Mode y revierte los cambios inmediatamente con reinicio.

**Query Parameters:**
- `ip_address` (string, requerido): IP del dispositivo
- `ssh_username` (string, opcional): Usuario SSH
- `ssh_password` (string, opcional): Contraseña SSH

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/ap-optimization/cancel-test-mode/by-ip?ip_address=100.64.11.83"
```

---

### 7. Habilitar Todas las Frecuencias en LiteBeam AC
**Endpoint:** `POST /ap-optimization/enable-litebeam-frequencies/by-ip`

**Descripción:** Habilita automáticamente todas las 237 frecuencias disponibles en LiteBeam AC. Solo aplica cambios si:
1. El dispositivo es LiteBeam AC (LBE-5AC)
2. No tiene todas las frecuencias configuradas

**Query Parameters:**
- `ip_address` (string, requerido): IP del dispositivo
- `ssh_username` (string, opcional): Usuario SSH
- `ssh_password` (string, opcional): Contraseña SSH

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/ap-optimization/enable-litebeam-frequencies/by-ip?ip_address=100.64.11.83"
```

**Respuesta (ya configurado):**
```json
{
  "success": true,
  "message": "✅ LiteBeam AC ya tiene todas las 237 frecuencias configuradas.",
  "action": "skipped",
  "reason": "already_configured",
  "device_model": "LBE-5AC-23",
  "total_frequencies": 237,
  "frequency_range": "4920-6100"
}
```

**Respuesta (configurado automáticamente):**
```json
{
  "success": true,
  "message": "✅ LiteBeam AC configurado con todas las 237 frecuencias disponibles.",
  "action": "configured",
  "device_model": "LBE-5AC-23",
  "frequencies_before": 2,
  "frequencies_after": 237,
  "frequencies_added": 235,
  "frequency_range": "4920-6100",
  "current_config": "4930,5115",
  "new_config": "4920,4925,4930,..."
}
```

---

### 8. Cambiar Frecuencia (sin Test Mode)
**Endpoint:** `POST /ap-optimization/change-frequency/by-ip`

**Descripción:** Cambia la frecuencia del dispositivo permanentemente sin Test Mode.

**Query Parameters:**
- `ip_address` (string, requerido): IP del dispositivo
- `frequency_mhz` (integer, requerido): Frecuencia en MHz
- `interface` (string, opcional): Interfaz wireless (default: ath0)
- `ssh_username` (string, opcional): Usuario SSH
- `ssh_password` (string, opcional): Contraseña SSH

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/ap-optimization/change-frequency/by-ip?ip_address=100.64.11.83&frequency_mhz=5840"
```

---

### 9. Analizar APs con IA
**Endpoint:** `POST /ap-optimization/analyze-aps`

**Descripción:** Analiza lista de APs escaneados y recomienda el mejor usando IA.

**Body (JSON):**
```json
{
  "current_ap": {
    "ssid": "AP-Actual",
    "signal": -65,
    "frequency": 5180
  },
  "available_aps": [
    {
      "ssid": "AP-Mejor",
      "signal": -45,
      "frequency": 5745
    }
  ]
}
```

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/api/v1/ap-optimization/analyze-aps" \
  -H "Content-Type: application/json" \
  -d '{"current_ap": {...}, "available_aps": [...]}'
```

---

## 🔍 Debug y Utilidades

### 10. Ver Campos de Frecuencias
**Endpoint:** `GET /ap-optimization/debug-frequency-fields/by-ip`

**Descripción:** Endpoint temporal para ver todos los campos relacionados con frecuencias en `/tmp/system.cfg`.

**Query Parameters:**
- `ip_address` (string, requerido): IP del dispositivo
- `ssh_username` (string, opcional): Usuario SSH
- `ssh_password` (string, opcional): Contraseña SSH

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/ap-optimization/debug-frequency-fields/by-ip?ip_address=100.64.11.83"
```

**Respuesta:**
```json
{
  "success": true,
  "ip_address": "100.64.11.83",
  "all_frequency_fields": "radio.1.scanbw.status=disabled\nradio.1.scan_list.status=enabled\nradio.1.scan_list.channels=4930,5115\nradio.1.freq=5115",
  "fields_list": [
    "radio.1.scanbw.status=disabled",
    "radio.1.scan_list.status=enabled",
    "radio.1.scan_list.channels=4930,5115",
    "radio.1.freq=5115"
  ]
}
```

---

## 📱 Dispositivos

### 11. Listar Todos los Dispositivos
**Endpoint:** `GET /devices`

**Descripción:** Lista todos los dispositivos registrados en UISP.

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/devices"
```

---

### 12. Obtener Dispositivo por ID
**Endpoint:** `GET /devices/{device_id}`

**Descripción:** Obtiene información detallada de un dispositivo específico.

**Path Parameters:**
- `device_id` (string, requerido): ID del dispositivo

**Ejemplo:**
```bash
curl "http://localhost:8000/api/v1/devices/abc123"
```

---

## 🏥 Health Check

### 13. Health Check
**Endpoint:** `GET /health`

**Descripción:** Verifica el estado de la API.

**Ejemplo:**
```bash
curl "http://localhost:8000/health"
```

**Respuesta:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## 📋 Flujos de Trabajo Recomendados

### Flujo 1: Análisis Completo y Optimización
```bash
# 1. Análisis completo con site survey automático
curl -X POST "http://localhost:8000/api/v1/diagnostics/analyze-complete/by-ip?ip_address=100.64.70.131"

# 2. Si la IA recomienda cambiar AP, cambiar frecuencia en Test Mode
curl -X POST "http://localhost:8000/api/v1/ap-optimization/change-frequency-test/by-ip?ip_address=100.64.70.131&frequency_mhz=5745&rollback_seconds=300"

# 3. Verificar que funciona (tienes 5 minutos)

# 4. Confirmar cambios
curl -X POST "http://localhost:8000/api/v1/ap-optimization/confirm-test-mode/by-ip?ip_address=100.64.70.131"
```

### Flujo 2: Configurar LiteBeam AC para Site Survey Completo
```bash
# 1. Habilitar todas las frecuencias (solo si es LiteBeam AC y faltan frecuencias)
curl -X POST "http://localhost:8000/api/v1/ap-optimization/enable-litebeam-frequencies/by-ip?ip_address=100.64.11.83"

# 2. Ejecutar análisis completo (ahora escaneará todas las 237 frecuencias)
curl -X POST "http://localhost:8000/api/v1/diagnostics/analyze-complete/by-ip?ip_address=100.64.11.83"
```

### Flujo 3: Test Mode Seguro
```bash
# 1. Cambiar frecuencia en Test Mode (rollback automático en 5 min)
curl -X POST "http://localhost:8000/api/v1/ap-optimization/change-frequency-test/by-ip?ip_address=100.64.11.83&frequency_mhz=5840&rollback_seconds=300"

# 2a. Si funciona - Confirmar
curl -X POST "http://localhost:8000/api/v1/ap-optimization/confirm-test-mode/by-ip?ip_address=100.64.11.83"

# 2b. Si NO funciona - Cancelar inmediatamente
curl -X POST "http://localhost:8000/api/v1/ap-optimization/cancel-test-mode/by-ip?ip_address=100.64.11.83"

# 2c. Si no haces nada - Revierte automáticamente en 5 minutos
```

---

## 🔐 Configuración SSH

Los endpoints que requieren SSH usan las siguientes credenciales por defecto (configurables en `.env`):

```bash
UBIQUITI_SSH_USERNAME=ubnt
UBIQUITI_SSH_PASSWORD=ubnt
```

Puedes sobrescribir estas credenciales pasando `ssh_username` y `ssh_password` como query parameters.

---

## 📊 Modelos de Dispositivos Soportados

### LiteBeam AC (237 frecuencias: 4920-6100 MHz)
- LBE-5AC-Gen2
- LBE-5AC-16-120
- LBE-5AC-23

### NanoBeam AC (146 frecuencias: 5150-5875 MHz)
- NBE-5AC-Gen2
- NBE-5AC-16
- NBE-5AC-19

### PowerBeam AC (146 frecuencias: 5150-5875 MHz)
- PBE-5AC-Gen2
- PBE-5AC-300
- PBE-5AC-400
- PBE-5AC-500
- PBE-5AC-620

Y más modelos...

---

## 🚨 Códigos de Error Comunes

| Código | Descripción | Solución |
|--------|-------------|----------|
| 404 | Dispositivo no encontrado | Verifica la IP del dispositivo |
| 500 | Error SSH | Verifica credenciales SSH y conectividad |
| 400 | Frecuencia inválida | Usa una frecuencia válida para el modelo |

---

## 📝 Notas Importantes

1. **Test Mode es seguro**: Si pierdes conexión, el dispositivo revierte automáticamente.
2. **LiteBeam AC**: Usa el endpoint `/enable-litebeam-frequencies` antes del site survey para escanear todas las frecuencias.
3. **Site Survey automático**: El endpoint `/analyze-complete` ejecuta site survey automáticamente si la señal es baja.
4. **Validación inteligente**: El sistema valida frecuencias según el modelo del dispositivo.
5. **Sin reinicio innecesario**: Usa `rc.softrestart` que solo reinicia servicios wireless, no el dispositivo completo.

---

## 🔄 Versión
**API Version:** 1.0.0  
**Última actualización:** 2026-01-18
