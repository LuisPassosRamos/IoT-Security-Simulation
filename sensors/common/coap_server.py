"""
CoAP server utilities for sensors
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from aiocoap import Context, Message, Code
from aiocoap.resource import Site, Resource
from aiocoap.numbers import ContentFormat


class SensorResource(Resource):
    """CoAP resource for sensor current reading"""
    
    def __init__(self, get_current_reading_func):
        super().__init__()
        self.get_current_reading = get_current_reading_func
        self.logger = logging.getLogger("coap.sensor_resource")
    
    async def render_get(self, request):
        """Handle GET request for current sensor reading"""
        try:
            # Get current reading
            reading = await self.get_current_reading()
            
            if reading is None:
                self.logger.warning("No current reading available")
                return Message(code=Code.NOT_FOUND)
            
            # Convert to JSON
            payload = json.dumps(reading, default=str).encode('utf-8')
            
            self.logger.debug(f"Returning sensor reading: {reading}")
            
            return Message(
                payload=payload,
                content_format=ContentFormat.APPLICATION_JSON
            )
            
        except Exception as e:
            self.logger.error(f"Error handling CoAP GET request: {e}")
            return Message(code=Code.INTERNAL_SERVER_ERROR)


class CoAPServer:
    """CoAP server for sensor endpoints"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5683):
        self.host = host
        self.port = port
        self.logger = logging.getLogger("coap.server")
        self.context: Optional[Context] = None
        self.site: Optional[Site] = None
    
    async def start(self, get_current_reading_func):
        """Start CoAP server"""
        try:
            # Create site and add resources
            self.site = Site()
            
            # Add sensor resource at /current
            sensor_resource = SensorResource(get_current_reading_func)
            self.site.add_resource(['current'], sensor_resource)
            
            # Create context and bind to address
            self.context = await Context.create_server_context(
                self.site,
                bind=(self.host, self.port)
            )
            
            self.logger.info(f"CoAP server started on {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start CoAP server: {e}")
            raise
    
    async def stop(self):
        """Stop CoAP server"""
        if self.context:
            await self.context.shutdown()
            self.logger.info("CoAP server stopped")


class CoAPClient:
    """CoAP client for making requests to sensors"""
    
    def __init__(self):
        self.logger = logging.getLogger("coap.client")
        self.context: Optional[Context] = None
    
    async def start(self):
        """Start CoAP client"""
        try:
            self.context = await Context.create_client_context()
            self.logger.info("CoAP client started")
        except Exception as e:
            self.logger.error(f"Failed to start CoAP client: {e}")
            raise
    
    async def stop(self):
        """Stop CoAP client"""
        if self.context:
            await self.context.shutdown()
            self.logger.info("CoAP client stopped")
    
    async def get_sensor_reading(self, host: str, port: int = 5683, path: str = "current") -> Optional[Dict[str, Any]]:
        """Get current reading from sensor via CoAP"""
        if not self.context:
            self.logger.error("CoAP client not started")
            return None
        
        try:
            # Create request
            uri = f"coap://{host}:{port}/{path}"
            request = Message(code=Code.GET, uri=uri)
            
            self.logger.debug(f"Sending CoAP GET request to {uri}")
            
            # Send request with timeout
            response = await asyncio.wait_for(
                self.context.request(request).response,
                timeout=10.0
            )
            
            if response.code.is_successful():
                # Parse JSON response
                payload = json.loads(response.payload.decode('utf-8'))
                self.logger.debug(f"Received CoAP response: {payload}")
                return payload
            else:
                self.logger.warning(f"CoAP request failed with code: {response.code}")
                return None
                
        except asyncio.TimeoutError:
            self.logger.error(f"CoAP request to {host}:{port} timed out")
            return None
        except Exception as e:
            self.logger.error(f"CoAP request to {host}:{port} failed: {e}")
            return None