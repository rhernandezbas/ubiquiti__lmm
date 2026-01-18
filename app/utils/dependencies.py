from functools import lru_cache
from app.config.settings import settings
from app.infrastructure.api.uisp_client import UISPClient
from app.infrastructure.llm.llm_service import LLMService
from app.infrastructure.repositories.memory_repository import (
    MemoryDeviceRepository,
    MemoryDiagnosticRepository
)

@lru_cache()
def get_uisp_client() -> UISPClient:
    return UISPClient(
        base_url=settings.UISP_BASE_URL,
        token=settings.UISP_TOKEN
    )

@lru_cache()
def get_llm_service() -> LLMService:
    return LLMService(
        api_key=settings.OPENAI_API_KEY,
        model=settings.LLM_MODEL
    )

@lru_cache()
def get_device_repository() -> MemoryDeviceRepository:
    return MemoryDeviceRepository()

@lru_cache()
def get_diagnostic_repository() -> MemoryDiagnosticRepository:
    return MemoryDiagnosticRepository()

def get_diagnostic_service():
    from app.application.services.diagnostic_service import DiagnosticService
    return DiagnosticService(
        device_repo=get_device_repository(),
        diagnostic_repo=get_diagnostic_repository(),
        uisp_client=get_uisp_client(),
        llm_service=get_llm_service()
    )
