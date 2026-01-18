from fastapi import APIRouter
from app.interfaces.api.v1.endpoints import diagnostics, devices, ap_optimization, device_analysis_complete

api_router = APIRouter()
api_router.include_router(device_analysis_complete.router, tags=["Device Analysis Complete"])
api_router.include_router(diagnostics.router, tags=["Diagnostics"])
api_router.include_router(devices.router, tags=["Devices"])
api_router.include_router(ap_optimization.router, tags=["AP Optimization"])
