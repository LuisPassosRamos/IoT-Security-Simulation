#!/bin/bash

# Certificate Generation Script for IoT Security Simulation
# Generates self-signed certificates for HTTPS and MQTTS

set -e

CERTS_DIR="$(dirname "$0")"
cd "$CERTS_DIR"

echo "IoT Security Simulation - Certificate Generation"
echo "================================================"

# Create certificates directory if it doesn't exist
mkdir -p .

# Configuration
CA_DAYS=3650      # 10 years
CERT_DAYS=365     # 1 year
KEY_SIZE=2048
COUNTRY="US"
STATE="California"
CITY="San Francisco"
ORG="IoT Security Simulation"
ORG_UNIT="Security Lab"

echo "Generating certificates with the following configuration:"
echo "  Key Size: ${KEY_SIZE} bits"
echo "  CA Valid: ${CA_DAYS} days"
echo "  Cert Valid: ${CERT_DAYS} days"
echo "  Organization: ${ORG}"
echo ""

# 1. Generate CA private key
echo "1. Generating Certificate Authority (CA) private key..."
openssl genrsa -out ca.key ${KEY_SIZE}

# 2. Generate CA certificate
echo "2. Generating Certificate Authority (CA) certificate..."
openssl req -new -x509 -days ${CA_DAYS} -key ca.key -out ca.crt -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${ORG_UNIT}/CN=IoT Security Simulation CA"

# 3. Generate server private key
echo "3. Generating server private key..."
openssl genrsa -out server.key ${KEY_SIZE}

# 4. Generate server certificate signing request
echo "4. Generating server certificate signing request..."
openssl req -new -key server.key -out server.csr -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${ORG_UNIT}/CN=cloud"

# 5. Create server certificate extensions file
echo "5. Creating server certificate extensions..."
cat > server.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = cloud
DNS.2 = localhost
DNS.3 = *.localhost
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
EOF

# 6. Generate server certificate signed by CA
echo "6. Generating server certificate..."
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days ${CERT_DAYS} -extensions v3_req -extfile server.ext

# 7. Generate client private key (for MQTT clients)
echo "7. Generating client private key..."
openssl genrsa -out client.key ${KEY_SIZE}

# 8. Generate client certificate signing request
echo "8. Generating client certificate signing request..."
openssl req -new -key client.key -out client.csr -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${ORG_UNIT}/CN=iot-client"

# 9. Generate client certificate signed by CA
echo "9. Generating client certificate..."
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days ${CERT_DAYS}

# 10. Generate MQTT broker certificate
echo "10. Generating MQTT broker certificate..."
openssl genrsa -out mqtt-server.key ${KEY_SIZE}
openssl req -new -key mqtt-server.key -out mqtt-server.csr -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${ORG_UNIT}/CN=mosquitto"

# Create MQTT server extensions
cat > mqtt-server.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = mosquitto
DNS.2 = localhost
IP.1 = 127.0.0.1
EOF

openssl x509 -req -in mqtt-server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out mqtt-server.crt -days ${CERT_DAYS} -extensions v3_req -extfile mqtt-server.ext

# 11. Set appropriate permissions
echo "11. Setting file permissions..."
chmod 600 *.key
chmod 644 *.crt *.pem

# 12. Cleanup temporary files
echo "12. Cleaning up temporary files..."
rm -f *.csr *.ext *.srl

# 13. Create PEM bundle files
echo "13. Creating PEM bundle files..."
cat ca.crt > ca-bundle.pem
cat server.crt server.key > server-bundle.pem
cat client.crt client.key > client-bundle.pem

# 14. Display certificate information
echo ""
echo "Certificate generation completed successfully!"
echo "============================================="
echo ""
echo "Generated files:"
echo "  ca.crt          - Certificate Authority certificate"
echo "  ca.key          - Certificate Authority private key"
echo "  server.crt      - Server certificate (for cloud service)"
echo "  server.key      - Server private key"
echo "  client.crt      - Client certificate (for IoT devices)"
echo "  client.key      - Client private key"
echo "  mqtt-server.crt - MQTT broker certificate"
echo "  mqtt-server.key - MQTT broker private key"
echo "  ca-bundle.pem   - CA certificate bundle"
echo "  server-bundle.pem - Server certificate bundle"
echo "  client-bundle.pem - Client certificate bundle"
echo ""
echo "Certificate Details:"
echo "==================="

# Display server certificate details
echo "Server Certificate (cloud service):"
openssl x509 -in server.crt -text -noout | grep -A 2 "Subject:"
openssl x509 -in server.crt -text -noout | grep -A 5 "Subject Alternative Name"
echo "  Valid from: $(openssl x509 -in server.crt -noout -startdate | cut -d= -f2)"
echo "  Valid to:   $(openssl x509 -in server.crt -noout -enddate | cut -d= -f2)"
echo ""

# Display MQTT certificate details
echo "MQTT Server Certificate:"
openssl x509 -in mqtt-server.crt -text -noout | grep -A 2 "Subject:"
echo "  Valid from: $(openssl x509 -in mqtt-server.crt -noout -startdate | cut -d= -f2)"
echo "  Valid to:   $(openssl x509 -in mqtt-server.crt -noout -enddate | cut -d= -f2)"
echo ""

echo "Usage Instructions:"
echo "=================="
echo "1. For HTTPS (cloud service):"
echo "   - Use server.crt and server.key"
echo "   - Configure your web server to use these certificates"
echo ""
echo "2. For MQTTS (MQTT broker):"
echo "   - Use mqtt-server.crt and mqtt-server.key for the broker"
echo "   - Use ca.crt for client certificate verification"
echo "   - Use client.crt and client.key for client authentication"
echo ""
echo "3. For development/testing:"
echo "   - Add ca.crt to your system's trusted certificate store"
echo "   - Or configure applications to trust ca.crt"
echo ""
echo "WARNING: These are self-signed certificates for development/demo use only!"
echo "Do not use in production environments!"
echo ""

# Create a quick verification test
echo "Verification Test:"
echo "=================="
echo -n "Testing server certificate chain... "
if openssl verify -CAfile ca.crt server.crt > /dev/null 2>&1; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

echo -n "Testing MQTT server certificate chain... "
if openssl verify -CAfile ca.crt mqtt-server.crt > /dev/null 2>&1; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

echo -n "Testing client certificate chain... "
if openssl verify -CAfile ca.crt client.crt > /dev/null 2>&1; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

echo ""
echo "Certificate generation and verification completed!"
echo "You can now start the IoT Security Simulation with TLS/SSL support."