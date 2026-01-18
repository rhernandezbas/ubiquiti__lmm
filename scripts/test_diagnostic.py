import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.api.uisp_client import UISPClient
from app.infrastructure.llm.llm_service import LLMService
from app.infrastructure.repositories.memory_repository import (
    MemoryDeviceRepository,
    MemoryDiagnosticRepository
)
from app.application.services.diagnostic_service import DiagnosticService
from app.config.settings import settings
import json

async def test_diagnostic():
    print("🔧 Iniciando test de diagnóstico...")
    
    uisp_client = UISPClient(
        base_url=settings.UISP_BASE_URL,
        token=settings.UISP_TOKEN
    )
    
    llm_service = LLMService(
        api_key=settings.OPENAI_API_KEY,
        model=settings.LLM_MODEL
    )
    
    device_repo = MemoryDeviceRepository()
    diagnostic_repo = MemoryDiagnosticRepository()
    
    diagnostic_service = DiagnosticService(
        device_repo=device_repo,
        diagnostic_repo=diagnostic_repo,
        uisp_client=uisp_client,
        llm_service=llm_service
    )
    
    try:
        print("\n📡 Obteniendo dispositivos...")
        devices = await diagnostic_service.get_all_devices()
        print(f"✅ Encontrados {len(devices)} dispositivos")
        
        if devices:
            device = devices[0]
            print(f"\n🔍 Diagnosticando dispositivo: {device.name} ({device.id})")
            
            result = await diagnostic_service.diagnose_device(device.id)
            
            print("\n" + "="*60)
            print("📊 RESULTADO DEL DIAGNÓSTICO")
            print("="*60)
            print(f"Device ID: {result.device_id}")
            print(f"Status: {result.status.value}")
            print(f"Confidence: {result.confidence:.2%}")
            print(f"Timestamp: {result.timestamp}")
            
            print(f"\n🔴 Issues encontrados ({len(result.issues)}):")
            for i, issue in enumerate(result.issues, 1):
                print(f"  {i}. {issue}")
            
            print(f"\n💡 Recomendaciones ({len(result.recommendations)}):")
            for i, rec in enumerate(result.recommendations, 1):
                print(f"  {i}. {rec}")
            
            if result.patterns_matched:
                print(f"\n🎯 Patrones detectados ({len(result.patterns_matched)}):")
                for pattern in result.patterns_matched:
                    print(f"  - {pattern}")
            
            print("\n" + "="*60)
            
        else:
            print("⚠️  No se encontraron dispositivos")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await uisp_client.close()

if __name__ == "__main__":
    asyncio.run(test_diagnostic())
