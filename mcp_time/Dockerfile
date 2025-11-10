# ================================
# MCP Time Tool
# ================================
FROM python:3.11-slim

WORKDIR /app

# System-Packages (curl) installieren
RUN apt-get update && apt-get install -y curl

# Python Dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Code
COPY . .

EXPOSE 4210

HEALTHCHECK CMD curl -f http://localhost:4210/health || exit 1

CMD ["uvicorn", "mcp_time:app", "--host", "0.0.0.0", "--port", "4210"]
