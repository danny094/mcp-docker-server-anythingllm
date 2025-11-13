# mini_bridge.py – Bridge v3.0.0
# Vollständig MCP-kompatibel, robust, multi-tool-fähig

import logging
import json
import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx

# -------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(message)s"
)
logger = logging.getLogger("bridge")

# -------------------------------------------------------------
# FastAPI App Setup
# -------------------------------------------------------------
app = FastAPI(title="Mini MCP Bridge")
PROMPT_INJECTOR_URL = "http://prompt-injector:4300/api/chat"

# -------------------------------------------------------------
# Beispiel-Tools – später dynamisch erweiterbar
# -------------------------------------------------------------
AVAILABLE_TOOLS = [
    {
        "name": "chat",
        "description": "Standard-Chat mit DeepSeek",
        "inputSchema": {
            "type": "object",
            "properties": {"prompt": {"type": "string"}},
            "required": ["prompt"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
        },
        "version": "1.0.0",
        "stream": False,
        "tags": ["deepseek", "default"],
    },
    {
        "name": "search",
        "description": "Websuche über MCP-Hub",
        "inputSchema": {
            "type": "object",
            "properties": {"prompt": {"type": "string"}},
            "required": ["prompt"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
        },
        "version": "1.0.0",
        "stream": False,
        "tags": ["mcp", "utility"],
    },
]

# -------------------------------------------------------------
# Utility: Safe JSON decode
# -------------------------------------------------------------
async def safe_json_response(resp: httpx.Response) -> dict:
    try:
        return resp.json()
    except Exception:
        text = (await resp.aread()).decode(errors="ignore")
        logger.warning("[Bridge] Kein valides JSON – Rohtext wird genutzt.")
        return {"final": text}

# -------------------------------------------------------------
# MCP Handler
# -------------------------------------------------------------
@app.post("/")
async def handle_mcp(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"[Bridge] Ungültige JSON-Anfrage: {e}")
        return {"error": "Invalid JSON"}

    method = data.get("method")
    req_id = data.get("id")

    # 🧩 Fix: Notifications und Requests ohne Methode richtig behandeln
    if not method:
        logger.warning("[Bridge] Anfrage ohne 'method' erhalten – sende 204 No Content.")
        return Response(status_code=204)

    # Notifications (z. B. notifications/initialized)
    if "notifications/" in method or req_id is None:
        logger.info(f"[Bridge] Notification erhalten: {method}")
        return Response(status_code=204)

    logger.info(f"[MCP] → {method}")
    params = data.get("params", {})

    # ---------------------------------------------------------
    # Base Methods
    # ---------------------------------------------------------
    if method == "ping":
        logger.info("[Bridge] Ping erhalten – 200 OK")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"list": True, "call": True},
                    "resources": {},
                    "roots": {},
                    "sampling": {}
                },
                "serverInfo": {
                    "name": "mini-bridge",
                    "version": "3.0.0",
                    "mcpVersion": "1.8.0",
                    "description": "Custom MCP bridge for AnythingLLM"
                }
            }
        }

    elif method == "get_capabilities":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"capabilities": {"tools": True, "logging": True}},
        }

    elif method == "shutdown":
        logger.info("[Bridge] MCP shutdown received")
        return {
            "jsonrpc": "2.0",
            "method": "shutdown",
            "params": {"status": "ok"}
        }

    # ---------------------------------------------------------
    # Tools
    # ---------------------------------------------------------
    elif method == "tools/list":
        logger.info("[Bridge] tools/list aufgerufen")
        try:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": AVAILABLE_TOOLS}
            }
        except Exception as e:
            logger.error(f"[Bridge] Fehler bei tools/list: {e}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": f"tools/list error: {e}"
                }
            }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        prompt = args.get("prompt", "")

        known_tools = [t["name"] for t in AVAILABLE_TOOLS]
        if tool_name not in known_tools:
            logger.warning(f"[Bridge] Unbekanntes Tool: {tool_name}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        payload = {"tool": tool_name, "prompt": prompt}
        logger.info(f"[Bridge] Tool-Call '{tool_name}' → Weiterleitung an Prompt Injector")

        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    PROMPT_INJECTOR_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                result_data = await safe_json_response(resp)
                result = (
                    result_data.get("final")
                    or result_data.get("response")
                    or str(result_data)
                )
                elapsed = time.time() - t0
                logger.info(f"[Bridge] Tool '{tool_name}' fertig ({elapsed:.2f}s)")

                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": result}],
                        "status": "ok",
                        "tool": tool_name,
                        "elapsed": elapsed,
                    },
                }

        except httpx.ReadTimeout:
            logger.error("[Bridge] Timeout bei Tool-Aufruf")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": f"Timeout calling tool '{tool_name}'",
                },
            }

        except httpx.RequestError as e:
            logger.error(f"[Bridge] Netzwerkfehler: {e}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32001,
                    "message": f"Network error to injector: {e}",
                },
            }

        except Exception as e:
            logger.exception("[Bridge] Unerwarteter Fehler:")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal bridge error: {e}",
                },
            }

    # ---------------------------------------------------------
    # Additional MCP Methods (AnythingLLM compatibility)
    # ---------------------------------------------------------
    elif method == "resources/list":
        logger.info("[Bridge] resources/list aufgerufen")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": []}
        }

    elif method == "prompts/list":
        logger.info("[Bridge] prompts/list aufgerufen")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"prompts": []}
        }

    elif method == "roots/list":
        logger.info("[Bridge] roots/list aufgerufen")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"roots": []}
        }

    # ---------------------------------------------------------
    # Notifications / Unknown
    # ---------------------------------------------------------
    elif method.startswith("notifications/"):
        logger.info(f"[Bridge] Notification erhalten: {method}")
        return Response(status_code=204)

    else:
        logger.warning(f"[Bridge] Unbekannte Methode: {method}")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

# -------------------------------------------------------------
# OpenAI-kompatibler Chat Endpoint (mit Streaming-Support)
# -------------------------------------------------------------
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-kompatibler Chat-Endpoint - unterstützt Streaming und Non-Streaming"""
    try:
        data = await request.json()
        messages = data.get("messages", [])
        model = data.get("model", "deepseek-r1:8b")
        stream = data.get("stream", False)
        
        prompt = messages[-1]["content"] if messages else ""
        logger.info(f"[Bridge] Chat-Anfrage (stream={stream}): {prompt[:80]}...")
        
        # Anfrage an Prompt-Injector
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(PROMPT_INJECTOR_URL, json={"prompt": prompt})
            resp.raise_for_status()
            result = resp.json()
            
        text = result.get("final") or result.get("response") or str(result)
        
        # STREAMING Response
        if stream:
            async def generate_stream():
                import asyncio

                # chunk_size = 4 ist ideal
                chunk_size = 4  

                # Text in kleine Teile aufsplitten
                chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

                for chunk_text in chunks:
                    chunk = {
                        "id": "chatcmpl-" + str(time.time()),
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk_text},
                            "finish_reason": None
                        }]
                    }

                    yield f"data: {json.dumps(chunk)}\n\n"

                    # leichte Verzögerung für realistische Typing-Illusion
                    await asyncio.sleep(0.012)  # 12ms optimal

                # final chunk
                final_chunk = {
                    "id": "chatcmpl-" + str(time.time()),
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }

                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        
        # NON-STREAMING Response
        else:
            return {
                "id": "chatcmpl-" + str(time.time()),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
            
    except Exception as e:
        logger.error(f"[Bridge] Chat-Completion Fehler: {e}")
        return {"error": {"message": str(e), "type": "bridge_error"}}

# -------------------------------------------------------------
# Health Endpoint (erweitert)
# -------------------------------------------------------------
@app.get("/health")
async def health():
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            ping = await client.get(f"{PROMPT_INJECTOR_URL.replace('/api/chat','')}/health")
            injector_ok = ping.status_code == 200
        except Exception:
            injector_ok = False
    return {
        "status": "ok" if injector_ok else "degraded",
        "bridge": "ready",
        "prompt_injector_alive": injector_ok,
        "tools_available": len(AVAILABLE_TOOLS),
        "version": "3.0.0",
        "uptime_hint": "reload-safe",
    }

# -------------------------------------------------------------
# Model Listing (AnythingLLM-Kompatibilität)
# -------------------------------------------------------------
@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
          {"id": "deepseek-r1:8b", "object": "model"},
          {"id": "qwen3-vl:8b", "object": "model"},
          {"id": "llama3.1:8b", "object": "model"},
          {"id": "deepseek-r1:14b", "object": "model"},
          {"id": "thirdeyeai/DeepSeek-R1-Distill-Qwen-7B-uncensored:Q4_0", "object": "model"},
          {"id": "dolphin3:8b", "object": "model"}
        ],
    }

# -------------------------------------------------------------
# SSE Stream (Keep-Alive)
# -------------------------------------------------------------
@app.get("/")
async def handle_mcp_get(request: Request):
    """SSE Stream für Server→Client Kommunikation"""
    async def event_stream():
        yield "data: {}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
