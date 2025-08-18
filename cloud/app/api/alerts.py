"""
Alerts API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import Optional, List
from pydantic import BaseModel

from app.db import get_session
from app.db.repo import CloudRepository
from app.db.models import AlertResponse, AlertSeverity
from app.security.jwt import get_current_user


router = APIRouter(prefix="/api", tags=["alerts"])


class AcknowledgeAlertRequest(BaseModel):
    """Request model for acknowledging alerts"""
    acknowledged_by: str


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    limit: Optional[int] = Query(100, le=1000, description="Maximum number of alerts"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get alerts with filtering
    
    Args:
        session: Database session
        current_user: Authenticated user
        sensor_id: Optional sensor ID filter
        severity: Optional severity filter
        acknowledged: Optional acknowledgment filter
        limit: Maximum alerts to return
        offset: Pagination offset
        
    Returns:
        List of alerts
    """
    try:
        repo = CloudRepository(session)
        
        alerts = repo.get_alerts(
            sensor_id=sensor_id,
            severity=severity,
            acknowledged=acknowledged,
            limit=limit,
            offset=offset
        )
        
        return [AlertResponse(**alert.dict()) for alert in alerts]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {e}")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    request: AcknowledgeAlertRequest,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user)
):
    """
    Acknowledge an alert
    
    Args:
        alert_id: Alert ID to acknowledge
        request: Acknowledgment request
        session: Database session
        current_user: Authenticated user
        
    Returns:
        Acknowledgment result
    """
    try:
        repo = CloudRepository(session)
        
        success = repo.acknowledge_alert(alert_id, request.acknowledged_by)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "status": "success",
            "message": "Alert acknowledged successfully",
            "alert_id": alert_id,
            "acknowledged_by": request.acknowledged_by
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {e}")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user)
):
    """
    Resolve an alert
    
    Args:
        alert_id: Alert ID to resolve
        session: Database session
        current_user: Authenticated user
        
    Returns:
        Resolution result
    """
    try:
        repo = CloudRepository(session)
        
        success = repo.resolve_alert(alert_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return {
            "status": "success",
            "message": "Alert resolved successfully",
            "alert_id": alert_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving alert: {e}")


@router.get("/alerts/summary")
async def get_alerts_summary(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user)
):
    """
    Get alerts summary for dashboard
    
    Args:
        session: Database session
        current_user: Authenticated user
        
    Returns:
        Alerts summary
    """
    try:
        repo = CloudRepository(session)
        
        # Get alerts by severity
        critical_alerts = repo.get_alerts(severity=AlertSeverity.CRITICAL, limit=1000)
        high_alerts = repo.get_alerts(severity=AlertSeverity.HIGH, limit=1000)
        medium_alerts = repo.get_alerts(severity=AlertSeverity.MEDIUM, limit=1000)
        low_alerts = repo.get_alerts(severity=AlertSeverity.LOW, limit=1000)
        
        # Get recent unacknowledged alerts
        recent_alerts = repo.get_alerts(acknowledged=False, limit=10)
        
        return {
            "total_alerts": len(critical_alerts) + len(high_alerts) + len(medium_alerts) + len(low_alerts),
            "critical_alerts": len(critical_alerts),
            "high_alerts": len(high_alerts),
            "medium_alerts": len(medium_alerts),
            "low_alerts": len(low_alerts),
            "unacknowledged_alerts": len(recent_alerts),
            "recent_alerts": [AlertResponse(**alert.dict()) for alert in recent_alerts[:5]]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts summary: {e}")


@router.get("/alerts/by-sensor")
async def get_alerts_by_sensor(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user)
):
    """
    Get alerts grouped by sensor
    
    Args:
        session: Database session
        current_user: Authenticated user
        
    Returns:
        Alerts grouped by sensor
    """
    try:
        repo = CloudRepository(session)
        
        # Get all alerts
        all_alerts = repo.get_alerts(limit=10000)
        
        # Group by sensor
        sensor_alerts = {}
        for alert in all_alerts:
            if alert.sensor_id not in sensor_alerts:
                sensor_alerts[alert.sensor_id] = {
                    "sensor_id": alert.sensor_id,
                    "total_alerts": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "unacknowledged": 0,
                    "recent_alerts": []
                }
            
            sensor_data = sensor_alerts[alert.sensor_id]
            sensor_data["total_alerts"] += 1
            sensor_data[alert.severity.value] += 1
            
            if not alert.is_acknowledged:
                sensor_data["unacknowledged"] += 1
            
            # Keep recent alerts (limit to 3 per sensor)
            if len(sensor_data["recent_alerts"]) < 3:
                sensor_data["recent_alerts"].append(AlertResponse(**alert.dict()))
        
        return list(sensor_alerts.values())
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts by sensor: {e}")


@router.get("/alerts/count")
async def get_alerts_count(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status")
):
    """
    Get count of alerts
    
    Args:
        session: Database session
        current_user: Authenticated user
        sensor_id: Optional sensor ID filter
        severity: Optional severity filter
        acknowledged: Optional acknowledgment filter
        
    Returns:
        Alert count
    """
    try:
        repo = CloudRepository(session)
        
        alerts = repo.get_alerts(
            sensor_id=sensor_id,
            severity=severity,
            acknowledged=acknowledged,
            limit=100000  # High limit to count all
        )
        
        return {
            "count": len(alerts),
            "sensor_id": sensor_id,
            "severity": severity.value if severity else None,
            "acknowledged": acknowledged
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting alerts: {e}")