from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.device import Device, DiagnosticResult

class DeviceRepository(ABC):
    @abstractmethod
    async def get_device(self, device_id: str) -> Optional[Device]:
        pass
    
    @abstractmethod
    async def get_devices(self, skip: int = 0, limit: int = 100) -> List[Device]:
        pass
    
    @abstractmethod
    async def save_device(self, device: Device) -> Device:
        pass

class DiagnosticRepository(ABC):
    @abstractmethod
    async def save_diagnostic_result(self, result: DiagnosticResult) -> DiagnosticResult:
        pass
    
    @abstractmethod
    async def get_diagnostic_history(self, device_id: str, limit: int = 10) -> List[DiagnosticResult]:
        pass
    
    @abstractmethod
    async def get_diagnostic_by_id(self, diagnostic_id: str) -> Optional[DiagnosticResult]:
        pass
