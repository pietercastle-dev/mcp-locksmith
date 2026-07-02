#!/usr/bin/env python3
"""Test fixture: a minimal stdio MCP server (initialize + tools/list only).

Tool surface is env-driven so tests can simulate drift WITHOUT changing the
server's command/args (mcp-pin's identity hashes name+command+args, so only an
env-driven change reads as the same server whose tools moved — a rug-pull):
  FAKE_TOOLS  comma-separated tool names          (default "hello")
  FAKE_DESC   description prefix for every tool   (default "does")
"""
import json
import os
import sys

TOOLS = [{"name": n, "description": f"{os.environ.get('FAKE_DESC', 'does')} {n}",
          "inputSchema": {"type": "object"}}
         for n in os.environ.get("FAKE_TOOLS", "hello").split(",") if n]

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    if "id" not in msg:
        continue  # notification
    if msg.get("method") == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "fake", "version": "0"}}
        print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}), flush=True)
    elif msg.get("method") == "tools/list":
        print(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                          "result": {"tools": TOOLS}}), flush=True)
    else:
        print(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                          "error": {"code": -32601, "message": "unsupported"}}), flush=True)
