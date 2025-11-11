# 🧭 Installation Guide — MCP Docker Server for AnythingLLM

> ⚙️ This project securely connects **AnythingLLM** with **MCP Tools (Model Context Protocol)** through Docker containers.  
> All services run inside an isolated Docker network — no `docker.sock`, no root privileges required.

---

## 📦 Included in the Project

| Folder / File | Description |
|----------------|-------------|
| 🧠 `anythingllm_data` | Data, plugins, and models for AnythingLLM |
| 🔍 `decision_rules` | Decision agent (work in progress) |
| ⚙️ `docker-compose.yml` | Defines and launches all containers |
| 🧩 `dummy_MCP` | Demo MCP server for testing |
| 🌐 `mcp_hub` | Hub that manages available MCP tools |
| ⏰ `mcp_time` | Example MCP tool for time queries |
| 🌉 `mini_bridge` | Connects AnythingLLM ↔ MCP Hub |
| 🔄 `n8n_data` | Optional: workflow automation data |
| 🧠 `prompt_injector` | Main controller, prompt rules & security layer |

---

## 🧠 Installing Ollama (GPU-Enabled)

Ollama is **not installed automatically**. You can run it separately with GPU support:

```bash
docker pull ollama

docker run -d   --gpus all   -v ollama:/root/.ollama   -p 11434:11434   --name ollama   ollama/ollama
```

> ✅ This starts Ollama with GPU acceleration.  
> Check the logs:
> ```bash
> docker logs -f ollama
> ```
> If you see “CUDA initialized”, GPU mode is active.

---

## 🐋 Container Setup & Launch

Make sure there are no port conflicts.  
You can adjust ports in `docker-compose.yml`.

### 📋 Show running containers
```bash
docker ps
```

---

## 🚀 Installation & Startup

1️⃣ **Clone the repository**
```bash
git clone https://github.com/danny094/mcp-docker-server-anythingllm.git
cd mcp-docker-server-anythingllm
```

2️⃣ **Check or create the Docker network**
```bash
docker network ls
```
If your network (e.g. `danny_ai-net`) doesn’t exist:
```bash
docker network create danny_ai-net
```
> If you prefer a custom network name, edit it inside `docker-compose.yml`.

3️⃣ **Start the containers**
```bash
docker compose up -d
```
*(Remove `-d` if you want to see live logs)*

---

## 🌐 Connecting to AnythingLLM

1️⃣ Open AnythingLLM in your browser:
```
http://YOUR_LOCAL_IP:3001
```

2️⃣ Select **Local AI**

3️⃣ Under *Local AI Base URL*, enter:
```
http://mini-bridge:4100/v1
```

4️⃣ You should now see the model  
**deepseek-r1:14b-qwen-distill-q4_K-M**  
→ Select & Save.

5️⃣ Go to:
```
Settings → Agent Abilities → MCP Servers
```
Make sure it shows **Bridge: ON** ✅

---

## 🧪 Testing the Setup

Ask in the AnythingLLM chat:
```
Can you tell me the time?
```

➡️ In the terminal (prompt-injector or bridge logs), you should see:
```
🔗 MCP call → mcp-time
```

The model automatically decides to use a tool,  
calls the MCP tool **time**, and returns the current time. 🕒

---

## 🧰 Useful Docker Commands

| Action | Command |
|--------|----------|
| Stop containers | `docker compose down` |
| Restart | `docker compose up -d` |
| View logs | `docker logs -f prompt-injector` |
| Full cleanup (images & volumes) | `docker compose down -v --rmi all` |

---

## 🔒 Security Tips

- No `docker.sock` mounting → safe, no root-level access  
- Runs inside dedicated network (e.g. `danny_ai-net`)  
- For external access: use a reverse proxy (like Nginx Proxy Manager) + HTTPS  
- Audit logs are stored in `prompt_injector/audit.log`

---

## ✅ Done!

Your full AnythingLLM + MCP stack is now running  
with GPU-accelerated Ollama, secure bridging, and modular tools. 🚀

---
> ✨ Created by **Danny** — a one-man dev who values security, control, and clean architecture.
