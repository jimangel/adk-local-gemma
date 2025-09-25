# Build stage - use full Python image with build tools
FROM python:3.13 AS builder

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage - use slim Python for smaller size
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy only the ADK agent code
COPY --chown=appuser:appuser kubernetes_agent/ ./kubernetes_agent/

# Switch to non-root user
USER appuser

# Add user's local bin to PATH so adk command is available
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port
EXPOSE 8081

# Environment variables
ENV PORT=8081
ENV HOST=0.0.0.0

# Run ADK web
CMD ["sh", "-c", "adk web --host ${HOST} --port ${PORT}"]
