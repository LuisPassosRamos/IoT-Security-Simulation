"""
Common MQTT client utilities for sensors
"""

import asyncio
import json
import logging
import ssl
from typing import Optional, Callable, Dict, Any
import paho.mqtt.client as mqtt
from paho.mqtt.client import MQTTMessage


class MQTTClient:
    """MQTT client wrapper for sensors"""
    
    def __init__(
        self,
        client_id: str,
        host: str = "localhost",
        port: int = 1883,
        secure_port: int = 8883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
        ca_cert_path: Optional[str] = None
    ):
        self.client_id = client_id
        self.host = host
        self.port = secure_port if use_tls else port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.ca_cert_path = ca_cert_path
        
        self.client = mqtt.Client(client_id)
        self.logger = logging.getLogger(f"mqtt.{client_id}")
        
        # Setup callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish
        self.client.on_message = self._on_message
        
        # Message callback
        self._message_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
        
        # Configure authentication
        if username and password:
            self.client.username_pw_set(username, password)
        
        # Configure TLS
        if use_tls:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            if ca_cert_path:
                context.load_verify_locations(ca_cert_path)
            else:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            self.client.tls_set_context(context)
    
    def set_message_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Set callback for received messages"""
        self._message_callback = callback
    
    async def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.logger.info(f"Connecting to MQTT broker at {self.host}:{self.port}")
            result = self.client.connect(self.host, self.port, 60)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info("MQTT connection initiated")
                return True
            else:
                self.logger.error(f"Failed to connect to MQTT broker: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception during MQTT connection: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.disconnect()
        self.logger.info("Disconnected from MQTT broker")
    
    def publish(self, topic: str, payload: Dict[str, Any], qos: int = 1) -> bool:
        """Publish message to topic"""
        try:
            json_payload = json.dumps(payload, default=str)
            result = self.client.publish(topic, json_payload, qos)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Published to {topic}: {json_payload}")
                return True
            else:
                self.logger.error(f"Failed to publish to {topic}: {result.rc}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception during publish to {topic}: {e}")
            return False
    
    def subscribe(self, topic: str, qos: int = 1) -> bool:
        """Subscribe to topic"""
        try:
            result, _ = self.client.subscribe(topic, qos)
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                self.logger.info(f"Subscribed to {topic}")
                return True
            else:
                self.logger.error(f"Failed to subscribe to {topic}: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Exception during subscribe to {topic}: {e}")
            return False
    
    def start_loop(self):
        """Start MQTT client loop"""
        self.client.loop_start()
        self.logger.info("MQTT client loop started")
    
    def stop_loop(self):
        """Stop MQTT client loop"""
        self.client.loop_stop()
        self.logger.info("MQTT client loop stopped")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.logger.info("Successfully connected to MQTT broker")
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        if rc != 0:
            self.logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
        else:
            self.logger.info("Cleanly disconnected from MQTT broker")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for message publish"""
        self.logger.debug(f"Message {mid} published successfully")
    
    def _on_message(self, client, userdata, msg: MQTTMessage):
        """Callback for received message"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            self.logger.debug(f"Received message on {topic}: {payload}")
            
            if self._message_callback:
                self._message_callback(topic, payload)
                
        except Exception as e:
            self.logger.error(f"Exception processing received message: {e}")


class MQTTPublisher:
    """Simple MQTT publisher for sensors"""
    
    def __init__(self, client: MQTTClient, base_topic: str):
        self.client = client
        self.base_topic = base_topic
        self.logger = logging.getLogger(f"publisher.{client.client_id}")
    
    async def publish_telemetry(self, sensor_id: str, payload: Dict[str, Any]) -> bool:
        """Publish telemetry data"""
        topic = f"{self.base_topic}/{sensor_id}/telemetry"
        
        success = self.client.publish(topic, payload)
        
        if success:
            self.logger.info(f"Published telemetry for {sensor_id}")
        else:
            self.logger.error(f"Failed to publish telemetry for {sensor_id}")
        
        return success
    
    async def publish_alert(self, sensor_id: str, alert_type: str, message: str) -> bool:
        """Publish alert message"""
        topic = f"{self.base_topic}/{sensor_id}/alert"
        
        payload = {
            'sensor_id': sensor_id,
            'alert_type': alert_type,
            'message': message,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        success = self.client.publish(topic, payload)
        
        if success:
            self.logger.info(f"Published alert for {sensor_id}: {alert_type}")
        else:
            self.logger.error(f"Failed to publish alert for {sensor_id}")
        
        return success