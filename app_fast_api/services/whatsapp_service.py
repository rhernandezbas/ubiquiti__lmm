"""
WhatsApp Service for sending alerts
"""

import httpx
import os
from typing import Dict, Any, Optional
from datetime import datetime
from app_fast_api.utils.logger import get_logger
from app_fast_api.utils.timezone import format_argentina_datetime, format_argentina_time, now_argentina

logger = get_logger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp notifications"""

    def __init__(self):
        """Initialize WhatsApp service"""
        self.api_url = os.getenv("WHATSAPP_API_URL", "http://190.7.234.37:7842/api/whatsapp/send/text")
        self.phone_complete = os.getenv("WHATSAPP_PHONE_COMPLETE", "")  # Número para mensaje completo
        self.phone_summary = os.getenv("WHATSAPP_PHONE_SUMMARY", "")  # Número para mensaje resumido
        self.timeout = 30.0
        self.enabled = os.getenv("WHATSAPP_ENABLED", "true").lower() == "true"

    async def send_message(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send WhatsApp message to a phone number.

        Args:
            phone_number: Phone number with country code (e.g., "5491112345678")
            message: Message text to send

        Returns:
            Dict with status and response
        """
        if not self.enabled:
            logger.warning("WhatsApp notifications are disabled")
            return {"success": False, "error": "WhatsApp disabled"}

        if not phone_number:
            logger.error("No phone number provided")
            return {"success": False, "error": "No phone number"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "phone_number": phone_number,
                    "message": message
                }

                logger.info(f"Sending WhatsApp message to {phone_number}")
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()

                result = response.json()
                logger.info(f"✅ WhatsApp message sent successfully to {phone_number}")

                return {
                    "success": True,
                    "phone_number": phone_number,
                    "provider_response": result,
                    "sent_at": now_argentina().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"❌ Timeout sending WhatsApp to {phone_number}")
            return {"success": False, "error": "Timeout", "phone_number": phone_number}

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error sending WhatsApp to {phone_number}: {e}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}",
                "phone_number": phone_number,
                "details": str(e)
            }

        except Exception as e:
            logger.error(f"❌ Error sending WhatsApp to {phone_number}: {e}")
            return {"success": False, "error": str(e), "phone_number": phone_number}

    def format_complete_message(self, site_data: Dict[str, Any], event_data: Dict[str, Any]) -> str:
        """
        Format complete alert message with all site details.

        Args:
            site_data: Site information from UISP
            event_data: Alert event data

        Returns:
            Formatted message string
        """
        site_name = site_data.get("identification", {}).get("name", "Unknown Site")
        device_count = site_data.get("description", {}).get("deviceCount", 0)
        device_outage = site_data.get("description", {}).get("deviceOutageCount", 0)
        outage_pct = (device_outage / device_count * 100) if device_count > 0 else 0

        # Extract contact info
        contact = site_data.get("description", {}).get("contact", {})
        contact_name = contact.get("name", "No especificado")
        contact_phone = contact.get("phone", "No especificado")
        contact_email = contact.get("email", "No especificado")

        # Parse description for additional info
        description = site_data.get("description", {}).get("note", "")

        # Extract key info from description (regex or simple parsing)
        def extract_info(text: str, label: str, default: str = "No especificado") -> str:
            try:
                if label in text:
                    start = text.find(label)
                    end = text.find("\n", start)
                    if end == -1:
                        end = len(text)
                    return text[start + len(label):end].strip()
            except:
                pass
            return default

        # Format detection time in Argentina timezone
        detected_at_str = event_data.get('detected_at')
        if isinstance(detected_at_str, str):
            try:
                detected_dt = datetime.fromisoformat(detected_at_str.replace('Z', '+00:00'))
                detected_at_formatted = format_argentina_datetime(detected_dt)
            except:
                detected_at_formatted = detected_at_str
        elif isinstance(detected_at_str, datetime):
            detected_at_formatted = format_argentina_datetime(detected_at_str)
        else:
            detected_at_formatted = format_argentina_datetime(now_argentina())

        # Build complete message
        message = f"""🚨 ALERTA CRÍTICA - SITE CAÍDO

📍 Site: {site_name}
⚠️ Estado: {outage_pct:.0f}% de dispositivos caídos ({device_outage}/{device_count})
🕐 Detectado: {detected_at_formatted}

📋 INFORMACIÓN DE CONTACTO
👤 Contacto: {contact_name}
📱 Teléfono: {contact_phone}
📧 Email: {contact_email}

🚪 ACCESO AL NODO
{extract_info(description, "Tipo de acceso:", "No especificado")}

🔋 ENERGÍA
{extract_info(description, "Tiene baterías:", "No especificado")}
Duración: {extract_info(description, "Duración estimada:", "No especificado")}

🏢 COOPERATIVA
Nombre: {extract_info(description, "Nombre:", "No especificado")}
☎️  Teléfono: {extract_info(description, "Teléfono:", "No especificado")}

🔗 CONECTIVIDAD DE RESPALDO
Nodo vecino: {extract_info(description, "Nodo vecino para recuperación:", "No especificado")}
AP disponible: {extract_info(description, "AP que se puede utilizar:", "No especificado")}

👮 CRITERIOS GUARDIA
{extract_info(description, "Se manda guardia solo si:", "No especificado")}
Horarios: {extract_info(description, "Horarios permitidos:", "No especificado")}
"""
        return message.strip()

    def format_summary_message(self, site_data: Dict[str, Any], event_data: Dict[str, Any]) -> str:
        """
        Format summary alert message (ultra simple).

        Args:
            site_data: Site information from UISP
            event_data: Alert event data

        Returns:
            Formatted summary message
        """
        site_name = site_data.get("identification", {}).get("name", "Unknown Site")
        device_count = site_data.get("description", {}).get("deviceCount", 0)
        device_outage = site_data.get("description", {}).get("deviceOutageCount", 0)
        outage_pct = (device_outage / device_count * 100) if device_count > 0 else 0

        # Format detection time in Argentina timezone
        detected_at_str = event_data.get('detected_at')
        if isinstance(detected_at_str, str):
            try:
                detected_dt = datetime.fromisoformat(detected_at_str.replace('Z', '+00:00'))
                detected_time = format_argentina_datetime(detected_dt)
            except:
                detected_time = detected_at_str
        elif isinstance(detected_at_str, datetime):
            detected_time = format_argentina_datetime(detected_at_str)
        else:
            detected_time = format_argentina_datetime(now_argentina())

        message = f"""🚨 ALERTA: {site_name} CAÍDO
⚠️ {device_outage}/{device_count} dispositivos down ({outage_pct:.0f}%)
🕐 {detected_time}"""

        return message.strip()

    def format_recovery_message(self, site_data: Dict[str, Any], event_data: Dict[str, Any]) -> str:
        """
        Format recovery message.

        Args:
            site_data: Site information from UISP
            event_data: Alert event data with recovery info

        Returns:
            Formatted recovery message
        """
        site_name = site_data.get("identification", {}).get("name", "Unknown Site")
        device_count = site_data.get("description", {}).get("deviceCount", 0)
        downtime = event_data.get("downtime_minutes", 0)

        hours = downtime // 60
        minutes = downtime % 60
        downtime_str = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"

        # Format recovery time in Argentina timezone
        recovered_at_str = event_data.get('recovered_at')
        if isinstance(recovered_at_str, str):
            try:
                recovered_dt = datetime.fromisoformat(recovered_at_str.replace('Z', '+00:00'))
                recovery_time = format_argentina_time(recovered_dt)
            except:
                recovery_time = recovered_at_str
        elif isinstance(recovered_at_str, datetime):
            recovery_time = format_argentina_time(recovered_at_str)
        else:
            recovery_time = format_argentina_time(now_argentina())

        message = f"""✅ RECUPERACIÓN: {site_name}
⏱️ Caída: {downtime_str}
📊 Devices: {device_count}/{device_count} activos
🕐 Recuperado: {recovery_time}"""

        return message.strip()

    async def send_outage_alert(self, site_data: Dict[str, Any], event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send both complete and summary outage alerts.

        Args:
            site_data: Site information from UISP
            event_data: Alert event data

        Returns:
            Dict with results of both notifications
        """
        results = {
            "complete": None,
            "summary": None
        }

        # Send complete message
        if self.phone_complete:
            complete_msg = self.format_complete_message(site_data, event_data)
            results["complete"] = await self.send_message(self.phone_complete, complete_msg)
        else:
            logger.warning("No phone number configured for complete messages")

        # Send summary message only if different from complete number
        if self.phone_summary and self.phone_summary != self.phone_complete:
            summary_msg = self.format_summary_message(site_data, event_data)
            results["summary"] = await self.send_message(self.phone_summary, summary_msg)
        elif self.phone_summary == self.phone_complete:
            logger.info("Summary phone is same as complete phone, skipping duplicate message")
            results["summary"] = results["complete"]  # Reuse complete result
        else:
            logger.warning("No phone number configured for summary messages")

        return results

    async def send_recovery_alert(self, site_data: Dict[str, Any], event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send recovery notification to both numbers (or just one if they're the same).

        Args:
            site_data: Site information from UISP
            event_data: Alert event data with recovery info

        Returns:
            Dict with results of notifications
        """
        recovery_msg = self.format_recovery_message(site_data, event_data)

        results = {
            "complete": None,
            "summary": None
        }

        # Send to complete number
        if self.phone_complete:
            results["complete"] = await self.send_message(self.phone_complete, recovery_msg)

        # Send to summary number only if different from complete number
        if self.phone_summary and self.phone_summary != self.phone_complete:
            results["summary"] = await self.send_message(self.phone_summary, recovery_msg)
        elif self.phone_summary == self.phone_complete:
            logger.info("Summary phone is same as complete phone, skipping duplicate recovery message")
            results["summary"] = results["complete"]  # Reuse complete result

        return results
