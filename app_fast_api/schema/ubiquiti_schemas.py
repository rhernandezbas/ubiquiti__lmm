"""Schemas for Ubiquiti monitoring models."""

from marshmallow import Schema, fields, validate
from datetime import datetime


class DeviceAnalysisSchema(Schema):
    """Schema for the DeviceAnalysis model."""
    
    id = fields.Integer(dump_only=True)
    device_ip = fields.String(required=True)
    device_mac = fields.String(required=True)
    device_name = fields.String()
    device_model = fields.String()
    identified_model = fields.String()
    
    # Device metrics
    signal_dbm = fields.Integer()
    frequency_mhz = fields.Integer()
    cpu_percent = fields.Float()
    ram_percent = fields.Float()
    
    # AP information
    ap_name = fields.String()
    ap_model = fields.String()
    ap_ip = fields.String()
    ap_mac = fields.String()
    ap_site_name = fields.String()
    ap_total_clients = fields.Integer()
    ap_active_clients = fields.Integer()
    
    # Capacity and performance
    downlink_capacity_mbps = fields.Float()
    uplink_capacity_mbps = fields.Float()
    downlink_utilization_percent = fields.Float()
    uplink_utilization_percent = fields.Float()
    
    # Link quality
    overall_score = fields.String()
    uplink_score = fields.String()
    downlink_score = fields.String()
    
    # Connectivity
    ping_avg_ms = fields.Float()
    packet_loss = fields.Float()
    ping_status = fields.String()
    
    # LAN information
    lan_ip_address = fields.String()
    lan_interface_id = fields.String()
    lan_available_speed = fields.String()
    
    # Scan results
    total_scanned_aps = fields.Integer()
    our_aps_count = fields.Integer()
    foreign_aps_count = fields.Integer()
    
    # LLM analysis
    llm_summary = fields.String()
    llm_recommendations = fields.String()
    llm_diagnosis = fields.String()
    
    # Metadata
    analysis_date = fields.DateTime(required=True)
    analysis_status = fields.String()
    needs_frequency_enable = fields.Boolean()
    next_action = fields.String()
    
    complete_data_json = fields.String()


class ScanResultSchema(Schema):
    """Schema for the ScanResult model."""
    
    id = fields.Integer(dump_only=True)
    device_analysis_id = fields.Integer(required=True)
    
    # AP information
    bssid = fields.String(required=True)
    ssid = fields.String()
    signal_dbm = fields.Integer()
    channel = fields.Integer(required=False, allow_none=True)  # Explícitamente no requerido y permite None
    frequency_mhz = fields.Integer()
    quality = fields.Integer()
    encrypted = fields.Boolean()
    
    # Classification
    is_our_ap = fields.Boolean()
    ap_name = fields.String()
    ap_model = fields.String()
    ap_ip = fields.String()
    ap_site = fields.String()
    current_clients = fields.Integer()
    
    # Match information
    match_type = fields.String()
    match_reason = fields.String()
    confidence = fields.String()
    
    scan_date = fields.DateTime()  # No es dump_only, puede guardar


class FrequencyChangeSchema(Schema):
    """Schema for the FrequencyChange model."""
    
    id = fields.Integer(dump_only=True)
    device_ip = fields.String(required=True)
    device_mac = fields.String(required=True)
    device_model = fields.String()
    
    # Operation details
    operation_type = fields.String()
    frequency_band = fields.String()
    operation_status = fields.String()
    
    # SSH connection details
    ssh_username = fields.String()
    ssh_result = fields.String()
    ssh_error = fields.String()
    
    # Metadata
    operation_date = fields.DateTime(dump_only=True)
    triggered_by = fields.String()
    analysis_id = fields.Integer()


# Schema instances
device_analysis_schema = DeviceAnalysisSchema()
devices_analysis_schema = DeviceAnalysisSchema(many=True)

scan_result_schema = ScanResultSchema()
scan_results_schema = ScanResultSchema(many=True)

frequency_change_schema = FrequencyChangeSchema()
frequency_changes_schema = FrequencyChangeSchema(many=True)
