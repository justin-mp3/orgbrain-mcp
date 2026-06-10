import json
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from starlette.responses import HTMLResponse, JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

# Persist to a volume if mounted at /data, otherwise local (dev only)
DATA_DIR = os.environ.get("DATA_DIR", ".")
EVENTS_FILE = os.path.join(DATA_DIR, "events.jsonl")

VALID_TYPES = {"correction", "redirect", "constraint", "preference", "decision", "approval"}

port = int(os.environ.get("PORT", 8000))
mcp = FastMCP("orgbrain", host="0.0.0.0", port=port, json_response=True, stateless_http=True)


@mcp.tool()
def log_steering_event(type: str, summary: str) -> str:
    """Log a steering event from the current conversation.

    type: correction | redirect | constraint | preference | decision | approval
      - correction:  user corrected Claude's approach or output
      - redirect:    user changed direction mid-conversation
      - constraint:  hard rule established (always/never do X)
      - preference:  softer preference revealed about style or method
      - decision:    key choice made between options
      - approval:    user explicitly signed off on something

    summary: one or two sentences describing what happened, written as a fact.
    """
    if type not in VALID_TYPES:
        return f"Unknown type '{type}'. Use one of: {', '.join(sorted(VALID_TYPES))}"

    os.makedirs(DATA_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": type,
        "summary": summary,
    }
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return "Logged."


UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>orgbrain — steering events</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:        #0f0f0f;
    --surface:   #1a1a1a;
    --border:    #242424;
    --border-hv: #333;
    --text:      #d8d8d8;
    --muted:     #555;
    --dim:       #333;

    --correction:  #e05252;
    --redirect:    #5b9cf6;
    --constraint:  #e8a030;
    --preference:  #a87ee8;
    --decision:    #3dbfa0;
    --approval:    #5bb56f;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 48px 24px 80px;
  }

  /* ── header ── */
  header {
    max-width: 780px;
    margin: 0 auto 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  h1 { font-size: 18px; font-weight: 600; color: #fff; letter-spacing: -0.02em; }
  h1 span { color: var(--muted); font-weight: 400; }

  #meta { font-size: 13px; color: var(--muted); display: flex; align-items: center; gap: 12px; }

  button {
    background: none;
    border: 1px solid var(--border);
    color: var(--muted);
    font-size: 12px;
    padding: 5px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s;
  }
  button:hover { border-color: var(--border-hv); color: #999; }

  /* ── filter bar ── */
  #filters {
    max-width: 780px;
    margin: 0 auto 28px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px 5px 10px;
    border-radius: 20px;
    border: 1px solid var(--border);
    font-size: 12px;
    cursor: pointer;
    color: var(--muted);
    transition: border-color 0.15s, color 0.15s, background 0.15s;
    user-select: none;
  }

  .chip .dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--muted);
    transition: background 0.15s;
    flex-shrink: 0;
  }

  .chip.active {
    border-color: var(--clr);
    color: var(--clr);
    background: color-mix(in srgb, var(--clr) 8%, transparent);
  }
  .chip.active .dot { background: var(--clr); }

  /* ── list ── */
  #list {
    max-width: 780px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--clr, var(--border));
    border-radius: 8px;
    padding: 16px 20px;
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 12px 16px;
    align-items: start;
    transition: border-color 0.15s;
  }
  .card:hover { border-color: var(--border-hv); border-left-color: var(--clr, var(--border-hv)); }

  .badge {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--clr);
    background: color-mix(in srgb, var(--clr) 12%, transparent);
    padding: 3px 8px;
    border-radius: 4px;
    white-space: nowrap;
    margin-top: 1px;
  }

  .body { display: flex; flex-direction: column; gap: 6px; }

  .summary {
    font-size: 14px;
    line-height: 1.6;
    color: var(--text);
    white-space: pre-wrap;
  }

  .ts {
    font-size: 12px;
    color: var(--dim);
    font-variant-numeric: tabular-nums;
  }
  .ts .date { color: var(--muted); }

  #empty {
    max-width: 780px;
    margin: 80px auto;
    text-align: center;
    color: var(--dim);
    font-size: 15px;
  }

  .divider {
    max-width: 780px;
    margin: 24px auto 16px;
    font-size: 12px;
    color: var(--dim);
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }
</style>
</head>
<body>

<header>
  <h1>orgbrain <span>/ steering events</span></h1>
  <div id="meta">
    <span id="count"></span>
    <button onclick="load()">refresh</button>
  </div>
</header>

<div id="filters"></div>
<div id="list"></div>
<div id="empty" style="display:none">no events logged yet</div>

<script>
const TYPES = {
  correction:  { label: 'Correction',  color: 'var(--correction)'  },
  redirect:    { label: 'Redirect',    color: 'var(--redirect)'    },
  constraint:  { label: 'Constraint',  color: 'var(--constraint)'  },
  preference:  { label: 'Preference',  color: 'var(--preference)'  },
  decision:    { label: 'Decision',    color: 'var(--decision)'    },
  approval:    { label: 'Approval',    color: 'var(--approval)'    },
};

// active = null means show all
let active = null;
let allEvents = [];

function relativeTime(date) {
  const s = (Date.now() - date) / 1000;
  if (s < 60)     return 'just now';
  if (s < 3600)   return Math.floor(s / 60) + 'm ago';
  if (s < 86400)  return Math.floor(s / 3600) + 'h ago';
  if (s < 604800) return Math.floor(s / 86400) + 'd ago';
  return Math.floor(s / 604800) + 'w ago';
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

function sameDay(a, b) {
  const da = new Date(a), db = new Date(b);
  return da.getFullYear() === db.getFullYear() &&
         da.getMonth()    === db.getMonth()    &&
         da.getDate()     === db.getDate();
}

function escape(s) { return s.replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function renderFilters(events) {
  const counts = {};
  for (const e of events) counts[e.type] = (counts[e.type] || 0) + 1;

  const bar = document.getElementById('filters');
  bar.innerHTML = Object.entries(TYPES).map(([key, meta]) => {
    const n = counts[key] || 0;
    if (!n) return '';
    const isActive = active === key;
    return `<span class="chip${isActive ? ' active' : ''}" style="--clr:${meta.color}"
              onclick="toggle('${key}')">
              <span class="dot"></span>${meta.label} <span style="opacity:.5">${n}</span>
            </span>`;
  }).join('');
}

function toggle(type) {
  active = (active === type) ? null : type;
  render();
}

function render() {
  const visible = active ? allEvents.filter(e => e.type === active) : allEvents;
  const list = document.getElementById('list');
  const empty = document.getElementById('empty');
  const count = document.getElementById('count');

  count.textContent = allEvents.length + ' event' + (allEvents.length === 1 ? '' : 's');

  renderFilters(allEvents);

  if (!visible.length) {
    list.innerHTML = '';
    empty.style.display = 'block';
    empty.textContent = active ? 'no ' + active + ' events' : 'no events logged yet';
    return;
  }
  empty.style.display = 'none';

  let html = '';
  let lastDate = null;

  for (const e of visible) {
    const dateStr = formatDate(e.timestamp);
    if (dateStr !== lastDate) {
      html += `<div class="divider">${dateStr}</div>`;
      lastDate = dateStr;
    }
    const meta = TYPES[e.type] || { label: e.type, color: 'var(--muted)' };
    html += `
      <div class="card" style="--clr:${meta.color}">
        <span class="badge" style="--clr:${meta.color}">${meta.label}</span>
        <div class="body">
          <div class="summary">${escape(e.summary)}</div>
          <div class="ts"><span class="date">${formatTime(e.timestamp)}</span> · ${relativeTime(new Date(e.timestamp))}</div>
        </div>
      </div>`;
  }
  list.innerHTML = html;
}

async function load() {
  const res = await fetch('/events');
  const data = await res.json();
  allEvents = [...data].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  render();
}

load();
</script>
</body>
</html>"""


class App:
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

        if scope["type"] == "http" and path == "/events":
            await self._events(scope, receive, send)
            return

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

    async def _events(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            with open(EVENTS_FILE, encoding="utf-8") as f:
                entries = [json.loads(line) for line in f if line.strip()]
        except FileNotFoundError:
            entries = []
        await JSONResponse(entries)(scope, receive, send)


app = App(mcp.streamable_http_app())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
