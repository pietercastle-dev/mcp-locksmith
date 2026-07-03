#!/usr/bin/env python3
"""Test fixture: a minimal streamable-HTTP MCP server (initialize + tools/list).

Serves on 127.0.0.1 and prints "PORT=<n>" on stdout once listening so tests can
build the url. Tool surface mirrors fake_mcp_server.py, env-driven so drift can
be simulated WITHOUT changing the url (same identity, moved tools):
  FAKE_TOOLS      comma-separated tool names        (default "hello")
  FAKE_DESC       description prefix for every tool (default "does")
  FAKE_PORT       listen port (default 0 = ephemeral); tests reuse a port
                  across restarts so the url stays stable while tools change
  FAKE_HTTP_AUTH  if set, require this exact Authorization header, else 401
  FAKE_SSE        if set, wrap each response as a text/event-stream data: event

Also exercises the session plumbing: initialize issues an Mcp-Session-Id and
every later POST without it gets 400; a client that drops the header can't
pass these tests by accident.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

TOOLS = [{"name": n, "description": f"{os.environ.get('FAKE_DESC', 'does')} {n}",
          "inputSchema": {"type": "object"}}
         for n in os.environ.get("FAKE_TOOLS", "hello").split(",") if n]
SESSION = "fake-session-1"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep test output clean

    def _send(self, code, body=b"", ctype="application/json", session=False):
        self.send_response(code)
        if session:
            self.send_header("Mcp-Session-Id", SESSION)
        if body:
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _reply(self, msg, session=False):
        body = json.dumps(msg).encode()
        if os.environ.get("FAKE_SSE"):
            self._send(200, b"event: message\ndata: " + body + b"\n\n",
                       "text/event-stream", session)
        else:
            self._send(200, body, "application/json", session)

    def do_DELETE(self):
        self._send(200)

    def do_POST(self):
        want = os.environ.get("FAKE_HTTP_AUTH")
        if want and self.headers.get("Authorization") != want:
            self._send(401, b'{"error":"unauthorized"}')
            return
        try:
            msg = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
        except Exception:
            self._send(400)
            return
        if msg.get("method") == "initialize":
            self._reply({"jsonrpc": "2.0", "id": msg["id"], "result": {
                "protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake-http", "version": "0"}}}, session=True)
            return
        if self.headers.get("Mcp-Session-Id") != SESSION:
            self._send(400, b'{"error":"missing session"}')
            return
        if "id" not in msg:
            self._send(202)  # notification
        elif msg.get("method") == "tools/list":
            self._reply({"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": TOOLS}})
        else:
            self._reply({"jsonrpc": "2.0", "id": msg["id"],
                         "error": {"code": -32601, "message": "unsupported"}})


srv = HTTPServer(("127.0.0.1", int(os.environ.get("FAKE_PORT", "0"))), Handler)
print(f"PORT={srv.server_address[1]}", flush=True)
sys.stdout.close()  # nothing else will be printed; let readers hit EOF
srv.serve_forever()
