# IoT Security Simulation Architecture

## Overview

The IoT Security Simulation is a comprehensive educational platform that demonstrates common IoT security vulnerabilities and their corresponding defensive measures. The system simulates a remote greenhouse monitoring environment with multiple sensors, edge computing capabilities, and cloud-based data management.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUD SERVICE                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Web Dashboard │  │   REST API      │  │   Database      │ │
│  │   (Chart.js)    │  │   (FastAPI)     │  │   (SQLite)      │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│              │                 │                        │      │
│              └─────────────────┼────────────────────────┘      │
│                               │ HTTPS/JWT                      │
└───────────────────────────────┼────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
┌───────────────────┼───────────┼───────────┼───────────────────┐
│                   │    FOG SERVICE        │                   │
│  ┌────────────────▼──┐  ┌────────────────▼──┐  ┌─────────────┐ │
│  │   MQTT Worker     │  │   CoAP Client     │  │   Security  │ │
│  │   (Subscriber)    │  │   (On-demand)     │  │   Engine    │ │
│  └────────────────┬──┘  └────────────────┬──┘  └─────────────┘ │
│                   │                      │                     │
│       ┌───────────┼──────────────────────┼───────────┐         │
│       │           │      VALIDATION      │           │         │
│       │  ┌────────▼──┐  ┌──────────────┐  │  ┌────────▼──────┐ │
│       │  │Rate Limit │  │HMAC/AES-GCM  │  │  │Timestamp/Nonce│ │
│       │  │(Token/    │  │(Signature &  │  │  │(Replay Protect│ │
│       │  │ Leaky)    │  │ Encryption)  │  │  │ & Clock Skew) │ │
│       │  └───────────┘  └──────────────┘  │  └───────────────┘ │
│       └─────────────────────────────────────────────────────┘   │
└─────────────────────┼───────────────────────┼───────────────────┘
                      │ MQTT (QoS 1)          │ CoAP
                      │                       │
┌─────────────────────┼───────────────────────┼───────────────────┐
│                MQTT BROKER                  │                   │
│  ┌──────────────────▼─────────────────────┐ │                   │
│  │           Eclipse Mosquitto            │ │                   │
│  │   ┌─────────────┐   ┌─────────────┐   │ │                   │
│  │   │ Port 1883   │   │ Port 8883   │   │ │                   │
│  │   │ (Insecure)  │   │ (MQTTS/TLS) │   │ │                   │
│  │   └─────────────┘   └─────────────┘   │ │                   │
│  └────────────────────────────────────────┘ │                   │
└─────────────────────┼────────────────────────┼───────────────────┘
                      │ MQTT Publish          │ CoAP GET
                      │                       │
        ┌─────────────┼────────┬──────────────┼────────────┐
        │             │        │              │            │
┌───────▼──┐  ┌───────▼──┐  ┌──▼──────┐  ┌───▼────────┐  │
│TEMP      │  │HUMIDITY  │  │WIND     │  │CoAP Server │  │
│SENSOR    │  │SENSOR    │  │SENSOR   │  │(Port 5683) │  │
│          │  │          │  │         │  │            │  │
│┌────────┐│  │┌────────┐│  │┌───────┐│  │┌──────────┐│  │
││Security││  ││Security││  ││Security││  ││ Current  ││  │
││- HMAC  ││  ││- HMAC  ││  ││- HMAC ││  ││ Reading  ││  │
││-AES-GCM││  ││-AES-GCM││  ││-AES-GCM││  ││ Endpoint ││  │
││- Nonce ││  ││- Nonce ││  ││- Nonce││  ││          ││  │
│└────────┘│  │└────────┘│  │└───────┘│  │└──────────┘│  │
└──────────┘  └──────────┘  └─────────┘  └────────────┘  │
                                                         │
┌────────────────────────────────────────────────────────┴──┐
│                  ATTACK VECTORS                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────┐ │
│  │   Replay    │ │  Spoofing   │ │     DoS     │ │ CoAP │ │
│  │   Attack    │ │   Attack    │ │   Attack    │ │Sniff │ │
│  │             │ │             │ │             │ │      │ │
│  │ • Capture   │ │ • Invalid   │ │ • Message   │ │• Pass│ │
│  │ • Delay     │ │   Signature │ │   Flooding  │ │  ive │ │
│  │ • Replay    │ │ • Tampered  │ │ • Rate      │ │• Disc│ │
│  │             │ │   Data      │ │   Exceed    │ │  ov  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────┘ │
└───────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Sensor Layer

**Temperature Sensor (temp-01)**
- **Function**: Monitors greenhouse temperature
- **Publishing**: Every 10 seconds to `greenhouse/temp-01/telemetry`
- **CoAP Endpoint**: `coap://sensor-temp:5683/current`
- **Range**: 15°C - 35°C (normal), alerts outside range

**Humidity Sensor (humidity-01)**
- **Function**: Monitors greenhouse humidity
- **Publishing**: Every 15 seconds to `greenhouse/humidity-01/telemetry`
- **CoAP Endpoint**: `coap://sensor-humidity:5683/current`
- **Range**: 20% - 80% (normal), alerts outside range

**Wind Sensor (wind-01)**
- **Function**: Monitors greenhouse airflow
- **Publishing**: Every 12 seconds to `greenhouse/wind-01/telemetry`
- **CoAP Endpoint**: `coap://sensor-wind:5683/current`
- **Range**: 0 - 20 m/s (normal), critical alerts above 20 m/s

**Security Features (Per Sensor)**
- **Message Integrity**: HMAC-SHA256 with unique keys per sensor
- **Confidentiality**: Optional AES-GCM encryption for sensitive data
- **Replay Protection**: Cryptographic nonces (UUID4) with each message
- **Clock Synchronization**: ISO8601 timestamps with configurable skew tolerance

### 2. Communication Layer

**MQTT Broker (Eclipse Mosquitto)**
- **Insecure Port**: 1883 (for demonstration of unprotected communications)
- **Secure Port**: 8883 (MQTTS with TLS certificates)
- **QoS Level**: 1 (at-least-once delivery)
- **Topic Structure**: `greenhouse/{sensor_id}/{message_type}`
- **Access Control**: ACL-based permissions per client/sensor

**Message Format**:
```json
{
  "sensor_id": "temp-01",
  "ts": "2024-01-01T12:00:00Z",
  "type": "temperature",
  "value": 25.5,
  "unit": "°C",
  "nonce": "uuid4-string",
  "enc": false,
  "sig": "base64-hmac-signature",
  "ver": 1
}
```

**CoAP Protocol**
- **Port**: 5683 (standard CoAP)
- **Method**: GET requests to `/current` endpoint
- **Response**: Same JSON format as MQTT messages
- **Use Case**: On-demand polling by fog service

### 3. Edge Layer (Fog Service)

**MQTT Worker Component**
- **Subscription**: `greenhouse/+/telemetry` (all sensor telemetry)
- **Validation Pipeline**:
  1. Message structure validation (Pydantic models)
  2. HMAC signature verification (sensor-specific keys)
  3. Timestamp validation (configurable window ±120s)
  4. Nonce replay protection (LRU cache)
  5. Rate limiting (token bucket algorithm)
  6. AES-GCM decryption (if enabled)

**CoAP Client Component**
- **Function**: On-demand sensor polling
- **Endpoints**: `/current`, `/status`, `/health`
- **Use Case**: Direct sensor queries bypassing MQTT

**Security Engine**
- **Rate Limiting**: Token bucket and leaky bucket algorithms
  - Default: 60 messages/minute per sensor
  - Burst capacity: 10 messages
- **Crypto Operations**: 
  - HMAC-SHA256 verification
  - AES-GCM decryption
  - JWT token generation for cloud communication
- **Event Logging**: Structured JSON logs for all security events

**Cloud Communication**
- **Protocol**: HTTPS with JWT authentication
- **Endpoint**: `POST /api/ingest`
- **Payload**: Validated and enriched telemetry data
- **Retries**: Configurable retry logic for failed transmissions

### 4. Cloud Layer

**FastAPI Application**
- **Authentication**: JWT tokens + API key validation
- **Database**: SQLite with SQLModel (async ORM)
- **Endpoints**:
  - `/api/ingest` - Telemetry data ingestion
  - `/api/readings` - Historical data queries
  - `/api/alerts` - Alert management
  - `/api/events` - System event logs
  - `/api/auth` - Authentication services

**Web Dashboard**
- **Framework**: Bootstrap 5 + Chart.js
- **Features**:
  - Real-time telemetry visualization
  - Alert management interface
  - Security event monitoring
  - Interactive attack/defense demonstrations
- **Charts**: Time-series plots with configurable time ranges
- **Security Demo**: Before/after comparison mode

**Database Schema**
- **Sensors**: Metadata and status
- **TelemetryReading**: Time-series sensor data
- **Alert**: Threshold violations and system alerts
- **Event**: System operational events
- **SecurityEvent**: Security-specific events and threats

### 5. Attack Simulation Layer

**Replay Attack (replay.py)**
- **Method**: Capture legitimate messages, replay after delay
- **Detection**: Nonce-based replay protection + timestamp validation
- **Demo**: Shows importance of message freshness guarantees

**Spoofing Attack (spoofing.py)**
- **Method**: Send messages with invalid/missing HMAC signatures
- **Detection**: Cryptographic signature verification
- **Demo**: Shows importance of message authentication

**DoS Attack (dos.py)**
- **Method**: High-frequency message flooding
- **Detection**: Rate limiting algorithms
- **Demo**: Shows importance of resource protection

**CoAP Sniffing (sniff_coap.py)**
- **Method**: Passive monitoring of unencrypted CoAP traffic
- **Detection**: End-to-end encryption
- **Demo**: Shows importance of confidentiality

## Security Mechanisms

### 1. Message Integrity
- **Algorithm**: HMAC-SHA256
- **Key Management**: Pre-shared keys per sensor (32 bytes hex)
- **Canonical Form**: Deterministic JSON serialization
- **Verification**: Real-time at fog service

### 2. Confidentiality
- **Algorithm**: AES-GCM (256-bit keys)
- **Mode**: Authenticated encryption
- **Nonce**: 96-bit random nonces
- **Scope**: Optional encryption of sensitive sensor values

### 3. Replay Protection
- **Nonces**: UUID4 with each message
- **Cache**: LRU cache of seen nonces (configurable size)
- **Timestamps**: ISO8601 with configurable time window
- **Clock Skew**: Tolerance for clock synchronization issues

### 4. Rate Limiting
- **Algorithms**: Token bucket and leaky bucket
- **Granularity**: Per-sensor rate limiting
- **Configuration**: Messages per minute + burst capacity
- **Actions**: Log security events, drop excess messages

### 5. Transport Security
- **MQTTS**: TLS 1.2+ with X.509 certificates
- **HTTPS**: TLS 1.2+ for cloud communication
- **Certificates**: Self-signed CA with proper SAN extensions

## Data Flow

### Normal Operation
1. Sensor generates reading with timestamp and nonce
2. Sensor signs message with HMAC using pre-shared key
3. Optional: Sensor encrypts sensitive data with AES-GCM
4. Sensor publishes to MQTT broker via QoS 1
5. Fog service receives and validates message:
   - Structure validation
   - Signature verification
   - Timestamp window check
   - Nonce replay check
   - Rate limit enforcement
6. Valid messages forwarded to cloud via HTTPS
7. Cloud stores data and triggers alerts if thresholds exceeded
8. Dashboard displays real-time data and security events

### Attack Scenarios
1. **Replay Attack**: Attacker captures and replays old messages
   - Defense: Nonce cache detects replayed messages
2. **Spoofing Attack**: Attacker sends messages with invalid signatures
   - Defense: HMAC verification rejects unsigned/invalid messages
3. **DoS Attack**: Attacker floods system with high-frequency messages
   - Defense: Rate limiting drops excess messages
4. **Eavesdropping**: Attacker monitors unencrypted communications
   - Defense: TLS transport + AES-GCM encryption

## Deployment Architecture

### Docker Compose Services
- **mosquitto**: MQTT broker with TLS configuration
- **sensor-temp**: Temperature sensor simulator
- **sensor-humidity**: Humidity sensor simulator  
- **sensor-wind**: Wind sensor simulator
- **fog**: Edge processing service
- **cloud**: Cloud data management service
- **attacker**: Attack simulation tools (on-demand)

### Network Configuration
- **Bridge Network**: Isolated Docker network (172.20.0.0/16)
- **Port Mapping**: External access to key services
- **Service Discovery**: DNS-based service names

### Volume Mounts
- **Certificates**: Shared TLS certificates across services
- **Logs**: Persistent logging for analysis
- **Database**: SQLite database persistence

## Educational Objectives

1. **Demonstrate IoT Vulnerabilities**: Show real attack vectors
2. **Illustrate Security Measures**: Prove effectiveness of defenses
3. **Hands-on Learning**: Interactive attack/defense scenarios
4. **Best Practices**: Showcase proper IoT security implementation
5. **Incident Response**: Log analysis and forensic techniques