import asyncio
import logging
from typing import Dict, Any, List, Optional
import asyncssh

logger = logging.getLogger(__name__)


class UbiquitiSSHClient:
    """Cliente SSH para conectarse directamente a dispositivos Ubiquiti"""
    
    def __init__(self, default_username: str = "ubnt", default_password: str = "ubnt"):
        """
        Inicializa el cliente SSH
        
        Args:
            default_username: Usuario por defecto para dispositivos Ubiquiti
            default_password: Contraseña por defecto para dispositivos Ubiquiti
        """
        self.default_username = default_username
        self.default_password = default_password
    
    async def connect(self, host: str, username: Optional[str] = None, password: Optional[str] = None, port: int = 22) -> asyncssh.SSHClientConnection:
        """
        Conecta al dispositivo vía SSH
        
        Args:
            host: IP del dispositivo
            username: Usuario SSH (usa default si no se especifica)
            password: Contraseña SSH (usa default si no se especifica)
            port: Puerto SSH (default: 22)
            
        Returns:
            Conexión SSH establecida
        """
        username = username or self.default_username
        password = password or self.default_password
        
        try:
            logger.info(f"Conectando vía SSH a {host}:{port} como {username}")
            conn = await asyncssh.connect(
                host,
                port=port,
                username=username,
                password=password,
                known_hosts=None,  # Deshabilitar verificación de known_hosts
                connect_timeout=10
            )
            logger.info(f"Conexión SSH establecida con {host}")
            return conn
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}" if str(e) else f"{type(e).__name__}"
            logger.error(f"Error conectando vía SSH a {host}: {error_msg}")
            raise
    
    async def execute_command(self, conn: asyncssh.SSHClientConnection, command: str) -> Dict[str, Any]:
        """
        Ejecuta un comando en el dispositivo
        
        Args:
            conn: Conexión SSH activa
            command: Comando a ejecutar
            
        Returns:
            Dict con stdout, stderr y exit_status
        """
        try:
            logger.debug(f"Ejecutando comando SSH: {command}")
            result = await conn.run(command, check=False)
            
            return {
                "stdout": result.stdout.strip() if result.stdout else "",
                "stderr": result.stderr.strip() if result.stderr else "",
                "exit_status": result.exit_status,
                "success": result.exit_status == 0
            }
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}" if str(e) else f"{type(e).__name__}"
            logger.error(f"Error ejecutando comando SSH: {error_msg}")
            return {
                "stdout": "",
                "stderr": error_msg,
                "exit_status": -1,
                "success": False
            }
    
    async def get_wireless_config(self, host: str, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene la configuración wireless actual del dispositivo
        
        Args:
            host: IP del dispositivo
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Configuración wireless actual
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Obtener configuración wireless
            result = await self.execute_command(conn, "mca-config get wireless")
            
            if not result["success"]:
                logger.error(f"Error obteniendo configuración wireless: {result['stderr']}")
                return {}
            
            # Parsear salida (formato JSON o texto)
            config_output = result["stdout"]
            logger.info(f"Configuración wireless obtenida: {config_output[:200]}...")
            
            return {
                "raw_output": config_output,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo configuración wireless vía SSH: {str(e)}")
            return {"success": False, "error": str(e)}
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def change_frequency(self, host: str, frequency_mhz: int, interface: str = "ath0", username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Cambia la frecuencia del dispositivo usando iwconfig
        
        Args:
            host: IP del dispositivo
            frequency_mhz: Frecuencia en MHz (ej: 5840)
            interface: Interfaz wireless (default: ath0)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Convertir MHz a GHz para iwconfig (ej: 5840 MHz = 5.840 GHz)
            frequency_ghz = frequency_mhz / 1000.0
            
            commands = [
                # Ver configuración actual
                f"iwconfig {interface}",
                # Cambiar frecuencia en la configuración (campo correcto: radio.1.freq)
                f"sed -i 's/radio.1.freq=.*/radio.1.freq={frequency_mhz}/' /tmp/system.cfg",
                # Guardar configuración
                "cfgmtd -w -p /tmp/",
                # Aplicar configuración con softrestart
                "/usr/etc/rc.d/rc.softrestart save",
                # Verificar cambio
                f"iwconfig {interface} | grep Frequency"
            ]
            
            results = []
            for cmd in commands:
                result = await self.execute_command(conn, cmd)
                results.append({
                    "command": cmd,
                    "success": result["success"],
                    "output": result["stdout"][:200] if result["stdout"] else result["stderr"][:200]
                })
            
            return {
                "success": True,
                "message": f"Frecuencia cambiada a {frequency_mhz} MHz ({frequency_ghz} GHz)",
                "frequency_mhz": frequency_mhz,
                "frequency_ghz": frequency_ghz,
                "interface": interface,
                "commands_executed": results,
                "requires_reboot": False
            }
            
        except Exception as e:
            logger.error(f"Error cambiando frecuencia vía SSH: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"No se pudo cambiar la frecuencia a {frequency_mhz} MHz"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def get_ap_clients(self, host: str, interface: str = "ath0", username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene los clientes conectados al AP actual
        
        Args:
            host: IP del dispositivo
            interface: Interfaz wireless (default: ath0)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Información de clientes conectados al AP
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Obtener tabla de asociaciones (clientes conectados)
            result = await self.execute_command(conn, f"iwpriv {interface} get_sta_list")
            
            if not result["success"]:
                # Alternativa: usar iwconfig station list
                result = await self.execute_command(conn, f"iwconfig {interface} station list")
            
            output = result["stdout"]
            clients_info = {
                "success": True,
                "clients_count": 0,
                "clients": [],
                "raw_output": output
            }
            
            # Parsear salida para extraer clientes
            if output and output.strip():
                lines = output.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("Station") and not line.startswith("--"):
                        # Formato típico: MAC  Signal  Rate  (varía por dispositivo)
                        parts = line.split()
                        if len(parts) >= 1:
                            mac = parts[0].upper().replace(":", "")
                            client_data = {"mac": mac}
                            
                            # Intentar extraer señal si está disponible
                            if len(parts) >= 2:
                                try:
                                    signal = int(parts[1])
                                    client_data["signal"] = signal
                                except:
                                    pass
                            
                            # Intentar extraer rate si está disponible
                            if len(parts) >= 3:
                                try:
                                    rate = parts[2]
                                    client_data["rate"] = rate
                                except:
                                    pass
                            
                            clients_info["clients"].append(client_data)
            
            clients_info["clients_count"] = len(clients_info["clients"])
            
            return clients_info
            
        except Exception as e:
            logger.error(f"Error obteniendo clientes del AP: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo obtener clientes del AP",
                "clients_count": 0,
                "clients": []
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()

    async def get_current_ap_info(self, host: str, interface: str = "ath0", username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene información del AP actual al que está conectado el dispositivo
        
        Args:
            host: IP del dispositivo
            interface: Interfaz wireless (default: ath0)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Información del AP actual (SSID, BSSID, señal, etc.)
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Obtener información wireless actual
            result = await self.execute_command(conn, f"iwconfig {interface}")
            
            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("stderr"),
                    "message": "No se pudo obtener información wireless"
                }
            
            output = result["stdout"]
            ap_info = {
                "success": True,
                "ssid": None,
                "bssid": None,
                "signal": None,
                "frequency": None,
                "raw_output": output
            }
            
            # Parsear salida de iwconfig para extraer información del AP
            for line in output.split("\n"):
                line = line.strip()
                
                # SSID (ESSID)
                if "ESSID:" in line:
                    essid_part = line.split("ESSID:")[1].strip()
                    ap_info["ssid"] = essid_part.strip('"') if essid_part else None
                
                # BSSID (Access Point)
                if "Access Point:" in line:
                    bssid_part = line.split("Access Point:")[1].strip()
                    ap_info["bssid"] = bssid_part.upper().replace(":", "") if bssid_part else None
                
                # Señal (Signal level)
                if "Signal level=" in line:
                    signal_part = line.split("Signal level=")[1].split()[0]
                    try:
                        ap_info["signal"] = int(signal_part.replace("dBm", "").strip())
                    except:
                        pass
                
                # Frecuencia
                if "Frequency:" in line:
                    freq_part = line.split("Frequency:")[1].split()[0]
                    try:
                        freq_ghz = float(freq_part)
                        ap_info["frequency"] = int(freq_ghz * 1000)  # Convertir a MHz
                    except:
                        pass
            
            return ap_info
            
        except Exception as e:
            logger.error(f"Error obteniendo información del AP actual: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo obtener información del AP actual"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def get_wireless_info(self, host: str, interface: str = "ath0", username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene información wireless actual del dispositivo usando iwconfig
        
        Args:
            host: IP del dispositivo
            interface: Interfaz wireless (default: ath0)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Información wireless actual
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            result = await self.execute_command(conn, f"iwconfig {interface}")
            
            return {
                "success": result["success"],
                "interface": interface,
                "output": result["stdout"],
                "raw_config": result["stdout"]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo info wireless vía SSH: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def set_frequency_list(self, host: str, frequencies: List[int], username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Configura una lista específica de frecuencias para escanear
        
        Args:
            host: IP del dispositivo
            frequencies: Lista de frecuencias en MHz (ej: [5725, 5745, 5765, 5785, 5805, 5825, 5840])
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Convertir lista de frecuencias a formato de canales
            freq_str = ",".join(str(f) for f in frequencies)
            
            commands = [
                f"mca-config set wireless.1.scan.channels '{freq_str}'",
                "cfgmtd -w -p /etc/"
            ]
            
            results = []
            for cmd in commands:
                result = await self.execute_command(conn, cmd)
                results.append({
                    "command": cmd,
                    "success": result["success"],
                    "output": result["stdout"][:100] if result["stdout"] else result["stderr"][:100]
                })
            
            return {
                "success": True,
                "message": f"Frecuencias configuradas: {freq_str}",
                "frequencies": frequencies,
                "commands_executed": results
            }
            
        except Exception as e:
            logger.error(f"Error configurando frecuencias vía SSH: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def setup_test_mode(self, host: str, rollback_seconds: int = 300, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Configura Test Mode con rollback automático.
        Crea scripts que revertirán los cambios automáticamente si no se confirman.
        
        Args:
            host: IP del dispositivo
            rollback_seconds: Segundos antes de revertir (default: 300 = 5 min)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Script de verificación que revierte cambios si no se confirma
            test_check_script = f"""#!/bin/sh
test -e /etc/persistent/test_backup.cfg
if [ $? = 0 ] ; then
    sleep {rollback_seconds}
    mv /etc/persistent/test_backup.cfg /tmp/system.cfg
    cfgmtd -w -p /etc/
    sleep 5
    reboot
else
    echo "No test mode active"
fi
"""
            
            # Script de inicio que ejecuta la verificación
            poststart_script = """#!/bin/sh
/etc/persistent/test_check.sh &
"""
            
            commands = [
                # Crear directorio persistent si no existe
                "mkdir -p /etc/persistent",
                # Verificar si ya existe un backup (test mode activo)
                "test -e /etc/persistent/test_backup.cfg && echo 'BACKUP_EXISTS' || echo 'NO_BACKUP'",
                # Crear script de verificación
                f"cat > /etc/persistent/test_check.sh << 'EOF'\n{test_check_script}\nEOF",
                # Hacer ejecutable
                "chmod +x /etc/persistent/test_check.sh",
                # Crear script poststart
                f"cat > /etc/persistent/rc.poststart << 'EOF'\n{poststart_script}\nEOF",
                # Hacer ejecutable
                "chmod +x /etc/persistent/rc.poststart",
                # Hacer backup SOLO si no existe (preserva configuración original)
                "test ! -e /etc/persistent/test_backup.cfg && cp /tmp/system.cfg /etc/persistent/test_backup.cfg || echo 'Backup ya existe, no se sobrescribe'",
                # Verificar que se creó el backup
                "ls -la /etc/persistent/"
            ]
            
            results = []
            backup_already_exists = False
            
            for i, cmd in enumerate(commands):
                result = await self.execute_command(conn, cmd)
                
                # Verificar si ya existía un backup (comando 1)
                if i == 1 and result["stdout"]:
                    backup_already_exists = "BACKUP_EXISTS" in result["stdout"]
                
                results.append({
                    "command": cmd[:100] + "..." if len(cmd) > 100 else cmd,
                    "success": result["success"],
                    "output": result["stdout"][:200] if result["stdout"] else result["stderr"][:200]
                })
            
            if backup_already_exists:
                message = f"⚠️ Test Mode ya estaba activo. El backup original se preserva. Los cambios se revertirán en {rollback_seconds} segundos si no confirmas."
            else:
                message = f"✅ Test Mode configurado. Backup creado. Los cambios se revertirán en {rollback_seconds} segundos si no confirmas."
            
            return {
                "success": True,
                "message": message,
                "rollback_seconds": rollback_seconds,
                "backup_created": not backup_already_exists,
                "backup_already_existed": backup_already_exists,
                "commands_executed": results
            }
            
        except Exception as e:
            logger.error(f"Error configurando Test Mode: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo configurar Test Mode"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def confirm_test_mode(self, host: str, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Confirma los cambios y desactiva el rollback automático.
        
        Args:
            host: IP del dispositivo
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            commands = [
                # Eliminar backup para confirmar cambios
                "rm -f /etc/persistent/test_backup.cfg",
                # Verificar que se eliminó
                "ls -la /etc/persistent/ | grep test_backup || echo 'Backup eliminado correctamente'"
            ]
            
            results = []
            for cmd in commands:
                result = await self.execute_command(conn, cmd)
                results.append({
                    "command": cmd,
                    "success": result["success"],
                    "output": result["stdout"][:200] if result["stdout"] else result["stderr"][:200]
                })
            
            return {
                "success": True,
                "message": "Cambios confirmados. El rollback automático ha sido desactivado.",
                "commands_executed": results
            }
            
        except Exception as e:
            logger.error(f"Error confirmando Test Mode: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo confirmar los cambios"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def cancel_test_mode(self, host: str, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Cancela Test Mode y revierte cambios inmediatamente.
        
        Args:
            host: IP del dispositivo
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            commands = [
                # Restaurar backup inmediatamente
                "test -e /etc/persistent/test_backup.cfg && mv /etc/persistent/test_backup.cfg /tmp/system.cfg",
                # Aplicar configuración
                "cfgmtd -w -p /etc/",
                # Reiniciar
                "reboot"
            ]
            
            results = []
            for cmd in commands[:-1]:  # No ejecutar reboot aún
                result = await self.execute_command(conn, cmd)
                results.append({
                    "command": cmd,
                    "success": result["success"],
                    "output": result["stdout"][:200] if result["stdout"] else result["stderr"][:200]
                })
            
            # Ejecutar reboot
            await self.execute_command(conn, "reboot")
            
            return {
                "success": True,
                "message": "Cambios revertidos. El dispositivo se está reiniciando.",
                "commands_executed": results
            }
            
        except Exception as e:
            # Es normal que la conexión se cierre durante el reboot
            if "connection" in str(e).lower() or "closed" in str(e).lower():
                return {
                    "success": True,
                    "message": "Cambios revertidos. El dispositivo se está reiniciando."
                }
            logger.error(f"Error cancelando Test Mode: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo cancelar Test Mode"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
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
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Ejecutar escaneo detallado con iwlist
            result = await self.execute_command(conn, f"iwlist {interface} scan")
            
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
                "total_aps": len(aps),
                "aps": aps,
                "raw_output": output
            }
            
        except Exception as e:
            logger.error(f"Error escaneando APs detallado vía SSH: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo escanear APs"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def scan_nearby_aps(self, host: str, interface: str = "ath0", username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Escanea APs cercanos usando wlanconfig
        
        Args:
            host: IP del dispositivo
            interface: Interfaz wireless (default: ath0)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Lista de APs encontrados con señal, frecuencia, etc.
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Ejecutar escaneo de APs
            result = await self.execute_command(conn, f"wlanconfig {interface} list scan")
            
            if not result["success"] or not result["stdout"]:
                return {
                    "success": False,
                    "message": "No se pudo ejecutar el escaneo",
                    "error": result.get("stderr")
                }
            
            # Parsear output del escaneo
            # Formato: SSID BSSID CHAN RATE S:N INT CAPS
            lines = result["stdout"].strip().split("\n")
            aps = []
            
            # Saltar header (primera línea)
            for line in lines[1:]:
                if not line.strip():
                    continue
                
                # El formato es complejo, usar split con límite
                parts = line.split(None, 7)  # Dividir en máximo 8 partes
                if len(parts) >= 5:
                    try:
                        # Extraer señal del formato "S:N" (ej: "31:0" significa señal 31)
                        signal_noise = parts[4]  # Formato "31:0"
                        signal_str = signal_noise.split(':')[0] if ':' in signal_noise else "0"
                        
                        ap = {
                            "ssid": parts[0],
                            "bssid": parts[1],
                            "channel": parts[2],  # Mantener como string, puede ser frecuencia
                            "rate": parts[3],  # Ej: "54M"
                            "signal": int(signal_str) if signal_str.isdigit() else 0,
                            "signal_noise": signal_noise,
                            "capabilities": parts[6] if len(parts) > 6 else "",
                            "raw_line": line
                        }
                        aps.append(ap)
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Error parsing line: {line}, error: {e}")
                        continue
            
            return {
                "success": True,
                "total_aps": len(aps),
                "aps": aps,
                "raw_output": result["stdout"]
            }
            
        except Exception as e:
            logger.error(f"Error escaneando APs vía SSH: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo escanear APs"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def enable_all_litebeam_frequencies(self, host: str, device_model: str, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
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
        from app.config.device_frequencies import get_frequencies_for_model, get_frequency_range_string
        
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Obtener frecuencias disponibles para el modelo
            available_frequencies = get_frequencies_for_model(device_model)
            freq_range = get_frequency_range_string(available_frequencies)
            
            if not available_frequencies:
                return {
                    "success": False,
                    "message": f"No se encontraron frecuencias para el modelo {device_model}",
                    "action": "skipped"
                }
            
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
            logger.debug(f"Available freqs: {available_frequencies[:5]}..., type: {type(available_frequencies)}, first elem type: {type(available_frequencies[0]) if available_frequencies else 'empty'}")
            
            # Verificar si ya tiene todas las frecuencias
            current_freqs_set = set(current_freqs)
            available_freqs_set = set(available_frequencies)
            logger.debug(f"Current set: {len(current_freqs_set)}, Available set: {len(available_freqs_set)}")
            missing_freqs = list(available_freqs_set - current_freqs_set)
            
            if not missing_freqs:
                return {
                    "success": True,
                    "message": f"✅ {device_model} ya tiene todas las {len(available_frequencies)} frecuencias configuradas.",
                    "action": "skipped",
                    "reason": "already_configured",
                    "device_model": device_model,
                    "current_frequencies": current_freqs,
                    "total_frequencies": len(available_frequencies),
                    "frequency_range": freq_range
                }
            
            # Configurar todas las frecuencias
            logger.info(f"{device_model} tiene {len(current_freqs)} frecuencias. Configurando todas las {len(available_frequencies)} disponibles.")
            
            # Crear lista completa de frecuencias separadas por comas
            all_freqs_str = ",".join(str(f) for f in available_frequencies)
            
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
                "message": f"✅ {device_model} configurado con todas las {len(available_frequencies)} frecuencias disponibles.",
                "action": "configured",
                "device_model": device_model,
                "frequencies_before": len(current_freqs),
                "frequencies_after": len(available_frequencies),
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
    
    async def change_frequency_test_mode(self, host: str, frequency_mhz: int, rollback_seconds: int = 300, interface: str = "ath0", username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
        """
        Cambia frecuencia en Test Mode con rollback automático.
        
        Args:
            host: IP del dispositivo
            frequency_mhz: Frecuencia en MHz
            rollback_seconds: Segundos antes de revertir (default: 300)
            interface: Interfaz wireless
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Resultado de la operación
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # 1. Configurar Test Mode
            test_setup = await self.setup_test_mode(host, rollback_seconds, username, password)
            if not test_setup.get("success"):
                return test_setup
            
            # 2. Cambiar frecuencia en /tmp/system.cfg
            frequency_ghz = frequency_mhz / 1000.0
            
            commands = [
                # Ver configuración actual
                f"iwconfig {interface}",
                # Ver lista de escaneo actual
                "grep 'radio.1.scan_list.channels=' /tmp/system.cfg",
                # Ver frecuencia operativa actual
                "grep 'radio.1.freq=' /tmp/system.cfg",
                # Cambiar frecuencia operativa
                f"sed -i 's/radio.1.freq=.*/radio.1.freq={frequency_mhz}/' /tmp/system.cfg",
                # Cambiar lista de frecuencias de escaneo (agregar la nueva frecuencia si no existe)
                f"sed -i 's/radio.1.scan_list.channels=.*/radio.1.scan_list.channels={frequency_mhz}/' /tmp/system.cfg",
                # Habilitar scan list si está deshabilitado
                "sed -i 's/radio.1.scan_list.status=.*/radio.1.scan_list.status=enabled/' /tmp/system.cfg",
                # Verificar cambios
                "grep 'radio.1.scan_list.channels=' /tmp/system.cfg",
                "grep 'radio.1.freq=' /tmp/system.cfg",
                # Guardar configuración
                "cfgmtd -w -p /tmp/",
                # Aplicar configuración con softrestart
                "/usr/etc/rc.d/rc.softrestart save",
                # Esperar
                "sleep 5",
                # Verificar cambio aplicado
                f"iwconfig {interface} | grep Frequency"
            ]
            
            results = []
            scan_list_before = None
            freq_before_cfg = None
            scan_list_after = None
            freq_after_cfg = None
            freq_after_apply = None
            
            for i, cmd in enumerate(commands):
                result = await self.execute_command(conn, cmd)
                output = result["stdout"][:200] if result["stdout"] else result["stderr"][:200]
                
                # Capturar scan list antes (comando 1)
                if i == 1 and result["stdout"]:
                    match = result["stdout"].strip()
                    if "radio.1.scan_list.channels=" in match:
                        scan_list_before = match.split("=")[1].strip()
                
                # Capturar frecuencia antes del cambio (comando 2)
                if i == 2 and result["stdout"]:
                    match = result["stdout"].strip()
                    if "radio.1.freq=" in match:
                        freq_before_cfg = match.split("=")[1].strip()
                
                # Capturar scan list después (comando 6)
                if i == 6 and result["stdout"]:
                    match = result["stdout"].strip()
                    if "radio.1.scan_list.channels=" in match:
                        scan_list_after = match.split("=")[1].strip()
                
                # Capturar frecuencia después del cambio (comando 7)
                if i == 7 and result["stdout"]:
                    match = result["stdout"].strip()
                    if "radio.1.freq=" in match:
                        freq_after_cfg = match.split("=")[1].strip()
                
                # Capturar frecuencia después de aplicar (comando 11: iwconfig final)
                if i == 11 and result["stdout"]:
                    # Extraer frecuencia de iwconfig output
                    if "Frequency:" in result["stdout"]:
                        freq_str = result["stdout"].split("Frequency:")[1].split()[0]
                        # Convertir GHz a MHz
                        freq_after_apply = str(int(float(freq_str) * 1000))
                
                results.append({
                    "command": cmd,
                    "success": result["success"],
                    "output": output
                })
            
            # Validar si el cambio se aplicó correctamente
            cambio_en_archivo = freq_after_cfg == str(frequency_mhz)
            cambio_scan_list = scan_list_after == str(frequency_mhz)
            cambio_aplicado = freq_after_apply == str(frequency_mhz) if freq_after_apply else None
            
            validation = {
                "scan_list_antes": scan_list_before,
                "frecuencia_antes": freq_before_cfg,
                "frecuencia_solicitada": str(frequency_mhz),
                "scan_list_despues": scan_list_after,
                "frecuencia_en_archivo": freq_after_cfg,
                "frecuencia_aplicada": freq_after_apply,
                "cambio_scan_list_exitoso": cambio_scan_list,
                "cambio_en_archivo_exitoso": cambio_en_archivo,
                "cambio_aplicado_exitoso": cambio_aplicado
            }
            
            # Determinar mensaje según validación
            if cambio_aplicado and cambio_scan_list:
                message = f"✅ Frecuencia cambiada exitosamente de {freq_before_cfg} MHz a {frequency_mhz} MHz. Scan list actualizada de [{scan_list_before}] a [{scan_list_after}]."
                success = True
            elif cambio_en_archivo and cambio_scan_list:
                message = f"⚠️ Frecuencia y scan list cambiadas en archivo pero aún no se reflejan en iwconfig. Espera 30 segundos."
                success = True
            elif cambio_scan_list:
                message = f"⚠️ Scan list actualizada a [{scan_list_after}] pero frecuencia operativa no cambió."
                success = True
            else:
                message = f"❌ Error: No se pudo cambiar. Scan list: {scan_list_after}, Frecuencia: {freq_after_cfg} MHz."
                success = False
            
            return {
                "success": success,
                "message": message,
                "frequency_mhz": frequency_mhz,
                "frequency_ghz": frequency_ghz,
                "rollback_seconds": rollback_seconds,
                "test_mode_active": True,
                "rebooting": False,
                "validation": validation,
                "commands_executed": results,
                "instrucciones": {
                    "verificar": f"Verifica en UISP que el dispositivo funciona en {frequency_mhz} MHz",
                    "confirmar": f"Si funciona, llama a /confirm-test-mode/by-ip?ip_address={host} ANTES de {rollback_seconds} segundos",
                    "cancelar": f"Si no funciona, llama a /cancel-test-mode/by-ip?ip_address={host} para revertir con reinicio",
                    "automatico": f"Si no haces nada, en {rollback_seconds} segundos se revertirá automáticamente CON REINICIO"
                }
            }
            
        except Exception as e:
            logger.error(f"Error cambiando frecuencia en Test Mode: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "No se pudo cambiar frecuencia en Test Mode"
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
    async def get_connected_clients_count(self, host: str, interface: str = "ath0", username: Optional[str] = None, password: Optional[str] = None) -> int:
        """
        Obtiene el número de clientes conectados a un AP vía SSH.
        
        Args:
            host: IP del AP
            interface: Interfaz wireless (default: ath0)
            username: Usuario SSH
            password: Contraseña SSH
            
        Returns:
            Número de clientes conectados
        """
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            # Usar wlanconfig para listar estaciones conectadas
            result = await self.execute_command(conn, f"wlanconfig {interface} list sta")
            
            if not result["success"] or not result["stdout"]:
                return 0
            
            # Contar líneas (cada línea es un cliente, excepto el header)
            lines = result["stdout"].strip().split("\n")
            # Restar 1 por el header
            client_count = max(0, len(lines) - 1)
            
            return client_count
            
        except Exception as e:
            logger.error(f"Error obteniendo clientes conectados de {host}: {str(e)}")
            return 0
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
    
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
        conn = None
        try:
            conn = await self.connect(host, username, password)
            
            logger.info(f"Reiniciando dispositivo {host}...")
            result = await self.execute_command(conn, "reboot")
            
            return {
                "success": True,
                "message": "Dispositivo reiniciándose. Espera 1-3 minutos para reconexión."
            }
            
        except Exception as e:
            # Es normal que la conexión se cierre durante el reboot
            if "connection" in str(e).lower() or "closed" in str(e).lower():
                return {
                    "success": True,
                    "message": "Dispositivo reiniciándose. Espera 1-3 minutos para reconexión."
                }
            logger.error(f"Error reiniciando dispositivo vía SSH: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if conn:
                conn.close()
                await conn.wait_closed()
