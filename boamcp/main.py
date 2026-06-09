import json
import os
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
