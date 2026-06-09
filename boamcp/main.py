import json
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

CONTEXTS_FILE = "contexts.jsonl"

port = int(os.environ.get("PORT", 8000))
mcp = FastMCP("orgbrain", host="0.0.0.0", port=port, json_response=True)


@mcp.tool()
def save_context(summary: str) -> str:
    """Save a conversation summary with a UTC timestamp to contexts.jsonl."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    }
    with open(CONTEXTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return "Saved."


class AcceptFixMiddleware:
    """Inject text/event-stream into Accept so FastMCP's header validation passes.

    Claude Projects (and other clients) don't send Accept: text/event-stream,
    which causes FastMCP to reject requests with 406. This middleware patches
    the header before it reaches the MCP transport layer.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
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
        await self.app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    app = AcceptFixMiddleware(mcp.streamable_http_app())
    uvicorn.run(app, host="0.0.0.0", port=port)
