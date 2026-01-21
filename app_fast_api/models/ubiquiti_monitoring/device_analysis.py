"""Models for Ubiquiti device monitoring data."""

from sqlalchemy import Column, BigInteger, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app_fast_api.utils.database import Base


class DeviceAnalysis(Base):
    """Model for device analysis results."""
    __tablename__ = 'device_analysis'

    id = Column(BigInteger, primary_key=True)
    device_ip = Column(String(45), nullable=False, index=True)
    device_mac = Column(String(17), nullable=False, index=True)
    device_name = Column(String(200))
    device_model = Column(String(100))
    identified_model = Column(String(50))  # ac, m5, m2, unknown
    
    # Device metrics
    signal_dbm = Column(Integer)
    frequency_mhz = Column(Integer)
    cpu_percent = Column(Float)
    ram_percent = Column(Float)
    
    # AP information
    ap_name = Column(String(200))
    ap_model = Column(String(100))
    ap_ip = Column(String(45))
    ap_mac = Column(String(17))
    ap_site_name = Column(String(200))
    ap_total_clients = Column(Integer)
    ap_active_clients = Column(Integer)
    
    # Capacity and performance
    downlink_capacity_mbps = Column(Float)
    uplink_capacity_mbps = Column(Float)
    downlink_utilization_percent = Column(Float)
    uplink_utilization_percent = Column(Float)
    
    # Link quality
    overall_score = Column(String(20))
    uplink_score = Column(String(20))
    downlink_score = Column(String(20))
    
    # Connectivity
    ping_avg_ms = Column(Float)
    packet_loss = Column(Float)
    ping_status = Column(String(20))
    
    # LAN information
    lan_ip_address = Column(String(45))
    lan_interface_id = Column(String(50))
    lan_available_speed = Column(String(100))
    
    # Scan results
    total_scanned_aps = Column(Integer, default=0)
    our_aps_count = Column(Integer, default=0)
    foreign_aps_count = Column(Integer, default=0)
    
    # LLM analysis
    llm_summary = Column(Text)
    llm_recommendations = Column(Text)
    llm_diagnosis = Column(Text)
    
    # Metadata
    analysis_date = Column(DateTime, nullable=False)
    analysis_status = Column(String(20), default='completed')
    needs_frequency_enable = Column(Boolean, default=False)
    next_action = Column(String(50))
    
    # Raw data (JSON)
    complete_data_json = Column(Text)  # Store complete_data as JSON
    
    # Relationships
    scan_results = relationship("ScanResult", back_populates="device_analysis", cascade="all, delete-orphan")
    frequency_changes = relationship("FrequencyChange", back_populates="analysis")
    
    def __repr__(self):
        return f'<DeviceAnalysis {self.device_ip} - {self.device_name}>'


class ScanResult(Base):
    """Model for AP scan results."""
    __tablename__ = 'scan_results'

    id = Column(BigInteger, primary_key=True)
    device_analysis_id = Column(BigInteger, ForeignKey('device_analysis.id'), nullable=False)
    
    # AP information
    bssid = Column(String(17), nullable=False)
    ssid = Column(String(200))
    signal_dbm = Column(Integer)
    channel = Column(Integer)
    frequency_mhz = Column(Integer)
    quality = Column(Integer)
    encrypted = Column(Boolean)
    
    # Classification
    is_our_ap = Column(Boolean, default=False)
    ap_name = Column(String(200))
    ap_model = Column(String(100))
    ap_ip = Column(String(45))
    ap_site = Column(String(200))
    current_clients = Column(Integer)
    
    # Match information
    match_type = Column(String(50))  # exact, ssid_partial, name_partial
    match_reason = Column(String(500))
    confidence = Column(String(20))  # high, medium, low
    
    scan_date = Column(DateTime, nullable=False)
    
    # Relationships
    device_analysis = relationship("DeviceAnalysis", back_populates="scan_results")
    
    def __repr__(self):
        return f'<ScanResult {self.bssid} - {self.ssid}>'


class FrequencyChange(Base):
    """Model for frequency enable/disable operations."""
    __tablename__ = 'frequency_changes'

    id = Column(BigInteger, primary_key=True)
    device_ip = Column(String(45), nullable=False)
    device_mac = Column(String(17), nullable=False)
    device_model = Column(String(50))
    
    # Operation details
    operation_type = Column(String(20))  # enable, disable
    frequency_band = Column(String(10))  # ac, m5, m2
    operation_status = Column(String(20))  # success, failed, pending
    
    # SSH connection details
    ssh_username = Column(String(100))
    ssh_result = Column(Text)
    ssh_error = Column(Text)
    
    # Metadata
    operation_date = Column(DateTime, nullable=False)
    triggered_by = Column(String(100))  # system, user
    analysis_id = Column(BigInteger, ForeignKey('device_analysis.id'))
    
    # Relationships
    analysis = relationship("DeviceAnalysis", back_populates="frequency_changes")
    
    def __repr__(self):
        return f'<FrequencyChange {self.device_ip} - {self.operation_type} {self.frequency_band}>'
