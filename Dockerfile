# Stage 1: Build the Vue frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# Stage 2: Build the Go agent
FROM golang:1.24-alpine AS agent-builder
RUN apk add --no-cache clang llvm linux-headers bpftool make libbpf-dev
WORKDIR /app/agent
COPY agent/ ./
RUN go mod tidy
# Generate eBPF bindings
RUN go generate ./...
RUN go test ./...
# Build AMD64
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o /netrunner-agent-amd64 main.go
# Build ARM64
RUN CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o /netrunner-agent-arm64 main.go

# Stage 3: Build Python wheels, including native YARA/Unicorn extensions
FROM python:3.14-slim-bookworm AS python-deps
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./backend/
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r backend/requirements.txt

# Stage 4: Create the final Python production container
FROM python:3.14-slim-bookworm
WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    docker.io \
    docker-compose \
    libpcap0.8 \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt ./backend/
COPY --from=python-deps /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r backend/requirements.txt \
    && rm -rf /wheels

# Copy backend code and netrunner entrypoint
COPY backend/ ./backend/
COPY protocols/ ./protocols/
COPY netrunner.py ./

# Copy compiled frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy compiled Go agents from Stage 2
RUN mkdir -p /app/bin
COPY --from=agent-builder /netrunner-agent-amd64 /app/bin/
COPY --from=agent-builder /netrunner-agent-arm64 /app/bin/

# Set up the data directory and volume
RUN mkdir -p /app/data
VOLUME /app/data

# Environment variables
ENV PORT=8000
ENV DATABASE_URL=sqlite+aiosqlite:///app/data/netrunner.db

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/ready', timeout=3)" || exit 1

CMD ["python3", "netrunner.py", "--host", "0.0.0.0", "--port", "8000"]
