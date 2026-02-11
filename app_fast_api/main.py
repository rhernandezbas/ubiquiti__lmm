# Cargar variables de entorno desde .env ANTES de cualquier importación
import os
from dotenv import load_dotenv
load_dotenv()

import uvicorn
from app_fast_api import create_app
from app_fast_api.utils.database import init_db, engine, Base
import logging

# Debug: Verificar si DATABASE_URL se cargó
database_url = os.getenv("DATABASE_URL")
print(f"🔍 DATABASE_URL cargada: {database_url}")

logger = logging.getLogger(__name__)

# Ejecutar migraciones de Alembic automáticamente
def run_alembic_migrations():
    """Ejecutar migraciones de Alembic automáticamente al iniciar"""
    logger.info("🔧 Ejecutando migraciones de Alembic...")

    try:
        from alembic.config import Config
        from alembic import command
        from pathlib import Path

        # Get project root (parent of app_fast_api)
        project_root = Path(__file__).parent.parent
        alembic_ini = project_root / "alembic.ini"

        if not alembic_ini.exists():
            logger.warning(f"⚠️ alembic.ini not found at {alembic_ini}, skipping migrations")
            return False

        # Configure Alembic
        alembic_cfg = Config(str(alembic_ini))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        # Run migrations to head (latest)
        logger.info("📝 Applying pending migrations...")
        command.upgrade(alembic_cfg, "head")

        logger.info("✅ Migraciones de Alembic completadas exitosamente")
        return True

    except Exception as e:
        logger.error(f"❌ Error ejecutando migraciones de Alembic: {str(e)}")
        logger.warning("La aplicación continuará, pero la base de datos puede estar desactualizada")
        import traceback
        traceback.print_exc()
        return False

app = create_app()

if __name__ == "__main__":
    # Ejecutar migraciones de Alembic automáticamente
    logger.info("🚀 Iniciando aplicación...")
    run_alembic_migrations()

    # Luego iniciar el servidor
    logger.info("🌐 Iniciando servidor FastAPI...")
    uvicorn.run(
        "app_fast_api.main:app",
        host="0.0.0.0",
        port=7657,
        reload=True,
        log_level="info"
    )
