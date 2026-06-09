import json
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

# Persist to a volume if mounted at /data, otherwise local (dev only)
DATA_DIR = os.environ.get("DATA_DIR", ".")
CONTEXTS_FILE = os.path.join(DATA_DIR, "contexts.jsonl")

port = int(os.environ.get("PORT", 8000))
mcp = FastMCP("orgbrain", host="0.0.0.0", port=port, json_response=True)


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


class App:
    """ASGI router that owns the MCP app's lifespan and adds a /contexts route.

    Starlette's Mount() doesn't forward lifespan events to sub-apps, which
    breaks FastMCP's internal task group. Owning the routing at the ASGI level
    ensures lifespan, MCP requests, and the /contexts endpoint all work.
    """

    def __init__(self, mcp_asgi: ASGIApp) -> None:
        self.mcp_asgi = mcp_asgi

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            # Forward lifespan directly so FastMCP's task group initializes.
            await self.mcp_asgi(scope, receive, send)
            return

        if scope["type"] == "http" and scope["path"] == "/contexts":
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
