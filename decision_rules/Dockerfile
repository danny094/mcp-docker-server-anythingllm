FROM python:3.11-slim

WORKDIR /app

# Systemabhängigkeiten für numpy
RUN apt-get update && apt-get install -y build-essential

COPY decision_engine.py /app/
COPY requirements.txt /app/
COPY .env /app/
COPY db /app/db

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 4500

CMD ["uvicorn", "decision_engine:app", "--host", "0.0.0.0", "--port", "4500"]
