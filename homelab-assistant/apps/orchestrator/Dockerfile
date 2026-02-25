FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared packages
COPY packages/homelab_schemas/homelab_schemas /app/homelab_schemas
COPY packages/homelab_common/homelab_common /app/homelab_common

# Copy service code
COPY apps/orchestrator/orchestrator /app/orchestrator

# Create audit log and database directories
RUN mkdir -p /var/log/homelab-assistant && mkdir -p /var/lib/homelab-assistant

EXPOSE 8001

CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8001"]
