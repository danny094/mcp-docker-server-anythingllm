from fastapi import FastAPI, Request
import sqlite3, json, logging, httpx, numpy as np

app = FastAPI(title="Decision Engine API")
DB_PATH = "/app/db/decision.db"
OLLAMA_URL = "http://ollama:11434/api/embeddings"  # dein lokales Ollama

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# Cache für geladene Regeln und Embeddings
RULE_CACHE = []

# ==================== DB LADEN UND EMBEDDINGS ====================
async def load_rules_with_embeddings():
    global RULE_CACHE
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, tool, pattern, language FROM decision_rules WHERE enabled=1")
    rows = cur.fetchall()
    conn.close()

    async with httpx.AsyncClient() as client:
        for r in rows:
            rule_id, tool, pattern, lang = r
            payload = {"model": "embedding-gemma:2b", "input": pattern}
            try:
                resp = await client.post(OLLAMA_URL, json=payload)
                embedding = resp.json().get("embedding", [])
                RULE_CACHE.append({
                    "id": rule_id,
                    "tool": tool,
                    "pattern": pattern,
                    "language": lang,
                    "embedding": embedding
                })
            except Exception as e:
                logging.error(f"Embedding Fehler bei Regel {rule_id}: {e}")

    logging.info(f"✅ {len(RULE_CACHE)} Regeln mit Embeddings geladen")

# ==================== ÄHNLICHKEITSBERECHNUNG ====================
def cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)

async def find_best_match(text: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(OLLAMA_URL, json={"model": "embedding-gemma:2b", "input": text})
        query_emb = resp.json().get("embedding", [])

    if not query_emb:
        return None

    best_match = None
    best_score = 0
    for rule in RULE_CACHE:
        if not rule.get("embedding"):
            continue
        score = cosine_similarity(rule["embedding"], query_emb)
        if score > best_score:
            best_match = rule
            best_score = score

    return best_match if best_score > 0.75 else None

# ==================== ENDPOINTS ====================
@app.on_event("startup")
async def startup_event():
    await load_rules_with_embeddings()

@app.post("/query")
async def query_decision(request: Request):
    data = await request.json()
    text = data.get("query", "")
    logging.info(f"[Decision Engine] Anfrage erhalten: {text}")

    match = await find_best_match(text)
    if not match:
        return {"decision": None, "reason": "No semantic match found."}

    return {"decision": match, "confidence": "semantic"}

@app.get("/health")
async def health():
    return {"status": "ok", "rules_loaded": len(RULE_CACHE)}
