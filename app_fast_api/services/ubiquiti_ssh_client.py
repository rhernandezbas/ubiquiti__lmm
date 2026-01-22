import logging
from typing import Dict, Any, List, Optional
import asyncssh
import asyncio
import time
import subprocess
import platform
from ping3 import ping

from app_fast_api.utils.constans import ac_m5_device_frencuency
from app_fast_api.services.ssh_auth_service import ssh_auth_service
logger = logging.getLogger(__name__)


class UbiquitiSSHClient:
    """Cliente SSH para conectarse directamente a dispositivos Ubiquiti"""
    
    def __init__(self):
        """
        Inicializa el cliente SSH con autenticación fallback automática
        
        Note:
            - Las credenciales se manejan automáticamente con fallback
            - No necesita credenciales por defecto en el constructor
            - Usa el sistema de 4 contraseñas con prioridad
        """
        # Ya no necesitamos credenciales por defecto
        # El sistema de autenticación maneja todo automáticamente
        pass
    
    async def connect(self, host: str, username: Optional[str] = None, password: Optional[str] = None, port: int = 22) -> asyncssh.SSHClientConnection:
        """
        Conecta al dispositivo vía SSH con autenticación fallback
        
        Args:
            host: IP del dispositivo
            username: Usuario SSH (opcional, prueba múltiples si no se especifica)
            password: Contraseña SSH (opcional, prueba múltiples si no se especifica)
            port: Puerto SSH (default: 22)
            
        Returns:
            Conexión SSH establecida
        """
        try:
            # Usar el servicio de autenticación con fallback
            success, auth_info, connection = await ssh_auth_service.authenticate_with_fallback(
                host, username, password, port
            )
            
            if not success or not connection:
                raise Exception(f"Autenticación SSH fallida para {host}: {auth_info.get('error', 'Unknown error')}")
            
            logger.info(f"Conexión SSH establecida con {host} usando {auth_info['user']} (intento {auth_info['attempt']}/{auth_info['total_attempts']})")
            return connection
            
        except Exception as e:
            logger.error(f"Error conectando a {host}: {str(e)}")
            raise

    async def execute_command_with_auth(self, host: str, command: str, username: Optional[str] = None, password: Optional[str] = None, port: int = 22, timeout: int = 30, existing_connection: Optional[asyncssh.SSHClientConnection] = None) -> Dict[str, Any]:
        """
        Ejecuta un comando SSH con autenticación fallback o usando conexión existente
        
        Args:
            host: IP del dispositivo
            command: Comando a ejecutar
            username: Usuario SSH (opcional)
            password: Contraseña SSH (opcional)
            port: Puerto SSH
            timeout: Timeout del comando
            existing_connection: Conexión SSH existente (opcional)
            
        Returns:
            Dict con resultado del comando incluyendo información de autenticación
        """
        try:
            # Si se proporciona una conexión existente, usarla directamente
            if existing_connection:
                logger.debug(f"Usando conexión existente para {host}")
                try:
                    result = await asyncio.wait_for(
                        existing_connection.run(command, check=False),
                        timeout=timeout
                    )
                    
                    return {
                        "status": "success",
                        "stdout": result.stdout.strip() if result.stdout else "",
                        "stderr": result.stderr.strip() if result.stderr else "",
                        "exit_status": result.exit_status,
                        "success": result.exit_status == 0,
                        "auth_info": {
                            "used_existing_connection": True,
                            "host": host
                        }
                    }
                except asyncio.TimeoutError:
                    error_msg = f"Comando timeout después de {timeout} segundos"
                    logger.error(f"Timeout ejecutando comando '{command}': {error_msg}")
                    return {
                        "status": "error",
                        "error": error_msg,
                        "auth_info": {"used_existing_connection": True, "host": host}
                    }
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}" if str(e) else f"{type(e).__name__}"
                    logger.error(f"Error ejecutando comando '{command}': {error_msg}")
                    return {
                        "status": "error",
                        "error": error_msg,
                        "auth_info": {"used_existing_connection": True, "host": host}
                    }
            
            # Si no hay conexión existente, usar autenticación fallback
            logger.debug(f"ssh_auth_service available: {ssh_auth_service is not None}")
            if not ssh_auth_service:
                logger.error("SSH auth service is None!")
                return {
                    "status": "error",
                    "error": "SSH auth service not available",
                    "auth_info": {}
                }
            
            logger.debug(f"Calling execute_command_with_auth for {host}")
            result = await ssh_auth_service.execute_command_with_auth(
                host, command, username, password, timeout
            )
            logger.debug(f"execute_command_with_auth returned: {type(result)}")
            
            if result["status"] == "success":
                logger.info(f"Comando ejecutado exitosamente en {host}")
                return {
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "exit_status": result["exit_status"],
                    "success": True,
                    "auth_info": result["auth_info"]
                }
            else:
                logger.error(f"Error ejecutando comando en {host}: {result['error']}")
                return {
                    "stdout": "",
                    "stderr": result["error"],
                    "exit_status": -1,
                    "success": False,
                    "auth_info": result.get("auth_info", {})
                }
                
        except Exception as e:
            logger.error(f"Error inesperado ejecutando comando en {host}: {str(e)}")
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_status": -1,
                "success": False,
                "auth_info": {}
            }

    async def scan_nearby_aps_detailed(self, host: str, interface: str = "ath0", username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Escanea APs cercanos usando iwlist scan que proporciona señal en dBm
        
        Args:
            host: IP del dispositivo
            interface: Interfaz wireless (default: ath0)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Lista de APs con señal en dBm, frecuencia, calidad, etc.
        """
        try:
            # Primer escaneo rápido para iniciar el proceso
            logger.info(f"Iniciando primer escaneo iwlist {interface} scan")
            first_scan = await self.execute_command_with_auth(
                host, 
                f"iwlist {interface} scan", 
                username, 
                password,
                timeout=30
            )
            
            # Esperar 20 segundos para que el dispositivo complete el escaneo
            logger.info("Esperando 20 segundos para escaneo completo...")
            await asyncio.sleep(20)
            
            # Segundo escaneo - este será el resultado completo
            logger.info(f"Iniciando segundo escaneo iwlist {interface} scan (resultado final)")
            result = await self.execute_command_with_auth(
                host, 
                f"iwlist {interface} scan", 
                username, 
                password,
                timeout=45
            )
            
            if not result["success"] or not result["stdout"]:
                return {
                    "success": False,
                    "message": "No se pudo ejecutar el escaneo",
                    "error": result.get("stderr")
                }
            
            # Parsear output de iwlist scan
            output = result["stdout"]
            aps = []
            current_ap = {}
            
            for line in output.split("\n"):
                line = line.strip()
                
                # Nueva celda (AP)
                if "Cell" in line and "Address:" in line:
                    if current_ap:
                        aps.append(current_ap)
                    current_ap = {
                        "bssid": line.split("Address:")[1].strip() if "Address:" in line else ""
                    }
                
                # SSID
                elif "ESSID:" in line:
                    essid = line.split("ESSID:")[1].strip().strip('"')
                    current_ap["ssid"] = essid if essid else "<hidden>"
                
                # Frecuencia
                elif "Frequency:" in line:
                    freq_part = line.split("Frequency:")[1].split()[0]
                    try:
                        freq_ghz = float(freq_part)
                        current_ap["frequency_ghz"] = freq_ghz
                        current_ap["frequency_mhz"] = int(freq_ghz * 1000)
                    except:
                        pass
                
                # Calidad y Señal
                elif "Quality=" in line:
                    # Formato: Quality=39/70  Signal level=-56 dBm
                    if "Signal level=" in line:
                        signal_part = line.split("Signal level=")[1].split()[0]
                        try:
                            # Extraer valor numérico (puede ser "-56" o "-56dBm")
                            signal_dbm = int(signal_part.replace("dBm", "").strip())
                            current_ap["signal_dbm"] = signal_dbm
                        except:
                            pass
                    
                    if "Quality=" in line:
                        quality_part = line.split("Quality=")[1].split()[0]
                        try:
                            # Formato: "39/70"
                            quality_num, quality_max = quality_part.split("/")
                            current_ap["quality"] = int(quality_num)
                            current_ap["quality_max"] = int(quality_max)
                            current_ap["quality_percent"] = int((int(quality_num) / int(quality_max)) * 100)
                        except:
                            pass
                
                # Canal
                elif "Channel:" in line:
                    try:
                        channel = int(line.split("Channel:")[1].strip())
                        current_ap["channel"] = channel
                    except:
                        pass
                
                # Encryption
                elif "Encryption key:" in line:
                    current_ap["encrypted"] = "on" in line.lower()
                
                # Modo
                elif "Mode:" in line:
                    current_ap["mode"] = line.split("Mode:")[1].strip()
            
            # Agregar último AP
            if current_ap:
                aps.append(current_ap)
            
            # Ordenar por señal (más fuerte primero)
            aps.sort(key=lambda x: x.get("signal_dbm", -100), reverse=True)
            
            return {
                "success": True,
                "host": host,
                "interface": interface,
                "aps_count": len(aps),
                "scan_strategy": "dual_scan_with_delay",
                "first_scan_success": first_scan["success"],
                "second_scan_success": result["success"],
                "delay_seconds": 20,
                "total_aps": len(aps),
                "aps": aps
            }
            
        except Exception as e:
            logger.error(f"Error escaneando APs detallado vía SSH: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo escanear APs"
            }

    async def enable_all_AC_frequencies(self, host: str, device_model: str, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Habilita todas las frecuencias disponibles para el modelo del dispositivo si no están configuradas.
        Funciona con LiteBeam AC, NanoBeam AC, PowerBeam AC, y otros modelos Ubiquiti.
        Solo aplica cambios si al dispositivo le faltan frecuencias.
        
        Args:
            host: IP del dispositivo
            device_model: Modelo del dispositivo (LBE-5AC-Gen2, NBE-5AC-19, PBE-5AC-Gen2, etc.)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación con información de frecuencias configuradas
        """

        conn = None
        try:
            conn = await self.connect(host, username, password)
            

            freq_range = ac_m5_device_frencuency

            
            # Obtener configuración actual de scan_list
            result = await self.execute_command(conn, "grep 'radio.1.scan_list.channels=' /tmp/system.cfg")
            
            if not result["success"] or not result["stdout"]:
                return {
                    "success": False,
                    "message": "No se pudo leer la configuración actual",
                    "error": result.get("stderr")
                }
            
            # Extraer frecuencias actuales
            current_config = result["stdout"].strip()
            logger.debug(f"Current config: {current_config}")
            current_freqs_str = current_config.split("=")[1].strip()
            logger.debug(f"Current freqs string: {current_freqs_str}")
            current_freqs = [int(f.strip()) for f in current_freqs_str.split(",") if f.strip().isdigit()]
            logger.debug(f"Current freqs parsed: {current_freqs}, type: {type(current_freqs)}")

            # Verificar si ya tiene todas las frecuencias
            current_freqs_set = set(current_freqs)
            available_freqs_set = set(ac_m5_device_frencuency)
            logger.debug(f"Current set: {len(current_freqs_set)}, Available set: {len(available_freqs_set)}")
            missing_freqs = list(available_freqs_set - current_freqs_set)
            
            if not missing_freqs:
                return {
                    "success": True,
                    "message": f"✅ {device_model} ya tiene todas las {len(ac_m5_device_frencuency)} frecuencias configuradas.",
                    "action": "skipped",
                    "reason": "already_configured",
                    "device_model": device_model,
                    "current_frequencies": current_freqs,
                    "frequency_range": freq_range
                }
            
            # Configurar todas las frecuencias
            logger.info(f"{device_model} tiene {len(current_freqs)} frecuencias. Configurando todas las {len(ac_m5_device_frencuency)} disponibles.")
            
            # Crear lista completa de frecuencias separadas por comas
            all_freqs_str = ",".join(str(f) for f in ac_m5_device_frencuency)
            
            commands = [
                # Hacer backup de configuración actual
                "cp /tmp/system.cfg /tmp/system.cfg.backup",
                # Configurar todas las frecuencias
                f"sed -i 's/radio.1.scan_list.channels=.*/radio.1.scan_list.channels={all_freqs_str}/' /tmp/system.cfg",
                # Habilitar scan list
                "sed -i 's/radio.1.scan_list.status=.*/radio.1.scan_list.status=enabled/' /tmp/system.cfg",
                # Verificar cambio
                "grep 'radio.1.scan_list.channels=' /tmp/system.cfg",
                # Guardar configuración
                "cfgmtd -w -p /tmp/",
                # Aplicar con softrestart
                "/usr/etc/rc.d/rc.softrestart save"
            ]
            
            results = []
            new_config = None
            
            for cmd in commands:
                result = await self.execute_command(conn, cmd)
                results.append({
                    "command": cmd[:100] + "..." if len(cmd) > 100 else cmd,
                    "success": result["success"],
                    "output": result["stdout"][:200] if result["stdout"] else result["stderr"][:200]
                })
                
                # Capturar nueva configuración
                if "grep 'radio.1.scan_list.channels='" in cmd and result["stdout"]:
                    new_config = result["stdout"].strip()
            
            return {
                "success": True,
                "message": f"✅ {device_model} configurado con todas las {len(ac_m5_device_frencuency)} frecuencias disponibles.",
                "action": "configured",
                "device_model": device_model,
                "frequencies_before": len(current_freqs),
                "frequencies_after": len(ac_m5_device_frencuency),
                "frequencies_added": len(missing_freqs),
                "frequency_range": freq_range,
                "current_config": current_freqs_str,
                "new_config": new_config.split("=")[1] if new_config else all_freqs_str,
                "commands_executed": results
            }
            
        except Exception as e:
            logger.error(f"Error habilitando frecuencias para {device_model}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"No se pudo habilitar las frecuencias para {device_model}"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()

    async def enable_all_m5_frequencies(self, host: str, device_model: str, username: Optional[str] = None,
                                        password: Optional[str] = None) -> Dict[str, Any]:
        """
        Habilita todas las frecuencias M5/AC disponibles para el modelo del dispositivo.
        Funciona con dispositivos M5 y AC de Ubiquiti.
        
        Args:
            host: IP del dispositivo
            device_model: Modelo del dispositivo
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación con información de frecuencias configuradas
        """
        logger.info(f"Iniciando configuración de frecuencias M5 para {device_model} en {host}")
        
        conn = None
        try:
            # Paso 1: Conectar al dispositivo
            logger.info(f"Conectando a {host}...")
            conn = await self.connect(host, username, password)
            logger.info(f"Conexión exitosa a {host}")
            
            # Paso 2: Obtener frecuencias disponibles
            freq_range = ac_m5_device_frencuency
            logger.info(f"Frecuencias M5 a configurar: {len(freq_range)} frecuencias")
            
            # Paso 3: Leer configuración actual
            logger.info("Leyendo configuración actual de scan_list...")
            
            # Primero verificar si el archivo system.cfg existe
            logger.info("Verificando existencia de /tmp/system.cfg...")
            check_file = await self.execute_command(conn, "ls -la /tmp/system.cfg")
            logger.info(f"Resultado ls system.cfg: {check_file}")
            
            # Verificar el contenido del archivo
            logger.info("Verificando contenido de /tmp/system.cfg...")
            file_content = await self.execute_command(conn, "cat /tmp/system.cfg | head -20")
            logger.info(f"Contenido parcial de system.cfg: {file_content}")
            
            # Buscar configuración de radio
            logger.info("Buscando configuración de radio...")
            radio_config = await self.execute_command(conn, "grep -n radio.1 /tmp/system.cfg | head -10")
            logger.info(f"Configuración radio encontrada: {radio_config}")
            
            # Intentar leer scan_list específicamente
            result = await self.execute_command(conn, "grep 'wireless.1.scan_list.channels=' /tmp/system.cfg")
            logger.info(f"Resultado específico scan_list: {result}")
            
            if not result["success"] or not result["stdout"]:
                logger.error(f"Error leyendo configuración: {result.get('stderr')}")
                
                # Intentar buscar alternativas
                logger.info("Buscando configuración alternativa...")
                alt_result = await self.execute_command(conn, "grep -i 'scan.*channel' /tmp/system.cfg")
                logger.info(f"Resultado búsqueda alternativa: {alt_result}")
                
                return {
                    "success": False,
                    "message": "No se pudo leer la configuración actual",
                    "error": result.get("stderr"),
                    "step": "reading_config",
                    "debug_info": {
                        "file_exists": check_file["success"],
                        "file_content": file_content["stdout"][:200] if file_content["success"] else "",
                        "radio_config": radio_config["stdout"][:200] if radio_config["success"] else "",
                        "alternative_search": alt_result["stdout"][:200] if alt_result["success"] else "",
                        "original_error": result.get("stderr", "")
                    }
                }
            
            # Paso 4: Parsear frecuencias actuales
            current_config = result["stdout"].strip()
            logger.debug(f"Configuración actual: {current_config}")
            
            try:
                current_freqs_str = current_config.split("=")[1].strip()
                current_freqs = [int(f.strip()) for f in current_freqs_str.split(",") if f.strip().isdigit()]
                logger.info(f"Frecuencias actuales: {len(current_freqs)} - {current_freqs[:5]}...")
            except (IndexError, ValueError) as e:
                logger.error(f"Error parseando frecuencias actuales: {e}")
                return {
                    "success": False,
                    "message": "Error parseando configuración actual",
                    "error": str(e),
                    "step": "parsing_config"
                }
            
            # Paso 5: Verificar si ya tiene todas las frecuencias
            current_freqs_set = set(current_freqs)
            available_freqs_set = set(freq_range)
            missing_freqs = list(available_freqs_set - current_freqs_set)
            
            logger.info(f"Frecuencias actuales: {len(current_freqs_set)}")
            logger.info(f"Frecuencias disponibles: {len(available_freqs_set)}")
            logger.info(f"Frecuencias faltantes: {len(missing_freqs)}")
            
            if not missing_freqs:
                logger.info(f"✅ {device_model} ya tiene todas las frecuencias configuradas")
                return {
                    "success": True,
                    "message": f"✅ {device_model} ya tiene todas las {len(freq_range)} frecuencias configuradas.",
                    "action": "skipped",
                    "reason": "already_configured",
                    "device_model": device_model,
                    "current_frequencies": current_freqs,
                    "frequency_range": freq_range,
                    "step": "validation_complete"
                }
            
            # Paso 6: Configurar todas las frecuencias
            logger.info(f"Configurando {len(missing_freqs)} frecuencias faltantes...")
            all_freqs_str = ",".join(str(f) for f in freq_range)
            logger.debug(f"Nueva configuración: {all_freqs_str[:100]}...")
            
            commands = [
                # Hacer backup de configuración actual
                ("backup", "cp /tmp/system.cfg /tmp/system.cfg.backup"),
                # Configurar todas las frecuencias
                ("configure", f"sed -i 's/wireless.1.scan_list.channels=.*/wireless.1.scan_list.channels={all_freqs_str}/' /tmp/system.cfg"),
                # Habilitar scan list
                ("enable_scan", "sed -i 's/wireless.1.scan_list.status=.*/wireless.1.scan_list.status=enabled/' /tmp/system.cfg"),
                # Verificar cambio
                ("verify", "grep 'wireless.1.scan_list.channels=' /tmp/system.cfg"),
                # Guardar configuración
                ("save", "cfgmtd -w -p /tmp/"),
                # Aplicar con softrestart
                ("apply", "/usr/etc/rc.d/rc.softrestart save")
            ]
            
            results = []
            new_config = None
            
            for step_name, cmd in commands:
                logger.info(f"Ejecutando paso: {step_name} - {cmd[:50]}...")
                result = await self.execute_command(conn, cmd)
                
                results.append({
                    "step": step_name,
                    "command": cmd[:100] + "..." if len(cmd) > 100 else cmd,
                    "success": result["success"],
                    "output": result["stdout"][:200] if result["stdout"] else result["stderr"][:200]
                })
                
                if result["success"]:
                    logger.info(f"✅ Paso {step_name} completado")
                else:
                    logger.error(f"❌ Error en paso {step_name}: {result.get('stderr')}")
                
                # Capturar nueva configuración
                if step_name == "verify" and result["stdout"]:
                    new_config = result["stdout"].strip()
                    logger.info(f"Configuración verificada: {new_config}")
            
            logger.info(f"✅ Configuración completada para {device_model}")
            
            return {
                "success": True,
                "message": f"✅ {device_model} configurado con todas las {len(freq_range)} frecuencias disponibles.",
                "action": "configured",
                "device_model": device_model,
                "frequencies_before": len(current_freqs),
                "frequencies_after": len(freq_range),
                "frequencies_added": len(missing_freqs),
                "frequency_range": freq_range,
                "current_config": current_freqs_str,
                "new_config": new_config.split("=")[1] if new_config else all_freqs_str,
                "commands_executed": results,
                "step": "configuration_complete"
            }
            
        except Exception as e:
            logger.error(f"Error habilitando frecuencias M5 para {device_model}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"No se pudo habilitar las frecuencias para {device_model}",
                "step": "exception_occurred"
            }
        finally:
            if conn:
                logger.info("Cerrando conexión SSH...")
                conn.close()
                await conn.wait_closed()
                logger.info("Conexión cerrada")

    async def ping_device_seconds(self, ip: str, time: int = 10):
        """
        Hace ping a un dispositivo por un tiempo determinado usando ping3
        
        Args:
            ip: Dirección IP del dispositivo
            time: Tiempo en segundos para hacer ping (default: 10)
            
        Returns:
            Dict con resultado del ping estructurado
        """
        try:

            
            logger.info(f"Haciendo ping estructurado a {ip} por {time} segundos...")
            
            # Hacer múltiples pings y calcular estadísticas
            pings = []
            for i in range(time):
                try:
                    result = ping(ip, timeout=1)  # 1 segundo timeout por ping
                    if result is not None:
                        pings.append(result * 1000)  # Convertir a ms
                    else:
                        pings.append(None)  # Timeout
                except:
                    pings.append(None)
            
            # Calcular estadísticas
            successful_pings = [p for p in pings if p is not None]
            failed_pings = len(pings) - len(successful_pings)
            
            if successful_pings:
                avg_ms = sum(successful_pings) / len(successful_pings)
                min_ms = min(successful_pings)
                max_ms = max(successful_pings)
                packet_loss = (failed_pings / len(pings)) * 100
            else:
                avg_ms = 0
                min_ms = 0
                max_ms = 0
                packet_loss = 100
            
            logger.info(f"Ping completado: {len(successful_pings)}/{len(pings)} exitosos, avg: {avg_ms:.2f}ms")
            
            return {
                "status": "success" if len(successful_pings) > 0 else "failed",
                "ip": ip,
                "time_seconds": time,
                "avg_ms": round(avg_ms, 2),
                "min_ms": round(min_ms, 2),
                "max_ms": round(max_ms, 2),
                "packet_loss": round(packet_loss, 1),
                "successful_pings": len(successful_pings),
                "total_pings": len(pings),
                "output": f"Ping3 results: {len(successful_pings)}/{len(pings)} successful, avg: {avg_ms:.2f}ms",
                "error": None
            }
            
        except ImportError:
            # Si no está ping3, usar el método original
            logger.warning("ping3 no disponible, usando método tradicional")
            return await self._ping_device_traditional(ip, time)
        except Exception as e:
            return {
                "status": "error",
                "ip": ip,
                "time_seconds": time,
                "error": str(e)
            }
    
    async def _ping_device_traditional(self, ip: str, time: int = 10):
        """
        Método fallback con ping tradicional
        
        Args:
            ip: Dirección IP del dispositivo
            time: Tiempo en segundos para hacer ping (default: 10)
            
        Returns:
            Dict con resultado del ping
        """
        try:
            import subprocess
            
            # Determinar el comando según el SO
            import platform
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", str(time), ip]
            else:
                cmd = ["ping", "-c", str(time), ip]
            
            # Ejecutar ping
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=time + 5
            )
            
            # Parsear el output para extraer estadísticas
            avg_ms = 0
            packet_loss = 0
            try:
                logger.debug(f"Output completo del ping: {result.stdout}")
                # Buscar la línea con las estadísticas
                lines = result.stdout.split('\n')
                for line in lines:
                    logger.debug(f"Analizando línea: {line}")
                    
                    # Buscar packet loss
                    if 'packet loss' in line:
                        # Extraer packet loss del formato: "10.0% packet loss"
                        # o del formato: "10 packets transmitted, 9 packets received, 10.0% packet loss"
                        try:
                            # Buscar el número antes de '%'
                            import re
                            match = re.search(r'(\d+\.?\d*)%', line)
                            if match:
                                packet_loss = float(match.group(1))
                                logger.debug(f"Packet loss extraído: {packet_loss}%")
                        except:
                            pass
                    
                    # Buscar promedio (round-trip)
                    if 'round-trip min/avg/max' in line:
                        # Extraer el promedio del formato: "round-trip min/avg/max/stddev = 14.478/18.065/23.734/3.037 ms"
                        stats_part = line.split('=')[1].strip()
                        stats = stats_part.split('/')
                        if len(stats) >= 2:
                            avg_ms = float(stats[1])
                            logger.debug(f"Promedio extraído: {avg_ms} ms")
            except Exception as parse_error:
                logger.warning(f"Error parseando ping: {parse_error}")
                pass  # Si falla el parseo, usar valores por defecto
            
            return {
                "status": "success" if result.returncode == 0 else "failed",
                "ip": ip,
                "time_seconds": time,
                "avg_ms": avg_ms,
                "packet_loss": packet_loss,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "ip": ip,
                "time_seconds": time,
                "error": f"Ping timeout después de {time} segundos"
            }
        except Exception as e:
            return {
                "status": "error",
                "ip": ip,
                "time_seconds": time,
                "error": str(e)
            }

    async def ping_until_connected(self, ip: str, max_wait_time: int = 360, check_interval: int = 5):
        """
        Hace ping continuamente hasta que el dispositivo responda o se alcance el tiempo máximo
        
        Args:
            ip: Dirección IP del dispositivo
            max_wait_time: Tiempo máximo de espera en segundos (default: 360 = 6 minutos)
            check_interval: Intervalo entre pings en segundos (default: 5)
            
        Returns:
            Dict con resultado del monitoreo
        """

        start_time = time.time()
        attempts = 0
        
        while time.time() - start_time < max_wait_time:
            attempts += 1
            
            try:
                # Ping simple para verificar conexión
                if platform.system().lower() == "windows":
                    cmd = ["ping", "-n", "1", "-w", "1000", ip]
                else:
                    cmd = ["ping", "-c", "1", "-W", "1", ip]
                
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=3
                )
                
                if result.returncode == 0:
                    # Dispositivo respondió
                    elapsed_time = time.time() - start_time
                    return {
                        "status": "connected",
                        "ip": ip,
                        "attempts": attempts,
                        "elapsed_seconds": round(elapsed_time, 2),
                        "message": f"Dispositivo conectado después de {attempts} intentos en {elapsed_time:.2f} segundos"
                    }
                
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                return {
                    "status": "error",
                    "ip": ip,
                    "attempts": attempts,
                    "elapsed_seconds": round(time.time() - start_time, 2),
                    "error": str(e)
                }
            
            # Esperar antes del siguiente intento
            await asyncio.sleep(check_interval)
        
        # Tiempo máximo alcanzado sin conexión
        elapsed_time = time.time() - start_time
        return {
            "status": "timeout",
            "ip": ip,
            "attempts": attempts,
            "elapsed_seconds": round(elapsed_time, 2),
            "message": f"Tiempo máximo de {max_wait_time}s alcanzado sin conexión"
        }





    async def reboot_device(self, host: str, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Reinicia el dispositivo
        
        Args:
            host: IP del dispositivo
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación
        """
        try:
            logger.info(f"Reiniciando dispositivo {host}...")
            result = await self.execute_command_with_auth(host, "reboot", username, password, timeout=10)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Dispositivo reiniciándose. Espera 1-3 minutos para reconexión."
                }
            else:
                return {
                    "success": False,
                    "message": "No se pudo ejecutar el reboot",
                    "error": result.get("stderr")
                }
            
        except Exception as e:
            # Es normal que la conexión se cierre durante el reboot
            if "connection" in str(e).lower() or "closed" in str(e).lower():
                return {
                    "success": True,
                    "message": "Dispositivo reiniciándose. Espera 1-3 minutos para reconexión."
                }
            else:
                logger.error(f"Error reiniciando dispositivo {host}: {str(e)}")
                return {
                    "success": False,
                    "message": f"Error reiniciando dispositivo: {str(e)}"
                }
