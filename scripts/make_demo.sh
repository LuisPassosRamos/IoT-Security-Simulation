#!/bin/bash

# Demo Runner Script for IoT Security Simulation
# Automates the complete security demonstration

set -e

SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "IoT Security Simulation - Demo Runner"
echo "===================================="
echo ""

# Configuration
DEMO_DURATION=300  # 5 minutes per phase
ATTACK_TYPES=("replay" "spoofing" "dos" "sniff_coap")
LOGS_DIR="logs/demo"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(printf '=%.0s' $(seq 1 ${#1}))"
}

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    print_header "Checking Dependencies"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    print_info "Docker is running"
    
    # Check if Docker Compose is available
    if ! command -v docker-compose > /dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose."
        exit 1
    fi
    print_info "Docker Compose is available"
    
    # Check if required files exist
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml not found. Please ensure you're in the project root."
        exit 1
    fi
    print_info "Docker Compose configuration found"
    
    echo ""
}

setup_environment() {
    print_header "Setting Up Environment"
    
    # Generate certificates if they don't exist
    if [ ! -f "certs/ca.crt" ]; then
        print_info "Generating SSL certificates..."
        cd certs
        ./make_certs.sh
        cd ..
    else
        print_info "SSL certificates already exist"
    fi
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_info "Creating .env file from template..."
        cp .env.example .env
    else
        print_info ".env file already exists"
    fi
    
    # Create logs directory structure
    mkdir -p logs/attacks logs/demo logs/system
    print_info "Created log directories"
    
    echo ""
}

start_services() {
    print_header "Starting IoT Security Simulation Services"
    
    print_info "Building and starting services..."
    docker-compose up --build -d
    
    print_info "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    print_info "Checking service health..."
    
    # Check mosquitto
    if docker-compose ps mosquitto | grep -q "Up"; then
        print_info "✓ MQTT Broker (Mosquitto) is running"
    else
        print_warning "✗ MQTT Broker may not be ready"
    fi
    
    # Check sensors
    for sensor in sensor-temp sensor-humidity sensor-wind; do
        if docker-compose ps $sensor | grep -q "Up"; then
            print_info "✓ $sensor is running"
        else
            print_warning "✗ $sensor may not be ready"
        fi
    done
    
    # Check fog service
    if docker-compose ps fog | grep -q "Up"; then
        print_info "✓ Fog service is running"
    else
        print_warning "✗ Fog service may not be ready"
    fi
    
    # Check cloud service
    if docker-compose ps cloud | grep -q "Up"; then
        print_info "✓ Cloud service is running"
    else
        print_warning "✗ Cloud service may not be ready"
    fi
    
    echo ""
    print_info "Services started successfully!"
    print_info "Dashboard URL: https://localhost:8443 (or http://localhost:8080)"
    echo ""
}

run_baseline_collection() {
    print_header "Phase 1: Baseline Data Collection (No Attacks)"
    
    print_info "Collecting baseline telemetry data for $DEMO_DURATION seconds..."
    print_info "This establishes normal system behavior before attacks."
    
    local start_time=$(date +%s)
    local log_file="$LOGS_DIR/baseline_$(date +%Y%m%d_%H%M%S).log"
    
    # Monitor system for baseline period
    timeout $DEMO_DURATION docker-compose logs -f fog cloud > "$log_file" 2>&1 &
    local monitor_pid=$!
    
    # Wait for baseline period
    sleep $DEMO_DURATION
    
    # Stop monitoring
    kill $monitor_pid 2>/dev/null || true
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    print_info "Baseline collection completed ($duration seconds)"
    print_info "Baseline logs saved to: $log_file"
    echo ""
}

run_attack_demonstrations() {
    print_header "Phase 2: Attack Demonstrations"
    
    for attack in "${ATTACK_TYPES[@]}"; do
        print_info "Running $attack attack demonstration..."
        
        local attack_log="$LOGS_DIR/${attack}_demo_$(date +%Y%m%d_%H%M%S).log"
        
        case $attack in
            "replay")
                print_info "Demonstrating replay attacks (message replay after delay)"
                docker-compose run --rm attacker python replay.py \
                    --mqtt-host mosquitto \
                    --capture-duration 60 \
                    --replay-delay 10 \
                    --replay-count 3 > "$attack_log" 2>&1
                ;;
            "spoofing")
                print_info "Demonstrating message spoofing (invalid signatures)"
                docker-compose run --rm attacker python spoofing.py \
                    --mqtt-host mosquitto \
                    --duration 120 \
                    --messages-per-sensor 10 > "$attack_log" 2>&1
                ;;
            "dos")
                print_info "Demonstrating DoS attacks (message flooding)"
                docker-compose run --rm attacker python dos.py \
                    --mqtt-host mosquitto \
                    --duration 60 \
                    --rate 50 \
                    --clients 3 > "$attack_log" 2>&1
                ;;
            "sniff_coap")
                print_info "Demonstrating CoAP sniffing (passive monitoring)"
                docker-compose run --rm attacker python sniff_coap.py \
                    --duration 120 \
                    --interval 10 > "$attack_log" 2>&1
                ;;
        esac
        
        print_info "$attack attack completed. Log: $attack_log"
        echo ""
        
        # Small delay between attacks
        sleep 10
    done
}

run_security_comparison() {
    print_header "Phase 3: Security Features Comparison"
    
    print_info "Comparing system behavior with and without security features..."
    
    # This would involve:
    # 1. Disabling security features
    # 2. Running attacks again
    # 3. Re-enabling security features
    # 4. Comparing results
    
    print_info "Security comparison phase would involve:"
    print_info "  1. Disabling HMAC verification, encryption, rate limiting"
    print_info "  2. Re-running attack scenarios"
    print_info "  3. Re-enabling security features"
    print_info "  4. Comparing attack success rates"
    print_info ""
    print_info "For this demo, check the dashboard's Security Demo mode"
    print_info "which provides an interactive comparison tool."
    
    echo ""
}

collect_evidence() {
    print_header "Phase 4: Evidence Collection"
    
    local evidence_dir="$LOGS_DIR/evidence_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$evidence_dir"
    
    print_info "Collecting evidence for analysis..."
    
    # Collect service logs
    print_info "Collecting service logs..."
    docker-compose logs mosquitto > "$evidence_dir/mosquitto.log" 2>&1
    docker-compose logs fog > "$evidence_dir/fog.log" 2>&1
    docker-compose logs cloud > "$evidence_dir/cloud.log" 2>&1
    
    # Collect attack logs
    print_info "Collecting attack logs..."
    if [ -d "logs/attacks" ]; then
        cp -r logs/attacks "$evidence_dir/"
    fi
    
    # Collect system stats
    print_info "Collecting system statistics..."
    docker stats --no-stream > "$evidence_dir/docker_stats.txt" 2>&1
    docker-compose ps > "$evidence_dir/service_status.txt" 2>&1
    
    # Create summary report
    print_info "Creating summary report..."
    cat > "$evidence_dir/demo_summary.txt" << EOF
IoT Security Simulation Demo Summary
===================================
Date: $(date)
Duration: $(($DEMO_DURATION * 3)) seconds (excluding setup)

Attack Types Demonstrated:
$(printf '%s\n' "${ATTACK_TYPES[@]}" | sed 's/^/- /')

Evidence Files:
- mosquitto.log: MQTT broker logs
- fog.log: Edge processing service logs  
- cloud.log: Cloud service logs
- attacks/: Attack demonstration logs
- docker_stats.txt: Container resource usage
- service_status.txt: Service status during demo

Key Findings:
- Check fog.log for security validation messages
- Check attacks/ directory for attack success/failure rates
- Compare system behavior before and during attacks
- Review dashboard metrics at https://localhost:8443

Next Steps:
1. Analyze logs for security event patterns
2. Review attack success rates with/without security
3. Generate formal security assessment report
4. Use findings to improve IoT security posture
EOF
    
    print_info "Evidence collection completed!"
    print_info "Evidence directory: $evidence_dir"
    echo ""
}

generate_report() {
    print_header "Demo Completion Report"
    
    echo -e "${GREEN}IoT Security Simulation Demo Completed Successfully!${NC}"
    echo ""
    echo "Demo Summary:"
    echo "============="
    echo "• Baseline data collection: ✓ Completed"
    echo "• Attack demonstrations: ✓ Completed (${#ATTACK_TYPES[@]} attack types)"
    echo "• Evidence collection: ✓ Completed"
    echo ""
    echo "Access Points:"
    echo "=============="
    echo "• Web Dashboard: https://localhost:8443"
    echo "• Alternative HTTP: http://localhost:8080"
    echo "• MQTT Broker: localhost:1883 (insecure) / localhost:8883 (secure)"
    echo ""
    echo "Key Files:"
    echo "=========="
    echo "• Demo logs: $LOGS_DIR/"
    echo "• Attack logs: logs/attacks/"
    echo "• Service logs: Use 'docker-compose logs [service]'"
    echo ""
    echo "What to Do Next:"
    echo "================"
    echo "1. Open the web dashboard to see real-time data"
    echo "2. Use the Security Demo mode for interactive comparison"
    echo "3. Review attack logs to understand security effectiveness"
    echo "4. Analyze fog service logs for security validation results"
    echo "5. Use findings to create your security assessment report"
    echo ""
    echo "To stop the demo:"
    echo "=================="
    echo "docker-compose down"
    echo ""
}

cleanup_on_exit() {
    print_info "Cleaning up..."
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}

main() {
    trap cleanup_on_exit EXIT
    
    echo "Starting IoT Security Simulation Demo..."
    echo "This demo will run for approximately $(( DEMO_DURATION * 3 / 60 )) minutes."
    echo ""
    
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Demo cancelled."
        exit 0
    fi
    
    check_dependencies
    setup_environment
    start_services
    
    print_info "Demo phases will begin in 30 seconds. You can monitor progress in the dashboard."
    sleep 30
    
    run_baseline_collection
    run_attack_demonstrations
    run_security_comparison
    collect_evidence
    generate_report
    
    print_info "Demo completed! Services are still running for analysis."
    print_info "Use 'docker-compose down' to stop all services when finished."
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --duration)
            DEMO_DURATION="$2"
            shift 2
            ;;
        --help)
            echo "IoT Security Simulation Demo Runner"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --duration SECONDS    Duration of each demo phase (default: 300)"
            echo "  --help               Show this help message"
            echo ""
            echo "This script automates the complete IoT security demonstration:"
            echo "1. Sets up the simulation environment"
            echo "2. Starts all services"
            echo "3. Collects baseline data"
            echo "4. Runs attack demonstrations"
            echo "5. Compares security features"
            echo "6. Collects evidence and generates reports"
            echo ""
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Run main function
main