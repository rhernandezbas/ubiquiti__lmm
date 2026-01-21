import uvicorn
from app_fast_api import create_app
from app_fast_api.utils.database import init_db, engine, Base
from app_fast_api.models.ubiquiti_monitoring.device_analysis import DeviceAnalysis
from app_fast_api.models.ubiquiti_monitoring.feedback import Feedback
import logging

logger = logging.getLogger(__name__)

# Ejecutar migración de base de datos antes de iniciar el servidor
def run_migration():
    """Ejecutar migración de base de datos"""
    logger.info("Verificando si necesita migración de base de datos...")
    
    try:
        
        # Verificar si las tablas ya existen
        with engine.connect() as conn:
            result = conn.execute("SHOW TABLES LIKE 'device_analysis'").fetchall()
            if result:
                logger.info("Las tablas ya existen, omitiendo migración")
                return True
            else:
                logger.info("Tablas no encontradas, ejecutando migración...")
        
        # Ejecutar migración
        init_db()
        logger.info("Migración completada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"Error en migración: {str(e)}")
        logger.warning("La aplicación continuará sin funcionalidad de base de datos")
        return False

app = create_app()

if __name__ == "__main__":
    # Primero ejecutar la migración
    #migration_success = run_migration()
    
    # Luego iniciar el servidor
    logger.info("Iniciando servidor FastAPI...")
    uvicorn.run(
        "app_fast_api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
