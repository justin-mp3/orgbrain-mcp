# orgbrain-mcp

Remote MCP server that logs steering events from Claude conversations — corrections, redirects, constraints, preferences, decisions, and approvals — with a viewer UI at `/`.

## Deploy to Railway

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "init orgbrain-mcp"
gh repo create orgbrain-mcp --public --source=. --push
```

### 2. Create a Railway project

1. Go to [railway.app](https://railway.app) and log in.
2. Click **New Project → Deploy from GitHub repo**.
3. Select your `orgbrain-mcp` repository.
4. Railway auto-detects Python and uses the `Procfile`.

### 3. Expose a public URL

1. In the Railway project dashboard, open your service.
2. Go to **Settings → Networking → Generate Domain**.
3. Copy the generated URL, e.g. `https://orgbrain-mcp-production.up.railway.app`.

Your MCP endpoint: `https://<your-railway-domain>/mcp`  
Your events viewer: `https://<your-railway-domain>/`

### 4. Persist events across deploys (optional but recommended)

1. Railway dashboard → service → **Volumes** → **Add Volume**
2. Mount path: `/data`
3. **Variables** → add `DATA_DIR=/data`

---

## Add the MCP server to a Claude Project

1. Open [claude.ai](https://claude.ai) → Project → **Settings → Integrations → Add MCP Server**
2. Fill in:
   - **Name:** `orgbrain`
   - **URL:** `https://<your-railway-domain>/mcp`
   - **Transport:** Streamable HTTP
3. Click **Save**.

---

## System prompt to paste into the Project

```
You have access to a tool called log_steering_event. Use it to record moments where the conversation changes direction, constraints are established, or key decisions are made.

Call log_steering_event whenever:
- The user corrects your approach or output → type: "correction"
- The user redirects the conversation → type: "redirect"
- A hard rule is established ("always", "never", "don't") → type: "constraint"
- A preference is revealed about style, method, or format → type: "preference"
- A key choice is made between options → type: "decision"
- The user explicitly approves something → type: "approval"

Write the summary as a plain fact, 1-2 sentences. No filler phrases.

Examples:
log_steering_event("constraint", "Never mock the database in tests — a prior incident where mock/prod divergence masked a broken migration.")
log_steering_event("redirect", "Switched from building a REST API to a CLI tool after user clarified the use case.")
log_steering_event("preference", "User prefers terse responses with no trailing summaries.")
```

---

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Server starts at `http://localhost:8000`.

Test with the MCP inspector:
```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```
