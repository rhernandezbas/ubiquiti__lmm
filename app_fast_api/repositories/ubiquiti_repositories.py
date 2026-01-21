"""Repositories for Ubiquiti monitoring data."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import and_, desc

from app_fast_api.utils.database import SessionLocal
from app_fast_api.models.ubiquiti_monitoring.device_analysis import DeviceAnalysis, ScanResult, FrequencyChange
from app_fast_api.interfaces.ubiquiti_interfaces import IDeviceAnalysisRepository, IScanResultRepository, IFrequencyChangeRepository
from app_fast_api.schema.ubiquiti_schemas import device_analysis_schema, scan_result_schema, frequency_change_schema
from marshmallow import ValidationError


class DeviceAnalysisRepository(IDeviceAnalysisRepository):
    """Device analysis repository."""

    def create_analysis(self, analysis_data: dict) -> DeviceAnalysis:
        """Create a new device analysis."""
        try:
            validated_data = device_analysis_schema.load(analysis_data)
            
            # Create SQLAlchemy model instance
            analysis = DeviceAnalysis(**validated_data)
            
            # Save to database
            db = SessionLocal()
            try:
                db.add(analysis)
                db.commit()
                db.refresh(analysis)
                return analysis
            finally:
                db.close()
                
        except ValidationError as e:
            raise ValueError(f"Validation error: {e.messages}") from e
        except Exception as e:
            raise RuntimeError(f"Database error: {str(e)}") from e

    def get_analysis_by_id(self, analysis_id: int) -> Optional[DeviceAnalysis]:
        """Get analysis by ID."""
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysis).filter_by(id=analysis_id).first()
        finally:
            db.close()

    def get_analysis_by_device_ip(self, device_ip: str) -> List[DeviceAnalysis]:
        """Get all analyses for a device IP."""
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysis).filter_by(device_ip=device_ip).order_by(desc(DeviceAnalysis.analysis_date)).all()
        finally:
            db.close()

    def get_latest_analysis_by_device_ip(self, device_ip: str) -> Optional[DeviceAnalysis]:
        """Get latest analysis for a device IP."""
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysis).filter_by(device_ip=device_ip).order_by(desc(DeviceAnalysis.analysis_date)).first()
        finally:
            db.close()

    def update_analysis(self, analysis_id: int, analysis_data: dict) -> Optional[DeviceAnalysis]:
        """Update an analysis."""
        db = SessionLocal()
        try:
            analysis = db.query(DeviceAnalysis).filter_by(id=analysis_id).first()
            if not analysis:
                raise ValueError(f"Analysis with id {analysis_id} not found")
            
            for key, value in analysis_data.items():
                setattr(analysis, key, value)
            db.commit()
            db.refresh(analysis)
            return analysis
        finally:
            db.close()

    def delete_analysis(self, analysis_id: int) -> None:
        """Delete an analysis."""
        db = SessionLocal()
        try:
            analysis = db.query(DeviceAnalysis).filter_by(id=analysis_id).first()
            if analysis:
                db.delete(analysis)
                db.commit()
            else:
                raise ValueError(f"Analysis with id {analysis_id} not found")
        finally:
            db.close()

    def get_analyses_by_date_range(self, start_date: datetime, end_date: datetime) -> List[DeviceAnalysis]:
        """Get analyses within a date range."""
        db = SessionLocal()
        try:
            return db.query(DeviceAnalysis).filter(
                and_(
                    DeviceAnalysis.analysis_date >= start_date,
                    DeviceAnalysis.analysis_date <= end_date
                )
            ).order_by(desc(DeviceAnalysis.analysis_date)).all()
        finally:
            db.close()


class ScanResultRepository(IScanResultRepository):
    """Scan result repository."""

    def create_scan_result(self, scan_data: dict) -> ScanResult:
        """Create a new scan result."""
        try:
            validated_data = scan_result_schema.load(scan_data)
            
            # Create SQLAlchemy model instance
            scan_result = ScanResult(**validated_data)
            
            # Save to database
            db = SessionLocal()
            try:
                db.add(scan_result)
                db.commit()
                db.refresh(scan_result)
                return scan_result
            finally:
                db.close()
                
        except ValidationError as e:
            raise ValueError(f"Validation error: {e.messages}") from e
        except Exception as e:
            raise RuntimeError(f"Database error: {str(e)}") from e

    def get_scan_results_by_analysis_id(self, analysis_id: int) -> List[ScanResult]:
        """Get all scan results for an analysis."""
        db = SessionLocal()
        try:
            return db.query(ScanResult).filter_by(device_analysis_id=analysis_id).all()
        finally:
            db.close()

    def get_scan_results_by_device_ip(self, device_ip: str) -> List[ScanResult]:
        """Get all scan results for a device IP."""
        db = SessionLocal()
        try:
            return db.query(ScanResult).join(DeviceAnalysis).filter(DeviceAnalysis.device_ip == device_ip).all()
        finally:
            db.close()

    def get_our_aps_only(self, analysis_id: int) -> List[ScanResult]:
        """Get only our APs from scan results."""
        db = SessionLocal()
        try:
            return db.query(ScanResult).filter(
                and_(
                    ScanResult.device_analysis_id == analysis_id,
                    ScanResult.is_our_ap == True
                )
            ).all()
        finally:
            db.close()

    def delete_scan_results_by_analysis_id(self, analysis_id: int) -> None:
        """Delete all scan results for an analysis."""
        db = SessionLocal()
        try:
            scan_results = self.get_scan_results_by_analysis_id(analysis_id)
            for scan_result in scan_results:
                db.delete(scan_result)
            db.commit()
        finally:
            db.close()


class FrequencyChangeRepository(IFrequencyChangeRepository):
    """Frequency change repository."""

    def create_frequency_change(self, change_data: dict) -> FrequencyChange:
        """Create a new frequency change record."""
        try:
            validated_data = frequency_change_schema.load(change_data)
            
            # Create SQLAlchemy model instance
            frequency_change = FrequencyChange(**validated_data)
            
            # Save to database
            db = SessionLocal()
            try:
                db.add(frequency_change)
                db.commit()
                db.refresh(frequency_change)
                return frequency_change
            finally:
                db.close()
                
        except ValidationError as e:
            raise ValueError(f"Validation error: {e.messages}") from e
        except Exception as e:
            raise RuntimeError(f"Database error: {str(e)}") from e

    def get_frequency_changes_by_device_ip(self, device_ip: str) -> List[FrequencyChange]:
        """Get all frequency changes for a device IP."""
        db = SessionLocal()
        try:
            return db.query(FrequencyChange).filter_by(device_ip=device_ip).order_by(desc(FrequencyChange.operation_date)).all()
        finally:
            db.close()

    def get_latest_frequency_change(self, device_ip: str) -> Optional[FrequencyChange]:
        """Get latest frequency change for a device IP."""
        db = SessionLocal()
        try:
            return db.query(FrequencyChange).filter_by(device_ip=device_ip).order_by(desc(FrequencyChange.operation_date)).first()
        finally:
            db.close()

    def update_frequency_change_status(self, change_id: int, status: str) -> Optional[FrequencyChange]:
        """Update frequency change status."""
        db = SessionLocal()
        try:
            change = db.query(FrequencyChange).filter_by(id=change_id).first()
            if not change:
                raise ValueError(f"Frequency change with id {change_id} not found")
            
            change.operation_status = status
            db.commit()
            db.refresh(change)
            return change
        finally:
            db.close()

    def get_frequency_changes_by_date_range(self, start_date: datetime, end_date: datetime) -> List[FrequencyChange]:
        """Get frequency changes within a date range."""
        db = SessionLocal()
        try:
            return db.query(FrequencyChange).filter(
                and_(
                    FrequencyChange.operation_date >= start_date,
                    FrequencyChange.operation_date <= end_date
                )
            ).order_by(desc(FrequencyChange.operation_date)).all()
        finally:
            db.close()
