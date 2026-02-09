"""Service for managing Ubiquiti monitoring data persistence."""

from datetime import datetime
from app_fast_api.utils.timezone import now_argentina
from typing import List, Optional, Dict, Any

from app_fast_api.repositories.ubiquiti_repositories import DeviceAnalysisRepository, ScanResultRepository, FrequencyChangeRepository
from app_fast_api.models.ubiquiti_monitoring.device_analysis import DeviceAnalysis, ScanResult, FrequencyChange
import json


class UbiquitiDataService:
    """Service for managing Ubiquiti device analysis data."""

    def __init__(self):
        self.device_analysis_repo = DeviceAnalysisRepository()
        self.scan_result_repo = ScanResultRepository()
        self.frequency_change_repo = FrequencyChangeRepository()

    def save_device_analysis(self, complete_data: Dict[str, Any], llm_analysis: Dict[str, Any]) -> DeviceAnalysis:
        """Save a complete device analysis to the database."""
        
        # Extract data with defaults and safe access
        device_info = complete_data.get('device_info', {})
        ap_info = complete_data.get('ap_info', {})
        connectivity = complete_data.get('connectivity', {})
        lan_info = complete_data.get('lan_info', {})
        scan_results = complete_data.get('scan_results', {})
        capacity = complete_data.get('capacity', {})
        link_quality = complete_data.get('link_quality', {}) or {}
        
        # Prepare analysis data with proper defaults
        analysis_data = {
            'device_ip': device_info.get('ip'),
            'device_mac': device_info.get('mac', '00:00:00:00:00:00'),
            'device_name': device_info.get('name', 'Unknown'),
            'device_model': device_info.get('model', 'Unknown'),
            'identified_model': device_info.get('identified_model', 'unknown'),
            'signal_dbm': device_info.get('signal_dbm'),
            'frequency_mhz': device_info.get('frequency_mhz'),
            'cpu_percent': device_info.get('cpu_percent') or 0.0,
            'ram_percent': device_info.get('ram_percent') or 0.0,
            'ap_name': ap_info.get('name'),
            'ap_model': ap_info.get('model'),
            'ap_ip': ap_info.get('ip'),
            'ap_mac': ap_info.get('mac'),
            'ap_site_name': ap_info.get('site_name'),
            'ap_total_clients': ap_info.get('total_clients') or 0,
            'ap_active_clients': ap_info.get('active_clients') or 0,
            'downlink_capacity_mbps': capacity.get('downlink_mbps'),
            'uplink_capacity_mbps': capacity.get('uplink_mbps'),
            'downlink_utilization_percent': ap_info.get('downlink_utilization') or 0.0,
            'uplink_utilization_percent': ap_info.get('uplink_utilization') or 0.0,
            'overall_score': str(link_quality.get('overall_score') or 'unknown'),
            'uplink_score': str(link_quality.get('uplink_score') or 'unknown'),
            'downlink_score': str(link_quality.get('downlink_score') or 'unknown'),
            'ping_avg_ms': connectivity.get('ping_avg_ms'),
            'packet_loss': connectivity.get('packet_loss'),
            'ping_status': connectivity.get('ping_status') or 'unknown',
            'lan_ip_address': lan_info.get('ip_address'),
            'lan_interface_id': lan_info.get('interface_id'),
            'lan_available_speed': lan_info.get('available_speed'),
            'total_scanned_aps': scan_results.get('total_aps') or 0,
            'our_aps_count': scan_results.get('our_aps_count') or 0,
            'foreign_aps_count': scan_results.get('foreign_aps_count') or 0,
            'llm_summary': llm_analysis.get('summary'),
            'llm_recommendations': json.dumps(llm_analysis.get('recommendations', [])),
            'llm_diagnosis': llm_analysis.get('diagnosis') or 'No diagnosis provided',
            'analysis_date': now_argentina(),
            'needs_frequency_enable': llm_analysis.get('needs_frequency_enable', False),
            'next_action': llm_analysis.get('next_action') or 'no_action',
            'complete_data_json': json.dumps(complete_data)
        }
        
        # Create analysis
        analysis = self.device_analysis_repo.create_analysis(analysis_data)
        
        # Save scan results if available
        our_aps = scan_results.get('our_aps', [])
        for ap in our_aps:
            scan_data = {
                'device_analysis_id': analysis.id,
                'bssid': ap.get('bssid'),
                'ssid': ap.get('ssid'),
                'signal_dbm': ap.get('signal_dbm'),
                'channel': ap.get('channel'),
                'frequency_mhz': ap.get('frequency_mhz'),
                'quality': ap.get('quality'),
                'encrypted': ap.get('encrypted'),
                'is_our_ap': ap.get('is_our_ap'),
                'ap_name': ap.get('ap_name'),
                'ap_model': ap.get('ap_model'),
                'ap_ip': ap.get('ap_ip'),
                'ap_site': ap.get('ap_site'),
                'current_clients': ap.get('current_clients'),
                'scan_date': now_argentina()
            }
            self.scan_result_repo.create_scan_result(scan_data)
        
        return analysis

    def get_device_history(self, device_ip: str, limit: int = 10) -> List[DeviceAnalysis]:
        """Get analysis history for a device."""
        return self.device_analysis_repo.get_analysis_by_device_ip(device_ip)[:limit]

    def get_latest_analysis(self, device_ip: str) -> Optional[DeviceAnalysis]:
        """Get the latest analysis for a device."""
        return self.device_analysis_repo.get_latest_analysis_by_device_ip(device_ip)

    def save_frequency_change(self, device_ip: str, device_mac: str, device_model: str, 
                            operation_type: str, frequency_band: str, operation_status: str,
                            ssh_username: str, ssh_result: str = None, ssh_error: str = None) -> FrequencyChange:
        """Save a frequency change operation."""
        
        change_data = {
            'device_ip': device_ip,
            'device_mac': device_mac,
            'device_model': device_model,
            'operation_type': operation_type,
            'frequency_band': frequency_band,
            'operation_status': operation_status,
            'ssh_username': ssh_username,
            'ssh_result': ssh_result,
            'ssh_error': ssh_error,
            'operation_date': now_argentina(),
            'triggered_by': 'system'
        }
        
        return self.frequency_change_repo.create_frequency_change(change_data)

    def get_frequency_history(self, device_ip: str) -> List[FrequencyChange]:
        """Get frequency change history for a device."""
        return self.frequency_change_repo.get_frequency_changes_by_device_ip(device_ip)

    def get_device_statistics(self, device_ip: str) -> Dict[str, Any]:
        """Get statistics for a device."""
        latest_analysis = self.get_latest_analysis(device_ip)
        if not latest_analysis:
            return {}
        
        history = self.get_device_history(device_ip)
        frequency_changes = self.get_frequency_history(device_ip)
        
        return {
            'latest_analysis': {
                'date': latest_analysis.analysis_date,
                'status': latest_analysis.analysis_status,
                'signal': latest_analysis.signal_dbm,
                'ping_avg_ms': latest_analysis.ping_avg_ms,
                'packet_loss': latest_analysis.packet_loss,
                'ap_name': latest_analysis.ap_name,
                'ap_clients': latest_analysis.ap_total_clients
            },
            'total_analyses': len(history),
            'total_frequency_changes': len(frequency_changes),
            'last_frequency_change': frequency_changes[0].operation_date if frequency_changes else None
        }
