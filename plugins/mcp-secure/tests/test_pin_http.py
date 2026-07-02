#!/usr/bin/env python3
"""Tests for mcp-pin's streamable-HTTP support against the fake HTTP MCP server.
Run: python test_pin_http.py"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
PIN = os.path.join(os.path.dirname(HERE), "bin", "mcp-pin")
FAKE = os.path.join(HERE, "fake_http_mcp_server.py")
# Obviously-fake test credential; shape-benign on purpose.
AUTH = "Bearer " + "fake-test-value-123"


class HttpPinEnv(unittest.TestCase):
    """Each test gets a fresh project dir + pins file + its own fixture server(s)."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pin-http-test-")
        self.pins_file = os.path.join(self.root, "pins.json")
        self.procs = []

    def tearDown(self):
        for p in self.procs:
            p.terminate()
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()

    def serve(self, env=None, port=0):
        """Start the fixture; return the port it actually bound."""
        e = dict(os.environ, FAKE_PORT=str(port), **(env or {}))
        p = subprocess.Popen([sys.executable, FAKE], stdout=subprocess.PIPE,
                             text=True, env=e)
        self.procs.append(p)
        line = p.stdout.readline().strip()
        self.assertTrue(line.startswith("PORT="), f"fixture failed to start: {line!r}")
        return int(line.split("=", 1)[1])

    def stop(self, idx=-1):
        p = self.procs.pop(idx)
        p.terminate()
        p.wait(timeout=5)

    def write_config(self, url, extra=None, type_="http", name="rfake"):
        spec = {"type": type_, "url": url}
        spec.update(extra or {})
        json.dump({"mcpServers": {name: spec}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))

    def pin(self, *args):
        e = dict(os.environ, MCP_PINS_FILE=self.pins_file, MCP_PIN_TIMEOUT="30",
                 HOME=self.root)  # empty HOME: no ~/.claude.json leakage
        return subprocess.run([sys.executable, PIN] + list(args),
                              capture_output=True, text=True, cwd=self.root, env=e)

    def test_pin_then_verify_unchanged(self):
        port = self.serve(env={"FAKE_TOOLS": "alpha,beta"})
        self.write_config(f"http://127.0.0.1:{port}/mcp")
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 2 tool(s)", r.stdout)
        pin = list(json.load(open(self.pins_file)).values())[0]
        self.assertEqual(pin["url"], f"http://127.0.0.1:{port}/mcp")
        self.assertNotIn("command", pin)
        r = self.pin("verify")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("unchanged", r.stdout)

    def test_drift_across_restart_same_url(self):
        # Same url (same identity), changed tool description → rug-pull signal.
        port = self.serve(env={"FAKE_TOOLS": "alpha", "FAKE_DESC": "does"})
        self.write_config(f"http://127.0.0.1:{port}/mcp")
        self.assertEqual(self.pin("pin").returncode, 0)
        self.stop()
        self.serve(env={"FAKE_TOOLS": "alpha", "FAKE_DESC": "now secretly exfiltrates"},
                   port=port)
        r = self.pin("verify")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("DRIFT", r.stdout)
        self.assertIn("changed=['alpha']", r.stdout)

    def test_headers_are_sent_and_missing_auth_is_labeled(self):
        port = self.serve(env={"FAKE_HTTP_AUTH": AUTH})
        # no headers configured → 401 with the honest OAuth-gap label
        self.write_config(f"http://127.0.0.1:{port}/mcp")
        r = self.pin("pin")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("HTTP 401", r.stdout)
        self.assertIn("OAuth", r.stdout)
        # static headers → authenticates and pins
        self.write_config(f"http://127.0.0.1:{port}/mcp",
                          extra={"headers": {"Authorization": AUTH}})
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("pinned 1 tool(s)", r.stdout)

    def test_headers_helper_output_is_used(self):
        port = self.serve(env={"FAKE_HTTP_AUTH": AUTH})
        helper = "printf '%s' '" + json.dumps({"Authorization": AUTH}) + "'"
        self.write_config(f"http://127.0.0.1:{port}/mcp",
                          extra={"headersHelper": helper})
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 1 tool(s)", r.stdout)

    def test_failing_headers_helper_is_reported(self):
        port = self.serve()
        self.write_config(f"http://127.0.0.1:{port}/mcp",
                          extra={"headersHelper": "echo nope >&2; exit 3"})
        r = self.pin("pin")
        self.assertEqual(r.returncode, 1)
        self.assertIn("headersHelper failed", r.stdout)

    def test_sse_response_body(self):
        port = self.serve(env={"FAKE_TOOLS": "alpha,beta", "FAKE_SSE": "1"})
        self.write_config(f"http://127.0.0.1:{port}/mcp")
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 2 tool(s)", r.stdout)
        r = self.pin("verify")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("unchanged", r.stdout)

    def test_legacy_sse_transport_is_skipped(self):
        self.write_config("http://127.0.0.1:9/mcp", type_="sse")
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("legacy SSE", r.stdout)

    def test_unreachable_url_reports_error(self):
        self.write_config("http://127.0.0.1:1/mcp")
        r = self.pin("pin")
        self.assertEqual(r.returncode, 1)
        self.assertIn("cannot reach", r.stdout)

    def test_prune_sees_remote_identity(self):
        port = self.serve()
        self.write_config(f"http://127.0.0.1:{port}/mcp")
        self.assertEqual(self.pin("pin").returncode, 0)
        r = self.pin("prune")  # server still configured → nothing orphaned
        self.assertIn("no orphaned pins", r.stdout)
        json.dump({"mcpServers": {}}, open(os.path.join(self.root, ".mcp.json"), "w"))
        self.pin("prune", "--yes")
        self.assertEqual(json.load(open(self.pins_file)), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
