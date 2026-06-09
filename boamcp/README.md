# orgbrain-mcp

A minimal remote MCP server with one tool: `save_context` — saves a conversation summary to a `contexts.jsonl` file with a UTC timestamp.

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

Your MCP endpoint will be:
```
https://<your-railway-domain>/mcp
```

---

## Add the MCP server to a Claude Project

1. Open [claude.ai](https://claude.ai) and navigate to the Project you want to use.
2. Click **Project Settings → Integrations → Add MCP Server**.
3. Fill in:
   - **Name:** `orgbrain`
   - **URL:** `https://<your-railway-domain>/mcp`
   - **Transport:** Streamable HTTP
4. Click **Save**.

The `save_context` tool is now available to Claude inside that Project.

---

## System prompt to paste into the Project

Paste the following into your Project's **Custom Instructions** (system prompt) field:

```
You have access to a memory tool called save_context.

After every conversation — or whenever the user asks you to remember something — call save_context with a concise, factual summary of the key points discussed: decisions made, facts shared, tasks completed, or open questions.

Format the summary in plain prose, 2-5 sentences. Do not include filler phrases like "the user said" — just the facts.

Example call:
save_context("Decided to use PostgreSQL for the project database. The schema has users, sessions, and events tables. Deployment target is Railway. Next step: write the migration scripts.")
```

---

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Server starts at `http://localhost:8000/mcp`.

Test with the MCP inspector:
```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```
