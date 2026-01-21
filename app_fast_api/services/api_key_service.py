"""
Servicio para manejar codificación y decodificación de API Keys de forma segura
"""

import base64
import os
from typing import Optional
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class APIKeyService:
    """Servicio para manejar API Keys de forma segura"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Inicializa el servicio de API Keys
        
        Args:
            encryption_key: Clave de encriptación (opcional, usa variable de entorno si no se proporciona)
        """
        self.encryption_key = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not self.encryption_key:
            # Generar una clave de encriptación si no existe
            self.encryption_key = Fernet.generate_key().decode()
            logger.warning("🔐 No se encontró ENCRYPTION_KEY, usando una generada automáticamente")
        
        # Crear el cifrador
        self.cipher_suite = Fernet(self.encryption_key.encode())
        
        logger.info("🔐 Servicio de API Keys inicializado")
    
    def encrypt_api_key(self, api_key: str) -> str:
        """
        Codifica una API Key
        
        Args:
            api_key: La API Key a codificar
            
        Returns:
            API Key codificada en base64
        """
        try:
            # Convertir a bytes si es string
            if isinstance(api_key, str):
                api_key_bytes = api_key.encode('utf-8')
            else:
                api_key_bytes = api_key
            
            # Cifrar
            encrypted_key = self.cipher_suite.encrypt(api_key_bytes)
            
            # Convertir a base64
            encrypted_b64 = base64.b64encode(encrypted_key).decode('utf-8')
            
            logger.info("🔐 API Key codificada exitosamente")
            return encrypted_b64
            
        except Exception as e:
            logger.error(f"❌ Error codificando API Key: {str(e)}")
            raise
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """
        Decodifica una API Key
        
        Args:
            encrypted_key: La API Key codificada en base64
            
        Returns:
            API Key decodificada
        """
        try:
            # Convertir desde base64
            encrypted_bytes = base64.b64decode(encrypted_key.encode('utf-8'))
            
            # Descifrar
            decrypted_key = self.cipher_suite.decrypt(encrypted_bytes)
            
            # Convertir a string
            api_key = decrypted_key.decode('utf-8')
            
            logger.info("🔓 API Key decodificada exitosamente")
            return api_key
            
        except Exception as e:
            logger.error(f"❌ Error decodificando API Key: {str(e)}")
            raise
    
    def get_api_key_from_env(self, env_var: str = "OPENAI_API_KEY") -> Optional[str]:
        """
        Obtiene API Key de variable de entorno y la decodifica si está codificada
        
        Args:
            env_var: Nombre de la variable de entorno
            
        Returns:
            API Key decodificada o None si no existe
        """
        try:
            encrypted_key = os.getenv(env_var)
            if not encrypted_key:
                logger.warning(f"⚠️ Variable de entorno {env_var} no encontrada")
                return None
            
            # Verificar si parece estar codificada (contiene caracteres no base64)
            try:
                # Intentar decodificar para verificar si está codificada
                return self.decrypt_api_key(encrypted_key)
            except Exception:
                # Si falla, asumir que no está codificada
                logger.info(f"🔓 Usando API Key directamente de variable de entorno")
                return encrypted_key
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo API Key de entorno: {str(e)}")
            return None
    
    def validate_api_key(self, api_key: str) -> bool:
        """
        Valida que una API Key tenga el formato correcto de OpenAI
        
        Args:
            api_key: API Key a validar
            
        Returns:
            True si es válida, False si no
        """
        try:
            # Las API Keys de OpenAI empiezan con "sk-"
            if not api_key.startswith("sk-"):
                return False
            
            # Las API Keys modernas de OpenAI pueden tener diferentes longitudes
            # - Keys antiguas: 51 caracteres (sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
            # - Keys nuevas: 56+ caracteres (sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
            if len(api_key) < 20:  # Mínimo razonable
                return False
            
            # Verificar caracteres válidos (solo alfanuméricos y guiones)
            valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-")
            for char in api_key[3:]:  # Después de "sk-"
                if char not in valid_chars:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validando API Key: {str(e)}")
            return False
    
    def mask_api_key(self, api_key: str, visible_chars: int = 8) -> str:
        """
        Enmascara una API Key para mostrar en logs
        
        Args:
            api_key: API Key a enmascarcar
            visible_chars: Número de caracteres visibles al inicio y final
            
        Returns:
            API Key enmascarada
        """
        if len(api_key) <= visible_chars * 2:
            return api_key
        
        start = api_key[:visible_chars]
        end = api_key[-visible_chars:] if len(api_key) > visible_chars else ""
        middle = "*" * (len(api_key) - visible_chars * 2)
        
        return f"{start}{middle}{end}"


# Instancia global del servicio
api_key_service = APIKeyService()
