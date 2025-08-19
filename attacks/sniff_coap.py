"""
CoAP Sniffing and Analysis Demonstration
Demonstrates passive monitoring of CoAP communications and data extraction
"""

import asyncio
import json
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import argparse
import os
from aiocoap import Context, Message, Code

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("attack.coap_sniff")


class CoAPSniffer:
    """Demonstrates CoAP traffic analysis and passive data collection"""
    
    def __init__(self):
        self.context: Optional[Context] = None
        self.collected_data = []
        self.analysis_results = {}
        
        # Target sensors
        self.target_sensors = [
            {"host": "sensor-temp", "port": 5683, "id": "temp-01"},
            {"host": "sensor-humidity", "port": 5683, "id": "humidity-01"},
            {"host": "sensor-wind", "port": 5683, "id": "wind-01"}
        ]
        
        # Sniffing configuration
        self.sniff_duration = 300  # 5 minutes
        self.request_interval = 30  # Request every 30 seconds
        
    async def run_sniffing(self):
        """Execute the complete CoAP sniffing demonstration"""
        logger.info("Starting CoAP sniffing demonstration")
        
        try:
            # Phase 1: Passive data collection
            await self.passive_collection_phase()
            
            # Phase 2: Active reconnaissance
            await self.active_reconnaissance_phase()
            
            # Phase 3: Data analysis
            await self.analysis_phase()
            
            # Phase 4: Generate report
            self.generate_report()
            
        except KeyboardInterrupt:
            logger.info("Sniffing demonstration interrupted by user")
        except Exception as e:
            logger.error(f"Sniffing demonstration failed: {e}")
        finally:
            await self.cleanup()
    
    async def passive_collection_phase(self):
        """Collect data by making regular CoAP requests"""
        logger.info(f"Phase 1: Passive data collection for {self.sniff_duration} seconds")
        
        # Initialize CoAP client
        self.context = await Context.create_client_context()
        
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < self.sniff_duration:
            # Request data from each sensor
            for sensor in self.target_sensors:
                try:
                    data = await self._request_sensor_data(sensor)
                    if data:
                        data['collection_method'] = 'passive'
                        data['request_number'] = request_count + 1
                        self.collected_data.append(data)
                        
                        logger.info(f"Collected data from {sensor['id']}: {data.get('value', 'N/A')} {data.get('unit', '')}")
                        
                except Exception as e:
                    logger.warning(f"Failed to collect from {sensor['id']}: {e}")
                
                # Small delay between sensor requests
                await asyncio.sleep(1)
            
            request_count += 1
            
            # Wait for next collection interval
            await asyncio.sleep(self.request_interval)
        
        logger.info(f"Passive collection completed. Collected {len(self.collected_data)} data points")
    
    async def active_reconnaissance_phase(self):
        """Perform active reconnaissance to discover additional information"""
        logger.info("Phase 2: Active reconnaissance")
        
        # Try different CoAP paths to discover additional endpoints
        reconnaissance_paths = [
            "current",
            "status",
            "info",
            "config",
            "health",
            "metrics",
            ".well-known/core"
        ]
        
        for sensor in self.target_sensors:
            sensor_recon = {
                'sensor_id': sensor['id'],
                'host': sensor['host'],
                'port': sensor['port'],
                'discovered_endpoints': [],
                'failed_endpoints': []
            }
            
            logger.info(f"Performing reconnaissance on {sensor['id']}")
            
            for path in reconnaissance_paths:
                try:
                    # Create CoAP request
                    uri = f"coap://{sensor['host']}:{sensor['port']}/{path}"
                    request = Message(code=Code.GET, uri=uri)
                    
                    # Send request with timeout
                    response = await asyncio.wait_for(
                        self.context.request(request).response,
                        timeout=5.0
                    )
                    
                    if response.code.is_successful():
                        endpoint_info = {
                            'path': path,
                            'response_code': str(response.code),
                            'content_format': str(response.opt.content_format) if response.opt.content_format else 'unknown',
                            'payload_size': len(response.payload),
                            'payload_preview': response.payload.decode('utf-8', errors='ignore')[:100]
                        }
                        
                        sensor_recon['discovered_endpoints'].append(endpoint_info)
                        logger.info(f"Discovered endpoint: {sensor['id']}/{path}")
                        
                        # If it's the well-known core, try to parse it
                        if path == ".well-known/core":
                            await self._parse_well_known_core(sensor, response.payload)
                    else:
                        sensor_recon['failed_endpoints'].append({
                            'path': path,
                            'response_code': str(response.code)
                        })
                        
                except asyncio.TimeoutError:
                    sensor_recon['failed_endpoints'].append({
                        'path': path,
                        'error': 'timeout'
                    })
                except Exception as e:
                    sensor_recon['failed_endpoints'].append({
                        'path': path,
                        'error': str(e)
                    })
                
                # Small delay between requests
                await asyncio.sleep(0.5)
            
            # Add reconnaissance results
            self.analysis_results[sensor['id']] = sensor_recon
        
        logger.info("Active reconnaissance completed")
    
    async def analysis_phase(self):
        """Analyze collected data for patterns and vulnerabilities"""
        logger.info("Phase 3: Data analysis")
        
        if not self.collected_data:
            logger.warning("No data collected for analysis")
            return
        
        # Analyze data patterns
        sensor_analysis = {}
        
        for data_point in self.collected_data:
            sensor_id = data_point.get('sensor_id', 'unknown')
            
            if sensor_id not in sensor_analysis:
                sensor_analysis[sensor_id] = {
                    'data_points': 0,
                    'values': [],
                    'timestamps': [],
                    'encryption_status': [],
                    'signature_status': [],
                    'patterns': {}
                }
            
            analysis = sensor_analysis[sensor_id]
            analysis['data_points'] += 1
            
            # Collect values and metadata
            if 'value' in data_point:
                analysis['values'].append(data_point['value'])
            
            if 'timestamp' in data_point:
                analysis['timestamps'].append(data_point['timestamp'])
            
            if 'encrypted' in data_point:
                analysis['encryption_status'].append(data_point['encrypted'])
            
            if 'signature_valid' in data_point:
                analysis['signature_status'].append(data_point['signature_valid'])
        
        # Calculate statistics for each sensor
        for sensor_id, analysis in sensor_analysis.items():
            if analysis['values']:
                analysis['patterns'] = {
                    'min_value': min(analysis['values']),
                    'max_value': max(analysis['values']),
                    'avg_value': sum(analysis['values']) / len(analysis['values']),
                    'value_range': max(analysis['values']) - min(analysis['values'])
                }
            
            # Security analysis
            if analysis['encryption_status']:
                encryption_rate = sum(analysis['encryption_status']) / len(analysis['encryption_status'])
                analysis['encryption_rate'] = encryption_rate
            
            if analysis['signature_status']:
                signature_rate = sum(analysis['signature_status']) / len(analysis['signature_status'])
                analysis['signature_rate'] = signature_rate
        
        # Store analysis results
        self.analysis_results['data_analysis'] = sensor_analysis
        
        logger.info("Data analysis completed")
    
    async def _request_sensor_data(self, sensor: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Request data from a specific sensor"""
        try:
            # Create CoAP request
            uri = f"coap://{sensor['host']}:{sensor['port']}/current"
            request = Message(code=Code.GET, uri=uri)
            
            # Send request with timeout
            response = await asyncio.wait_for(
                self.context.request(request).response,
                timeout=10.0
            )
            
            if response.code.is_successful():
                # Parse JSON response
                payload = json.loads(response.payload.decode('utf-8'))
                
                # Add metadata
                collection_data = {
                    'sensor_id': sensor['id'],
                    'host': sensor['host'],
                    'port': sensor['port'],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'response_time_ms': 0,  # Would need timing measurement
                    'coap_response_code': str(response.code),
                    'payload_size': len(response.payload),
                    **payload  # Include all sensor data
                }
                
                # Analyze security aspects
                collection_data['encrypted'] = payload.get('enc', False)
                collection_data['has_signature'] = 'sig' in payload
                collection_data['signature_valid'] = None  # Can't verify without key
                
                return collection_data
            else:
                logger.warning(f"CoAP request failed: {response.code}")
                return None
                
        except Exception as e:
            logger.error(f"Error requesting sensor data: {e}")
            return None
    
    async def _parse_well_known_core(self, sensor: Dict[str, Any], payload: bytes):
        """Parse .well-known/core response to discover resources"""
        try:
            core_data = payload.decode('utf-8')
            logger.info(f"Well-known core for {sensor['id']}: {core_data}")
            
            # Basic parsing of CoRE Link Format
            # In a real implementation, you would use a proper parser
            resources = []
            if core_data:
                # Split by commas and extract resource paths
                parts = core_data.split(',')
                for part in parts:
                    if '<' in part and '>' in part:
                        start = part.find('<') + 1
                        end = part.find('>')
                        if start < end:
                            resource_path = part[start:end]
                            resources.append(resource_path)
            
            if sensor['id'] not in self.analysis_results:
                self.analysis_results[sensor['id']] = {}
            
            self.analysis_results[sensor['id']]['discovered_resources'] = resources
            
        except Exception as e:
            logger.error(f"Error parsing well-known core: {e}")
    
    def generate_report(self):
        """Generate comprehensive sniffing report"""
        logger.info("Generating CoAP sniffing report")
        
        # Create logs directory
        os.makedirs("logs/attacks", exist_ok=True)
        
        # Generate summary statistics
        total_requests = len(self.collected_data)
        successful_requests = len([d for d in self.collected_data if d.get('value') is not None])
        
        # Security assessment
        security_assessment = {
            'encrypted_communications': 0,
            'unencrypted_communications': 0,
            'signed_messages': 0,
            'unsigned_messages': 0,
            'vulnerable_endpoints': []
        }
        
        for data_point in self.collected_data:
            if data_point.get('encrypted', False):
                security_assessment['encrypted_communications'] += 1
            else:
                security_assessment['unencrypted_communications'] += 1
            
            if data_point.get('has_signature', False):
                security_assessment['signed_messages'] += 1
            else:
                security_assessment['unsigned_messages'] += 1
        
        # Check for vulnerable configurations
        unencrypted_rate = security_assessment['unencrypted_communications'] / total_requests if total_requests > 0 else 0
        unsigned_rate = security_assessment['unsigned_messages'] / total_requests if total_requests > 0 else 0
        
        vulnerabilities = []
        if unencrypted_rate > 0.5:
            vulnerabilities.append("High rate of unencrypted communications")
        if unsigned_rate > 0.5:
            vulnerabilities.append("High rate of unsigned messages")
        
        # Generate detailed report
        report = {
            'attack_type': 'coap_sniffing',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': total_requests - successful_requests,
                'target_sensors': len(self.target_sensors),
                'sniff_duration_seconds': self.sniff_duration,
                'data_collection_rate': total_requests / (self.sniff_duration / 60) if self.sniff_duration > 0 else 0
            },
            'security_assessment': security_assessment,
            'vulnerabilities': vulnerabilities,
            'reconnaissance_results': self.analysis_results,
            'collected_data_sample': self.collected_data[:10],  # First 10 samples
            'configuration': {
                'request_interval_seconds': self.request_interval,
                'target_sensors': self.target_sensors
            }
        }
        
        # Save report to file
        report_file = f"logs/attacks/coap_sniff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Attack report saved to {report_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("COAP SNIFFING DEMONSTRATION RESULTS")
        print("="*60)
        print(f"Total Requests Made: {total_requests}")
        print(f"Successful Requests: {successful_requests}")
        print(f"Failed Requests: {total_requests - successful_requests}")
        print(f"Data Collection Rate: {report['summary']['data_collection_rate']:.1f} requests/minute")
        print("\nSecurity Assessment:")
        print(f"  Encrypted Communications: {security_assessment['encrypted_communications']}")
        print(f"  Unencrypted Communications: {security_assessment['unencrypted_communications']}")
        print(f"  Signed Messages: {security_assessment['signed_messages']}")
        print(f"  Unsigned Messages: {security_assessment['unsigned_messages']}")
        
        if vulnerabilities:
            print(f"\nVulnerabilities Detected:")
            for vuln in vulnerabilities:
                print(f"  - {vuln}")
        
        print(f"\nReport File: {report_file}")
        print("\nDemonstration Shows:")
        print("- CoAP communications can be passively monitored")
        print("- Unencrypted data is easily accessible")
        print("- Endpoint discovery reveals system structure")
        print("- Regular patterns in data transmission can be analyzed")
        print("="*60)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.context:
            await self.context.shutdown()
            logger.info("CoAP context cleaned up")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="CoAP Sniffing Demonstration")
    parser.add_argument("--duration", type=int, default=300, help="Sniffing duration in seconds")
    parser.add_argument("--interval", type=int, default=30, help="Request interval in seconds")
    parser.add_argument("--sensors", nargs="+", 
                       default=["sensor-temp:5683:temp-01", "sensor-humidity:5683:humidity-01", "sensor-wind:5683:wind-01"],
                       help="Target sensors in format host:port:id")
    
    args = parser.parse_args()
    
    # Parse sensor specifications
    target_sensors = []
    for sensor_spec in args.sensors:
        parts = sensor_spec.split(':')
        if len(parts) == 3:
            target_sensors.append({
                'host': parts[0],
                'port': int(parts[1]),
                'id': parts[2]
            })
    
    # Create sniffer
    sniffer = CoAPSniffer()
    sniffer.sniff_duration = args.duration
    sniffer.request_interval = args.interval
    sniffer.target_sensors = target_sensors
    
    # Run sniffing
    await sniffer.run_sniffing()


if __name__ == "__main__":
    asyncio.run(main())