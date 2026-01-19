from fastapi import APIRouter
from app.interfaces.api.v1.endpoints import diagnostics, devices, ap_optimization, device_analysis_complete, logs, device_overview, ap_clients, debug_ssh

api_router = APIRouter()
api_router.include_router(device_analysis_complete.router, tags=["Device Analysis Complete"])
api_router.include_router(diagnostics.router, tags=["Diagnostics"])
api_router.include_router(devices.router, tags=["Devices"])
api_router.include_router(ap_optimization.router, tags=["AP Optimization"])
api_router.include_router(logs.router, tags=["Logs"])
api_router.include_router(device_overview.router, tags=["Device Overview"])
api_router.include_router(ap_clients.router, tags=["AP Clients"])
api_router.include_router(debug_ssh.router, tags=["Debug SSH"])
