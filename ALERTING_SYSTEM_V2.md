# Sistema de Alertas y Post-Mortem - Diseño Completo

## 📋 Descripción General

Sistema completo de alertas basado en eventos para monitoreo de sites UISP con:
- Detección automática de caídas (>95% devices down)
- Notificaciones por WhatsApp (mensaje completo y resumido)
- Polling automático y detección de recuperación
- Sistema de Post-Mortem para análisis de incidentes
- Métricas y analytics (MTTR, uptime, etc.)

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│         UISP API (/v2.1/sites)         │
└──────────────┬──────────────────────────┘
               │ Polling (cada 5 min)
┌──────────────▼──────────────────────────┐
│    SiteMonitoringPollingService        │
│  • Scan all sites                       │
│  • Detect outages (>95% down)          │
│  • Detect recoveries                    │
│  • Calculate metrics                    │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼────┐ ┌──▼────┐ ┌──▼─────────────┐
│   DB   │ │ Alert │ │   WhatsApp     │
│ Events │ │Engine │ │   Service      │
└────────┘ └───────┘ └────────────────┘
                           │
                      ┌────┴────┐
                      │         │
              ┌───────▼──┐ ┌───▼────────┐
              │ Message  │ │ Notification│
              │ Complete │ │  Summary    │
              └──────────┘ └─────────────┘
```

---

## 📊 Modelos de Base de Datos

### 1. SiteMonitoring (ya existe)
```python
- site_id (UUID de UISP)
- site_name
- device_count
- device_outage_count
- outage_percentage
- is_site_down (>95%)
- contact_info (JSON)
- description
- last_checked_at
```

### 2. AlertEvent (ya existe, mejorado)
```python
- event_type (site_outage, site_recovery, etc.)
- severity (critical, high, medium, low)
- status (active, acknowledged, resolved)
- site_id (FK)
- title, description
- metadata (JSON)
- timestamps (created, acknowledged, resolved)
```

### 3. AlertNotification (NUEVO)
```python
- alert_event_id (FK)
- channel (whatsapp, email, webhook, sms)
- recipient (phone/email)
- status (pending, sent, failed, retry)
- message_type (full, summary, recovery)
- message_content
- sent_at, delivered_at, failed_at
- retry_count, error_message
- provider_message_id
- metadata (JSON)
```

### 4. PostMortem (NUEVO)
```python
- alert_event_id (FK único)
- title, status (draft, in_progress, completed, reviewed)
- incident_start, incident_end
- detection_time, response_time, resolution_time
- summary, impact_description
- root_cause, trigger
- affected_users, affected_devices, downtime_minutes
- severity, customer_impact
- timeline_events (JSON array)
- response_actions (JSON array)
- resolution_description
- preventive_actions (JSON array)
- lessons_learned
- action_items (JSON array)
- author, reviewers, contributors (JSON)
- tags, related_incidents, external_links (JSON)
```

---

## 🔧 Servicios

### 1. **WhatsAppService** (NUEVO)
```python
class WhatsAppService:
    def send_message(phone: str, message: str) -> bool
    def send_template_message(phone: str, template: str, params: dict) -> bool
    def format_full_message(site: SiteMonitoring, event: AlertEvent) -> str
    def format_summary_message(site: SiteMonitoring, event: AlertEvent) -> str
    def format_recovery_message(site: SiteMonitoring, event: AlertEvent) -> str
```

**Formatos de mensajes:**

**Mensaje Completo:**
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

🔗 Ver detalles: [URL]
```

**Mensaje Resumido:**
```
🚨 ALERTA: Site "[4] Nodo Estudiantes" CAÍDO
⚠️ 65/69 dispositivos down (94%)
📱 Contacto: Carlos - 2324500057
🕐 14:30:00
```

**Mensaje de Recuperación:**
```
✅ RECUPERACIÓN: [4] Nodo Estudiantes
⏱️ Caída: 2h 35min
📊 Devices: 69/69 activos
🕐 Recuperado: 17:05:00
```

### 2. **SiteMonitoringPollingService** (NUEVO)
```python
class SiteMonitoringPollingService:
    async def poll_all_sites() -> dict
    async def detect_outages() -> List[AlertEvent]
    async def detect_recoveries() -> List[AlertEvent]
    async def calculate_metrics(site_id: str) -> dict
```

### 3. **PostMortemService** (NUEVO)
```python
class PostMortemService:
    def create_post_mortem(alert_event_id: int, data: dict) -> PostMortem
    def update_post_mortem(post_mortem_id: int, data: dict) -> PostMortem
    def get_post_mortem(post_mortem_id: int) -> PostMortem
    def list_post_mortems(filters: dict) -> List[PostMortem]
    def calculate_mttr(post_mortem_id: int) -> int
    def generate_report(post_mortem_id: int) -> dict
```

---

## 🌐 Endpoints API

### Alertas Base
```
GET    /api/v1/alerting/events           # Listar eventos
GET    /api/v1/alerting/events/{id}      # Detalle de evento
POST   /api/v1/alerting/events/{id}/acknowledge  # Reconocer evento
POST   /api/v1/alerting/events/{id}/resolve      # Resolver evento
DELETE /api/v1/alerting/events/{id}      # Eliminar evento
```

### Polling y Monitoreo
```
POST   /api/v1/alerting/scan-sites       # Scan manual (ya existe)
POST   /api/v1/alerting/polling/start    # Iniciar polling automático
POST   /api/v1/alerting/polling/stop     # Detener polling
GET    /api/v1/alerting/polling/status   # Estado del polling
```

### Sites
```
GET    /api/v1/alerting/sites                    # Listar sites monitoreados
GET    /api/v1/alerting/sites/{site_id}          # Detalle de site
GET    /api/v1/alerting/sites/{site_id}/events   # Eventos de un site
GET    /api/v1/alerting/sites/{site_id}/metrics  # Métricas de un site
```

### Notificaciones
```
GET    /api/v1/alerting/notifications           # Historial de notificaciones
GET    /api/v1/alerting/notifications/{id}      # Detalle de notificación
POST   /api/v1/alerting/notifications/test      # Test de notificación
POST   /api/v1/alerting/notifications/retry/{id} # Reintentar notificación
```

### Post-Mortem
```
POST   /api/v1/alerting/post-mortems                # Crear post-mortem
GET    /api/v1/alerting/post-mortems                # Listar post-mortems
GET    /api/v1/alerting/post-mortems/{id}          # Detalle de post-mortem
PUT    /api/v1/alerting/post-mortems/{id}          # Actualizar post-mortem
DELETE /api/v1/alerting/post-mortems/{id}          # Eliminar post-mortem
POST   /api/v1/alerting/post-mortems/{id}/complete # Marcar como completado
POST   /api/v1/alerting/post-mortems/{id}/review   # Marcar como revisado
GET    /api/v1/alerting/post-mortems/{id}/report   # Generar reporte
```

### Analytics y Métricas
```
GET    /api/v1/alerting/metrics/overview         # Métricas generales
GET    /api/v1/alerting/metrics/mttr             # Mean Time To Recovery
GET    /api/v1/alerting/metrics/mtbf             # Mean Time Between Failures
GET    /api/v1/alerting/metrics/uptime           # Uptime por site
GET    /api/v1/alerting/metrics/incidents-count  # Conteo de incidentes
```

---

## 🔄 Flujo de Trabajo

### 1. Detección de Caída
```
1. Polling service escanea sites cada 5 min
2. Detecta deviceOutageCount >= 95% de deviceCount
3. Crea AlertEvent (type=site_outage, severity=critical)
4. Guarda en DB
5. Trigger WhatsAppService:
   - Envía mensaje completo
   - Envía mensaje resumido
6. Guarda AlertNotification para tracking
```

### 2. Detección de Recuperación
```
1. Polling detecta site recuperado (deviceOutageCount < 50%)
2. Actualiza AlertEvent (status=resolved)
3. Calcula métricas (downtime, MTTR)
4. Trigger WhatsAppService:
   - Envía mensaje de recuperación
5. Auto-crea template de PostMortem (draft)
```

### 3. Post-Mortem
```
1. NOC crea/completa post-mortem vía API
2. Agrega: root cause, timeline, actions
3. Status: draft → in_progress → completed → reviewed
4. Sistema calcula métricas automáticas
5. Frontend consulta via API para visualización
```

---

## 🚀 Mejoras Propuestas

### 1. **Escalamiento Inteligente**
- Si el site no se recupera en X tiempo, escalar severidad
- Notificar a contactos adicionales

### 2. **Detección Proactiva**
- Alertas si deviceOutageCount > 50% (warning)
- Alertas si CPU/RAM de devices > 90%

### 3. **Integración con Calendario**
- Registrar ventanas de mantenimiento
- No alertar durante mantenimientos programados

### 4. **Machine Learning** (futuro)
- Predecir caídas basado en patrones históricos
- Sugerir root causes en post-mortems

### 5. **SLA Tracking**
- Tracking de SLA por site
- Alertas si se acerca a breach de SLA

### 6. **Webhooks**
- Notificar a sistemas externos vía webhook
- Integración con PagerDuty, Opsgenie, etc.

---

## 📝 Configuración

### Variables de Entorno
```bash
# WhatsApp (API de proveedor)
WHATSAPP_API_URL=https://api.whatsapp.provider.com
WHATSAPP_API_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBERS=+5491123456789,+5491198765432

# Polling
POLLING_INTERVAL_SECONDS=300  # 5 minutos
POLLING_ENABLED=true

# Alertas
ALERT_OUTAGE_THRESHOLD_PERCENT=95
ALERT_WARNING_THRESHOLD_PERCENT=50
ALERT_RETRY_COUNT=3
ALERT_RETRY_DELAY_SECONDS=60

# Métricas
METRICS_RETENTION_DAYS=90
```

---

## 🔜 Próximos Pasos

1. ✅ Modelos creados (PostMortem, AlertNotification)
2. ✅ Crear repositorios para nuevos modelos (AlertNotificationRepository, PostMortemRepository)
3. ✅ Implementar WhatsAppService
4. ✅ Implementar SiteMonitoringPollingService
5. ✅ Implementar PostMortemService
6. ✅ Crear endpoints API (WhatsApp, Post-Mortem, Polling)
7. ✅ Agregar tarea de polling en background (auto-start en startup)
8. ⏳ Testing y documentación (próximo)

## ✅ Implementación Completada

### Componentes Implementados:

**Repositorios:**
- `AlertNotificationRepository` - Tracking de notificaciones enviadas
- `PostMortemRepository` - Gestión de post-mortems

**Servicios:**
- `WhatsAppService` - Envío de alertas por WhatsApp
- `PostMortemService` - CRUD y análisis de incidentes
- `SiteMonitoringPollingService` - Polling automático cada 5 minutos

**Endpoints API:**
- `/api/v1/alerting/scan-sites-with-alerts` - Scan con WhatsApp
- `/api/v1/alerting/test-notification` - Test de notificaciones
- `/api/v1/alerting/post-mortems/*` - CRUD de post-mortems (8 endpoints)
- `/api/v1/alerting/polling/*` - Control de polling (start, stop, status)

**Funcionalidades:**
- Auto-start de polling si `POLLING_ENABLED=true`
- Validación de UISP antes de alertar
- Mensajes completos y resumidos
- Post-mortem con métricas (MTTR, downtime, etc.)
- Tracking completo de notificaciones

## 📝 Próximo: Testing y Documentación

Para probar el sistema completo, sigue las instrucciones en `WHATSAPP_CONFIG.md`.
