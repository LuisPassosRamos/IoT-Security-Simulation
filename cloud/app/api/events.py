"""
Events API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import Optional, List
from datetime import datetime, timedelta

from app.db import get_session
from app.db.repo import CloudRepository
from app.db.models import EventResponse, EventType
from app.security.jwt import get_current_user


router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events", response_model=List[EventResponse])
async def get_events(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    hours: Optional[int] = Query(24, description="Hours of events to retrieve"),
    limit: Optional[int] = Query(100, le=1000, description="Maximum number of events"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get system events with filtering
    
    Args:
        session: Database session
        current_user: Authenticated user
        event_type: Optional event type filter
        sensor_id: Optional sensor ID filter
        severity: Optional severity filter
        hours: Hours of historical events
        limit: Maximum events to return
        offset: Pagination offset
        
    Returns:
        List of events
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        events = repo.get_events(
            event_type=event_type,
            sensor_id=sensor_id,
            severity=severity,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        
        return [EventResponse(**event.dict()) for event in events]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events: {e}")


@router.get("/events/summary")
async def get_events_summary(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    hours: Optional[int] = Query(24, description="Hours for summary period")
):
    """
    Get events summary for dashboard
    
    Args:
        session: Database session
        current_user: Authenticated user
        hours: Hours for summary period
        
    Returns:
        Events summary
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get events by type
        all_events = repo.get_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Count by type
        event_counts = {}
        severity_counts = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        
        for event in all_events:
            event_type = event.event_type.value
            if event_type not in event_counts:
                event_counts[event_type] = 0
            event_counts[event_type] += 1
            
            if event.severity in severity_counts:
                severity_counts[event.severity] += 1
        
        # Get recent critical/error events
        critical_events = [e for e in all_events if e.severity in ["critical", "error"]][:10]
        
        return {
            "period_hours": hours,
            "total_events": len(all_events),
            "event_types": event_counts,
            "severity_counts": severity_counts,
            "recent_critical_events": [EventResponse(**event.dict()) for event in critical_events]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events summary: {e}")


@router.get("/events/timeline")
async def get_events_timeline(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    hours: Optional[int] = Query(24, description="Hours for timeline"),
    resolution: Optional[str] = Query("hour", description="Time resolution (hour, day)")
):
    """
    Get events timeline for visualization
    
    Args:
        session: Database session
        current_user: Authenticated user
        hours: Hours for timeline
        resolution: Time resolution
        
    Returns:
        Timeline data
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get events
        events = repo.get_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Group events by time buckets
        timeline_data = {}
        
        for event in events:
            # Create time bucket based on resolution
            if resolution == "hour":
                bucket = event.created_at.replace(minute=0, second=0, microsecond=0)
            else:  # day
                bucket = event.created_at.replace(hour=0, minute=0, second=0, microsecond=0)
            
            bucket_str = bucket.isoformat()
            
            if bucket_str not in timeline_data:
                timeline_data[bucket_str] = {
                    "timestamp": bucket_str,
                    "total_events": 0,
                    "by_type": {},
                    "by_severity": {"info": 0, "warning": 0, "error": 0, "critical": 0}
                }
            
            bucket_data = timeline_data[bucket_str]
            bucket_data["total_events"] += 1
            
            # Count by type
            event_type = event.event_type.value
            if event_type not in bucket_data["by_type"]:
                bucket_data["by_type"][event_type] = 0
            bucket_data["by_type"][event_type] += 1
            
            # Count by severity
            if event.severity in bucket_data["by_severity"]:
                bucket_data["by_severity"][event.severity] += 1
        
        # Sort by timestamp
        timeline = sorted(timeline_data.values(), key=lambda x: x["timestamp"])
        
        return {
            "timeline": timeline,
            "resolution": resolution,
            "period_hours": hours
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events timeline: {e}")


@router.get("/events/by-sensor")
async def get_events_by_sensor(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    hours: Optional[int] = Query(24, description="Hours for analysis")
):
    """
    Get events grouped by sensor
    
    Args:
        session: Database session
        current_user: Authenticated user
        hours: Hours for analysis
        
    Returns:
        Events grouped by sensor
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Get events
        events = repo.get_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        # Group by sensor
        sensor_events = {}
        system_events = []
        
        for event in events:
            if event.sensor_id:
                if event.sensor_id not in sensor_events:
                    sensor_events[event.sensor_id] = {
                        "sensor_id": event.sensor_id,
                        "total_events": 0,
                        "by_type": {},
                        "by_severity": {"info": 0, "warning": 0, "error": 0, "critical": 0},
                        "recent_events": []
                    }
                
                sensor_data = sensor_events[event.sensor_id]
                sensor_data["total_events"] += 1
                
                # Count by type
                event_type = event.event_type.value
                if event_type not in sensor_data["by_type"]:
                    sensor_data["by_type"][event_type] = 0
                sensor_data["by_type"][event_type] += 1
                
                # Count by severity
                if event.severity in sensor_data["by_severity"]:
                    sensor_data["by_severity"][event.severity] += 1
                
                # Keep recent events (limit to 5 per sensor)
                if len(sensor_data["recent_events"]) < 5:
                    sensor_data["recent_events"].append(EventResponse(**event.dict()))
            else:
                # System-wide event
                system_events.append(EventResponse(**event.dict()))
        
        return {
            "sensor_events": list(sensor_events.values()),
            "system_events": system_events[:10],  # Limit system events
            "period_hours": hours
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving events by sensor: {e}")


@router.get("/events/count")
async def get_events_count(
    session: Session = Depends(get_session),
    current_user: str = Depends(get_current_user),
    event_type: Optional[EventType] = Query(None, description="Filter by event type"),
    sensor_id: Optional[str] = Query(None, description="Filter by sensor ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    hours: Optional[int] = Query(24, description="Hours to count")
):
    """
    Get count of events
    
    Args:
        session: Database session
        current_user: Authenticated user
        event_type: Optional event type filter
        sensor_id: Optional sensor ID filter
        severity: Optional severity filter
        hours: Hours to count
        
    Returns:
        Event count
    """
    try:
        repo = CloudRepository(session)
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        events = repo.get_events(
            event_type=event_type,
            sensor_id=sensor_id,
            severity=severity,
            start_time=start_time,
            end_time=end_time,
            limit=100000  # High limit to count all
        )
        
        return {
            "count": len(events),
            "event_type": event_type.value if event_type else None,
            "sensor_id": sensor_id,
            "severity": severity,
            "period_hours": hours
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting events: {e}")