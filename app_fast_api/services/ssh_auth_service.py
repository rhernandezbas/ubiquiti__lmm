"""
Servicio de autenticación SSH con múltiples credenciales
"""

import asyncssh
import asyncio
from typing import Dict, Any, Optional, Tuple
from app_fast_api.utils.constans import ubitiqui_password
import logging

logger = logging.getLogger(__name__)


class SSHAuthService:
    """Servicio para manejar autenticación SSH con múltiples credenciales"""
    
    def __init__(self):
        self.credentials = ubitiqui_password
    
    async def authenticate_with_fallback(
        self, 
        ip: str, 
        username: Optional[str] = None, 
        password: Optional[str] = None,
        port: int = 22,
        timeout: int = 10
    ) -> Tuple[bool, Dict[str, Any], Optional[asyncssh.SSHClientConnection]]:
        """
        Intenta autenticarse con múltiples credenciales por prioridad
        
        Args:
            ip: IP del dispositivo
            username: Usuario opcional (si no se proporciona, usa "ubnt")
            password: Contraseña opcional (si no se proporciona, prueba todas)
            port: Puerto SSH
            timeout: Timeout de conexión
            
        Returns:
            Tuple[success, credentials_used, connection]
        """
        # Lista de credenciales a probar en orden de prioridad
        credentials_to_try = []
        
        # Si se proporcionan credenciales específicas, probarlas primero
        if username and password:
            credentials_to_try.append({"user": username, "password": password})
            logger.info(f"Probando credenciales proporcionadas: {username}@{ip}")
        
        # Agregar las credenciales por defecto en orden de prioridad
        credentials_to_try.extend(self.credentials)
        
        last_error = None
        
        for i, creds in enumerate(credentials_to_try):
            try:
                logger.info(f"Intento {i+1}/{len(credentials_to_try)}: {creds['user']}@{ip}")
                
                # Intentar conectar con timeout usando asyncio.wait_for
                try:
                    connection = await asyncio.wait_for(
                        asyncssh.connect(
                            ip,
                            port=port,
                            username=creds['user'],
                            password=creds['password'],
                            known_hosts=None  # Desactivar verificación de host key
                        ),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    raise Exception(f"Connection timeout after {timeout} seconds")
                
                logger.info(f"✅ Autenticación exitosa con {creds['user']}@{ip}")
                
                return True, {
                    "user": creds['user'],
                    "password": creds['password'],
                    "attempt": i + 1,
                    "total_attempts": len(credentials_to_try),
                    "provided_credentials": username and password is not None
                }, connection
                
            except asyncssh.PermissionDenied as e:
                last_error = e
                logger.warning(f"❌ Permiso denegado con {creds['user']}@{ip}: {str(e)}")
                continue
                
            except Exception as e:
                last_error = e
                # Verificar si es un error de conexión
                if "connection" in str(e).lower() or "network" in str(e).lower() or "timeout" in str(e).lower():
                    logger.error(f"❌ Error de conexión con {creds['user']}@{ip}: {str(e)}")
                    # Si es error de conexión, no probar con otras credenciales
                    break
                else:
                    logger.error(f"❌ Error inesperado con {creds['user']}@{ip}: {str(e)}")
                    continue
        
        # Si llegamos aquí, todas las autenticaciones fallaron
        logger.error(f"❌ Todas las autenticaciones fallaron para {ip}")
        return False, {
            "error": str(last_error) if last_error else "Unknown authentication error",
            "total_attempts": len(credentials_to_try),
            "provided_credentials": username and password is not None
        }, None
    
    async def execute_command_with_auth(
        self,
        ip: str,
        command: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Ejecuta un comando SSH con autenticación fallback
        
        Args:
            ip: IP del dispositivo
            command: Comando a ejecutar
            username: Usuario opcional
            password: Contraseña opcional
            timeout: Timeout del comando
            
        Returns:
            Dict con resultado del comando
        """
        try:
            # Intentar autenticación
            success, auth_info, connection = await self.authenticate_with_fallback(
                ip, username, password
            )
            
            if not success or not connection:
                return {
                    "status": "error",
                    "error": auth_info.get("error", "Authentication failed"),
                    "auth_info": auth_info
                }
            
            try:
                # Ejecutar comando
                if not connection:
                    return {
                        "status": "error",
                        "error": "Connection is None",
                        "auth_info": auth_info
                    }
                
                result = await connection.run(command, timeout=timeout)
                
                return {
                    "status": "success",
                    "stdout": result.stdout.strip() if result.stdout else "",
                    "stderr": result.stderr.strip() if result.stderr else "",
                    "exit_status": result.exit_status,
                    "auth_info": auth_info
                }
                
            except Exception as e:
                logger.error(f"Error ejecutando comando en {ip}: {str(e)}")
                return {
                    "status": "error",
                    "error": str(e),
                    "auth_info": {}
                }
        except Exception as e:
            logger.error(f"Error ejecutando comando en {ip}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "auth_info": {}
            }


# Instancia global del servicio
ssh_auth_service = SSHAuthService()


