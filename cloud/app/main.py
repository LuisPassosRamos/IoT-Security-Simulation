"""
Cloud Service - Main FastAPI application
Provides REST API and web interface for IoT data management
"""

import os
import ssl
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
import uvicorn

from app.db import create_db_engine, init_database, get_session
from app.db.repo import CloudRepository
from app.db.models import EventType
from app.security.jwt import get_current_user, create_admin_token
from app.api import auth, ingest, readings, alerts, events


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cloud.main")

# Global variables
engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global engine
    
    logger.info("Starting cloud service")
    
    try:
        # Initialize database
        engine = create_db_engine()
        init_database(engine)
        
        # Create startup event
        with Session(engine) as session:
            repo = CloudRepository(session)
            repo.create_event(
                event_type=EventType.SYSTEM_STARTUP,
                title="Cloud Service Started",
                message="Cloud service started successfully",
                source="cloud"
            )
        
        logger.info("Cloud service started successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start cloud service: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down cloud service")
        
        try:
            # Create shutdown event
            with Session(engine) as session:
                repo = CloudRepository(session)
                repo.create_event(
                    event_type=EventType.SYSTEM_SHUTDOWN,
                    title="Cloud Service Shutdown",
                    message="Cloud service shutdown initiated",
                    source="cloud"
                )
        except:
            pass  # Don't fail on cleanup
        
        logger.info("Cloud service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="IoT Cloud Service",
    description="Cloud data management service for IoT security simulation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(ingest.router)
app.include_router(readings.router)
app.include_router(alerts.router)
app.include_router(events.router)

# Templates and static files
templates = Jinja2Templates(directory="app/ui/templates")
app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")


# Session dependency for web routes
def get_db_session():
    """Get database session for web routes"""
    with Session(engine) as session:
        yield session


@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to dashboard"""
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    # For demo purposes, auto-generate token and redirect
    token = create_admin_token()
    
    # In a real application, you would render a login form
    # For demo, we'll redirect with token in URL (not secure, just for demo)
    response = RedirectResponse(url="/dashboard")
    response.set_cookie(key="authToken", value=token, httponly=True, secure=False)
    
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "cloud",
        "version": "1.0.0"
    }


@app.get("/metrics")
async def get_metrics(
    session: Session = Depends(get_db_session),
    current_user: str = Depends(get_current_user)
):
    """Get service metrics"""
    try:
        repo = CloudRepository(session)
        stats = repo.get_dashboard_stats()
        
        return {
            "service": "cloud",
            "dashboard_stats": stats.dict(),
            "database_connected": True
        }
    
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving metrics")


@app.get("/api/dashboard")
async def get_dashboard_data(
    session: Session = Depends(get_db_session),
    current_user: str = Depends(get_current_user)
):
    """Get complete dashboard data"""
    try:
        repo = CloudRepository(session)
        
        # Get dashboard stats
        stats = repo.get_dashboard_stats()
        
        # Get sensor summaries
        sensors = repo.get_sensor_summaries()
        
        # Get recent alerts
        recent_alerts = repo.get_alerts(limit=5, acknowledged=False)
        
        # Get recent events
        recent_events = repo.get_events(limit=5)
        
        return {
            "stats": stats.dict(),
            "sensors": [s.dict() for s in sensors],
            "recent_alerts": [a.dict() for a in recent_alerts],
            "recent_events": [e.dict() for e in recent_events]
        }
    
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving dashboard data")


@app.post("/api/demo/start")
async def start_security_demo(
    session: Session = Depends(get_db_session),
    current_user: str = Depends(get_current_user)
):
    """Start security demonstration"""
    try:
        repo = CloudRepository(session)
        
        # Create demo start event
        repo.create_event(
            event_type=EventType.SYSTEM_STARTUP,
            title="Security Demo Started",
            message="Security demonstration initiated by admin",
            source="cloud"
        )
        
        return {
            "status": "started",
            "message": "Security demo started successfully"
        }
    
    except Exception as e:
        logger.error(f"Error starting demo: {e}")
        raise HTTPException(status_code=500, detail="Error starting demo")


@app.post("/api/demo/stop")
async def stop_security_demo(
    session: Session = Depends(get_db_session),
    current_user: str = Depends(get_current_user)
):
    """Stop security demonstration"""
    try:
        repo = CloudRepository(session)
        
        # Create demo stop event
        repo.create_event(
            event_type=EventType.SYSTEM_SHUTDOWN,
            title="Security Demo Stopped",
            message="Security demonstration stopped by admin",
            source="cloud"
        )
        
        return {
            "status": "stopped",
            "message": "Security demo stopped successfully"
        }
    
    except Exception as e:
        logger.error(f"Error stopping demo: {e}")
        raise HTTPException(status_code=500, detail="Error stopping demo")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Custom 404 handler"""
    if request.url.path.startswith('/api/'):
        # Return JSON for API calls
        return {"error": "Not found", "status_code": 404}
    else:
        # Redirect web requests to dashboard
        return RedirectResponse(url="/dashboard")


def create_ssl_context():
    """Create SSL context for HTTPS"""
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # In production, use proper certificates
    cert_file = os.getenv('SSL_CERT_FILE', 'certs/server.crt')
    key_file = os.getenv('SSL_KEY_FILE', 'certs/server.key')
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        ssl_context.load_cert_chain(cert_file, key_file)
        return ssl_context
    
    return None


if __name__ == "__main__":
    # Configuration
    host = os.getenv('CLOUD_HOST', '0.0.0.0')
    port = int(os.getenv('CLOUD_PORT', '8443'))
    log_level = os.getenv('LOG_LEVEL', 'info').lower()
    enable_tls = os.getenv('ENABLE_TLS', 'false').lower() == 'true'
    
    # SSL configuration
    ssl_context = None
    if enable_tls:
        ssl_context = create_ssl_context()
        if ssl_context:
            logger.info(f"Starting cloud service with HTTPS on {host}:{port}")
        else:
            logger.warning("SSL certificates not found, falling back to HTTP")
            port = 8080  # Use HTTP port instead
    
    if not ssl_context:
        logger.info(f"Starting cloud service with HTTP on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        ssl_certfile=os.getenv('SSL_CERT_FILE') if ssl_context else None,
        ssl_keyfile=os.getenv('SSL_KEY_FILE') if ssl_context else None,
        log_level=log_level,
        reload=False
    )