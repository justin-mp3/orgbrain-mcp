import json
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from starlette.responses import HTMLResponse, JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

# Persist to a volume if mounted at /data, otherwise local (dev only)
DATA_DIR = os.environ.get("DATA_DIR", ".")
CONTEXTS_FILE = os.path.join(DATA_DIR, "contexts.jsonl")

port = int(os.environ.get("PORT", 8000))
mcp = FastMCP("orgbrain", host="0.0.0.0", port=port, json_response=True, stateless_http=True)


@mcp.tool()
def save_context(summary: str) -> str:
    """Save a conversation summary with a UTC timestamp to contexts.jsonl."""
    os.makedirs(DATA_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    }
    with open(CONTEXTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return "Saved."


UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>orgbrain</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0f0f0f;
    color: #e8e8e8;
    min-height: 100vh;
    padding: 48px 24px;
  }

  header {
    max-width: 720px;
    margin: 0 auto 40px;
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
  }

  h1 {
    font-size: 20px;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: #fff;
  }

  #meta {
    font-size: 13px;
    color: #555;
  }

  #list {
    max-width: 720px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 10px;
    padding: 20px 24px;
    display: grid;
    grid-template-rows: auto 1fr;
    gap: 10px;
    transition: border-color 0.15s;
  }

  .card:hover { border-color: #3a3a3a; }

  .ts {
    font-size: 12px;
    color: #555;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.01em;
  }

  .ts .date { color: #777; }
  .ts .time { color: #444; }
  .ts .age  { color: #3a3a3a; margin-left: 8px; }

  .summary {
    font-size: 15px;
    line-height: 1.65;
    color: #d0d0d0;
    white-space: pre-wrap;
  }

  #empty {
    max-width: 720px;
    margin: 80px auto;
    text-align: center;
    color: #333;
    font-size: 15px;
  }

  #refresh {
    background: none;
    border: 1px solid #2a2a2a;
    color: #555;
    font-size: 12px;
    padding: 5px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }
  #refresh:hover { border-color: #444; color: #999; }
</style>
</head>
<body>
<header>
  <h1>orgbrain</h1>
  <span id="meta"><button id="refresh" onclick="load()">refresh</button></span>
</header>
<div id="list"></div>
<div id="empty" style="display:none">no contexts saved yet</div>

<script>
function relativeTime(date) {
  const diff = (Date.now() - date) / 1000;
  if (diff < 60)    return 'just now';
  if (diff < 3600)  return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  if (diff < 604800)return Math.floor(diff / 86400) + 'd ago';
  return Math.floor(diff / 604800) + 'w ago';
}

function formatTs(iso) {
  const d = new Date(iso);
  const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  return `<span class="date">${date}</span>&nbsp;&nbsp;<span class="time">${time}</span><span class="age">${relativeTime(d)}</span>`;
}

async function load() {
  const res = await fetch('/contexts');
  const data = await res.json();
  const sorted = [...data].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  const list = document.getElementById('list');
  const empty = document.getElementById('empty');
  const meta = document.getElementById('meta');

  if (!sorted.length) {
    list.innerHTML = '';
    empty.style.display = 'block';
    meta.innerHTML = '<button id="refresh" onclick="load()">refresh</button>';
    return;
  }

  empty.style.display = 'none';
  meta.innerHTML = `<span>${sorted.length} entr${sorted.length === 1 ? 'y' : 'ies'}</span>&nbsp;&nbsp;<button id="refresh" onclick="load()">refresh</button>`;

  list.innerHTML = sorted.map(e => `
    <div class="card">
      <div class="ts">${formatTs(e.timestamp)}</div>
      <div class="summary">${e.summary.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
    </div>
  `).join('');
}

load();
</script>
</body>
</html>"""


class App:
    """ASGI router that owns the MCP app's lifespan and adds UI + API routes.

    Starlette's Mount() doesn't forward lifespan events to sub-apps, which
    breaks FastMCP's internal task group. Owning the routing at the ASGI level
    ensures lifespan, MCP requests, and extra endpoints all work correctly.
    """

    def __init__(self, mcp_asgi: ASGIApp) -> None:
        self.mcp_asgi = mcp_asgi

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self.mcp_asgi(scope, receive, send)
            return

        path = scope.get("path", "")

        if scope["type"] == "http" and path == "/":
            await HTMLResponse(UI)(scope, receive, send)
            return

        if scope["type"] == "http" and path == "/contexts":
            await self._contexts(scope, receive, send)
            return

        # Patch Accept header so Claude Projects requests pass FastMCP validation.
        if scope["type"] == "http":
            new_headers = []
            accept_found = False
            for key, val in scope["headers"]:
                if key.lower() == b"accept":
                    accept_found = True
                    decoded = val.decode()
                    if "text/event-stream" not in decoded:
                        val = (decoded + ", text/event-stream").encode()
                new_headers.append((key, val))
            if not accept_found:
                new_headers.append((b"accept", b"application/json, text/event-stream"))
            scope["headers"] = new_headers

        await self.mcp_asgi(scope, receive, send)

    async def _contexts(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            with open(CONTEXTS_FILE, encoding="utf-8") as f:
                entries = [json.loads(line) for line in f if line.strip()]
        except FileNotFoundError:
            entries = []
        await JSONResponse(entries)(scope, receive, send)


app = App(mcp.streamable_http_app())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
