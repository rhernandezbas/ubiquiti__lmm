import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def ping_device(ip_address: str, count: int = 2) -> Dict[str, Any]:
    """
    Ping a device and return connectivity statistics
    """
    try:
        process = await asyncio.create_subprocess_exec(
            'ping', '-c', str(count), '-W', '2', ip_address,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        output = stdout.decode()
        
        if process.returncode == 0:
            # Parse ping output
            lines = output.split('\n')
            stats_line = [l for l in lines if 'packets transmitted' in l]
            rtt_line = [l for l in lines if 'min/avg/max' in l or 'round-trip' in l]
            
            result = {
                "reachable": True,
                "packets_sent": count,
                "packets_received": 0,
                "packet_loss": 0,
                "avg_latency_ms": None
            }
            
            if stats_line:
                parts = stats_line[0].split(',')
                for part in parts:
                    if 'received' in part:
                        received = int(part.strip().split()[0])
                        result["packets_received"] = received
                    if 'packet loss' in part or 'loss' in part:
                        loss_str = part.strip().split()[0].replace('%', '')
                        result["packet_loss"] = float(loss_str)
            
            if rtt_line:
                # Extract average latency
                rtt_parts = rtt_line[0].split('=')[-1].strip().split('/')
                if len(rtt_parts) >= 2:
                    result["avg_latency_ms"] = float(rtt_parts[1])
            
            return result
        else:
            return {
                "reachable": False,
                "packets_sent": count,
                "packets_received": 0,
                "packet_loss": 100,
                "avg_latency_ms": None,
                "error": "Device unreachable"
            }
            
    except Exception as e:
        logger.error(f"Error pinging device {ip_address}: {str(e)}")
        return {
            "reachable": False,
            "error": str(e)
        }
