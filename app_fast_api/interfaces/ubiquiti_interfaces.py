"""Interfaces for Ubiquiti monitoring repositories."""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from app_fast_api.models.ubiquiti_monitoring.device_analysis import DeviceAnalysis, ScanResult, FrequencyChange


class IDeviceAnalysisRepository(ABC):
    """Interface for the DeviceAnalysis repository."""

    @abstractmethod
    def create_analysis(self, analysis_data: dict) -> DeviceAnalysis:
        """Create a new device analysis."""
        pass  # pragma: no cover

    @abstractmethod
    def get_analysis_by_id(self, analysis_id: int) -> Optional[DeviceAnalysis]:
        """Get analysis by ID."""
        pass  # pragma: no cover

    @abstractmethod
    def get_analysis_by_device_ip(self, device_ip: str) -> List[DeviceAnalysis]:
        """Get all analyses for a device IP."""
        pass  # pragma: no cover

    @abstractmethod
    def get_latest_analysis_by_device_ip(self, device_ip: str) -> Optional[DeviceAnalysis]:
        """Get latest analysis for a device IP."""
        pass  # pragma: no cover

    @abstractmethod
    def update_analysis(self, analysis_id: int, analysis_data: dict) -> Optional[DeviceAnalysis]:
        """Update an analysis."""
        pass  # pragma: no cover

    @abstractmethod
    def delete_analysis(self, analysis_id: int) -> None:
        """Delete an analysis."""
        pass  # pragma: no cover

    @abstractmethod
    def get_analyses_by_date_range(self, start_date: datetime, end_date: datetime) -> List[DeviceAnalysis]:
        """Get analyses within a date range."""
        pass  # pragma: no cover


class IScanResultRepository(ABC):
    """Interface for the ScanResult repository."""

    @abstractmethod
    def create_scan_result(self, scan_data: dict) -> ScanResult:
        """Create a new scan result."""
        pass  # pragma: no cover

    @abstractmethod
    def get_scan_results_by_analysis_id(self, analysis_id: int) -> List[ScanResult]:
        """Get all scan results for an analysis."""
        pass  # pragma: no cover

    @abstractmethod
    def get_scan_results_by_device_ip(self, device_ip: str) -> List[ScanResult]:
        """Get all scan results for a device IP."""
        pass  # pragma: no cover

    @abstractmethod
    def get_our_aps_only(self, analysis_id: int) -> List[ScanResult]:
        """Get only our APs from scan results."""
        pass  # pragma: no cover

    @abstractmethod
    def delete_scan_results_by_analysis_id(self, analysis_id: int) -> None:
        """Delete all scan results for an analysis."""
        pass  # pragma: no cover


class IFrequencyChangeRepository(ABC):
    """Interface for the FrequencyChange repository."""

    @abstractmethod
    def create_frequency_change(self, change_data: dict) -> FrequencyChange:
        """Create a new frequency change record."""
        pass  # pragma: no cover

    @abstractmethod
    def get_frequency_changes_by_device_ip(self, device_ip: str) -> List[FrequencyChange]:
        """Get all frequency changes for a device IP."""
        pass  # pragma: no cover

    @abstractmethod
    def get_latest_frequency_change(self, device_ip: str) -> Optional[FrequencyChange]:
        """Get latest frequency change for a device IP."""
        pass  # pragma: no cover

    @abstractmethod
    def update_frequency_change_status(self, change_id: int, status: str) -> Optional[FrequencyChange]:
        """Update frequency change status."""
        pass  # pragma: no cover

    @abstractmethod
    def get_frequency_changes_by_date_range(self, start_date: datetime, end_date: datetime) -> List[FrequencyChange]:
        """Get frequency changes within a date range."""
        pass  # pragma: no cover
