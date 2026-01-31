# Sistema de Alerting para Monitoreo de Sites UNMS

## Descripción General

Sistema de alertas orientado a eventos que monitorea sites de UNMS/UISP y genera alertas automáticas cuando detecta problemas de conectividad en los dispositivos.

## Arquitectura

### Componentes

1. **Modelos de Base de Datos** (`models/ubiquiti_monitoring/alerting.py`)
   - `SiteMonitoring`: Almacena información de sites de UNMS
   - `AlertEvent`: Gestiona eventos de alertas
   - Enums: `AlertSeverity`, `AlertStatus`, `EventType`

2. **Repositorios** (`repositories/alerting_repositories.py`)
   - `SiteMonitoringRepository`: CRUD para sites
   - `AlertEventRepository`: CRUD para eventos

3. **Servicios** (`services/alerting_services.py`)
   - `UNMSAlertingService`: Escanea sites y genera alertas automáticas
   - `AlertEventService`: Gestiona eventos manualmente

4. **Rutas API** (`routes/alerting_routes.py`)
   - Endpoints para monitoreo de sites
   - Endpoints para gestión de eventos

## Lógica de Detección de Outages

### Umbrales de Alerta

- **Site Caído (CRITICAL)**: `deviceOutageCount >= 95%` de `deviceCount`
- **Site Degradado (HIGH)**: `deviceOutageCount >= 50%` de `deviceCount`
- **Site Saludable**: `deviceOutageCount < 50%` de `deviceCount`

### Ejemplo

Si un site tiene:
- `deviceCount: 443`
- `deviceOutageCount: 440`
- Porcentaje: `440/443 = 99.3%`
- **Resultado**: Se genera alerta CRITICAL (SITE_OUTAGE)

## API Endpoints

### Monitoreo de Sites

#### 1. Escanear todos los sites
```bash
POST /api/v1/alerting/scan-sites
```

Escanea todos los sites de UNMS y crea alertas automáticamente para los que están caídos.

**Response:**
```json
{
  "success": true,
  "message": "Scan completed: 150 sites checked",
  "summary": {
    "total_sites": 150,
    "sites_down": 3,
    "sites_degraded": 5,
    "sites_healthy": 142,
    "new_events_created": 8,
    "scan_timestamp": "2026-01-30T10:30:00"
  }
}
```

#### 2. Listar todos los sites monitoreados
```bash
GET /api/v1/alerting/sites
```

#### 3. Listar solo sites con problemas
```bash
GET /api/v1/alerting/sites/outages
```

#### 4. Obtener detalles de un site específico
```bash
GET /api/v1/alerting/sites/{site_id}
```

### Gestión de Eventos

#### 1. Crear evento personalizado
```bash
POST /api/v1/alerting/events
Content-Type: application/json

{
  "event_type": "custom",
  "severity": "high",
  "title": "Mantenimiento programado en Nodo Central",
  "description": "Se realizará mantenimiento el día 31/01/2026",
  "custom_data": {
    "scheduled_time": "2026-01-31T02:00:00",
    "duration_hours": 4
  }
}
```

**Tipos de eventos:**
- `site_outage`: Sitio completamente caído
- `site_degraded`: Sitio con servicio degradado
- `site_recovered`: Sitio recuperado
- `device_outage`: Dispositivo específico caído
- `device_recovered`: Dispositivo recuperado
- `custom`: Evento personalizado

**Niveles de severidad:**
- `critical`: Crítico (servicio caído)
- `high`: Alto (degradación significativa)
- `medium`: Medio
- `low`: Bajo
- `info`: Informativo

#### 2. Listar eventos
```bash
# Todos los eventos
GET /api/v1/alerting/events

# Filtrar por estado
GET /api/v1/alerting/events?status=active

# Filtrar por severidad
GET /api/v1/alerting/events?severity=critical

# Filtrar por tipo
GET /api/v1/alerting/events?event_type=site_outage

# Combinar filtros
GET /api/v1/alerting/events?status=active&severity=critical&limit=50
```

#### 3. Listar solo eventos activos
```bash
GET /api/v1/alerting/events/active
```

#### 4. Obtener detalles de un evento
```bash
GET /api/v1/alerting/events/{event_id}
```

#### 5. Reconocer (acknowledge) un evento
```bash
POST /api/v1/alerting/events/{event_id}/acknowledge
Content-Type: application/json

{
  "acknowledged_by": "Juan Pérez",
  "note": "Equipo técnico ya está trabajando en el problema"
}
```

#### 6. Resolver un evento
```bash
POST /api/v1/alerting/events/{event_id}/resolve
Content-Type: application/json

{
  "resolved_by": "María González",
  "note": "Problema resuelto. Se reemplazó cable de fibra dañado"
}
```

#### 7. Eliminar un evento
```bash
DELETE /api/v1/alerting/events/{event_id}
```

## Ciclo de Vida de un Evento

```
┌─────────────┐
│   ACTIVE    │ ← Evento recién creado
└─────┬───────┘
      │
      ├──────────────────────┐
      │                      │
      ▼                      ▼
┌─────────────┐      ┌──────────────┐
│ACKNOWLEDGED │      │   RESOLVED   │
└─────┬───────┘      └──────────────┘
      │
      ▼
┌─────────────┐
│  RESOLVED   │
└─────────────┘
```

### Estados:
- **ACTIVE**: Evento activo que requiere atención
- **ACKNOWLEDGED**: Alguien está trabajando en el problema
- **RESOLVED**: Problema resuelto
- **IGNORED**: Evento ignorado (no relevante)

## Auto-resolución de Eventos

El sistema automáticamente resuelve eventos cuando:
1. Un site que estaba caído vuelve a la normalidad
2. El porcentaje de outage baja por debajo del 50%

**Ejemplo:**
```
Site "Nodo Estudiantes"
- Antes: 440/443 devices caídos (99.3%) → CRITICAL
- Después de reparación: 5/443 devices caídos (1.1%) → AUTO-RESOLVE
```

## Configuración

### Variables de Entorno

Ya están configuradas en el `.env` existente:
```bash
UISP_BASE_URL=https://190.7.234.36/
UISP_TOKEN=cb53a0bc-48e8-480c-aa47-19e1042e4897
```

### Umbral de Outage

Por defecto: **95%**

Para cambiar el umbral, modificar en `routes/alerting_routes.py`:
```python
unms_service = UNMSAlertingService(
    base_url=UISP_BASE_URL,
    token=UISP_TOKEN,
    site_repo=site_repo,
    event_repo=event_repo,
    outage_threshold=90.0  # Cambiar aquí (por ejemplo, 90%)
)
```

## Migraciones de Base de Datos

Las nuevas tablas se crearán automáticamente al iniciar la aplicación:
- `site_monitoring`
- `alert_events`

## Uso Recomendado

### 1. Monitoreo Automático (Cron Job)

Crear un cron job que ejecute el escaneo periódicamente:

```bash
# Cada 5 minutos
*/5 * * * * curl -X POST http://localhost:7657/api/v1/alerting/scan-sites
```

### 2. Dashboard de Monitoreo

```bash
# Ver sites con problemas
curl http://localhost:7657/api/v1/alerting/sites/outages

# Ver eventos activos
curl http://localhost:7657/api/v1/alerting/events/active
```

### 3. Workflow de Respuesta a Incidentes

1. **Detección**: Sistema escanea y crea evento automáticamente
2. **Notificación**: Se consultan eventos activos vía API
3. **Acknowledgment**: Técnico reconoce el evento
4. **Resolución**: Técnico resuelve el problema y marca evento como resuelto
5. **Verificación**: Siguiente escaneo verifica que el problema está resuelto

## Ejemplos de Uso con curl

### Escanear sites y ver resultados
```bash
curl -X POST http://localhost:7657/api/v1/alerting/scan-sites
```

### Ver todos los eventos críticos activos
```bash
curl "http://localhost:7657/api/v1/alerting/events?status=active&severity=critical"
```

### Reconocer un evento
```bash
curl -X POST http://localhost:7657/api/v1/alerting/events/1/acknowledge \
  -H "Content-Type: application/json" \
  -d '{
    "acknowledged_by": "NOC Team",
    "note": "Técnico en camino al nodo"
  }'
```

### Resolver un evento
```bash
curl -X POST http://localhost:7657/api/v1/alerting/events/1/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "resolved_by": "Técnico Juan",
    "note": "Cable de fibra reemplazado, servicio restaurado"
  }'
```

## Swagger UI

Todos los endpoints están documentados en:
```
http://localhost:7657/docs
```

Buscar la sección **"alerting"** para ver todos los endpoints disponibles.

## Próximas Mejoras

- [ ] Integración con notificaciones (email, SMS, Slack)
- [ ] Webhooks para eventos
- [ ] Dashboard web
- [ ] Métricas históricas
- [ ] Exportación de reportes
