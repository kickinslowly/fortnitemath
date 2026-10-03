"""Minimal client for UEFN's built-in MCP server (http://127.0.0.1:8000/mcp).

UEFN exposes three gateway tools (list_toolsets / describe_toolset / call_tool); everything else is
reached through call_tool(toolset, tool, args). Tool references: tools/uefn_mcp_ref/*.txt.

    python tools/uefn_mcp.py <toolset> <tool> '<json args>'
    python tools/uefn_mcp.py ValkyrieToolset.VerseToolset BuildAll '{}'
"""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:8000/mcp"
_session = None


def _post(payload, timeout=600):
    global _session
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if _session:
        headers["Mcp-Session-Id"] = _session
    req = urllib.request.Request(URL, json.dumps(payload).encode("utf-8"), headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        _session = r.headers.get("Mcp-Session-Id") or _session
        body = r.read().decode("utf-8")
    if body.lstrip().startswith("data:"):  # SSE framing
        body = "\n".join(l[5:] for l in body.splitlines() if l.startswith("data:"))
    return json.loads(body)


def _init():
    if _session is None:
        _post({"jsonrpc": "2.0", "id": 0, "method": "initialize",
               "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                          "clientInfo": {"name": "fnm", "version": "0"}}})


def call(toolset, tool, args=None, timeout=600, raw=False):
    """Call a toolset tool. Returns parsed JSON of the text result when possible, else the text.
    Raises RuntimeError when the tool reports an error."""
    _init()
    params = {"name": "call_tool", "arguments": {"tool_name": tool, "arguments": args or {}}}
    if toolset:
        params["arguments"]["toolset_name"] = toolset
    res = _post({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}, timeout)
    if "error" in res:
        raise RuntimeError(res["error"])
    result = res["result"]
    if raw:
        return result
    text = "".join(c.get("text", "") for c in result.get("content", []))
    if result.get("isError"):
        raise RuntimeError(text)
    try:
        return json.loads(text)
    except ValueError:
        return text


if __name__ == "__main__":
    out = call(sys.argv[1], sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {})
    print(json.dumps(out, indent=2, ensure_ascii=False) if not isinstance(out, str) else out)
