# ================================
# Prompt Injector – DeepSeek Handler
# ================================
FROM python:3.11-slim

WORKDIR /app

# System-Packages (curl) installieren
RUN apt-get update && apt-get install -y curl

# Python Dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt fastapi uvicorn httpx python-dotenv

# Code
COPY . .

EXPOSE 4300

HEALTHCHECK CMD curl -f http://localhost:4300/health || exit 1

CMD ["uvicorn", "mini_prompt_injector:app", "--host", "0.0.0.0", "--port", "4300"]