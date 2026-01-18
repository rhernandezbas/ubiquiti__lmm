import logging
import sys
from logging.config import dictConfig
from pathlib import Path
from app.config.settings import settings

def configure_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_level = settings.LOG_LEVEL if hasattr(settings, 'LOG_LEVEL') else "INFO"
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "level": "DEBUG" if settings.DEBUG else log_level,
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
            },
            "file": {
                "level": log_level,
                "formatter": "detailed",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_dir / "app.log",
                "maxBytes": 10485760,
                "backupCount": 5,
                "encoding": "utf8",
            },
            "error_file": {
                "level": "ERROR",
                "formatter": "detailed",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_dir / "error.log",
                "maxBytes": 10485760,
                "backupCount": 5,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "app": {
                "handlers": ["console", "file", "error_file"],
                "level": "DEBUG" if settings.DEBUG else log_level,
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console", "file", "error_file"],
            "level": "WARNING",
        },
    }
    
    dictConfig(log_config)
    logging.info(f"Logging configured with level: {log_level}")
