# mcp_time.py - Zeit-Tool (MCP-kompatibel)
from fastapi import FastAPI, Request
from datetime import datetime
import pytz
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s"
)
logger = logging.getLogger("mcp-time")

app = FastAPI(title="MCP Time Tool")

@app.post("/")
async def get_time(request: Request):
    """Liefert aktuelle Zeit im ISO-Format mit Zeitzone."""
    try:
        _ = await request.json()  # Payload ignorieren, aber validieren
    except Exception:
        logger.warning("[Time] Kein valides JSON erhalten – ignoriere Request.")

    tz = pytz.timezone("Europe/Berlin")
    now_local = datetime.now(tz)
    logger.info("[Time] Zeitabfrage erfolgreich.")

    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "time": now_local.strftime("%Y-%m-%dT%H:%M:%S"),
            "timezone": "Europe/Berlin",
            "status": "ok"
        }
    }

@app.get("/health")
async def health():
    """Einfacher Healthcheck für den MCP-Hub."""
    return {"status": "ok", "tool": "mcp-time", "version": "1.0.0"}
