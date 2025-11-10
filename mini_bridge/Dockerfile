# ================================
# Mini Bridge – MCP Server
# ================================
FROM python:3.11-slim

WORKDIR /app

# System-Packages (curl) installieren
RUN apt-get update && apt-get install -y curl

# Python Requirements installieren
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt 

# Code kopieren
COPY . .

EXPOSE 4100

HEALTHCHECK CMD curl -f http://localhost:4100/health || exit 1

CMD ["uvicorn", "mini_bridge:app", "--host", "0.0.0.0", "--port", "4100"]