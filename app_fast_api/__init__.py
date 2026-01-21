from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app_fast_api.routes.ssh_test import router as ssh_test_router
from app_fast_api.routes.analyze_station_routes import router as analyze_station_router
from app_fast_api.routes.feedback_routes import router as feedback_router
from app_fast_api.routes.logs_routes import router as logs_router
import logging

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Ubiquiti LLM Service",
        description="FastAPI application for Ubiquiti device analysis and LLM integration",
        version="1.0.0",
        debug=True
    )
    
    # Configurar timeouts para operaciones largas
    from fastapi import Request
    @app.middleware("http")
    async def add_timeout_header(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Process-Time"] = "long-operation-enabled"
        return response
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Incluir rutas de SSH test
    app.include_router(ssh_test_router)
    
    # Incluir rutas de análisis de estaciones
    app.include_router(analyze_station_router)
    
    # Incluir rutas de feedback
    app.include_router(feedback_router)
    
    # Incluir rutas de logs
    app.include_router(logs_router)
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting Ubiquiti LLM Service")
        
        # Inicializar base de datos
        try:
            from app_fast_api.utils.database import init_db
            init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            # No fallar la aplicación si la BD no está disponible
            logger.warning("Application will continue without database functionality")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down Ubiquiti LLM Service")
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "Ubiquiti LLM Service"}
    
    @app.get("/")
    async def root():
        return {"message": "Ubiquiti LLM Service API", "version": "1.0.0"}
    
    return app
    