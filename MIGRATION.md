# Guía de Migración de Base de Datos

## Resumen

El sistema de alerting requiere dos nuevas tablas en la base de datos:
- `site_monitoring` - Almacena información de sites de UNMS
- `alert_events` - Gestiona eventos de alertas

## ✅ Opción 1: Migración Automática (Recomendada)

La migración es **automática** cuando inicias la aplicación. Las tablas se crean automáticamente si no existen.

### Paso 1: Asegúrate de tener el archivo .env configurado

```bash
# Verifica que exista el archivo .env con:
DATABASE_URL=mysql+pymysql://ipnext:1234@190.7.234.37:4456/ipnext
```

### Paso 2: Inicia la aplicación

```bash
# Opción A: Local
python app_fast_api/main.py

# Opción B: Docker
docker compose up --build
```

### Paso 3: Verifica los logs

Busca en los logs algo como:

```
✅ Tablas de base de datos creadas exitosamente
Tablas disponibles:
   - device_analysis
   - scan_results
   - frequency_changes
   - feedback
   - site_monitoring (NEW)
   - alert_events (NEW)
```

## 🔧 Opción 2: Migración Manual

Si prefieres ejecutar la migración manualmente:

```bash
# Ejecutar el script de migración
python migrate_db.py
```

El script te mostrará:
1. Tablas existentes
2. Te pedirá confirmación
3. Creará las nuevas tablas
4. Mostrará las tablas después de la migración

### Ejemplo de salida:

```
============================================================
  MIGRACIÓN DE BASE DE DATOS - Sistema de Alerting
============================================================

📊 Base de datos: mysql+pymysql://ipnext:***@190.7.234.37:4456/ipnext

🔍 Verificando tablas existentes...
   Tablas encontradas: 4
   ✓ device_analysis
   ✓ scan_results
   ✓ frequency_changes
   ✓ feedback

¿Deseas continuar con la migración? [s/N]: s

🚀 Ejecutando migración...

✅ Tablas de base de datos creadas exitosamente

============================================================
✅ MIGRACIÓN COMPLETADA EXITOSAMENTE
============================================================

📋 Tablas después de la migración:
   ✓ alert_events
   ✓ device_analysis
   ✓ feedback
   ✓ frequency_changes
   ✓ scan_results
   ✓ site_monitoring
```

## 🔍 Opción 3: Verificación Manual en MySQL

Si quieres verificar manualmente que las tablas existen:

```bash
# Conectar a MySQL
mysql -h 190.7.234.37 -P 4456 -u ipnext -p ipnext

# Dentro de MySQL
SHOW TABLES;

# Ver estructura de las nuevas tablas
DESCRIBE site_monitoring;
DESCRIBE alert_events;
```

## 📊 Estructura de las Nuevas Tablas

### Tabla: site_monitoring

```sql
CREATE TABLE site_monitoring (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    site_id VARCHAR(100) UNIQUE NOT NULL,
    site_name VARCHAR(200) NOT NULL,
    site_status VARCHAR(50),
    site_type VARCHAR(50),
    address VARCHAR(500),
    latitude FLOAT,
    longitude FLOAT,
    height FLOAT,
    contact_name VARCHAR(200),
    contact_phone VARCHAR(50),
    contact_email VARCHAR(200),
    device_count INT DEFAULT 0,
    device_outage_count INT DEFAULT 0,
    device_list_status VARCHAR(50),
    outage_percentage FLOAT DEFAULT 0.0,
    is_site_down BOOLEAN DEFAULT FALSE,
    note TEXT,
    ip_addresses TEXT,
    regulatory_domain VARCHAR(10),
    suspended BOOLEAN DEFAULT FALSE,
    last_checked DATETIME NOT NULL,
    last_updated DATETIME,
    created_at DATETIME NOT NULL,
    INDEX idx_site_id (site_id)
);
```

### Tabla: alert_events

```sql
CREATE TABLE alert_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    event_type ENUM('site_outage', 'site_degraded', 'site_recovered',
                    'device_outage', 'device_recovered', 'custom') NOT NULL,
    severity ENUM('critical', 'high', 'medium', 'low', 'info') NOT NULL,
    status ENUM('active', 'resolved', 'acknowledged', 'ignored') NOT NULL DEFAULT 'active',
    title VARCHAR(500) NOT NULL,
    description TEXT,
    site_id BIGINT,
    device_count INT,
    outage_count INT,
    outage_percentage FLOAT,
    affected_devices TEXT,
    custom_data TEXT,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_sent_at DATETIME,
    notification_recipients TEXT,
    acknowledged_by VARCHAR(200),
    acknowledged_at DATETIME,
    acknowledged_note TEXT,
    resolved_at DATETIME,
    resolved_by VARCHAR(200),
    resolved_note TEXT,
    auto_resolved BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    INDEX idx_event_type (event_type),
    INDEX idx_status (status),
    INDEX idx_site_id (site_id),
    FOREIGN KEY (site_id) REFERENCES site_monitoring(id) ON DELETE CASCADE
);
```

## ⚠️ Troubleshooting

### Error: "DATABASE_URL no está configurada"

Solución:
```bash
# Verifica que el archivo .env existe y contiene:
cat .env | grep DATABASE_URL

# Si no existe, créalo:
echo "DATABASE_URL=mysql+pymysql://ipnext:1234@190.7.234.37:4456/ipnext" >> .env
```

### Error: "Access denied for user"

Solución:
- Verifica que el usuario y contraseña en DATABASE_URL sean correctos
- Verifica que el usuario tenga permisos CREATE TABLE

```sql
-- En MySQL, verifica permisos:
SHOW GRANTS FOR 'ipnext'@'%';

-- Si necesitas dar permisos:
GRANT CREATE ON ipnext.* TO 'ipnext'@'%';
FLUSH PRIVILEGES;
```

### Error: "Can't connect to MySQL server"

Solución:
- Verifica que MySQL esté corriendo
- Verifica que el host y puerto sean correctos
- Verifica que el firewall permita la conexión

```bash
# Prueba la conexión manualmente:
mysql -h 190.7.234.37 -P 4456 -u ipnext -p
```

### Las tablas no se crean

Solución:
1. Ejecuta el script de migración manual: `python migrate_db.py`
2. Verifica los logs de la aplicación
3. Verifica que los modelos estén importados en `utils/database.py`

## 🚀 Después de la Migración

Una vez completada la migración, puedes usar el sistema de alerting:

```bash
# Probar el sistema
curl -X POST http://localhost:7657/api/v1/alerting/scan-sites

# Ver documentación
http://localhost:7657/docs
```

## 📝 Rollback (Eliminar Tablas)

Si necesitas eliminar las tablas nuevas:

```sql
-- Conectar a MySQL
mysql -h 190.7.234.37 -P 4456 -u ipnext -p ipnext

-- Eliminar tablas (en orden por dependencias)
DROP TABLE IF EXISTS alert_events;
DROP TABLE IF EXISTS site_monitoring;
```

## 📚 Referencias

- Documentación completa: `ALERTING_SYSTEM.md`
- Modelos de datos: `app_fast_api/models/ubiquiti_monitoring/alerting.py`
- Script de migración: `migrate_db.py`
