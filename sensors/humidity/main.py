"""
Humidity Sensor IoT Device
Publishes humidity readings via MQTT and exposes CoAP endpoint
"""

import asyncio
import os
import sys
from typing import Optional, Dict, Any

# Add common module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))

from security import PayloadGenerator, SensorSimulator
from mqtt_client import MQTTClient, MQTTPublisher
from coap_server import CoAPServer
from logging_utils import setup_logging, log_sensor_event, log_security_event


class HumiditySensor:
    """Humidity sensor implementation"""
    
    def __init__(self):
        # Environment configuration
        self.sensor_id = os.getenv('SENSOR_ID', 'humidity-01')
        self.sensor_type = os.getenv('SENSOR_TYPE', 'humidity')
        self.mqtt_host = os.getenv('MQTT_HOST', 'localhost')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.mqtt_secure_port = int(os.getenv('MQTT_SECURE_PORT', '8883'))
        self.hmac_key = os.getenv('HMAC_KEY', '')
        self.aes_key = os.getenv('AES_GCM_KEY', '')
        self.publish_interval = int(os.getenv('PUBLISH_INTERVAL', '15'))
        self.enable_encryption = os.getenv('ENABLE_ENCRYPTION', 'true').lower() == 'true'
        self.enable_tls = os.getenv('ENABLE_TLS', 'false').lower() == 'true'
        self.coap_port = int(os.getenv('COAP_PORT', '5683'))
        
        # Setup logging
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.logger = setup_logging(log_level, self.sensor_id)
        
        # Initialize components
        self.payload_generator = PayloadGenerator(
            self.sensor_id,
            self.sensor_type,
            self.hmac_key,
            self.aes_key if self.enable_encryption else None
        )
        
        self.sensor_simulator = SensorSimulator(self.sensor_type)
        
        # MQTT client
        self.mqtt_client = MQTTClient(
            client_id=self.sensor_id,
            host=self.mqtt_host,
            port=self.mqtt_port,
            secure_port=self.mqtt_secure_port,
            use_tls=self.enable_tls
        )
        
        self.mqtt_publisher = MQTTPublisher(self.mqtt_client, "greenhouse")
        
        # CoAP server
        self.coap_server = CoAPServer(port=self.coap_port)
        
        # Current reading storage
        self.current_reading: Optional[Dict[str, Any]] = None
        
        # Control flags
        self.running = False
    
    async def get_current_reading(self) -> Optional[Dict[str, Any]]:
        """Get current sensor reading for CoAP endpoint"""
        if self.current_reading is None:
            # Generate initial reading
            value = self.sensor_simulator.get_reading()
            unit = self.sensor_simulator.get_unit()
            self.current_reading = self.payload_generator.generate_reading(
                value, unit, self.enable_encryption
            )
        
        return self.current_reading
    
    async def publish_reading(self):
        """Generate and publish a sensor reading"""
        try:
            # Generate new reading
            value = self.sensor_simulator.get_reading()
            unit = self.sensor_simulator.get_unit()
            
            reading = self.payload_generator.generate_reading(
                value, unit, self.enable_encryption
            )
            
            # Store for CoAP endpoint
            self.current_reading = reading
            
            # Publish via MQTT
            success = await self.mqtt_publisher.publish_telemetry(
                self.sensor_id, reading
            )
            
            if success:
                log_sensor_event(
                    self.logger,
                    "telemetry_published",
                    f"Published reading: {value} {unit}",
                    self.sensor_id,
                    value=value,
                    unit=unit,
                    encrypted=self.enable_encryption
                )
            else:
                log_security_event(
                    self.logger,
                    "publish_failed",
                    "Failed to publish telemetry data",
                    self.sensor_id,
                    severity="ERROR"
                )
                
        except Exception as e:
            log_security_event(
                self.logger,
                "publish_error",
                f"Error publishing reading: {e}",
                self.sensor_id,
                severity="ERROR",
                error=str(e)
            )
    
    async def publishing_loop(self):
        """Main publishing loop"""
        while self.running:
            await self.publish_reading()
            await asyncio.sleep(self.publish_interval)
    
    async def start(self):
        """Start the sensor"""
        self.running = True
        
        log_sensor_event(
            self.logger,
            "sensor_starting",
            f"Starting {self.sensor_type} sensor",
            self.sensor_id,
            mqtt_host=self.mqtt_host,
            mqtt_port=self.mqtt_port,
            coap_port=self.coap_port,
            encryption_enabled=self.enable_encryption,
            tls_enabled=self.enable_tls
        )
        
        try:
            # Connect to MQTT broker
            connected = await self.mqtt_client.connect()
            if not connected:
                raise Exception("Failed to connect to MQTT broker")
            
            self.mqtt_client.start_loop()
            
            # Start CoAP server
            await self.coap_server.start(self.get_current_reading)
            
            log_sensor_event(
                self.logger,
                "sensor_started",
                f"{self.sensor_type} sensor started successfully",
                self.sensor_id
            )
            
            # Start publishing loop
            await self.publishing_loop()
            
        except Exception as e:
            log_security_event(
                self.logger,
                "startup_error",
                f"Error starting sensor: {e}",
                self.sensor_id,
                severity="CRITICAL",
                error=str(e)
            )
            raise
    
    async def stop(self):
        """Stop the sensor"""
        self.running = False
        
        log_sensor_event(
            self.logger,
            "sensor_stopping",
            f"Stopping {self.sensor_type} sensor",
            self.sensor_id
        )
        
        try:
            # Stop MQTT client
            self.mqtt_client.stop_loop()
            self.mqtt_client.disconnect()
            
            # Stop CoAP server
            await self.coap_server.stop()
            
            log_sensor_event(
                self.logger,
                "sensor_stopped",
                f"{self.sensor_type} sensor stopped successfully",
                self.sensor_id
            )
            
        except Exception as e:
            log_security_event(
                self.logger,
                "shutdown_error",
                f"Error stopping sensor: {e}",
                self.sensor_id,
                severity="ERROR",
                error=str(e)
            )


async def main():
    """Main function"""
    sensor = HumiditySensor()
    
    try:
        await sensor.start()
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Sensor error: {e}")
    finally:
        await sensor.stop()


if __name__ == "__main__":
    asyncio.run(main())