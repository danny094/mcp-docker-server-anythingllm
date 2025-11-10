# mini_prompt_injector.py
import json
import logging
import httpx
import os 
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from security_utils import sanitize_input, validate_tool_access, humanize_result, audit_log



logging.basicConfig(level=logging.INFO, format="🧩 [%(levelname)s] %(message)s")

app = FastAPI(title="Prompt Injector - Claude Style")

load_dotenv()
# Modell und URLs aus der .env laden
MODEL_NAME = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.0.224:11434/api/chat")
MCP_HUB_URL = os.getenv("MCP_HUB_URL", "http://mcp-hub:4400")              # Für Tool-Weiterleitung

# 🧠 Claude-Style Systemprompt
SYSTEM_PROMPT = """
Du bist ein präziser KI-Assistent mit Zugriff auf Tools (MCP).
Verhalte dich wie folgt:

1️⃣ Wenn du die Anfrage direkt beantworten kannst (Erklärung, Meinung, Wissen, Smalltalk),
    antworte sofort natürlich in Textform.
2️⃣ Wenn ein Tool nötig ist (Zeit, Wetter, Dokumente, externe Daten),
    gib nur JSON im Format zurück:
    {"action": "mcp_call", "tool": "<toolname>", "query": "<benutzerfrage>"}
3️⃣ Beantworte keine philosophischen oder offenen Fragen mit Tool-Calls.
4️⃣ Gib keine JSON-Struktur aus, wenn kein Tool gebraucht wird.
"""

# ============================================================
# 🧩 DeepSeek-Aufruf
# ============================================================
async def ask_deepseek(user_prompt: str):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(OLLAMA_URL, json=payload)
            r.raise_for_status()
            data = r.json()
            message = data.get("message") or data.get("response") or data
            if isinstance(message, dict):
                text = message.get("content", json.dumps(message))
            else:
                text = str(message)
            return text
        except Exception as e:
            logging.error(f"❌ DeepSeek Fehler: {e}")
            return f"⚠️ Modellfehler: {e}"


# ============================================================
# 🔧 Tool-Aufruf via MCP-Hub
# ============================================================
async def call_mcp_tool(tool: str, query: str):
    rpc_payload = {"jsonrpc": "2.0", "id": 1, "method": "query", "params": {"query": query}}
    url = f"{MCP_HUB_URL}/{tool}"

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            logging.info(f"🔗 MCP-Aufruf → {url}")
            r = await client.post(url, json=rpc_payload)
            r.raise_for_status()
            result = r.json()
            content = (
                result.get("result", {}).get("content")
                or result.get("result", {}).get("time")
                or str(result.get("result"))
            )
            return content
        except Exception as e:
            logging.error(f"❌ MCP-Aufruf fehlgeschlagen: {e}")
            return f"⚠️ MCP-Fehler: {e}"


# ============================================================
# 💬 Haupt-Endpunkt
# ============================================================
@app.post("/api/chat")
async def handle_chat(request: Request):
    body = await request.json()
    prompt = body.get("prompt") or body.get("input") or body.get("content", "")
    logging.info(f"💬 Eingabe erhalten: {prompt[:120]}")
    
    # 🧩 --- SECURITY-LAYER ---
    prompt = sanitize_input(prompt)



    # Schritt 1️⃣ – DeepSeek befragen
    deepseek_output = await ask_deepseek(prompt)
    if not isinstance(deepseek_output, str):
        deepseek_output = str(deepseek_output)

    # Schritt 2️⃣ – Robust prüfen, ob ein JSON-Toolaufruf enthalten ist
    if "{" in deepseek_output and "}" in deepseek_output and '"tool":' in deepseek_output:
        try:
            # JSON-Fragment isolieren (ignoriert Text vor/nach dem JSON)
            start = deepseek_output.find("{")
            end = deepseek_output.rfind("}") + 1
            json_fragment = deepseek_output[start:end]

            decision = json.loads(json_fragment)
            if decision.get("action") == "mcp_call":
                tool = decision.get("tool")
                query = decision.get("query", "")
                #Sicherheitsprüfung:
                if not validate_tool_access(decision.get("tool", "")):
                    return {"final": "Tool nicht erlaubt."}
                
                logging.info(f"🧠 Tool-Call erkannt → {tool}")
                mcp_result = await call_mcp_tool(tool, query)
                
                 # 🧾 Audit Logging
                audit_log(prompt, decision, {"result": mcp_result})

                # ✨ Ergebnis verschönern (optional)
                pretty = humanize_result({"result": mcp_result})
                return {"final": pretty}
                
                
        except json.JSONDecodeError as e:
            logging.warning(f"⚠️ JSON-Parsing unvollständig oder fehlerhaft: {e}")
            return {"final": f"⚠️ Unvollständige JSON-Ausgabe erkannt. Text: {deepseek_output.strip()[:200]}"}
        except Exception as e:
            logging.error(f"❌ Tool-Call Fehler: {e}")
            return {"final": f"⚠️ Fehler bei der Tool-Verarbeitung: {e}"}

    # Schritt 3️⃣ – Falls kein Tool-Call oder Parsing fehlgeschlagen → Textantwort
    logging.info("🗣️ Direkte Antwort von DeepSeek oder anderem Modell.")
    return {"final": deepseek_output.strip()}


# ============================================================
# 💚 Health Endpoint
# ============================================================
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "mode": "claude-style",
        "bridge_ready": True,
        "mcp_target": MCP_HUB_URL
    }
