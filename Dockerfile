# Stage 1: Build the Vue frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# Stage 2: Create the final Python production container
FROM python:3.10-slim
WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code and netrunner entrypoint
COPY backend/ ./backend/
COPY netrunner.py ./

# Copy compiled frontend assets from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Set up the data directory and volume
RUN mkdir -p /app/data
VOLUME /app/data

# Environment variables
ENV PORT=8000
ENV DATABASE_URL=sqlite+aiosqlite:///app/data/netrunner.db

EXPOSE 8000

CMD ["python3", "netrunner.py", "--host", "0.0.0.0", "--port", "8000"]
