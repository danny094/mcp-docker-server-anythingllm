
# MCP Bridge & Prompt Injector (Danny)

Hello — I'm Danny, a solo developer, hobbyist dev, and security fanatic. This project provides a secure, Docker-friendly **bridge** for AnythingLLM, enabling the use of MCP (Model Context Protocol) tools across Docker networks — without granting Docker itself permission to start other containers.

## Why this project?

Most AI or LLM interfaces running in Docker share the same problem:  
**Containers cannot (safely) start or manage other containers.**  
This limitation breaks MCP workflows and prevents tool usage in isolated environments.

Instead of granting Docker dangerous privileges (which defeats the entire purpose of container security),  
I built a modular architecture — an **MCP Bridge** combined with a **Prompt Injector** —  
that safely connects any UI (like AnythingLLM, OpenWebUI, or other local AI dashboards)  
to MCP-compatible tools inside Docker networks.

In short:  
I wanted to maintain full control, stability, and security —  
while still allowing AI systems to call real tools like `time`, `weather`, `docs`, or any custom MCP service.
----

## Architecture (in brief)
- **bridge** – a dummy MCP that acts as a target for any AI WEBUI and forwards calls to real MCP services.
- **prompt-injector** – central control center. Decides whether a tool is needed, injects system prompts, sanitizes input (security layer), and calls the MCP Hub if necessary.
- **MCP Hub** – directory containing the available MCP tools (e.g., `time`, `weather`, `docs`), typically accessible as separate Docker containers.

---

## Main Principles
- No elevation of Docker privileges: no `docker.sock` mount, no DinD.
- Security-first: Input sanitizer, tool access control, and audit logger.
- Modular: simply add new MCP containers to the `TOOLS` map.

---

## Example configuration (prompt rules)
```python
SYSTEM_PROMPT = """
You are a precise AI assistant with access to tools (MCP).
Behave as follows:
1️⃣ If you can answer the query directly (explanation, opinion, knowledge, small talk),
respond immediately, of course, in text form.
2️⃣ If a tool is needed (time, weather, documents, external data),
return only JSON in the format:
{"action": "mcp_call", "tool": "<toolname>", "query": "<user question>"}
3️⃣ Do not answer philosophical or open-ended questions with tool calls.
4️⃣ Do not return a JSON structure if no tool is required.
"""
```

---

## Prompt Injector — Core Functions (Short)
- `ask_deepseek(user_prompt: str)` — sends the message to the model with the system prompt and temperature.
- `call_mcp_tool(tool: str, query: str)` — constructs a JSON-RPC and calls `MCP_HUB_URL/{tool}`, parses the response, and returns the content.
- `sanitize_input(prompt: str)` — filters dangerous payloads such as `rm -rf`, `sudo`, `curl`, API keys, etc.
- `ALLOWED_TOOLS` — list of allowed tools (e.g., `["time","docs","search"]`).

---

## MCP Hub — Example
```py
TOOLS = {
    "time": "http://mcp-time:4210/",
    "weather": "http://mcp-weather:4220/",
    "docs": "http://mcp-docs:4230/"
}
```
`time` This works as a demo; the others are placeholders — simply enter the new MCP container there.

---

##Data & Context
- `prompt-injector/data/memory.db` – Simple context database (currently: 10 entries) to ensure that subsequent queries for MCP calls remain context-sensitive.

---

## TODO / Roadmap

- Complete implementation of Decision Rules (an agent that decides in advance whether an MCP call is necessary).
- Expand the audit logger (who made which request).
- Add more unit tests and sample MCPs (weather, docs).
- Optional authentication/user management for shared operation (family).

---
## Security Notes
- This architecture deliberately avoids `docker.sock` mounts.
- Nevertheless: MCP services are web endpoints — be mindful of network access and secure your internal network (e.g., Docker Network ACLs, internal firewalls).

--
## Participation / Usage
1. Clone the repository
2. Run `docker compose up` (Note: create external networks like `danny_ai-net` if necessary, or set `external: true`)
3. Adjust `TOOLS` and `SYSTEM_PROMPT` to your needs.
4. Check `prompt-injector/` for sanitizer, ALLOWED_TOOLS, and memory configuration.

---

## Kontakt
If you find bugs or want to suggest improvements, please open an issue or pull request. I'm a solo developer—constructive feedback is very welcome. 🚀
---

*README generated/revised by Danny (with help).*
