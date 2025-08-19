# Remote Greenhouse IoT Security Simulation

A comprehensive educational platform demonstrating IoT security vulnerabilities and defensive measures through a simulated remote greenhouse monitoring system.

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/LuisPassosRamos/IoT-Security-Simulation.git
cd IoT-Security-Simulation

# Generate certificates
cd certs && ./make_certs.sh && cd ..

# Start the simulation
docker-compose up --build -d

# Access dashboard
open https://localhost:8443
```

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Attack Demonstrations](#attack-demonstrations)
- [Security Features](#security-features)
- [Documentation](#documentation)
- [Contributing](#contributing)

## 🎯 Overview

This project provides a realistic IoT security simulation environment that demonstrates:

- **Common IoT vulnerabilities** and attack vectors
- **Effective security measures** and their implementation
- **Real-time attack/defense scenarios** with visual feedback
- **Educational insights** into IoT security best practices

The simulation models a remote greenhouse with multiple sensors, edge computing capabilities, and cloud-based data management, showcasing a complete IoT ecosystem with both vulnerable and secure configurations.

## ✨ Features

### 🔧 Core Components
- **IoT Sensors**: Temperature, humidity, and wind sensors with MQTT and CoAP protocols
- **Edge Computing**: Fog service with security validation and data processing
- **Cloud Platform**: Data storage, analytics, and web dashboard
- **MQTT Broker**: Mosquitto with both secure and insecure configurations

### 🛡️ Security Features
- **Message Authentication**: HMAC-SHA256 signatures
- **End-to-End Encryption**: AES-GCM for sensitive data
- **Replay Protection**: Cryptographic nonces and timestamp validation
- **Rate Limiting**: Token bucket and leaky bucket algorithms
- **Transport Security**: TLS/MQTTS and HTTPS with certificates

### 🎮 Attack Simulations
- **Replay Attacks**: Message capture and replay demonstrations
- **Spoofing Attacks**: Invalid signature and unauthorized messages
- **DoS Attacks**: High-frequency message flooding
- **CoAP Sniffing**: Passive monitoring and data extraction

### 📊 Interactive Dashboard
- **Real-time Visualization**: Chart.js-based telemetry charts
- **Security Monitoring**: Live security event tracking
- **Alert Management**: Threshold violations and system alerts
- **Attack/Defense Demo**: Interactive before/after comparison

## 🏗️ Architecture

```
┌─────────────┐    HTTPS/JWT    ┌─────────────┐
│   Cloud     │◄─────────────────│    Fog      │
│  Service    │                  │  Service    │
│             │                  │             │
│ • FastAPI   │                  │ • FastAPI   │
│ • SQLite    │                  │ • MQTT Sub  │
│ • Dashboard │                  │ • Security  │
└─────────────┘                  └─────┬───────┘
                                       │ MQTT
                          ┌────────────┼────────────┐
                          │            │            │
                    ┌─────▼─────┐ ┌────▼────┐ ┌────▼────┐
                    │   Temp    │ │Humidity │ │  Wind   │
                    │  Sensor   │ │ Sensor  │ │ Sensor  │
                    │           │ │         │ │         │
                    │ • MQTT    │ │ • MQTT  │ │ • MQTT  │
                    │ • CoAP    │ │ • CoAP  │ │ • CoAP  │
                    │ • Security│ │ • Security│ │ • Security│
                    └───────────┘ └─────────┘ └─────────┘
```

### Service Details

| Service | Port | Protocol | Function |
|---------|------|----------|----------|
| **Cloud** | 8443 | HTTPS | Web dashboard and API |
| **Fog** | 8000 | HTTP | Edge processing and validation |
| **Mosquitto** | 1883/8883 | MQTT/MQTTS | Message broker |
| **Sensors** | 5683 | CoAP | On-demand sensor readings |

## 🛠️ Installation

### Prerequisites
- **Docker** 20.10+ and **Docker Compose** 2.0+
- **4GB+ RAM** available
- **Open ports**: 1883, 8000, 8080, 8443, 5683-5685

### Step-by-Step Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/LuisPassosRamos/IoT-Security-Simulation.git
   cd IoT-Security-Simulation
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

3. **Generate SSL Certificates**
   ```bash
   cd certs
   ./make_certs.sh
   cd ..
   ```

4. **Build and Start Services**
   ```bash
   docker-compose up --build -d
   ```

5. **Verify Installation**
   ```bash
   docker-compose ps
   curl -k https://localhost:8443/health
   ```

## 🚀 Usage

### Basic Operation

1. **Access Dashboard**: Open https://localhost:8443
2. **Monitor Sensors**: View real-time telemetry data
3. **Check Security**: Review security events and alerts
4. **Run Demos**: Use the Security Demo mode for interactive comparisons

### Service Management

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f fog
docker-compose logs -f cloud

# Stop services
docker-compose down

# Restart with new config
docker-compose restart fog
```

### Configuration

Key environment variables in `.env`:

```bash
# Security Features
ENABLE_SIGNATURE_VERIFICATION=true
ENABLE_ENCRYPTION=true
ENABLE_RATE_LIMITING=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10

# Timing
TIMESTAMP_WINDOW_SECONDS=120
SENSOR_TEMP_INTERVAL=10
```

## ⚔️ Attack Demonstrations

### Running Attack Scripts

The simulation includes four main attack scenarios:

#### 1. Replay Attack
```bash
docker-compose run --rm attacker python replay.py \
  --mqtt-host mosquitto \
  --capture-duration 60 \
  --replay-delay 300
```

**Demonstrates**: Importance of message freshness and replay protection

#### 2. Message Spoofing
```bash
docker-compose run --rm attacker python spoofing.py \
  --mqtt-host mosquitto \
  --messages-per-sensor 20
```

**Demonstrates**: Need for message authentication and integrity

#### 3. DoS Attack
```bash
docker-compose run --rm attacker python dos.py \
  --mqtt-host mosquitto \
  --rate 100 \
  --duration 60
```

**Demonstrates**: Importance of rate limiting and resource protection

#### 4. CoAP Sniffing
```bash
docker-compose run --rm attacker python sniff_coap.py \
  --duration 300 \
  --interval 30
```

**Demonstrates**: Need for end-to-end encryption and secure protocols

### Automated Demo

For a complete demonstration experience:

```bash
./scripts/make_demo.sh
```

This script:
- Sets up the environment
- Runs baseline data collection
- Executes all attack scenarios
- Compares security on/off results
- Generates evidence reports

## 🔒 Security Features

### Authentication & Authorization
- **HMAC-SHA256**: Message authentication with per-sensor keys
- **JWT Tokens**: Service-to-service authentication
- **API Keys**: Dashboard and API access control

### Encryption & Privacy
- **AES-GCM**: End-to-end encryption for sensitive data
- **TLS 1.2+**: Transport layer security (MQTTS/HTTPS)
- **Certificate Management**: X.509 certificates with proper extensions

### Integrity & Freshness
- **Digital Signatures**: HMAC-based message integrity
- **Nonce Protection**: UUID-based replay attack prevention
- **Timestamp Validation**: Configurable time window enforcement

### Availability & Performance
- **Rate Limiting**: Token bucket and leaky bucket algorithms
- **Resource Monitoring**: CPU and memory usage tracking
- **Error Handling**: Graceful degradation and recovery

### Monitoring & Logging
- **Structured Logging**: JSON-formatted security events
- **Real-time Dashboards**: Visual security metrics
- **Audit Trails**: Complete event history and forensics

## 📚 Documentation

### Quick References
- **[Architecture Guide](docs/architecture.md)**: Detailed system design and components
- **[Operations Runbook](docs/runbook.md)**: Complete usage and troubleshooting guide
- **[Security Report Template](docs/report-template.md)**: Framework for assessment documentation

### Learning Materials
- **Interactive Tutorials**: Built-in dashboard tutorials
- **Attack Scenarios**: Step-by-step attack demonstrations
- **Security Analysis**: Before/after comparison tools
- **Best Practices**: IoT security recommendations

## 🔍 Key Learning Outcomes

### For Students
- **IoT Vulnerability Assessment**: Hands-on experience with real attack vectors
- **Security Implementation**: Understanding of cryptographic protections
- **Incident Response**: Log analysis and forensic techniques
- **Risk Management**: Business impact assessment of security failures

### For Educators
- **Demonstration Platform**: Ready-to-use security scenarios
- **Assessment Tools**: Built-in metrics and reporting
- **Customization Options**: Configurable attack parameters
- **Evidence Collection**: Automated logging and report generation

## 🧪 Testing the Security

### Scenario 1: Baseline (Security Enabled)
```bash
# Normal operation with all security features
./scripts/make_demo.sh --duration 300
```
**Expected Results**: All attacks blocked, clean security logs

### Scenario 2: Vulnerable System (Security Disabled)
```bash
# Edit .env to disable security features
ENABLE_SIGNATURE_VERIFICATION=false
ENABLE_ENCRYPTION=false
ENABLE_RATE_LIMITING=false

# Restart and test
docker-compose restart fog
./scripts/make_demo.sh --duration 300
```
**Expected Results**: All attacks succeed, security events logged

### Scenario 3: Partial Protection
```bash
# Enable only some security features
ENABLE_SIGNATURE_VERIFICATION=true
ENABLE_ENCRYPTION=false
ENABLE_RATE_LIMITING=true

# Test specific vulnerabilities
docker-compose restart fog
```
**Expected Results**: Mixed success rates, specific protections effective

## 📊 Performance Metrics

### System Requirements
- **CPU**: 2+ cores recommended
- **Memory**: 4GB+ RAM
- **Storage**: 10GB+ available space
- **Network**: Docker networking support

### Throughput Capacity
- **Normal Load**: 60 messages/minute per sensor
- **Burst Capacity**: 10 messages/burst per sensor
- **DoS Threshold**: 100+ messages/second triggers protection
- **Concurrent Users**: 10+ dashboard users supported

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

### Development Setup
```bash
# Fork and clone repository
git clone <your-fork-url>
cd IoT-Security-Simulation

# Create feature branch
git checkout -b feature/your-feature

# Make changes and test
docker-compose up --build -d
# Run tests and validation

# Submit pull request
```

### Areas for Contribution
- **New Attack Vectors**: Additional IoT vulnerability demonstrations
- **Security Enhancements**: Improved defensive measures
- **UI/UX Improvements**: Dashboard and visualization enhancements
- **Documentation**: Tutorials, guides, and educational content
- **Performance**: Optimization and scalability improvements

### Code Style
- **Python**: Follow PEP 8, use type hints
- **JavaScript**: ES6+, consistent formatting
- **Docker**: Multi-stage builds, minimal base images
- **Documentation**: Markdown with clear examples

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Eclipse Mosquitto**: MQTT broker implementation
- **FastAPI**: High-performance web framework
- **Chart.js**: Interactive data visualization
- **Bootstrap**: Responsive UI framework
- **Docker**: Containerization platform

## 📞 Support

- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and community support
- **Documentation**: Comprehensive guides in `/docs` directory
- **Examples**: Sample configurations and use cases

---

**Educational Use**: This simulation is designed for educational and demonstration purposes. Always follow responsible disclosure practices and obtain proper authorization before testing security tools in production environments.
