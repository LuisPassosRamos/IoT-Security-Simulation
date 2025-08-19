# IoT Security Simulation - Runbook

## Quick Start Guide

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- Ports 1883, 8000, 8080, 8443 available

### 1. Clone and Setup
```bash
git clone <repository-url>
cd IoT-Security-Simulation
cp .env.example .env
```

### 2. Generate Certificates
```bash
cd certs
./make_certs.sh
cd ..
```

### 3. Start the Simulation
```bash
# Option A: Automated demo
./scripts/make_demo.sh

# Option B: Manual startup
docker-compose up --build -d
```

### 4. Access the Dashboard
- **HTTPS**: https://localhost:8443
- **HTTP**: http://localhost:8080

## Detailed Operation Guide

### Service Management

#### Starting Services
```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d mosquitto fog cloud

# Build and start (after code changes)
docker-compose up --build -d
```

#### Monitoring Services
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f fog
docker-compose logs -f cloud
docker-compose logs --tail=100 mosquitto

# Monitor resource usage
docker stats
```

#### Stopping Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop specific service
docker-compose stop fog
```

### Attack Demonstrations

#### Running Individual Attacks

**Replay Attack**
```bash
docker-compose run --rm attacker python replay.py \
  --mqtt-host mosquitto \
  --capture-duration 60 \
  --replay-delay 300 \
  --replay-count 5
```

**Message Spoofing**
```bash
docker-compose run --rm attacker python spoofing.py \
  --mqtt-host mosquitto \
  --duration 120 \
  --messages-per-sensor 20
```

**DoS Attack**
```bash
docker-compose run --rm attacker python dos.py \
  --mqtt-host mosquitto \
  --duration 60 \
  --rate 100 \
  --clients 5
```

**CoAP Sniffing**
```bash
docker-compose run --rm attacker python sniff_coap.py \
  --duration 300 \
  --interval 30
```

#### Expected Results

**With Security Enabled (Default)**
- Replay attacks: BLOCKED (nonce validation)
- Spoofing attacks: BLOCKED (HMAC verification fails)
- DoS attacks: THROTTLED (rate limiting active)
- CoAP sniffing: LIMITED (encryption may be enabled)

**With Security Disabled**
- Replay attacks: SUCCESS (no validation)
- Spoofing attacks: SUCCESS (no signature checking)
- DoS attacks: SUCCESS (no rate limiting)
- CoAP sniffing: FULL ACCESS (no encryption)

### Security Configuration

#### Enabling/Disabling Security Features

Edit `.env` file:
```bash
# Enable all security features
ENABLE_SIGNATURE_VERIFICATION=true
ENABLE_TIMESTAMP_VALIDATION=true
ENABLE_NONCE_VALIDATION=true
ENABLE_RATE_LIMITING=true
ENABLE_ENCRYPTION=true

# Disable for vulnerability demonstration
ENABLE_SIGNATURE_VERIFICATION=false
ENABLE_TIMESTAMP_VALIDATION=false
ENABLE_NONCE_VALIDATION=false
ENABLE_RATE_LIMITING=false
ENABLE_ENCRYPTION=false
```

#### Security Parameters
```bash
# HMAC keys (32 bytes hex)
SENSOR_TEMP_HMAC_KEY=a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789a
SENSOR_HUMIDITY_HMAC_KEY=b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789ab1
SENSOR_WIND_HMAC_KEY=c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abc2

# Encryption key (32 bytes hex)
AES_GCM_KEY=d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789abcde3

# Timing parameters
TIMESTAMP_WINDOW_SECONDS=120
NONCE_CACHE_SIZE=10000

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

### Dashboard Usage

#### Navigation
- **Dashboard**: Overview with real-time metrics
- **Sensors**: Individual sensor status and readings
- **Alerts**: Security alerts and threshold violations
- **Events**: System events and audit log
- **Security Demo**: Interactive attack/defense comparison

#### Key Metrics
- **Active Sensors**: Number of online sensors
- **Total Readings**: Telemetry messages processed
- **Active Alerts**: Unresolved security/system alerts
- **Security Events**: Security violations in last 24h

#### Charts
- **Telemetry Chart**: Real-time sensor data visualization
- **Alert Distribution**: Pie chart of alert severities
- **Time Controls**: 1H, 6H, 24H data views

### Demonstration Scenarios

#### Scenario 1: Baseline Operation
1. Start services with security enabled
2. Monitor normal telemetry flow for 5 minutes
3. Observe clean logs with successful validation
4. Note regular sensor readings without alerts

#### Scenario 2: Attack Without Security
1. Disable security features in `.env`
2. Restart services: `docker-compose restart fog`
3. Run replay attack: All replayed messages accepted
4. Run spoofing attack: Invalid messages processed
5. Observe lack of security events in logs

#### Scenario 3: Attack With Security
1. Enable security features in `.env`
2. Restart services: `docker-compose restart fog`
3. Run replay attack: Messages blocked by nonce validation
4. Run spoofing attack: Messages rejected due to invalid HMAC
5. Observe security events logged in fog service

#### Scenario 4: DoS Protection
1. Monitor normal message rate (dashboard metrics)
2. Run DoS attack with high message rate
3. Observe rate limiting in action (fog logs)
4. Check that legitimate messages still processed
5. Review blocked message statistics

#### Scenario 5: CoAP Vulnerability
1. Run CoAP sniffing tool to collect data
2. Observe unencrypted data exposure
3. Enable end-to-end encryption
4. Re-run sniffing: encrypted payloads only
5. Compare data exposure before/after

### Log Analysis

#### Key Log Locations
```bash
# Service logs
docker-compose logs fog > fog.log
docker-compose logs cloud > cloud.log
docker-compose logs mosquitto > mqtt.log

# Attack logs
docker-compose run --rm -v $(pwd)/logs:/app/logs attacker ls /app/logs/attacks/
```

#### Important Log Patterns

**Security Validation (Fog Service)**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "WARNING",
  "event_type": "security.validation_failed",
  "sensor_id": "temp-01",
  "message": "Invalid HMAC signature",
  "severity": "ERROR"
}
```

**Rate Limiting (Fog Service)**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "WARNING", 
  "event_type": "security.rate_limit_exceeded",
  "sensor_id": "temp-01",
  "message": "Rate limit exceeded for sensor temp-01",
  "severity": "WARNING"
}
```

**Successful Processing (Fog Service)**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "event_type": "telemetry.processed",
  "sensor_id": "temp-01",
  "message": "Successfully processed telemetry from temp-01",
  "value": 25.5,
  "unit": "°C"
}
```

### Troubleshooting

#### Common Issues

**Services Won't Start**
```bash
# Check Docker daemon
sudo systemctl status docker

# Check port conflicts
sudo netstat -tulpn | grep -E '(1883|8000|8080|8443)'

# Check logs for errors
docker-compose logs
```

**MQTT Connection Issues**
```bash
# Test MQTT connectivity
mosquitto_pub -h localhost -p 1883 -t test -m "hello"
mosquitto_sub -h localhost -p 1883 -t test

# Check Mosquitto logs
docker-compose logs mosquitto
```

**Certificate Issues**
```bash
# Regenerate certificates
cd certs
rm -f *.crt *.key *.pem
./make_certs.sh
cd ..
docker-compose restart
```

**Dashboard Not Loading**
```bash
# Check cloud service status
docker-compose ps cloud
docker-compose logs cloud

# Verify port accessibility
curl -k https://localhost:8443/health
```

#### Performance Issues

**High Memory Usage**
```bash
# Check container resources
docker stats

# Reduce logging verbosity
# Edit .env: LOG_LEVEL=WARNING

# Limit historical data
# Edit database queries in cloud service
```

**High CPU Usage**
```bash
# Reduce sensor publishing frequency
# Edit .env: SENSOR_*_INTERVAL=30

# Reduce attack intensity
# Use lower rates in attack scripts
```

### Security Considerations

#### Production Deployment
- **Never use default keys**: Generate new HMAC and encryption keys
- **Use proper certificates**: Replace self-signed with CA-issued certificates  
- **Network isolation**: Deploy in secure network segments
- **Access controls**: Implement proper authentication and authorization
- **Log monitoring**: Set up security event monitoring and alerting

#### Key Management
```bash
# Generate new HMAC key (32 bytes)
openssl rand -hex 32

# Generate new AES key (32 bytes)
openssl rand -hex 32

# Generate new JWT secret (32 bytes)
openssl rand -hex 32
```

### Data Collection

#### Evidence Gathering
```bash
# Create evidence package
mkdir evidence_$(date +%Y%m%d_%H%M%S)
cd evidence_*/

# Service logs
docker-compose logs > services.log

# Attack logs
cp -r ../logs/attacks/ .

# System state
docker-compose ps > service_status.txt
docker stats --no-stream > resource_usage.txt

# Configuration
cp ../.env config.txt
```

#### Report Generation
1. Collect logs from all attack scenarios
2. Extract security event counts from fog logs
3. Analyze attack success/failure rates
4. Document dashboard screenshots
5. Create timeline of attack vs. defense events

### Educational Outcomes

#### Learning Objectives Assessment
- **Vulnerability Identification**: Can students identify IoT attack vectors?
- **Defense Implementation**: Do students understand security mechanism effectiveness?
- **Log Analysis**: Can students interpret security logs and events?
- **Risk Assessment**: Do students grasp the impact of security misconfigurations?

#### Hands-on Exercises
1. **Attack Implementation**: Students run and analyze each attack type
2. **Security Configuration**: Students enable/disable security features
3. **Log Forensics**: Students analyze logs to identify attack patterns
4. **Improvement Recommendations**: Students propose additional security measures

This runbook provides comprehensive guidance for operating the IoT Security Simulation in educational and demonstration environments.