import re
from app_fast_api.services.llm_services import LLMService
from app_fast_api.services.uisp_services import UISPService
from app_fast_api.services.ubiquiti_ssh_client import UbiquitiSSHClient
from app_fast_api.utils.logger import get_logger

logger = get_logger(__name__)

class AnalyzeStationsServices:
    """"""
    def __init__(self, llm_service: LLMService,
                 uisp_service: UISPService, ssh_service: UbiquitiSSHClient):
        """"""
        self.llm_service = llm_service
        self.uisp_service = uisp_service
        self.ssh_service = ssh_service


    async def match_device_data(self, ip: str = None, mac: str = None) -> dict:
        """ Identifica el dispositivo por IP o MAC """

        if not ip and not mac:
            return None

        logger.info(f"Buscando dispositivo: IP={ip}, MAC={mac}")
        
        all_data = await self.uisp_service.get_all_uisp_devices()
        
        if not all_data:
            logger.error("No se obtuvieron dispositivos de UISP")
            return None
            
        logger.info(f"Total de dispositivos en UISP: {len(all_data)}")

        for device in all_data:
            device_ip = device.get("ipAddress", "")
            device_mac = device.get("identification", {}).get("mac", "")
            
            if ip and device_ip == ip:
                logger.info(f"Dispositivo encontrado por IP: {ip}")
                return device
            elif mac and device_mac == mac:
                logger.info(f"Dispositivo encontrado por MAC: {mac}")
                return device

        logger.warning(f"Dispositivo NO encontrado: IP={ip}, MAC={mac}")
        return None

    @staticmethod
    async def get_device_data(device_data: dict) -> dict:
        """ Obtiene y procesa la información completa del dispositivo """
        
        if not device_data:
            return {"error": "No se proporcionaron datos del dispositivo"}

        # Información básica del dispositivo
        basic_info = {
            "mac": device_data.get("identification", {}).get("mac", "N/A"),
            "name": device_data.get("identification", {}).get("name", "N/A"),
            "hostname": device_data.get("identification", {}).get("hostname", "N/A"),
            "model": device_data.get("identification", {}).get("model", "N/A"),
            "model_name": device_data.get("identification", {}).get("modelName", "N/A"),
            "role": device_data.get("identification", {}).get("role", "N/A"),
            "ip_address": device_data.get("ipAddress", "N/A"),
            "device_id": device_data.get("identification", {}).get("id", "N/A")
        }
        
        # Información de capacidad y rendimiento
        overview = device_data.get("overview", {})
        capacity_info = {
            "downlink_capacity_mbps": overview.get("downlinkCapacity", 0) / 1000000,  # Convertir a Mbps
            "uplink_capacity_mbps": overview.get("uplinkCapacity", 0) / 1000000,
            "total_capacity_mbps": overview.get("totalCapacity", 0) / 1000000,
            "downlink_utilization_percent": overview.get("downlinkUtilization", 0) * 100,
            "uplink_utilization_percent": overview.get("uplinkUtilization", 0) * 100,
            "theoretical_total_capacity_mbps": overview.get("theoreticalTotalCapacity", 0) / 1000000
        }
        
        # Información de señal y conexión
        signal_info = {
            "signal_dbm": overview.get("signal", "N/A"),
            "signal_max_dbm": overview.get("signalMax", "N/A"),
            "remote_signal_max_dbm": overview.get("remoteSignalMax", "N/A"),
            "frequency_mhz": overview.get("frequency", "N/A"),
            "channel_width_mhz": overview.get("channelWidth", "N/A"),
            "transmit_power_dbm": overview.get("transmitPower", "N/A"),
            "wireless_mode": overview.get("wirelessMode", "N/A")
        }
        
        # Información del sistema
        system_info = {
            "cpu_usage_percent": overview.get("cpu", "N/A"),
            "ram_usage_percent": overview.get("ram", "N/A"),
            "uptime_seconds": overview.get("uptime", "N/A"),
            "uptime_days": overview.get("uptime", 0) / 86400 if overview.get("uptime") else "N/A",  # Convertir a días
            "mode": device_data.get("mode", "N/A")
        }
        
        # Información de calidad del enlace (linkScore)
        link_score = overview.get("linkScore", {})
        link_info = {
            "overall_score": link_score.get("linkScore", "N/A"),
            "uplink_score": link_score.get("uplinkScore", "N/A"),
            "downlink_score": link_score.get("downlinkScore", "N/A"),
            "score": link_score.get("score", "N/A"),
            "max_score": link_score.get("scoreMax", "N/A"),
            "air_time": link_score.get("airTime", "N/A"),
            "link_score_hint": link_score.get("linkScoreHint", "N/A")
        }
        
        # Información de atributos adicionales
        attributes = device_data.get("attributes", {})
        attributes_info = {
            "series": attributes.get("series", "N/A"),
            "ssid": attributes.get("ssid", "N/A"),
            "secondary_ssid": attributes.get("secondarySsid", "N/A"),
            "country": attributes.get("country", "N/A"),
            "country_code": attributes.get("countryCode", "N/A")
        }
        
        # Información del AP conectado
        ap_device = attributes.get("apDevice", {})
        ap_info = {
            "ap_name": ap_device.get("name", "N/A"),
            "ap_model": ap_device.get("model", "N/A"),
            "ap_type": ap_device.get("type", "N/A"),
            "ap_site_id": ap_device.get("siteId", "N/A"),
            "firmware_compatible": ap_device.get("firmware", {}).get("compatible", "N/A")
        }
        
        # Información de interfaz
        main_interface = overview.get("mainInterfaceSpeed", {})
        interface_info = {
            "interface_id": main_interface.get("interfaceId", "N/A"),
            "available_speed": main_interface.get("availableSpeed", "N/A")
        }

        # Identificar el modelo
        model = device_data.get("identification", {}).get("model", "").lower()  # Busca en lugar correcto

        if "ac" in model:
            identified_model = "ac"
        elif "m5" in model:
            identified_model = "m5"
        elif "m2" in model:
            identified_model = "m2"
        else:
            identified_model = "unknown"

        # Combinar toda la información
        processed_data = {
            "basic_info": basic_info,
            "capacity_info": capacity_info,
            "signal_info": signal_info,
            "system_info": system_info,
            "link_info": link_info,
            "attributes_info": attributes_info,
            "ap_info": ap_info,
            "interface_info": interface_info,
            "identified_model": identified_model,
        }
        return processed_data

    async def enabled_frecuency(self, model: str, ip: str):
        """"""
        try:
            if model == "ac":
                await self.ssh_service.enable_all_AC_frequencies(ip,model)
            elif model == "m5":
                await self.ssh_service.enable_all_m5_frequencies(ip,model)
            elif model == "m2":
                pass
            else:
                raise ValueError(f"Modelo no soportado: {model}")

            return {"status": "success", "model": model, "ip": ip}

        except Exception as e:
            return {"status": "error", "error": str(e), "model": model, "ip": ip}

    def match_scanned_aps_with_device(self, scanned_aps: dict, device_data: dict) -> dict:
        """
        Matchea APs escaneados con el dispositivo específico y los separa en nuestros vs extranjeros

        Args:
            scanned_aps: Datos de APs escaneados (resultado de scan_nearby_aps_detailed)
            device_data: Datos del dispositivo UISP

        Returns:
            Dict con:
            - our_aps: Lista de APs nuestros (que hacen match)
            - foreign_aps: Lista de APs extranjeros (que no hacen match)
            - our_aps_count: Cantidad de APs nuestros
            - foreign_aps_count: Cantidad de APs extranjeros
            - matched_aps: Lista de APs con info de match (para compatibilidad)
        """
        if not scanned_aps or not device_data:
            return {
                "our_aps": [],
                "foreign_aps": [],
                "our_aps_count": 0,
                "foreign_aps_count": 0,
                "matched_aps": []
            }

        matched_aps = []
        device_mac = device_data.get("mac", "").lower()
        device_name = device_data.get("name", "").lower()
        device_ip = device_data.get("ipAddress", "").lower()

        # Si scanned_aps tiene formato directo (lista de APs)
        if isinstance(scanned_aps, list):
            aps_list = scanned_aps
        # Si tiene el formato del resultado de scan_nearby_aps_detailed
        elif isinstance(scanned_aps, dict) and "aps" in scanned_aps:
            aps_list = scanned_aps["aps"]
        else:
            return {
                "our_aps": [],
                "foreign_aps": [],
                "our_aps_count": 0,
                "foreign_aps_count": 0,
                "matched_aps": []
            }

        for ap in aps_list:
            ap_bssid = ap.get("bssid", "").lower()
            ap_ssid = ap.get("ssid", "").lower()

            # Match por BSSID/MAC (prioridad alta)
            if ap_bssid == device_mac:
                matched_aps.append({
                    "scanned_ap": ap,
                    "match_type": "bssid_exact",
                    "match_reason": f"BSSID {ap_bssid} coincide con MAC del dispositivo {device_mac}",
                    "confidence": "high"
                })
            # Match por SSID/nombre (prioridad media)
            elif ap_ssid == device_name:
                matched_aps.append({
                    "scanned_ap": ap,
                    "match_type": "ssid_exact",
                    "match_reason": f"SSID '{ap_ssid}' coincide con nombre del dispositivo '{device_name}'",
                    "confidence": "medium"
                })
            # Match parcial SSID/nombre (prioridad baja)
            elif device_name and device_name in ap_ssid:
                matched_aps.append({
                    "scanned_ap": ap,
                    "match_type": "ssid_partial",
                    "match_reason": f"SSID '{ap_ssid}' contiene parcialmente el nombre '{device_name}'",
                    "confidence": "low"
                })
            # Match por patrones conocidos de nuestra red (prioridad media-baja)
            elif self._is_our_ap_by_pattern(ap_ssid, ap_bssid):
                matched_aps.append({
                    "scanned_ap": ap,
                    "match_type": "pattern_match",
                    "match_reason": f"SSID '{ap_ssid}' o BSSID '{ap_bssid}' coincide con patrones de nuestra red",
                    "confidence": "medium"
                })

        # Separar en nuestros y extranjeros
        our_aps_bssid = {match["scanned_ap"]["bssid"] for match in matched_aps}

        our_aps = []
        foreign_aps = []

        for ap in aps_list:
            if ap["bssid"] in our_aps_bssid:
                our_aps.append(ap)
            else:
                foreign_aps.append(ap)

        return {
            "our_aps": our_aps,
            "foreign_aps": foreign_aps,
            "our_aps_count": len(our_aps),
            "foreign_aps_count": len(foreign_aps),
            "matched_aps": matched_aps  # Para compatibilidad
        }

    async def get_current_ap_data(self, device_data: dict) -> dict:
        """
        Obtiene los datos completos del AP actual al que está conectado el dispositivo

        Args:
            device_data: Datos del dispositivo desde UISP

        Returns:
            Dict con información completa del AP actual
        """
        try:
            # Extraer información del AP actual desde device_data
            attributes = device_data.get("attributes", {})
            ap_device = attributes.get("apDevice", {})

            if not ap_device:
                return {
                    "status": "error",
                    "error": "No se encontró información del AP en device_data"
                }

            ap_id = ap_device.get("id")
            ap_name = ap_device.get("name", "N/A")
            ap_model = ap_device.get("model", "N/A")
            ap_type = ap_device.get("type", "N/A")
            site_id = ap_device.get("siteId", "N/A")

            logger.info(f"Buscando AP actual: {ap_name} ({ap_model})")

            # Obtener todos los dispositivos UISP para encontrar el AP completo
            all_uisp_devices = await self.uisp_service.get_all_uisp_devices()

            # Buscar el AP por ID
            ap_complete_data = None
            for device in all_uisp_devices:
                if device.get("identification", {}).get("id") == ap_id:
                    ap_complete_data = device
                    break

            if not ap_complete_data:
                return {
                    "status": "error",
                    "error": f"AP con ID {ap_id} no encontrado en UISP",
                    "basic_info": {
                        "name": ap_name,
                        "model": ap_model,
                        "type": ap_type,
                        "site_id": site_id
                    }
                }

            # Extraer información completa del AP
            overview = ap_complete_data.get("overview", {})

            ap_data = {
                "status": "success",
                "basic_info": {
                    "id": ap_id,
                    "name": ap_name,
                    "model": ap_model,
                    "type": ap_type,
                    "site_id": site_id,
                    "ip": ap_complete_data.get("ipAddress", "N/A"),
                    "mac": ap_complete_data.get("identification", {}).get("mac", "N/A"),
                    "site_name": ap_complete_data.get("identification", {}).get("site", {}).get("name", "N/A")
                },
                "capacity": {
                    "downlink_capacity_mbps": overview.get("downlinkCapacity", 0) / 1000000,
                    "uplink_capacity_mbps": overview.get("uplinkCapacity", 0) / 1000000,
                    "total_capacity_mbps": overview.get("totalCapacity", 0) / 1000000,
                    "downlink_utilization_percent": overview.get("downlinkUtilization", 0) * 100,
                    "uplink_utilization_percent": overview.get("uplinkUtilization", 0) * 100
                },
                "clients": {
                    "total_clients": overview.get("stationsCount", 0),
                    "active_clients": overview.get("activeStationsCount", 0),
                    "average_signal": overview.get("averageSignal", "N/A"),
                    "average_distance": overview.get("averageDistance", "N/A")
                },
                "wireless": {
                    "frequency": overview.get("frequency", "N/A"),
                    "channel_width": overview.get("channelWidth", "N/A"),
                    "transmit_power": overview.get("transmitPower", "N/A"),
                    "noise_floor": overview.get("noiseFloor", "N/A")
                },
                "full_uisp_data": ap_complete_data
            }

            logger.info(f"AP actual encontrado: {ap_name} con {ap_data['clients']['total_clients']} clientes")
            return ap_data

        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def scan_and_match_aps_direct(self, device_data: dict, interface: str = "ath0") -> dict:
        """
        Escanea APs y hace match usando device_data ya obtenido (evita doble consulta a UISP)
        Identifica APs propios por BSSID de UISP y separa los que no son nuestros

        Args:
            device_data: Datos del dispositivo ya obtenidos de UISP
            interface: Interfaz wireless (default: ath0)

        Returns:
            Diccionario con resultados del escaneo y matching
        """
        try:
            # Obtener IP del dispositivo ya obtenido
            ip = device_data.get("ipAddress", "")

            if not ip:
                return {
                    "status": "error",
                    "error": "No se encontró IP en device_data"
                }

            # 1. Escanear APs cercanos usando la función ya establecida
            scan_result = await self.ssh_service.scan_nearby_aps_detailed(
                host=ip,
                interface=interface
            )

            if not scan_result.get("success", False):
                return {
                    "status": "error",
                    "error": "No se pudo escanear APs",
                    "scan_error": scan_result.get("error")
                }

            # 2. Obtener APs escaneados primero para saber qué BSSIDs buscar
            scanned_aps = scan_result.get("aps", [])
            logger.info(f"Total APs escaneados: {len(scanned_aps)}")

            if not scanned_aps:
                logger.warning("No se encontraron APs escaneados")
                return {
                    "status": "success",
                    "device_info": {
                        "ip": ip,
                        "mac": device_data.get("identification", {}).get("mac"),
                        "name": device_data.get("identification", {}).get("name"),
                        "model": device_data.get("identification", {}).get("model")
                    },
                    "scan_results": scan_result,
                    "our_aps": [],
                    "foreign_aps": [],
                    "matched_aps": [],
                    "matched_count": 0,
                    "full_analysis": await self.get_device_data(device_data),
                    "summary": {
                        "total_scanned_aps": 0,
                        "our_aps_count": 0,
                        "foreign_aps_count": 0,
                        "matched_aps": 0,
                        "scan_success": scan_result.get("success", False),
                        "device_found_in_uisp": bool(device_data)
                    }
                }

            # Extraer BSSIDs del escaneo para buscar solo esos en UISP
            scanned_bssids = [ap.get("bssid", "").lower() for ap in scanned_aps]
            logger.info(f"BSSIDs escaneados a buscar en UISP: {scanned_bssids}")

            # Obtener todos los dispositivos UISP pero filtrar por BSSIDs escaneados
            logger.info("Obteniendo dispositivos UISP para BSSIDs escaneados...")
            all_uisp_devices = await self.uisp_service.get_all_uisp_devices()

            uisp_aps_by_bssid = {}

            # Crear mapa de BSSID -> info AP solo para BSSIDs escaneados
            logger.info("Identificando APs UISP que coinciden con escaneo...")
            ap_count = 0
            for device in all_uisp_devices:
                if device.get("identification", {}).get("role") == "ap":
                    mac = device.get("identification", {}).get("mac", "").lower()
                    if mac and mac in scanned_bssids:
                        ap_count += 1
                        uisp_aps_by_bssid[mac] = {
                            "name": device.get("identification", {}).get("name", "N/A"),
                            "model": device.get("identification", {}).get("model", "N/A"),
                            "ip": device.get("ipAddress", "N/A"),
                            "site": device.get("identification", {}).get("site", {}).get("name", "N/A"),
                            "stations_count": device.get("overview", {}).get("stationsCount", 0),
                            "signal": device.get("overview", {}).get("signal", "N/A"),
                            "frequency": device.get("overview", {}).get("frequency", "N/A")
                        }
                        logger.info(f"AP propio encontrado en escaneo: {uisp_aps_by_bssid[mac]['name']} ({mac})")

            logger.info(f"Total APs UISP mapeados del escaneo: {ap_count}")

            # 3. Procesar APs escaneados y clasificar
            our_aps = []
            foreign_aps = []

            for i, ap in enumerate(scanned_aps):
                bssid = ap.get("bssid", "").lower()
                logger.debug(f"Analizando AP #{i+1}: {bssid} - {ap.get('ssid', 'N/A')}")

                ap_info = {
                    "bssid": ap.get("bssid"),
                    "ssid": ap.get("ssid"),
                    "signal_dbm": ap.get("signal_dbm"),
                    "channel": ap.get("channel"),
                    "frequency_mhz": ap.get("frequency_mhz"),
                    "quality": ap.get("quality"),
                    "encrypted": ap.get("encrypted")
                }

                if bssid in uisp_aps_by_bssid:
                    # Es nuestro AP - agregar info de UISP
                    uisp_ap = uisp_aps_by_bssid[bssid]
                    ap_info.update({
                        "is_our_ap": True,
                        "ap_name": uisp_ap["name"],
                        "ap_model": uisp_ap["model"],
                        "ap_ip": uisp_ap["ip"],
                        "ap_site": uisp_ap["site"],
                        "current_clients": uisp_ap["stations_count"],
                        "ap_signal": uisp_ap["signal"],
                        "ap_frequency": uisp_ap["frequency"]
                    })
                    our_aps.append(ap_info)
                    logger.info(f"AP propio identificado: {uisp_ap['name']} (clientes: {uisp_ap['stations_count']})")
                else:
                    # Es AP ajeno
                    ap_info.update({
                        "is_our_ap": False,
                        "ap_name": "AP Externo",
                        "current_clients": "N/A"
                    })
                    foreign_aps.append(ap_info)
                    logger.info(f"AP externo: {ap.get('ssid', 'N/A')}")

            logger.info(f"Resumen: {len(our_aps)} APs propios, {len(foreign_aps)} APs externos")

            # 4. Hacer matching específico para nuestro dispositivo
            matched_aps = self.match_scanned_aps_with_device(scan_result, device_data)

            # 5. Analizar dispositivo completo
            processed_data = await self.get_device_data(device_data)

            # 6. Agregar información de APs
            if matched_aps:
                processed_data["matched_aps"] = matched_aps

            return {
                "status": "success",
                "device_info": {
                    "ip": ip,
                    "mac": device_data.get("identification", {}).get("mac"),
                    "name": device_data.get("identification", {}).get("name"),
                    "model": device_data.get("identification", {}).get("model")
                },
                "scan_results": scan_result,
                "our_aps": our_aps,  # Nuestros APs con info de clientes
                "foreign_aps": foreign_aps,  # APs ajenos
                "matched_aps": matched_aps,
                "matched_count": len(matched_aps),
                "full_analysis": processed_data,
                "summary": {
                    "total_scanned_aps": len(scanned_aps),
                    "our_aps_count": len(our_aps),
                    "foreign_aps_count": len(foreign_aps),
                    "matched_aps": len(matched_aps),
                    "scan_success": scan_result.get("success", False),
                    "device_found_in_uisp": bool(device_data)
                }
            }

        except Exception as e:
            logger.error(f"Error en scan_and_match_aps_direct: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "ip": device_data.get("ipAddress", "")
            }

