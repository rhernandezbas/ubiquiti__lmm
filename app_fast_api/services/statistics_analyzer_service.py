"""
Service for analyzing UISP device statistics timeseries data
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app_fast_api.utils.logger import get_logger
from app_fast_api.utils.timezone import now_argentina

logger = get_logger(__name__)


class StatisticsAnalyzerService:
    """Analyzes UISP statistics timeseries to detect outages, degradation, and patterns."""

    @staticmethod
    def analyze_signal_timeseries(statistics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze signal strength over time to detect degradation or drops.

        Args:
            statistics: UISP statistics response with timeseries data

        Returns:
            Dictionary with signal analysis: current, min, max, avg, drops_detected
        """
        if not statistics:
            return {"error": "No statistics data provided"}

        if not isinstance(statistics, dict):
            logger.warning(f"Statistics is not a dict, got: {type(statistics)}")
            return {"error": f"Invalid statistics format: {type(statistics)}"}

        signal_data = statistics.get('signal', [])
        if not signal_data:
            return {"error": "No signal data in statistics"}

        # DEBUG: Log the actual structure
        logger.info(f"🔍 Signal data type: {type(signal_data)}")
        logger.info(f"🔍 Signal data keys (if dict): {signal_data.keys() if isinstance(signal_data, dict) else 'N/A'}")
        logger.info(f"🔍 Signal data sample: {str(signal_data)[:500]}")

        # Extract signal values and timestamps
        signal_values = []
        timestamps = []

        # Handle both list and dict formats
        if isinstance(signal_data, dict):
            # Check if it's UISP format: {"avg": [...], "max": [...]}
            if 'avg' in signal_data or 'max' in signal_data:
                # Use 'avg' if available, otherwise 'max'
                data_points = signal_data.get('avg') or signal_data.get('max', [])
                logger.info(f"✅ Found UISP format (avg/max): {len(data_points)} points")

                # Extract values from list of {"x": timestamp, "y": value}
                for point in data_points:
                    if isinstance(point, dict):
                        x_val = point.get('x')
                        y_val = point.get('y')
                        if y_val is not None:
                            signal_values.append(y_val)
                        if x_val is not None:
                            timestamps.append(x_val)

                logger.info(f"✅ Extracted {len(signal_values)} signal values from UISP format")
            # Check if it's x/y format: {"x": [...], "y": [...]}
            elif 'x' in signal_data and 'y' in signal_data:
                timestamps = signal_data.get('x', [])
                y_data = signal_data.get('y', [])

                if isinstance(y_data, list):
                    signal_values = y_data
                elif isinstance(y_data, dict):
                    signal_values = list(y_data.values())
                else:
                    signal_values = [y_data]

                logger.info(f"✅ Found x/y format: {len(signal_values)} values")
            else:
                # Format: {timestamp: value, timestamp: value, ...}
                timestamps = list(signal_data.keys())
                signal_values = list(signal_data.values())
                logger.info(f"✅ Found key-value format: {len(signal_values)} values")
        elif isinstance(signal_data, list):
            logger.info(f"✅ Found list format with {len(signal_data)} items")
            for point in signal_data:
                if isinstance(point, dict):
                    y_val = point.get('y')
                    x_val = point.get('x')
                    if y_val is not None:
                        signal_values.append(y_val)
                    if x_val is not None:
                        timestamps.append(x_val)
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    # Si el formato es [x, y] en lugar de {"x": ..., "y": ...}
                    timestamps.append(point[0])
                    signal_values.append(point[1])
                else:
                    logger.debug(f"Skipping invalid point format: {type(point)}")

        if not signal_values:
            return {"error": "No valid signal values found"}

        # DEBUG: Check what we got
        logger.info(f"🔍 signal_values before validation: {type(signal_values)}")
        logger.info(f"🔍 First few values: {signal_values[:3] if len(signal_values) > 0 else 'empty'}")
        logger.info(f"🔍 First value type: {type(signal_values[0]) if signal_values else 'empty'}")

        # Validate that signal_values contains numbers
        try:
            cleaned_values = []

            for v in signal_values:
                if v is None:
                    continue
                # If it's a dict, try to extract a numeric value
                elif isinstance(v, dict):
                    # Try common keys: 'value', 'y', 'val', or first numeric value
                    extracted = v.get('value') or v.get('y') or v.get('val')
                    if extracted is None:
                        # Get first numeric value from dict
                        for dict_val in v.values():
                            try:
                                cleaned_values.append(float(dict_val))
                                break
                            except (TypeError, ValueError):
                                continue
                    else:
                        cleaned_values.append(float(extracted))
                # If it's a list, flatten it
                elif isinstance(v, list):
                    for item in v:
                        try:
                            cleaned_values.append(float(item))
                        except (TypeError, ValueError):
                            continue
                # If it's already numeric, use it
                else:
                    try:
                        cleaned_values.append(float(v))
                    except (TypeError, ValueError):
                        logger.warning(f"⚠️ Skipping non-numeric value: {v} (type: {type(v)})")
                        continue

            signal_values = cleaned_values
            logger.info(f"✅ Converted {len(signal_values)} signal values to float")
        except (TypeError, ValueError) as e:
            logger.error(f"❌ Invalid signal values: {e}")
            logger.error(f"❌ signal_values content: {signal_values[:5]}")
            return {"error": f"Signal values are not numeric: {type(signal_values[0]) if signal_values else 'empty'}"}

        if not signal_values:
            return {"error": "No numeric signal values after validation"}

        # Calculate metrics
        current_signal = signal_values[-1] if signal_values else None
        min_signal = min(signal_values)
        max_signal = max(signal_values)
        avg_signal = sum(signal_values) / len(signal_values)

        # Detect signal drops (>10 dBm drop from average)
        drops = []
        for i, signal in enumerate(signal_values):
            if signal < (avg_signal - 10):
                drops.append({
                    "timestamp": timestamps[i] if i < len(timestamps) else None,
                    "signal_dbm": signal,
                    "drop_magnitude": avg_signal - signal
                })

        return {
            "current_signal_dbm": round(current_signal, 2) if current_signal else None,
            "min_signal_dbm": round(min_signal, 2),
            "max_signal_dbm": round(max_signal, 2),
            "avg_signal_dbm": round(avg_signal, 2),
            "signal_stability": "stable" if (max_signal - min_signal) < 10 else "unstable",
            "drops_detected": len(drops),
            "drop_events": drops[:5],  # Last 5 drops
            "data_points": len(signal_values)
        }

    @staticmethod
    def analyze_outages(statistics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect outages or connectivity issues from statistics.

        Args:
            statistics: UISP statistics response

        Returns:
            Dictionary with outage analysis
        """
        if not statistics or not isinstance(statistics, dict):
            return {"error": "No statistics data provided"}

        # Check for signal drops to 0 or missing data
        signal_data = statistics.get('signal', [])
        if not signal_data:
            return {"error": "No signal data"}

        outages = []

        # Handle dict format: {"x": [...], "y": [...]} or {timestamp: value, ...}
        if isinstance(signal_data, dict):
            if 'x' in signal_data and 'y' in signal_data:
                timestamps = signal_data.get('x', [])
                values = signal_data.get('y', [])
                for timestamp, signal in zip(timestamps, values):
                    if signal is None or signal == 0:
                        outages.append({"timestamp": timestamp, "type": "signal_loss"})
            else:
                for timestamp, signal in signal_data.items():
                    if signal is None or signal == 0:
                        outages.append({"timestamp": timestamp, "type": "signal_loss"})
        elif isinstance(signal_data, list):
            for i, point in enumerate(signal_data):
                signal = None
                timestamp = None

                if isinstance(point, dict):
                    signal = point.get('y')
                    timestamp = point.get('x')
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    timestamp = point[0]
                    signal = point[1]
                else:
                    continue

                if signal is None or signal == 0:
                    outages.append({"timestamp": timestamp, "type": "signal_loss"})
        else:
            return {"error": f"Invalid signal data format: {type(signal_data)}"}

            # Detect outage: signal = 0 or None
            if signal is None or signal == 0:
                outages.append({
                    "timestamp": timestamp,
                    "type": "signal_loss"
                })

        # Group consecutive outages
        outage_periods = []
        if outages:
            current_period = {"start": outages[0]["timestamp"], "end": outages[0]["timestamp"], "count": 1}
            for outage in outages[1:]:
                # If within 5 minutes of last outage, extend period
                if outage["timestamp"] - current_period["end"] < 300000:  # 5 min in ms
                    current_period["end"] = outage["timestamp"]
                    current_period["count"] += 1
                else:
                    outage_periods.append(current_period)
                    current_period = {"start": outage["timestamp"], "end": outage["timestamp"], "count": 1}
            outage_periods.append(current_period)

        return {
            "total_outage_points": len(outages),
            "outage_periods": len(outage_periods),
            "outage_details": outage_periods[:5],  # Last 5 periods
            "has_recent_outage": len(outages) > 0 and (now_argentina().timestamp() * 1000 - outages[-1]["timestamp"]) < 3600000  # Within 1 hour
        }

    @staticmethod
    def analyze_capacity_timeseries(statistics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze capacity/throughput over time.

        Args:
            statistics: UISP statistics response

        Returns:
            Dictionary with capacity analysis
        """
        if not statistics:
            return {"error": "No statistics data provided"}

        # Analyze downlink and uplink capacity
        downlink_data = statistics.get('downlinkCapacity', [])
        uplink_data = statistics.get('uplinkCapacity', [])

        def analyze_metric(data, metric_name: str) -> Dict[str, Any]:
            if not data:
                return {f"{metric_name}_error": "No data available"}

            values = []

            # Handle dict format
            if isinstance(data, dict):
                # UISP format: {"avg": [...], "max": [...]}
                if 'avg' in data or 'max' in data:
                    data_points = data.get('avg') or data.get('max', [])
                    for point in data_points:
                        if isinstance(point, dict) and 'y' in point:
                            values.append(point['y'])
                # x/y format: {"x": [...], "y": [...]}
                elif 'x' in data and 'y' in data:
                    values = [v for v in data.get('y', []) if v is not None]
                else:
                    values = [v for v in data.values() if v is not None]
            # Handle list format
            elif isinstance(data, list):
                for point in data:
                    if isinstance(point, dict):
                        y_val = point.get('y')
                        if y_val is not None:
                            values.append(y_val)
                    elif isinstance(point, (list, tuple)) and len(point) >= 2:
                        values.append(point[1])
            else:
                return {f"{metric_name}_error": f"Invalid format: {type(data)}"}

            if not values:
                return {f"{metric_name}_error": "No valid values"}

            # Validate and convert to float (handle dicts, lists, nested structures)
            try:
                cleaned_values = []

                for v in values:
                    if v is None:
                        continue
                    elif isinstance(v, dict):
                        # Extract numeric value from dict
                        extracted = v.get('value') or v.get('y') or v.get('val')
                        if extracted is None:
                            for dict_val in v.values():
                                try:
                                    cleaned_values.append(float(dict_val))
                                    break
                                except (TypeError, ValueError):
                                    continue
                        else:
                            cleaned_values.append(float(extracted))
                    elif isinstance(v, list):
                        for item in v:
                            try:
                                cleaned_values.append(float(item))
                            except (TypeError, ValueError):
                                continue
                    else:
                        try:
                            cleaned_values.append(float(v))
                        except (TypeError, ValueError):
                            continue

                values = cleaned_values
                logger.info(f"✅ {metric_name}: Converted {len(values)} values to float")
            except (TypeError, ValueError) as e:
                logger.error(f"❌ {metric_name}: Invalid values - {e}")
                return {f"{metric_name}_error": f"Non-numeric values: {type(values[0]) if values else 'empty'}"}

            if not values:
                return {f"{metric_name}_error": "No numeric values after validation"}

            return {
                f"{metric_name}_current_mbps": round(values[-1], 2) if values else None,
                f"{metric_name}_min_mbps": round(min(values), 2),
                f"{metric_name}_max_mbps": round(max(values), 2),
                f"{metric_name}_avg_mbps": round(sum(values) / len(values), 2),
                f"{metric_name}_data_points": len(values)
            }

        downlink_analysis = analyze_metric(downlink_data, "downlink")
        uplink_analysis = analyze_metric(uplink_data, "uplink")

        return {
            **downlink_analysis,
            **uplink_analysis
        }

    @staticmethod
    def get_comprehensive_analysis(statistics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get comprehensive analysis of all statistics.

        Args:
            statistics: UISP statistics response

        Returns:
            Complete analysis with signal, outages, and capacity
        """
        return {
            "signal_analysis": StatisticsAnalyzerService.analyze_signal_timeseries(statistics),
            "outage_analysis": StatisticsAnalyzerService.analyze_outages(statistics),
            "capacity_analysis": StatisticsAnalyzerService.analyze_capacity_timeseries(statistics),
            "timestamp": now_argentina().isoformat()
        }
