"""
Telemetry readings API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import Optional, List
from datetime import datetime, timedelta

from app.db import get_session
from app.db.repo import CloudRepository
from app.db.models import TelemetryReadingResponse, SensorType
from app.security.jwt import get_current_user


router = APIRouter(prefix="/api", tags=["readings"])


@router.get("/readings", response_model=List[TelemetryReadingResponse])
async def get_readings(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    sensor_type: Optional[SensorType] = Query(None, description="Filter by sensor type"),
    hours: Optional[int] = Query(24, description="Hours of data to retrieve"),
    limit: Optional[int] = Query(1000, le=10000, description="Maximum number of readings"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get telemetry readings with filtering
    
    Args:
        session: Database session
        current_user: Authenticated user
        sensor_id: Optional sensor ID filter
        sensor_type: Optional sensor type filter
        hours: Hours of historical data
        limit: Maximum readings to return
        offset: Pagination offset
        
    Returns:
        List of telemetry readings
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        readings = repo.get_telemetry_readings(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        return [TelemetryReadingResponse(**reading.dict()) for reading in readings]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving readings: {e}")


@router.get("/readings/latest")
async def get_latest_readings(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user)
):
    """
    Get latest reading from each sensor
    
    Args:
        session: Database session
        current_user: Authenticated user
        
    Returns:
        Dictionary of latest readings by sensor
    """
    try:
        repo = CloudRepository(session)
        sensors = repo.get_sensors(active_only=True)
        
        latest_readings = {}
        for sensor in sensors:
            reading = repo.get_latest_reading(sensor.sensor_id)
            if reading:
                latest_readings[sensor.sensor_id] = TelemetryReadingResponse(**reading.dict())
        
        return latest_readings
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest readings: {e}")


@router.get("/readings/summary")
async def get_readings_summary(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    hours: Optional[int] = Query(24, description="Hours for summary period")
):
    """
    Get summary statistics for readings
    
    Args:
        session: Database session
        current_user: Authenticated user
        hours: Hours for summary period
        
    Returns:
        Summary statistics
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get sensor summaries
        sensor_summaries = repo.get_sensor_summaries()
        
        # Calculate totals
        total_readings = sum(s.reading_count_24h for s in sensor_summaries)
        total_alerts = sum(s.alert_count_24h for s in sensor_summaries)
        active_sensors = sum(1 for s in sensor_summaries if s.is_active)
        
        return {
            "period_hours": hours,
            "total_readings": total_readings,
            "total_alerts": total_alerts,
            "active_sensors": active_sensors,
            "sensors": sensor_summaries
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving summary: {e}")


@router.get("/readings/chart-data")
async def get_chart_data(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    sensor_id: Optional[str] = Query(None, description="Sensor ID for chart"),
    hours: Optional[int] = Query(24, description="Hours of data for chart"),
    resolution: Optional[str] = Query("hour", description="Data resolution (minute, hour, day)")
):
    """
    Get chart-ready telemetry data
    
    Args:
        session: Database session
        current_user: Authenticated user
        sensor_id: Optional sensor ID filter
        hours: Hours of data
        resolution: Time resolution for aggregation
        
    Returns:
        Chart data in format suitable for Chart.js
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get readings
        readings = repo.get_telemetry_readings(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000  # High limit for chart data
        )
        
        # Organize data by sensor and time
        chart_data = {
            "labels": [],
            "datasets": {}
        }
        
        # Group readings by sensor
        sensor_data = {}
        for reading in readings:
            if reading.sensor_id not in sensor_data:
                sensor_data[reading.sensor_id] = []
            sensor_data[reading.sensor_id].append(reading)
        
        # Create datasets for each sensor
        colors = {
            "temp-01": "rgb(255, 99, 132)",
            "humidity-01": "rgb(54, 162, 235)", 
            "wind-01": "rgb(75, 192, 192)"
        }
        
        for sensor_id, readings_list in sensor_data.items():
            # Sort by timestamp
            readings_list.sort(key=lambda r: r.timestamp)
            
            # Extract data points
            timestamps = [r.timestamp.isoformat() for r in readings_list]
            values = [r.value for r in readings_list]
            
            chart_data["datasets"][sensor_id] = {
                "label": f"{sensor_id} ({readings_list[0].sensor_type if readings_list else 'unknown'})",
                "data": [{"x": t, "y": v} for t, v in zip(timestamps, values)],
                "borderColor": colors.get(sensor_id, "rgb(128, 128, 128)"),
                "backgroundColor": colors.get(sensor_id, "rgba(128, 128, 128, 0.2)"),
                "fill": False,
                "tension": 0.1
            }
        
        return chart_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving chart data: {e}")


@router.get("/readings/count")
async def get_readings_count(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    hours: Optional[int] = Query(24, description="Hours to count")
):
    """
    Get count of telemetry readings
    
    Args:
        session: Database session
        current_user: Authenticated user
        sensor_id: Optional sensor ID filter
        hours: Hours to count
        
    Returns:
        Reading count
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        count = repo.get_readings_count(
            sensor_id=sensor_id,
            start_time=start_time,
            end_time=end_time
        )
        
        return {
            "count": count,
            "sensor_id": sensor_id,
            "period_hours": hours
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting readings: {e}")