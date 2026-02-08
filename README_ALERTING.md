# 🚨 Sistema de Alertas - Guía Completa

## ✅ Estado de Implementación

Todas las funcionalidades del sistema de alertas están **completamente implementadas** y listas para usar.

---

## 📦 Componentes Implementados

### 1. **Modelos de Base de Datos**
- ✅ `SiteMonitoring` - Datos de sites UISP
- ✅ `AlertEvent` - Eventos de alertas
- ✅ `AlertNotification` - Tracking de notificaciones enviadas (NUEVO)
- ✅ `PostMortem` - Análisis post-incidente (NUEVO)

### 2. **Repositorios**
- ✅ `SiteMonitoringRepository`
- ✅ `AlertEventRepository`
- ✅ `AlertNotificationRepository` (NUEVO)
- ✅ `PostMortemRepository` (NUEVO)

### 3. **Servicios**
- ✅ `UNMSAlertingService` - Lógica de alertas
- ✅ `AlertEventService` - Gestión de eventos
- ✅ `WhatsAppService` - Notificaciones por WhatsApp (NUEVO)
- ✅ `PostMortemService` - Análisis de incidentes (NUEVO)
- ✅ `SiteMonitoringPollingService` - Polling automático (NUEVO)

### 4. **Endpoints API** (34 endpoints totales)

#### Alertas Base
```
GET    /api/v1/alerting/events
GET    /api/v1/alerting/events/{id}
POST   /api/v1/alerting/events
POST   /api/v1/alerting/events/{id}/acknowledge
POST   /api/v1/alerting/events/{id}/resolve
DELETE /api/v1/alerting/events/{id}
GET    /api/v1/alerting/events/active
```

#### Sites
```
POST   /api/v1/alerting/scan-sites
GET    /api/v1/alerting/sites
GET    /api/v1/alerting/sites/outages
GET    /api/v1/alerting/sites/{site_id}
```

#### WhatsApp (NUEVO)
```
POST   /api/v1/alerting/scan-sites-with-alerts
POST   /api/v1/alerting/test-notification
```

#### Post-Mortem (NUEVO)
```
POST   /api/v1/alerting/post-mortems
GET    /api/v1/alerting/post-mortems
GET    /api/v1/alerting/post-mortems/{id}
PUT    /api/v1/alerting/post-mortems/{id}
DELETE /api/v1/alerting/post-mortems/{id}
POST   /api/v1/alerting/post-mortems/{id}/complete
POST   /api/v1/alerting/post-mortems/{id}/review
GET    /api/v1/alerting/post-mortems/{id}/report
```

#### Polling (NUEVO)
```
POST   /api/v1/alerting/polling/start
POST   /api/v1/alerting/polling/stop
GET    /api/v1/alerting/polling/status
```

---

## 🔧 Configuración

### 1. Variables de Entorno

Agregar al `.env`:

```bash
# WhatsApp Service Configuration
WHATSAPP_API_URL=http://190.7.234.37:7842/api/whatsapp/send/text
WHATSAPP_ENABLED=true

# Números de teléfono (código país + número, sin espacios ni +)
WHATSAPP_PHONE_COMPLETE=5491112345678  # Mensaje completo
WHATSAPP_PHONE_SUMMARY=5491198765432   # Mensaje resumido

# Polling Configuration
POLLING_ENABLED=true          # Auto-start al iniciar servidor
POLLING_INTERVAL_SECONDS=300  # 5 minutos

# Alerting Configuration
ALERT_OUTAGE_THRESHOLD_PERCENT=95  # Umbral de caída crítica
```

### 2. Migración de Base de Datos

El sistema creará las tablas automáticamente al iniciar:
- `alert_notifications`
- `post_mortems`

Si necesitas ejecutar la migración manualmente:
```python
from app_fast_api.utils.database import init_db
init_db()
```

---

## 🚀 Inicio Rápido

### 1. Configurar Variables
```bash
# Editar .env con los valores de WhatsApp y polling
nano .env
```

### 2. Reiniciar Servidor
```bash
# Local
python app_fast_api/main.py

# Docker
docker compose restart
```

### 3. Verificar Estado
```bash
# Health check
curl http://localhost:7657/api/v1/alerting/health

# Estado del polling
curl http://localhost:7657/api/v1/alerting/polling/status
```

### 4. Test de WhatsApp
```bash
# Test mensaje completo
curl -X POST http://localhost:7657/api/v1/alerting/test-notification \
  -H "Content-Type: application/json" \
  -d '{"type": "complete"}'

# Test mensaje resumido
curl -X POST http://localhost:7657/api/v1/alerting/test-notification \
  -H "Content-Type: application/json" \
  -d '{"type": "summary"}'

# Test mensaje de recuperación
curl -X POST http://localhost:7657/api/v1/alerting/test-notification \
  -H "Content-Type: application/json" \
  -d '{"type": "recovery"}'
```

---

## 📱 Mensajes de WhatsApp

### Mensaje Completo
Enviado a `WHATSAPP_PHONE_COMPLETE`:
```
🚨 ALERTA CRÍTICA - SITE CAÍDO

📍 Site: [4] Nodo Estudiantes
⚠️ Estado: 95% de dispositivos caídos (65/69)
🕐 Detectado: 2024-01-15 14:30:00

📋 INFORMACIÓN DE CONTACTO
👤 Contacto: Carlos
📱 Teléfono: 2324500057
📧 Email: Por definir

🚪 ACCESO AL NODO
Tipo: Ingreso libre

🔋 ENERGÍA
Baterías: Si
Duración: 4 Horas

🏢 COOPERATIVA
Nombre: Eden Nis 1697321-01
☎️  Teléfono: 0800-999-3336 (24h)

🔗 CONECTIVIDAD DE RESPALDO
Nodo vecino: Arzobispado
AP disponible: Hornet_Arzo_Nissan

👮 CRITERIOS GUARDIA
Se envía guardia si: Corte de fibra para grupo
Horarios: 24h / 365 días
```

### Mensaje Resumido
Enviado a `WHATSAPP_PHONE_SUMMARY`:
```
🚨 ALERTA: [4] Nodo Estudiantes CAÍDO
⚠️ 65/69 dispositivos down (94%)
🕐 14:30:00
```

### Mensaje de Recuperación
Enviado a **ambos números**:
```
✅ RECUPERACIÓN: [4] Nodo Estudiantes
⏱️ Caída: 2h 35min
📊 Devices: 69/69 activos
🕐 Recuperado: 17:05:00
```

---

## 🔄 Polling Automático

### Funcionamiento

Cuando `POLLING_ENABLED=true`:
1. ✅ Se inicia automáticamente al arrancar el servidor
2. ✅ Escanea sites cada `POLLING_INTERVAL_SECONDS`
3. ✅ Detecta caídas (>95% devices down)
4. ✅ Detecta recuperaciones
5. ✅ Envía WhatsApp automáticamente
6. ✅ Valida disponibilidad de UISP antes de alertar

### Control Manual

```bash
# Iniciar polling
curl -X POST http://localhost:7657/api/v1/alerting/polling/start

# Detener polling
curl -X POST http://localhost:7657/api/v1/alerting/polling/stop

# Ver estado
curl http://localhost:7657/api/v1/alerting/polling/status
```

### Respuesta de Estado
```json
{
  "is_running": true,
  "enabled": true,
  "interval_seconds": 300,
  "last_scan_time": "2024-01-15T14:30:00",
  "last_scan_result": {
    "success": true,
    "summary": {
      "total_sites": 45,
      "sites_down": 2,
      "sites_recovered": 1
    },
    "notifications": {
      "outage_alerts_sent": 2,
      "recovery_alerts_sent": 1
    }
  }
}
```

---

## 📊 Post-Mortem

### Crear Post-Mortem

```bash
curl -X POST http://localhost:7657/api/v1/alerting/post-mortems \
  -H "Content-Type: application/json" \
  -d '{
    "alert_event_id": 123,
    "title": "Caída masiva Nodo Estudiantes",
    "summary": "Corte de fibra afectó 65 dispositivos",
    "root_cause": "Corte de fibra por trabajos en la vía pública",
    "author": "Juan Perez",
    "timeline_events": [
      {
        "time": "14:30",
        "event": "Detectada caída del site"
      },
      {
        "time": "14:35",
        "event": "Técnico notificado"
      },
      {
        "time": "17:05",
        "event": "Servicio restaurado"
      }
    ],
    "preventive_actions": [
      {
        "action": "Solicitar bypass de fibra a la cooperativa",
        "owner": "NOC",
        "priority": "high"
      }
    ]
  }'
```

### Listar Post-Mortems

```bash
# Todos
curl http://localhost:7657/api/v1/alerting/post-mortems

# Solo completados
curl "http://localhost:7657/api/v1/alerting/post-mortems?status=completed"
```

### Generar Reporte

```bash
curl http://localhost:7657/api/v1/alerting/post-mortems/123/report
```

Respuesta:
```json
{
  "post_mortem": {
    "id": 123,
    "title": "Caída masiva Nodo Estudiantes",
    "status": "completed",
    "downtime_minutes": 155,
    ...
  },
  "metrics": {
    "mttr_minutes": 155,
    "mttr_hours": 2.58,
    "detection_time_minutes": 5,
    "response_time_minutes": 10,
    "resolution_time_minutes": 155
  },
  "generated_at": "2024-01-15T18:00:00"
}
```

---

## 🔒 Características de Seguridad

### ✅ Validación de UISP
Antes de enviar alertas, el sistema verifica que UISP esté disponible:
```python
# Si UISP no responde → NO envía alertas
# Previene falsos positivos durante caídas de UISP
```

### ✅ Reintentos Automáticos
- 3 reintentos en caso de fallo
- Delay exponencial entre reintentos
- Tracking completo en `alert_notifications`

### ✅ Rate Limiting
- Evita spam de notificaciones
- Deduplicación de eventos

### ✅ Logging Completo
- Todas las notificaciones se registran
- Tracking de errores y reintentos
- Métricas de envío

---

## 🧪 Testing

### Swagger UI
```
http://localhost:7657/docs
```

### Endpoints de Test

1. **Health Check**
   ```bash
   curl http://localhost:7657/api/v1/alerting/health
   ```

2. **Test Notificación**
   ```bash
   curl -X POST http://localhost:7657/api/v1/alerting/test-notification \
     -H "Content-Type: application/json" \
     -d '{"type": "complete"}'
   ```

3. **Scan Manual**
   ```bash
   curl -X POST http://localhost:7657/api/v1/alerting/scan-sites-with-alerts
   ```

4. **Estado de Polling**
   ```bash
   curl http://localhost:7657/api/v1/alerting/polling/status
   ```

---

## 📈 Métricas y Analytics

### Métricas Disponibles

- **MTTR** (Mean Time To Recovery): Tiempo promedio de recuperación
- **MTBF** (Mean Time Between Failures): Tiempo entre fallos
- **Uptime**: Porcentaje de disponibilidad por site
- **Incident Count**: Conteo de incidentes por período

### Calculadas Automáticamente

- `detection_time`: Tiempo desde inicio hasta detección
- `response_time`: Tiempo desde detección hasta respuesta
- `resolution_time`: Tiempo desde inicio hasta resolución
- `downtime_minutes`: Minutos totales de caída

---

## 🐛 Troubleshooting

### Polling no inicia
```bash
# Verificar configuración
echo $POLLING_ENABLED  # Debe ser "true"

# Ver logs
docker compose logs -f | grep polling

# Iniciar manualmente
curl -X POST http://localhost:7657/api/v1/alerting/polling/start
```

### WhatsApp no envía
```bash
# Verificar configuración
echo $WHATSAPP_ENABLED  # Debe ser "true"
echo $WHATSAPP_PHONE_COMPLETE
echo $WHATSAPP_PHONE_SUMMARY

# Test manual
curl -X POST http://localhost:7657/api/v1/alerting/test-notification \
  -H "Content-Type: application/json" \
  -d '{"type": "summary"}'

# Ver logs
docker compose logs -f | grep WhatsApp
```

### UISP no responde
```bash
# El sistema NO enviará alertas si UISP no responde
# Ver logs para confirmar
docker compose logs -f | grep "UISP unavailable"
```

---

## 📚 Documentos Relacionados

- `ALERTING_SYSTEM_V2.md` - Diseño técnico completo
- `WHATSAPP_CONFIG.md` - Configuración de WhatsApp
- `CLAUDE.md` - Guía del proyecto

---

## 🎯 Próximos Pasos Sugeridos

1. ✅ Configurar variables de entorno
2. ✅ Reiniciar servidor
3. ✅ Probar con endpoint de test
4. ✅ Habilitar polling automático
5. ⏳ Monitorear logs durante 24h
6. ⏳ Crear post-mortems de incidentes reales
7. ⏳ Analizar métricas semanalmente

---

## 💡 Tips

- **Desarrollo**: `POLLING_ENABLED=false` para evitar scans constantes
- **Producción**: `POLLING_ENABLED=true` con `POLLING_INTERVAL_SECONDS=300`
- **Testing**: Usa `test-notification` antes de scan real
- **Logs**: `docker compose logs -f` para ver actividad en tiempo real

---

## 🆘 Soporte

Si tienes problemas:
1. Revisa logs: `docker compose logs -f`
2. Verifica configuración en `.env`
3. Prueba endpoints de test primero
4. Consulta `ALERTING_SYSTEM_V2.md` para detalles técnicos

---

**Sistema implementado y listo para producción** 🚀
