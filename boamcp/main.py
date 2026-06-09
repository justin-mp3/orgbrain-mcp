import json
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

CONTEXTS_FILE = "contexts.jsonl"

mcp = FastMCP("orgbrain")


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


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
