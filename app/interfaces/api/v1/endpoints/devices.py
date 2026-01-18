from fastapi import APIRouter, Depends, HTTPException
from typing import List
from pydantic import BaseModel
from datetime import datetime
from app.application.services.diagnostic_service import DiagnosticService
from app.utils.dependencies import get_diagnostic_service

router = APIRouter(prefix="/devices", tags=["devices"])

class DeviceResponse(BaseModel):
    id: str
    name: str
    ip_address: str
    mac_address: str
    model: str
    status: str
    last_seen: datetime
    firmware_version: str = None
    uptime: int = None
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[DeviceResponse])
async def get_all_devices(
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service)
) -> List[DeviceResponse]:
    try:
        devices = await diagnostic_service.get_all_devices()
        return [
            DeviceResponse(
                id=d.id,
                name=d.name,
                ip_address=d.ip_address,
                mac_address=d.mac_address,
                model=d.model,
                status=d.status.value,
                last_seen=d.last_seen,
                firmware_version=d.firmware_version,
                uptime=d.uptime
            )
            for d in devices
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service)
) -> DeviceResponse:
    try:
        device = await diagnostic_service.device_repo.get_device(device_id)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        return DeviceResponse(
            id=device.id,
            name=device.name,
            ip_address=device.ip_address,
            mac_address=device.mac_address,
            model=device.model,
            status=device.status.value,
            last_seen=device.last_seen,
            firmware_version=device.firmware_version,
            uptime=device.uptime
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
