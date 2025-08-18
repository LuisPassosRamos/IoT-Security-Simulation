"""
Telemetry ingestion API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends, Header
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session
from typing import Optional
import logging

from app.db import get_session
from app.db.repo import CloudRepository
from app.db.models import TelemetryIngestDTO, EventType
from app.security.jwt import verify_service_token, verify_api_key


router = APIRouter(prefix="/api", tags=["ingestion"])
logger = logging.getLogger("cloud.api.ingest")


@router.post("/ingest")
async def ingest_telemetry(
    data: TelemetryIngestDTO,
    session: Session = Depends(get_session),
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[HTTPAuthorizationCredentials] = None
):
    """
    Ingest telemetry data from fog service
    
    Args:
        data: Telemetry data to ingest
        session: Database session
        x_api_key: API key authentication
        authorization: JWT token authentication
        
    Returns:
        Ingestion result
    """
    # Authentication: either API key or JWT token
    authenticated = False
    auth_method = "none"
    
    if x_api_key:
        if verify_api_key(x_api_key):
            authenticated = True
            auth_method = "api_key"
        else:
            logger.warning(f"Invalid API key used for ingestion: {x_api_key[:10]}...")
    
    if not authenticated and authorization:
        try:
            service_name = verify_service_token(authorization)
            if service_name:
                authenticated = True
                auth_method = "jwt"
        except HTTPException:
            pass
    
    if not authenticated:
        logger.error(f"Unauthorized ingestion attempt for sensor {data.sensor_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    try:
        repo = CloudRepository(session)
        
        # Create telemetry reading
        reading = repo.create_telemetry_reading(data)
        
        # Create ingestion event
        repo.create_event(
            event_type=EventType.TELEMETRY_RECEIVED,
            sensor_id=data.sensor_id,
            title="Telemetry Received",
            message=f"Received telemetry from {data.sensor_id}: {data.value} {data.unit}",
            details=f"Authentication: {auth_method}, Security validated: {data.security_validated}",
            source="fog"
        )
        
        logger.info(
            f"Successfully ingested telemetry",
            extra={
                'sensor_id': data.sensor_id,
                'value': data.value,
                'unit': data.unit,
                'auth_method': auth_method,
                'security_validated': data.security_validated
            }
        )
        
        return {
            "status": "success",
            "message": "Telemetry ingested successfully",
            "reading_id": reading.id,
            "sensor_id": reading.sensor_id,
            "timestamp": reading.timestamp.isoformat()
        }
    
    except Exception as e:
        logger.error(
            f"Error ingesting telemetry from {data.sensor_id}: {e}",
            extra={
                'sensor_id': data.sensor_id,
                'error': str(e)
            }
        )
        
        # Create error event
        try:
            repo = CloudRepository(session)
            repo.create_event(
                event_type=EventType.TELEMETRY_RECEIVED,
                sensor_id=data.sensor_id,
                severity="error",
                title="Telemetry Ingestion Error",
                message=f"Failed to ingest telemetry from {data.sensor_id}: {str(e)}",
                source="cloud"
            )
        except:
            pass  # Don't fail on event creation error
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing telemetry: {str(e)}"
        )


@router.get("/ingest/health")
async def ingest_health():
    """Health check for ingestion endpoint"""
    return {
        "status": "healthy",
        "service": "telemetry_ingestion",
        "message": "Ingestion endpoint is operational"
    }