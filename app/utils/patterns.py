from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DiagnosticPatterns:
    def __init__(self):
        self.patterns = [
            {
                "name": "High CPU Usage",
                "description": "Device CPU usage is above 80%",
                "severity": "high",
                "check": lambda stats: (stats.get("cpu") or 0) > 80,
                "recommendation": "Investigate processes consuming CPU, consider firmware update or device restart"
            },
            {
                "name": "High Memory Usage",
                "description": "Device memory usage is above 85%",
                "severity": "high",
                "check": lambda stats: (stats.get("ram") or stats.get("memory") or 0) > 85,
                "recommendation": "Check for memory leaks, restart device if necessary"
            },
            {
                "name": "Interface Errors",
                "description": "Network interface has packet errors",
                "severity": "medium",
                "check": lambda iface: (iface.get("errors") or 0) > 100,
                "recommendation": "Check cable quality, inspect for physical damage"
            },
            {
                "name": "High Packet Loss",
                "description": "Packet loss detected above 5%",
                "severity": "high",
                "check": lambda stats: (stats.get("packetLoss") or 0) > 5,
                "recommendation": "Check wireless interference, verify signal strength"
            },
            {
                "name": "Frequent Disconnections",
                "description": "Device has multiple recent outages",
                "severity": "critical",
                "check": lambda outages: len(outages) > 3,
                "recommendation": "Investigate power supply, check network stability"
            },
            {
                "name": "Low Signal Strength",
                "description": "Wireless signal strength is poor",
                "severity": "medium",
                "check": lambda stats: (stats.get("signal") or 0) < -70 and stats.get("signal") is not None,
                "recommendation": "Adjust antenna positioning, reduce distance to AP"
            },
            {
                "name": "Outdated Firmware",
                "description": "Device firmware is outdated",
                "severity": "low",
                "check": lambda device: device.get("outdated", False),
                "recommendation": "Update to latest firmware version"
            },
            {
                "name": "High Temperature",
                "description": "Device temperature is elevated",
                "severity": "high",
                "check": lambda stats: stats.get("temperature") is not None and stats.get("temperature") > 70,
                "recommendation": "Ensure proper ventilation, check cooling system"
            }
        ]

    def check_patterns(
        self,
        device_data: Dict[str, Any],
        statistics: Dict[str, Any],
        interfaces: List[Dict[str, Any]],
        outages: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        matched_patterns = []
        issues = []
        recommendations = []
        
        # Extract overview from device_data (UISP structure)
        overview = device_data.get("overview", {})
        
        try:
            for pattern in self.patterns:
                try:
                    matched = False
                    
                    if "cpu" in pattern["name"].lower() or "memory" in pattern["name"].lower() or "temperature" in pattern["name"].lower():
                        # Use overview instead of statistics
                        if pattern["check"](overview):
                            matched = True
                    
                    elif "interface" in pattern["name"].lower():
                        for iface in interfaces:
                            if pattern["check"](iface):
                                matched = True
                                break
                    
                    elif "disconnection" in pattern["name"].lower() and outages:
                        if pattern["check"](outages):
                            matched = True
                    
                    elif "firmware" in pattern["name"].lower():
                        if pattern["check"](device_data):
                            matched = True
                    
                    elif "signal" in pattern["name"].lower():
                        # Use overview instead of statistics
                        if pattern["check"](overview):
                            matched = True
                    
                    elif "packet" in pattern["name"].lower():
                        # Use overview instead of statistics
                        if pattern["check"](overview):
                            matched = True
                    
                    if matched:
                        matched_patterns.append({
                            "name": pattern["name"],
                            "severity": pattern["severity"],
                            "description": pattern["description"]
                        })
                        issues.append(pattern["description"])
                        recommendations.append(pattern["recommendation"])
                        
                except Exception as e:
                    logger.warning(f"Error checking pattern {pattern['name']}: {str(e)}")
                    continue
            
            return {
                "matched_patterns": matched_patterns,
                "issues": issues,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error in pattern checking: {str(e)}")
            return {
                "matched_patterns": [],
                "issues": [],
                "recommendations": []
            }
