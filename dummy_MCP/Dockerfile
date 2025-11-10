FROM python:3.11-slim
WORKDIR /app
COPY dummy_mcp.py .
RUN pip install fastapi uvicorn
CMD ["uvicorn", "dummy_mcp:app", "--host", "0.0.0.0", "--port", "4200"]
