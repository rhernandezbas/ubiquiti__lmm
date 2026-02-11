# Alembic - Sistema de Migraciones Automáticas

## ✅ Configuración Completada

Alembic está configurado y funcionando en modo **automático**. Las migraciones se ejecutan automáticamente al:
- Iniciar la aplicación FastAPI
- Push a production (si configurado en CI/CD)

## 📁 Estructura de Archivos

```
ubiquiti_llm/
├── alembic/                    # Directorio de Alembic
│   ├── versions/              # Migraciones (auto-generadas)
│   │   └── d2f224889c86_add_recovery_notified_to_alert_events.py
│   ├── env.py                 # Configuración de entorno (modificado)
│   └── script.py.mako         # Template para nuevas migraciones
├── alembic.ini                # Configuración de Alembic
├── run_migrations.py          # Script manual para migraciones
├── app_fast_api/
│   └── main.py                # ✅ Auto-run migrations on startup
└── pyproject.toml             # ✅ Alembic added as dependency
```

## 🚀 Migraciones Automáticas

### En Desarrollo (Local)
Cuando ejecutas la aplicación:
```bash
cd /Users/rhernandezba/PycharmProjects/ubiquiti_llm
export DATABASE_URL="mysql+pymysql://root:pass@host:port/db"
python app_fast_api/main.py
```

**Salida esperada:**
```
🚀 Iniciando aplicación...
🔧 Ejecutando migraciones de Alembic...
📝 Applying pending migrations...
✅ Migraciones de Alembic completadas exitosamente
🌐 Iniciando servidor FastAPI...
```

### En Producción (VPS)
Las migraciones se ejecutan automáticamente cuando el contenedor Docker inicia:
1. GitHub Actions hace push al VPS
2. Docker Compose reinicia el contenedor
3. `main.py` ejecuta migraciones automáticamente
4. Aplicación inicia con BD actualizada

## 🔧 Uso Manual

### Ver estado actual
```bash
cd /Users/rhernandezba/PycharmProjects/ubiquiti_llm
export DATABASE_URL="mysql+pymysql://root:pass@host:port/db"
python run_migrations.py status
```

### Ejecutar migraciones manualmente
```bash
export DATABASE_URL="mysql+pymysql://root:pass@host:port/db"
python run_migrations.py
```

### Comandos Alembic directos
```bash
# Ver historial
alembic history

# Ver estado actual
alembic current

# Aplicar todas las migraciones
alembic upgrade head

# Rollback una migración
alembic downgrade -1

# Rollback todas
alembic downgrade base
```

## 📝 Crear Nueva Migración

### Método 1: Auto-generación (Recomendado)
```bash
cd /Users/rhernandezba/PycharmProjects/ubiquiti_llm
export DATABASE_URL="mysql+pymysql://root:pass@host:port/db"

# Modifica los modelos en app_fast_api/models/
# Luego genera la migración automáticamente:
alembic revision --autogenerate -m "descripcion_del_cambio"
```

Alembic detecta automáticamente:
- ✅ Nuevas columnas
- ✅ Columnas eliminadas
- ✅ Cambios de tipo
- ✅ Nuevas tablas
- ✅ Índices
- ⚠️ Renombres (requieren revisión manual)

### Método 2: Manual
```bash
# Crear migración vacía
alembic revision -m "mi_migracion"

# Editar el archivo generado en alembic/versions/
# Agregar código en upgrade() y downgrade()
```

## 🔍 Verificar Migración Aplicada

### En MySQL
```sql
-- Ver tabla de versiones de Alembic
SELECT * FROM alembic_version;

-- Verificar que la columna existe
DESCRIBE alert_events;

-- Ver eventos pendientes de notificación
SELECT COUNT(*)
FROM alert_events
WHERE status = 'resolved'
  AND auto_resolved = TRUE
  AND recovery_notified = FALSE;
```

### En Python
```python
from sqlalchemy import inspect
from app_fast_api.utils.database import engine

inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('alert_events')]
print('recovery_notified' in columns)  # Should be True
```

## 🛠️ Troubleshooting

### Error: "alembic_version table doesn't exist"
```bash
# Crear tabla de versiones
alembic stamp head
```

### Error: "Can't locate revision identifier"
```bash
# Resetear al estado actual
alembic stamp d2f224889c86
```

### Error: "column already exists"
```bash
# Marcar migración como aplicada sin ejecutarla
alembic stamp head
```

### Forzar re-aplicar migración
```bash
# 1. Rollback
alembic downgrade -1

# 2. Re-aplicar
alembic upgrade head
```

## 📊 Migración Actual: recovery_notified

**Archivo:** `alembic/versions/d2f224889c86_add_recovery_notified_to_alert_events.py`

**Cambios:**
- ✅ Agrega columna `recovery_notified` BOOLEAN DEFAULT FALSE
- ✅ Crea índice compuesto para queries rápidas
- ✅ Incluye rollback (downgrade)

**Impacto:**
- Garantiza entrega de notificaciones de recuperación
- Elimina dependencia de ventanas de tiempo (60s)
- Permite queries eficientes para pending notifications

## 🔐 Variables de Entorno

La conexión a BD se configura con:
```bash
export DATABASE_URL="mysql+pymysql://root:password@host:port/database"
```

**Formato:**
- `mysql+pymysql://` - Driver de MySQL con PyMySQL
- `root:password` - Credenciales
- `host:port` - Servidor (ej: `190.7.234.37:3025`)
- `/database` - Nombre de BD (ej: `ipnext`)

## 📦 Deployment

### Docker
El `Dockerfile` debe incluir:
```dockerfile
# Install dependencies
RUN pip install alembic

# Set environment
ENV DATABASE_URL=mysql+pymysql://root:pass@mysql:3306/db

# Run migrations on startup (handled by main.py)
CMD ["python", "app_fast_api/main.py"]
```

### GitHub Actions
Opcional - ejecutar migraciones antes de reiniciar servicio:
```yaml
- name: Run database migrations
  run: |
    ssh user@vps "cd /path/to/project && \
      export DATABASE_URL='...' && \
      python run_migrations.py"
```

## 🎯 Beneficios

✅ **Automático** - No requiere intervención manual
✅ **Versionado** - Historial completo de cambios
✅ **Rollback** - Revertir migraciones fácilmente
✅ **Team-friendly** - Cada desarrollador aplica migraciones localmente
✅ **Safe** - Detecta conflictos automáticamente
✅ **Production-ready** - Zero-downtime deployments

## 📚 Referencias

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://www.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
