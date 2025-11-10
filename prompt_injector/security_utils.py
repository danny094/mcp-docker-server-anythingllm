import logging
import json

logger = logging.getLogger("security")

# 🧩 --- INPUT SANITIZER ---
def sanitize_input(prompt: str) -> str:
    """Entfernt gefährliche oder verdächtige Eingaben."""
    blocked = [
        "ignore all", "system prompt", "sudo", "rm -rf",
        "bash", "python", "curl", "wget", "os.system",
        "exec(", "subprocess", "api key", "token"
    ]
    if any(b in prompt.lower() for b in blocked):
        logger.warning(f"[Security] ⚠️ Verdächtiger Prompt blockiert: {prompt}")
        return "[BLOCKED PROMPT: sicherheitsbedenklich entfernt]"
    return prompt


# 🚦 --- TOOL ACCESS CONTROL ---
ALLOWED_TOOLS = ["time", "docs", "search"]

def validate_tool_access(tool_name: str) -> bool:
    """Überprüft, ob ein Tool genutzt werden darf."""
    if tool_name not in ALLOWED_TOOLS:
        logger.warning(f"[Security] 🚫 Tool '{tool_name}' ist nicht erlaubt.")
        return False
    return True


# ✨ --- OUTPUT FORMATTER ---
def humanize_result(result: dict) -> str:
    """Formatiert MCP-Ergebnisse menschenfreundlich."""
    try:
        if "time" in result:
            return f"⏰ Es ist {result['time']} Uhr ({result.get('timezone', 'Unbekannte Zeitzone')})."
        if "weather" in result:
            return f"🌤️ Das Wetter ist {result['weather']} bei {result['temp']}°C."
        if "status" in result and result["status"] == "ok":
            return "✅ Vorgang erfolgreich abgeschlossen."
        return json.dumps(result, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[Security] Fehler beim Formatieren des Outputs: {e}")
        return str(result)


# 🧾 --- AUDIT LOGGER ---
def audit_log(prompt: str, decision: dict = None, tool_result: dict = None):
    """Erstellt einen konsolidierten Sicherheits-Logeintrag."""
    try:
        logger.info(
            f"[Audit] Prompt: {prompt[:80]}... | Tool: {decision.get('tool') if decision else 'N/A'} "
            f"| Result keys: {list(tool_result.keys()) if tool_result else 'N/A'}"
        )
    except Exception:
        pass
