"""Database configuration for Ubiquiti FastAPI application."""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://ipnext:1234@190.7.234.37:4456/ipnext")
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ubiquiti_monitoring.db")

# Create engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    logger.info("Inicializando base de datos...")
    logger.info(f"Conectando a: {DATABASE_URL}")
    
    try:
        # Import all models here to ensure they are registered
        from app_fast_api.models.ubiquiti_monitoring.device_analysis import DeviceAnalysis, ScanResult, FrequencyChange
        from app_fast_api.models.ubiquiti_monitoring.feedback import Feedback
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas de base de datos creadas exitosamente")
        logger.info("Tablas disponibles:")
        logger.info("   - device_analysis")
        logger.info("   - scan_results") 
        logger.info("   - frequency_changes")
        logger.info("   - feedback")
        
        if "sqlite" in DATABASE_URL:
            logger.info("Usando SQLite local")
        elif "mysql" in DATABASE_URL:
            logger.info("Usando MySQL")
        
    except Exception as e:
        logger.error(f"Error inicializando base de datos: {str(e)}")
        raise
