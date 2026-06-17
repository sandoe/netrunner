#!/bin/bash
set -e
docker run --rm -v $(pwd):/app -w /app golang:alpine sh -c "
  apk add --no-cache gcc musl-dev linux-headers
  cd agent
  GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o ../backend/bin/netrunner-agent-amd64
  GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -o ../backend/bin/netrunner-agent-arm64
"
