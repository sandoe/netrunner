#!/bin/bash
set -e
echo "Building agent..."
docker run --rm -v $(pwd):/app -w /app/agent golang:1.24-alpine sh -c "CGO_ENABLED=0 go build -o netrunner-agent -ldflags \"-extldflags '-static'\" . && cp netrunner-agent ../bin/"

echo "Deploying to Linux..."
scp bin/netrunner-agent aso@192.168.1.17:/tmp/netrunner-agent
ssh aso@192.168.1.17 "echo Fall2025 | sudo -S mv /tmp/netrunner-agent /usr/local/bin/netrunner-agent && sudo systemctl restart netrunner-agent"

echo "Deploying to RPi..."
scp bin/netrunner-agent aso@192.168.1.29:/tmp/netrunner-agent
ssh aso@192.168.1.29 "echo Fall2025 | sudo -S mv /tmp/netrunner-agent /usr/local/bin/netrunner-agent && sudo systemctl restart netrunner-agent"

echo "Deployment complete."
