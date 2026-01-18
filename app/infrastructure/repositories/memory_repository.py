from typing import List, Optional, Dict
from app.domain.entities.device import Device, DiagnosticResult
from app.domain.repositories.device_repository import DeviceRepository, DiagnosticRepository
import uuid

class MemoryDeviceRepository(DeviceRepository):
    def __init__(self):
        self.devices: Dict[str, Device] = {}

    async def get_device(self, device_id: str) -> Optional[Device]:
        return self.devices.get(device_id)
    
    async def get_devices(self, skip: int = 0, limit: int = 100) -> List[Device]:
        devices_list = list(self.devices.values())
        return devices_list[skip:skip + limit]
    
    async def save_device(self, device: Device) -> Device:
        self.devices[device.id] = device
        return device

class MemoryDiagnosticRepository(DiagnosticRepository):
    def __init__(self):
        self.diagnostics: Dict[str, DiagnosticResult] = {}
        self.device_diagnostics: Dict[str, List[str]] = {}

    async def save_diagnostic_result(self, result: DiagnosticResult) -> DiagnosticResult:
        diagnostic_id = str(uuid.uuid4())
        self.diagnostics[diagnostic_id] = result
        
        if result.device_id not in self.device_diagnostics:
            self.device_diagnostics[result.device_id] = []
        self.device_diagnostics[result.device_id].append(diagnostic_id)
        
        return result
    
    async def get_diagnostic_history(self, device_id: str, limit: int = 10) -> List[DiagnosticResult]:
        diagnostic_ids = self.device_diagnostics.get(device_id, [])
        diagnostics = [self.diagnostics[did] for did in diagnostic_ids if did in self.diagnostics]
        diagnostics.sort(key=lambda x: x.timestamp, reverse=True)
        return diagnostics[:limit]
    
    async def get_diagnostic_by_id(self, diagnostic_id: str) -> Optional[DiagnosticResult]:
        return self.diagnostics.get(diagnostic_id)
