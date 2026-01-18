from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.logging_config import configure_logging
from app.config.settings import settings
from app.interfaces.api.v1.api import api_router
import logging

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    configure_logging()
    
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="1.0.0"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(api_router, prefix="/api/v1")
    
    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info(f"Shutting down {settings.APP_NAME}")
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": settings.APP_NAME}
    
    return app
