import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.domain.entities.device import Device, DiagnosticResult, DiagnosticStatus, DeviceStatus
from app.domain.repositories.device_repository import DeviceRepository, DiagnosticRepository
from app.infrastructure.llm.llm_service import LLMService
from app.infrastructure.api.uisp_client import UISPClient
from app.utils.patterns import DiagnosticPatterns
from app.utils.network_utils import ping_device

logger = logging.getLogger(__name__)

class DiagnosticService:
    def __init__(
        self,
        device_repo: DeviceRepository,
        diagnostic_repo: DiagnosticRepository,
        uisp_client: UISPClient,
        llm_service: LLMService
    ):
        self.device_repo = device_repo
        self.diagnostic_repo = diagnostic_repo
        self.uisp_client = uisp_client
        self.llm_service = llm_service
        self.patterns = DiagnosticPatterns()

    async def diagnose_device(self, device_id: str, use_patterns: bool = True) -> DiagnosticResult:
        try:
            logger.info(f"Starting diagnostic for device {device_id}")
            
            device_data = await self.uisp_client.get_device(device_id)
            statistics = await self.uisp_client.get_device_statistics(device_id)
            interfaces = await self.uisp_client.get_device_interfaces(device_id)
            
            # Ping device to check connectivity
            ip_address = device_data.get("ipAddress")
            ping_result = None
            if ip_address:
                logger.info(f"Pinging device at {ip_address}")
                ping_result = await ping_device(ip_address)
            
            try:
                outages = await self.uisp_client.get_device_outages(device_id)
            except Exception as e:
                logger.warning(f"Could not fetch outages: {str(e)}")
                outages = []
            
            try:
                logs = await self.uisp_client.get_device_logs(device_id, limit=50)
            except Exception as e:
                logger.warning(f"Could not fetch logs: {str(e)}")
                logs = []
            
            device = self._parse_device(device_data)
            await self.device_repo.save_device(device)
            
            if use_patterns:
                pattern_results = self.patterns.check_patterns(
                    device_data, statistics, interfaces, outages
                )
            else:
                pattern_results = {"matched_patterns": [], "issues": [], "recommendations": []}
            
            # LLM analysis eliminado - se hace solo en unified_analysis con análisis completo de APs
            llm_analysis = {
                "issues": [],
                "recommendations": [],
                "confidence": 0.0,
                "severity": "unknown",
                "summary": ""
            }
            
            all_issues = list(set(pattern_results.get("issues", []) + llm_analysis.get("issues", [])))
            all_recommendations = list(set(
                pattern_results.get("recommendations", []) + llm_analysis.get("recommendations", [])
            ))
            
            result = DiagnosticResult(
                device_id=device_id,
                timestamp=datetime.utcnow(),
                status=DiagnosticStatus.COMPLETED,
                issues=all_issues,
                recommendations=all_recommendations,
                confidence=llm_analysis.get("confidence", 0.8),
                patterns_matched=[p["name"] for p in pattern_results.get("matched_patterns", [])],
                raw_data={
                    "device": device_data,
                    "statistics": statistics,
                    "interfaces": interfaces,
                    "outages": outages,
                    "logs": logs[:10],
                    "llm_analysis": llm_analysis,
                    "pattern_analysis": pattern_results
                }
            )
            
            await self.diagnostic_repo.save_diagnostic_result(result)
            logger.info(f"Diagnostic completed for device {device_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error diagnosing device {device_id}: {str(e)}", exc_info=True)
            error_result = DiagnosticResult(
                device_id=device_id,
                timestamp=datetime.utcnow(),
                status=DiagnosticStatus.FAILED,
                issues=[f"Diagnostic failed: {str(e)}"],
                recommendations=["Check device connectivity and UISP API status", "Verify API credentials"],
                confidence=0.0,
                raw_data={"error": str(e)},
                error_message=str(e)
            )
            await self.diagnostic_repo.save_diagnostic_result(error_result)
            raise

    async def get_device_history(self, device_id: str, limit: int = 10) -> List[DiagnosticResult]:
        return await self.diagnostic_repo.get_diagnostic_history(device_id, limit)

    async def get_all_devices(self) -> List[Device]:
        devices_data = await self.uisp_client.get_devices()
        devices = [self._parse_device(d) for d in devices_data]
        for device in devices:
            await self.device_repo.save_device(device)
        return devices

    async def diagnose_device_by_ip(self, ip_address: str, use_patterns: bool = True) -> DiagnosticResult:
        try:
            logger.info(f"Searching for device with IP {ip_address}")
            devices_data = await self.uisp_client.get_devices()
            logger.debug(f"Retrieved {len(devices_data)} devices from UISP")
            
            device_data = None
            for device in devices_data:
                if device.get("ipAddress") == ip_address:
                    device_data = device
                    logger.debug(f"Found matching device: {device}")
                    break
            
            if not device_data:
                logger.warning(f"No device found with IP address {ip_address}")
                logger.debug(f"Available IPs: {[d.get('ipAddress') for d in devices_data[:10]]}")
                raise ValueError(f"No device found with IP address {ip_address}")
            
            # El ID está en identification.id según la estructura de UISP
            device_id = device_data.get("identification", {}).get("id") or device_data.get("id")
            if not device_id:
                logger.error(f"Device found with IP {ip_address} but has no ID. Device data: {device_data}")
                raise ValueError(f"Device with IP {ip_address} has no valid ID")
            
            logger.info(f"Found device {device_id} with IP {ip_address}")
            
            return await self.diagnose_device(device_id, use_patterns=use_patterns)
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error diagnosing device by IP {ip_address}: {str(e)}", exc_info=True)
            raise

    def _map_device_status(self, status: str) -> DeviceStatus:
        """Mapea el status de UISP a un valor válido del enum DeviceStatus"""
        status_lower = status.lower() if status else "unknown"
        
        # Mapeo de estados de UISP a enum
        status_map = {
            "active": DeviceStatus.ACTIVE,
            "online": DeviceStatus.ONLINE,
            "offline": DeviceStatus.OFFLINE,
            "disconnected": DeviceStatus.OFFLINE,
            "unknown": DeviceStatus.OFFLINE,
            "disabled": DeviceStatus.OFFLINE,
        }
        
        return status_map.get(status_lower, DeviceStatus.OFFLINE)
    
    def _parse_device(self, device_data: Dict[str, Any]) -> Device:
        identification = device_data.get("identification", {})
        overview = device_data.get("overview", {})
        
        return Device(
            id=identification.get("id") or device_data.get("id", ""),
            name=identification.get("name") or device_data.get("name", "Unknown"),
            ip_address=device_data.get("ipAddress", ""),
            mac_address=identification.get("mac") or device_data.get("mac", ""),
            model=identification.get("model") or device_data.get("model", "Unknown"),
            status=self._map_device_status(overview.get("status", "unknown")),
            last_seen=datetime.fromisoformat(overview.get("lastSeen", datetime.utcnow().isoformat()).replace("Z", "+00:00")),
            firmware_version=identification.get("firmwareVersion"),
            uptime=overview.get("uptime"),
            metadata=device_data
        )
