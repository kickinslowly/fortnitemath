"""Capture the UEFN viewport from a pose to a PNG:  python tools/capture.py out.png x y z pitch yaw"""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import uefn_mcp as u  # noqa: E402

out, x, y, z, pitch, yaw = sys.argv[1], *map(float, sys.argv[2:7])
r = u.call("EditorToolset.EditorAppToolset", "CaptureViewport", {
    "captureTransform": {"location": {"x": x, "y": y, "z": z}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0}}},
    raw=True)
img = next(c for c in r["content"] if c.get("type") == "image")  # image travels as an MCP image block
Path(out).write_bytes(base64.b64decode(img["data"]))
print("wrote", out)
