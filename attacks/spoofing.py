"""
Message Spoofing Attack Demonstration
Sends fake sensor messages with invalid signatures to test integrity verification
"""

import asyncio
import json
import time
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import paho.mqtt.client as mqtt
import argparse
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("attack.spoofing")


class SpoofingAttacker:
    """Demonstrates message spoofing attacks against IoT sensors"""
    
    def __init__(self, mqtt_host: str = "mosquitto", mqtt_port: int = 1883):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.client: Optional[mqtt.Client] = None
        self.attack_log = []
        
        # Attack configuration
        self.attack_duration = 120  # 2 minutes
        self.messages_per_sensor = 20
        self.target_sensors = ["temp-01", "humidity-01", "wind-01"]
        
    async def run_attack(self):
        """Execute the complete spoofing attack demonstration"""
        logger.info("Starting message spoofing attack demonstration")
        
        try:
            # Phase 1: Send spoofed messages with invalid signatures
            await self.spoofing_phase()
            
            # Phase 2: Send spoofed messages with no signatures
            await self.unsigned_phase()
            
            # Phase 3: Send spoofed messages with tampered data
            await self.tampering_phase()
            
            # Phase 4: Generate report
            self.generate_report()
            
        except KeyboardInterrupt:
            logger.info("Attack demonstration interrupted by user")
        except Exception as e:
            logger.error(f"Attack demonstration failed: {e}")
        finally:
            self.cleanup()
    
    async def spoofing_phase(self):
        """Send messages with invalid HMAC signatures"""
        logger.info("Phase 1: Sending messages with invalid signatures")
        
        # Setup MQTT client
        self.client = mqtt.Client("spoofing-attacker")
        self.client.on_connect = self._on_connect
        self.client.on_publish = self._on_publish
        
        # Connect
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()
        
        # Attack each sensor
        for sensor_id in self.target_sensors:
            logger.info(f"Attacking sensor: {sensor_id}")
            
            for i in range(self.messages_per_sensor):
                # Create fake message with invalid signature
                fake_message = self._create_fake_message(sensor_id, "invalid_signature")
                
                # Log attack attempt
                attack_entry = {
                    'attack_type': 'invalid_signature',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'sensor_id': sensor_id,
                    'message_number': i + 1,
                    'payload': fake_message
                }
                
                # Send message
                topic = f"greenhouse/{sensor_id}/telemetry"
                result = self.client.publish(topic, json.dumps(fake_message), qos=1)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    attack_entry['status'] = 'sent'
                    logger.debug(f"Sent spoofed message {i+1} to {sensor_id}")
                else:
                    attack_entry['status'] = 'failed'
                    logger.error(f"Failed to send spoofed message: {result.rc}")
                
                self.attack_log.append(attack_entry)
                
                # Small delay between messages
                await asyncio.sleep(0.5)
        
        logger.info(f"Invalid signature phase completed. Sent {len([a for a in self.attack_log if a['status'] == 'sent'])} messages")
    
    async def unsigned_phase(self):
        """Send messages without signatures"""
        logger.info("Phase 2: Sending messages without signatures")
        
        # Attack each sensor
        for sensor_id in self.target_sensors:
            logger.info(f"Attacking sensor with unsigned messages: {sensor_id}")
            
            for i in range(self.messages_per_sensor // 2):  # Fewer unsigned messages
                # Create fake message without signature
                fake_message = self._create_fake_message(sensor_id, "no_signature")
                
                # Log attack attempt
                attack_entry = {
                    'attack_type': 'no_signature',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'sensor_id': sensor_id,
                    'message_number': i + 1,
                    'payload': fake_message
                }
                
                # Send message
                topic = f"greenhouse/{sensor_id}/telemetry"
                result = self.client.publish(topic, json.dumps(fake_message), qos=1)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    attack_entry['status'] = 'sent'
                    logger.debug(f"Sent unsigned message {i+1} to {sensor_id}")
                else:
                    attack_entry['status'] = 'failed'
                    logger.error(f"Failed to send unsigned message: {result.rc}")
                
                self.attack_log.append(attack_entry)
                
                # Small delay between messages
                await asyncio.sleep(0.5)
        
        logger.info(f"Unsigned message phase completed")
    
    async def tampering_phase(self):
        """Send messages with tampered data but valid structure"""
        logger.info("Phase 3: Sending messages with tampered data")
        
        # Attack each sensor
        for sensor_id in self.target_sensors:
            logger.info(f"Attacking sensor with tampered data: {sensor_id}")
            
            for i in range(self.messages_per_sensor // 3):  # Even fewer tampered messages
                # Create fake message with tampered values
                fake_message = self._create_fake_message(sensor_id, "tampered_data")
                
                # Log attack attempt
                attack_entry = {
                    'attack_type': 'tampered_data',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'sensor_id': sensor_id,
                    'message_number': i + 1,
                    'payload': fake_message
                }
                
                # Send message
                topic = f"greenhouse/{sensor_id}/telemetry"
                result = self.client.publish(topic, json.dumps(fake_message), qos=1)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    attack_entry['status'] = 'sent'
                    logger.debug(f"Sent tampered message {i+1} to {sensor_id}")
                else:
                    attack_entry['status'] = 'failed'
                    logger.error(f"Failed to send tampered message: {result.rc}")
                
                self.attack_log.append(attack_entry)
                
                # Small delay between messages
                await asyncio.sleep(0.5)
        
        logger.info(f"Tampered data phase completed")
    
    def _create_fake_message(self, sensor_id: str, attack_type: str) -> Dict[str, Any]:
        """Create a fake sensor message"""
        # Base message structure
        message = {
            'sensor_id': sensor_id,
            'ts': datetime.now(timezone.utc).isoformat(),
            'type': self._get_sensor_type(sensor_id),
            'value': self._get_fake_value(sensor_id, attack_type),
            'unit': self._get_sensor_unit(sensor_id),
            'nonce': str(uuid.uuid4()),
            'enc': False,
            'ver': 1
        }
        
        # Add signature based on attack type
        if attack_type == "invalid_signature":
            # Use a fake signature
            message['sig'] = "fake_signature_" + str(random.randint(1000, 9999))
        elif attack_type == "no_signature":
            # Don't include signature
            pass
        elif attack_type == "tampered_data":
            # Create message with extreme values and fake signature
            message['sig'] = "tampered_sig_" + str(random.randint(1000, 9999))
        
        return message
    
    def _get_sensor_type(self, sensor_id: str) -> str:
        """Get sensor type from sensor ID"""
        if "temp" in sensor_id:
            return "temperature"
        elif "humidity" in sensor_id:
            return "humidity"
        elif "wind" in sensor_id:
            return "wind"
        return "unknown"
    
    def _get_sensor_unit(self, sensor_id: str) -> str:
        """Get sensor unit from sensor ID"""
        if "temp" in sensor_id:
            return "°C"
        elif "humidity" in sensor_id:
            return "%"
        elif "wind" in sensor_id:
            return "m/s"
        return "unit"
    
    def _get_fake_value(self, sensor_id: str, attack_type: str) -> float:
        """Generate fake sensor value"""
        if attack_type == "tampered_data":
            # Use extreme values to make tampering obvious
            if "temp" in sensor_id:
                return random.choice([-50.0, 100.0, 999.9])
            elif "humidity" in sensor_id:
                return random.choice([-10.0, 150.0, 999.9])
            elif "wind" in sensor_id:
                return random.choice([-20.0, 200.0, 999.9])
        else:
            # Use realistic but fake values
            if "temp" in sensor_id:
                return round(random.uniform(18.0, 28.0), 2)
            elif "humidity" in sensor_id:
                return round(random.uniform(30.0, 70.0), 2)
            elif "wind" in sensor_id:
                return round(random.uniform(0.0, 15.0), 2)
        
        return 0.0
    
    def generate_report(self):
        """Generate attack report"""
        logger.info("Generating spoofing attack report")
        
        # Create logs directory
        os.makedirs("logs/attacks", exist_ok=True)
        
        # Analyze attack results
        attack_types = {}
        for entry in self.attack_log:
            attack_type = entry['attack_type']
            if attack_type not in attack_types:
                attack_types[attack_type] = {'sent': 0, 'failed': 0}
            
            if entry['status'] == 'sent':
                attack_types[attack_type]['sent'] += 1
            else:
                attack_types[attack_type]['failed'] += 1
        
        # Generate detailed report
        report = {
            'attack_type': 'message_spoofing',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_attempts': len(self.attack_log),
                'successful_sends': len([a for a in self.attack_log if a['status'] == 'sent']),
                'failed_sends': len([a for a in self.attack_log if a['status'] == 'failed']),
                'attack_types': attack_types,
                'target_sensors': self.target_sensors
            },
            'configuration': {
                'attack_duration_seconds': self.attack_duration,
                'messages_per_sensor': self.messages_per_sensor,
                'mqtt_broker': f"{self.mqtt_host}:{self.mqtt_port}"
            },
            'attack_log': self.attack_log
        }
        
        # Save report to file
        report_file = f"logs/attacks/spoofing_attack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Attack report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("MESSAGE SPOOFING ATTACK DEMONSTRATION RESULTS")
        print("="*60)
        print(f"Total Attack Attempts: {report['summary']['total_attempts']}")
        print(f"Messages Sent: {report['summary']['successful_sends']}")
        print(f"Failed Sends: {report['summary']['failed_sends']}")
        print(f"Target Sensors: {', '.join(self.target_sensors)}")
        print("\nAttack Types:")
        for attack_type, counts in attack_types.items():
            print(f"  {attack_type}: {counts['sent']} sent, {counts['failed']} failed")
        print(f"\nReport File: {report_file}")
        print("\nExpected Behavior:")
        print("- With security enabled: Fog should reject messages with invalid/missing signatures")
        print("- Without security: All spoofed messages will be accepted")
        print("- Check fog service logs for signature verification failures")
        print("="*60)
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            logger.info("Connected to MQTT broker for spoofing attack")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for published messages"""
        logger.debug(f"Spoofed message {mid} published")
    
    def cleanup(self):
        """Cleanup resources"""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Message Spoofing Attack Demonstration")
    parser.add_argument("--mqtt-host", default="mosquitto", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--duration", type=int, default=120, help="Attack duration in seconds")
    parser.add_argument("--messages-per-sensor", type=int, default=20, help="Number of messages per sensor")
    parser.add_argument("--sensors", nargs="+", default=["temp-01", "humidity-01", "wind-01"], 
                       help="Target sensor IDs")
    
    args = parser.parse_args()
    
    # Create attacker
    attacker = SpoofingAttacker(args.mqtt_host, args.mqtt_port)
    attacker.attack_duration = args.duration
    attacker.messages_per_sensor = args.messages_per_sensor
    attacker.target_sensors = args.sensors
    
    # Run attack
    await attacker.run_attack()


if __name__ == "__main__":
    asyncio.run(main())