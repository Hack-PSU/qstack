FROM node:18-alpine AS frontend-builder

WORKDIR /app/client

# Copy frontend package files
COPY client/package*.json ./
RUN npm ci && npm cache clean --force

# Copy frontend source
COPY client/ ./

# Build frontend
RUN npm run build && rm -rf src node_modules

FROM python:3.9-slim-bullseye

# Install PostgreSQL and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn && \
    rm -rf ~/.cache/pip

# Remove build dependencies after Python packages are installed
RUN apt-get purge -y --auto-remove gcc python3-dev && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY server/ ./server/
COPY wsgi.py .

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/client/dist ./client/dist

# Create PostgreSQL data directory
RUN mkdir -p /var/lib/postgresql/data && \
    chown -R postgres:postgres /var/lib/postgresql

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=3001

# Copy startup script
COPY start.prod.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port
EXPOSE 3001

# Volume for PostgreSQL data persistence
VOLUME ["/var/lib/postgresql/data"]

# Start script
CMD ["/app/start.sh"]
