from fastapi import FastAPI, Request, Response
import logging, json

app = FastAPI()
logging.basicConfig(level=logging.INFO)

@app.post("/")
async def root(request: Request):
    data = await request.json()
    method = data.get("method", "")
    logging.info(f"[DummyMCP] Request received: {json.dumps(data)}")

    if method == "initialize":
        result = {
            "protocolVersion": "2025-03-26",
            "capabilities": {"streaming": False},
            "serverInfo": {"name": "DummyMCP", "version": "1.0.0"}
        }

    # 👇 HIER — dieser Block ist der neue/ersetzte Teil:
    elif method in ("get_manifest", "manifest", "tools/list"):
        result = {
            "protocolVersion": "2025-03-26",
            "name": "DummyMCP",
            "version": "1.0.0",
            "description": "A dummy MCP server for AnythingLLM testing",
            "tools": [
                {
                    "name": "ping",
                    "description": "Simple connectivity check",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    },
                    "outputSchema": {
                        "type": "object",
                        "properties": {}
                        }
                    
                    }
            
            ],
            "resources": [],
            "models": [],
            "prompts": []
        }

    elif method == "ping":
        result = {}
    
    elif method == "tools/list":
        result = {"tools": []}

    elif method == "resources/list":
        result = {"resources": []}

    elif method == "models/list":
        result = {"models": []}

    elif method == "prompts/list":
        result = {"prompts": []}

    else:
        result = {}
        logging.info(f"[DummyMCP] Unhandled method '{method}' – returning empty result")

    payload = {"jsonrpc": "2.0", "id": data.get("id", 0), "result": result}
    text = json.dumps(payload)
    logging.info(f"[DummyMCP] Sending response: {text}")
    return Response(content=text, media_type="application/json")


@app.get("/manifest.json")
async def manifest():
    return {
        "name": "DummyMCP",
        "version": "1.0.0",
        "description": "Minimal MCP manifest",
        "tools": [{"name": "ping", "description": "Test tool"}],
        "resources": [],
        "models": [],
        "prompts": []
    }
