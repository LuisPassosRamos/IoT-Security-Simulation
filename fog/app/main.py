"""
Fog Service - Main FastAPI application
Handles MQTT telemetry processing and CoAP requests
"""

import asyncio
import httpx
import json
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

from app.core.config import load_config
from app.core.logging import setup_logging, log_security_event, log_performance_event
from app.mqtt_worker import MQTTWorker
from app.coap_client import CoAPClient
from app.security.jwk import generate_service_token, create_auth_header
from app.models.telemetry import CloudTelemetryDTO, ProcessedTelemetry


# Global components
config = load_config()
logger = setup_logging(config.log_level)
mqtt_worker: Optional[MQTTWorker] = None
coap_client: Optional[CoAPClient] = None
cloud_http_client: Optional[httpx.AsyncClient] = None

# Statistics
app_stats = {
    'start_time': time.time(),
    'total_telemetry_processed': 0,
    'total_cloud_sends': 0,
    'successful_cloud_sends': 0,
    'failed_cloud_sends': 0,
    'total_coap_requests': 0
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global mqtt_worker, coap_client, cloud_http_client
    
    logger.info("Starting fog service")
    
    try:
        # Initialize HTTP client for cloud communication
        cloud_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.cloud.timeout_seconds),
            verify=False  # Allow self-signed certificates
        )
        
        # Initialize CoAP client
        coap_client = CoAPClient(config)
        await coap_client.start()
        
        # Initialize and start MQTT worker
        mqtt_worker = MQTTWorker(config, send_to_cloud)
        await mqtt_worker.start()
        
        logger.info("Fog service started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start fog service: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down fog service")
        
        if mqtt_worker:
            await mqtt_worker.stop()
        
        if coap_client:
            await coap_client.stop()
        
        if cloud_http_client:
            await cloud_http_client.aclose()
        
        logger.info("Fog service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="IoT Fog Service",
    description="Edge processing service for IoT sensor data",
    version="1.0.0",
    lifespan=lifespan
)


async def send_to_cloud(telemetry: ProcessedTelemetry):
    """Send processed telemetry to cloud service"""
    if not cloud_http_client:
        logger.error("Cloud HTTP client not initialized")
        return
    
    start_time = time.time()
    app_stats['total_cloud_sends'] += 1
    
    try:
        # Create DTO for cloud
        cloud_dto = CloudTelemetryDTO.from_processed(telemetry)
        
        # Generate JWT token for authentication
        token = generate_service_token("fog", config.security.jwt_secret)
        headers = create_auth_header(token)
        headers['X-API-Key'] = config.cloud.api_key
        headers['Content-Type'] = 'application/json'
        
        # Send to cloud
        url = f"{config.cloud.url}/api/ingest"
        response = await cloud_http_client.post(
            url,
            json=cloud_dto.dict(),
            headers=headers
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        if response.status_code in [200, 201, 202]:
            app_stats['successful_cloud_sends'] += 1
            
            log_performance_event(
                logger,
                "cloud_send_success",
                f"Successfully sent telemetry to cloud",
                duration_ms=processing_time,
                sensor_id=telemetry.sensor_id,
                status_code=response.status_code
            )
        else:
            app_stats['failed_cloud_sends'] += 1
            
            log_security_event(
                logger,
                "cloud_send_failed",
                f"Failed to send telemetry to cloud: HTTP {response.status_code}",
                severity="ERROR",
                sensor_id=telemetry.sensor_id,
                status_code=response.status_code,
                response_text=response.text[:500]
            )
    
    except Exception as e:
        app_stats['failed_cloud_sends'] += 1
        processing_time = (time.time() - start_time) * 1000
        
        log_security_event(
            logger,
            "cloud_send_error",
            f"Error sending telemetry to cloud: {e}",
            severity="ERROR",
            sensor_id=telemetry.sensor_id,
            error=str(e),
            duration_ms=processing_time
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    uptime = time.time() - app_stats['start_time']
    
    health_status = {
        'status': 'healthy',
        'uptime_seconds': round(uptime, 2),
        'mqtt_connected': mqtt_worker is not None and mqtt_worker.running,
        'coap_client_ready': coap_client is not None and coap_client.context is not None,
        'cloud_client_ready': cloud_http_client is not None
    }
    
    # Check if any critical components are down
    if not all([health_status['mqtt_connected'], health_status['coap_client_ready'], health_status['cloud_client_ready']]):
        health_status['status'] = 'degraded'
    
    return health_status


@app.get("/metrics")
async def get_metrics():
    """Get service metrics"""
    uptime = time.time() - app_stats['start_time']
    
    metrics = {
        'uptime_seconds': round(uptime, 2),
        'application': app_stats.copy(),
        'mqtt_worker': mqtt_worker.get_stats() if mqtt_worker else {},
        'coap_client': coap_client.get_stats() if coap_client else {},
        'memory_usage': _get_memory_usage()
    }
    
    return metrics


@app.post("/coap/poll")
async def poll_sensors(background_tasks: BackgroundTasks):
    """Poll sensors via CoAP on demand"""
    if not coap_client:
        raise HTTPException(status_code=503, detail="CoAP client not available")
    
    # Default sensor configurations
    sensor_configs = [
        {'host': 'sensor-temp', 'port': 5683, 'id': 'temp-01'},
        {'host': 'sensor-humidity', 'port': 5683, 'id': 'humidity-01'},
        {'host': 'sensor-wind', 'port': 5683, 'id': 'wind-01'}
    ]
    
    app_stats['total_coap_requests'] += 1
    
    try:
        # Poll sensors concurrently
        results = await coap_client.poll_sensors(sensor_configs)
        
        # Process valid results
        processed_count = 0
        for result in results:
            if result.valid:
                # Send to cloud in background
                background_tasks.add_task(send_to_cloud, result.telemetry)
                processed_count += 1
        
        return {
            'message': f'Polled {len(sensor_configs)} sensors',
            'successful_polls': len(results),
            'valid_readings': processed_count,
            'results': [
                {
                    'sensor_id': r.telemetry.sensor_id if r.telemetry else 'unknown',
                    'valid': r.valid,
                    'value': r.telemetry.value if r.telemetry else None,
                    'errors': r.errors
                } for r in results
            ]
        }
    
    except Exception as e:
        log_security_event(
            logger,
            "coap_poll_error",
            f"Error polling sensors: {e}",
            severity="ERROR",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error polling sensors: {e}")


@app.get("/sensors/{sensor_id}/current")
async def get_sensor_current(sensor_id: str):
    """Get current reading from specific sensor via CoAP"""
    if not coap_client:
        raise HTTPException(status_code=503, detail="CoAP client not available")
    
    # Map sensor ID to hostname
    sensor_hosts = {
        'temp-01': 'sensor-temp',
        'humidity-01': 'sensor-humidity',
        'wind-01': 'sensor-wind'
    }
    
    host = sensor_hosts.get(sensor_id)
    if not host:
        raise HTTPException(status_code=404, detail=f"Unknown sensor: {sensor_id}")
    
    try:
        result = await coap_client.get_sensor_reading(host)
        
        if result and result.valid:
            return {
                'sensor_id': result.telemetry.sensor_id,
                'timestamp': result.telemetry.timestamp.isoformat(),
                'type': result.telemetry.sensor_type,
                'value': result.telemetry.value,
                'unit': result.telemetry.unit,
                'security_validated': all([
                    result.telemetry.signature_valid,
                    result.telemetry.timestamp_valid
                ])
            }
        else:
            errors = result.errors if result else ["Failed to get reading"]
            raise HTTPException(status_code=400, detail=f"Invalid sensor reading: {errors}")
    
    except HTTPException:
        raise
    except Exception as e:
        log_security_event(
            logger,
            "sensor_read_error",
            f"Error reading sensor {sensor_id}: {e}",
            severity="ERROR",
            sensor_id=sensor_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error reading sensor: {e}")


@app.get("/config")
async def get_config():
    """Get service configuration (sanitized)"""
    return {
        'mqtt': {
            'host': config.mqtt.host,
            'port': config.mqtt.port,
            'secure_port': config.mqtt.secure_port,
            'use_tls': config.mqtt.use_tls
        },
        'security': {
            'enable_signature_verification': config.security.enable_signature_verification,
            'enable_timestamp_validation': config.security.enable_timestamp_validation,
            'enable_nonce_validation': config.security.enable_nonce_validation,
            'enable_rate_limiting': config.security.enable_rate_limiting,
            'timestamp_window_seconds': config.security.timestamp_window_seconds,
            'nonce_cache_size': config.security.nonce_cache_size
        },
        'rate_limit': {
            'messages_per_minute': config.rate_limit.messages_per_minute,
            'burst_capacity': config.rate_limit.burst_capacity
        },
        'cloud': {
            'url': config.cloud.url,
            'timeout_seconds': config.cloud.timeout_seconds
        }
    }


def _get_memory_usage() -> Dict[str, Any]:
    """Get memory usage information"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss_mb': round(memory_info.rss / 1024 / 1024, 2),
            'vms_mb': round(memory_info.vms / 1024 / 1024, 2),
            'percent': round(process.memory_percent(), 2)
        }
    except ImportError:
        return {'error': 'psutil not available'}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        reload=False
    )