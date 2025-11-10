# mcp_hub.py - MCP Tool Hub v2.0.0
# Zentrale Routing-Schicht für Tools (time, weather, docs, etc.)
import logging
from fastapi import FastAPI, Request
import httpx
import time

# ---------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s"
)
logger = logging.getLogger("mcp-hub")

app = FastAPI(title="MCP Tool Hub")

# ---------------------------------------------------------
# Tool-Registry – hier kannst du beliebig neue Tools ergänzen
# ---------------------------------------------------------
TOOLS = {
    "time": "http://mcp-time:4210/",
    "weather": "http://mcp-weather:4220/",
    "docs": "http://mcp-docs:4230/"
}

# Timeout-Konfiguration
DEFAULT_TIMEOUT = 20.0


# ---------------------------------------------------------
# Utility – sicheres JSON-Antwort-Parsing
# ---------------------------------------------------------
async def safe_json_response(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except Exception:
        text = (await resp.aread()).decode(errors="ignore")
        logger.warning("[Hub] Antwort kein valides JSON, Rohtext wird genutzt.")
        return {"result": text}


# ---------------------------------------------------------
# Root & Manifest
# ---------------------------------------------------------
@app.get("/")
async def root():
    return {
        "service": "mcp-hub",
        "status": "ok",
        "tools_registered": list(TOOLS.keys()),
        "version": "2.0.0"
    }


@app.get("/manifest")
async def manifest():
    """Zeigt aktuelle Tool-Registry."""
    return {"tools": TOOLS, "count": len(TOOLS)}


# ---------------------------------------------------------
# Tool-Aufrufe
# ---------------------------------------------------------
@app.post("/{tool}")
async def call_tool(tool: str, request: Request):
    """Leitet JSON-RPC Requests an das passende Tool weiter."""
    if tool not in TOOLS:
        logger.warning(f"[Hub] Unbekanntes Tool '{tool}' angefragt.")
        return {
            "error": f"Tool '{tool}' ist nicht registriert.",
            "available_tools": list(TOOLS.keys())
        }

    try:
        body = await request.json()
    except Exception:
        logger.error("[Hub] Request enthält kein valides JSON.")
        return {"error": "Invalid JSON body."}

    target_url = TOOLS[tool]
    logger.info(f"[Hub] → Weiterleitung an {tool}: {target_url}")

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(target_url, json=body)
            result = await safe_json_response(resp)
            elapsed = time.time() - t0
            logger.info(f"[Hub] Tool '{tool}' erfolgreich ({elapsed:.2f}s)")

            return {
                "tool": tool,
                "status": "ok",
                "elapsed": elapsed,
                "result": result
            }

    except httpx.ReadTimeout:
        logger.error(f"[Hub] Timeout beim Tool '{tool}'")
        return {"error": f"Timeout calling tool '{tool}'"}

    except httpx.RequestError as e:
        logger.error(f"[Hub] Netzwerkfehler zu '{tool}': {e}")
        return {"error": f"Network error contacting '{tool}'", "detail": str(e)}

    except Exception as e:
        logger.exception("[Hub] Unerwarteter Fehler:")
        return {"error": f"Internal error in hub: {e}"}


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/health")
async def health():
    """Überprüft den Zustand aller registrierten Tools."""
    async with httpx.AsyncClient(timeout=3.0) as client:
        results = {}
        for name, url in TOOLS.items():
            try:
                r = await client.get(url.rstrip("/") + "/health")
                results[name] = (r.status_code == 200)
            except Exception:
                results[name] = False

        return {
            "status": "ok" if all(results.values()) else "degraded",
            "tools_alive": results,
            "total_tools": len(TOOLS),
            "version": "2.0.0"
        }
