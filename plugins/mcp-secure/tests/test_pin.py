#!/usr/bin/env python3
"""Tests for mcp-pin against the fake stdio MCP server. Run: python test_pin.py"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
PIN = os.path.join(os.path.dirname(HERE), "bin", "mcp-pin")
FAKE = os.path.join(HERE, "fake_mcp_server.py")


class PinEnv(unittest.TestCase):
    """Each test gets a fresh project dir + pins file."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pin-test-")
        self.pins_file = os.path.join(self.root, "pins.json")

    def write_config(self, env=None, name="fake"):
        spec = {"command": sys.executable, "args": [FAKE]}
        if env:
            spec["env"] = env
        json.dump({"mcpServers": {name: spec}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))

    def pin(self, *args, home=None):
        e = dict(os.environ, MCP_PINS_FILE=self.pins_file, MCP_PIN_TIMEOUT="30")
        # Point HOME at an empty dir so the runner's real ~/.claude.json
        # servers don't leak into discovery.
        e["HOME"] = home or self.root
        return subprocess.run([sys.executable, PIN] + list(args),
                              capture_output=True, text=True, cwd=self.root, env=e)

    def test_pin_then_verify_unchanged(self):
        self.write_config(env={"FAKE_TOOLS": "alpha,beta"})
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 2 tool(s)", r.stdout)
        r = self.pin("verify")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("unchanged", r.stdout)

    def test_changed_description_is_drift(self):
        self.write_config(env={"FAKE_TOOLS": "alpha", "FAKE_DESC": "does"})
        self.pin("pin")
        self.write_config(env={"FAKE_TOOLS": "alpha", "FAKE_DESC": "now secretly exfiltrates"})
        r = self.pin("verify")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("DRIFT", r.stdout)
        self.assertIn("changed=['alpha']", r.stdout)

    def test_added_and_removed_tools_are_drift(self):
        self.write_config(env={"FAKE_TOOLS": "alpha,beta"})
        self.pin("pin")
        self.write_config(env={"FAKE_TOOLS": "alpha,gamma"})
        r = self.pin("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("added=['gamma']", r.stdout)
        self.assertIn("removed=['beta']", r.stdout)

    def test_changed_args_reads_as_unpinned_not_drift(self):
        # identity = name+command+args, so a version bump (new args) must read
        # as "new, re-pin" — the documented semantics /mcp-secure:update relies on.
        self.write_config()
        self.pin("pin")
        spec = {"command": sys.executable, "args": [FAKE, "--v2"]}
        json.dump({"mcpServers": {"fake": spec}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))
        r = self.pin("verify")
        self.assertEqual(r.returncode, 0)  # unpinned warns, doesn't fail
        self.assertIn("not pinned", r.stdout)

    def test_unpinned_server_warns(self):
        self.write_config()
        r = self.pin("verify")
        self.assertEqual(r.returncode, 0)
        self.assertIn("not pinned", r.stdout)

    def test_unpin_and_prune(self):
        self.write_config()
        self.pin("pin")
        self.assertEqual(len(json.load(open(self.pins_file))), 1)
        r = self.pin("unpin", "fake")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.load(open(self.pins_file)), {})
        # prune: re-pin, then remove the server from config → orphan
        self.write_config()
        self.pin("pin")
        json.dump({"mcpServers": {}}, open(os.path.join(self.root, ".mcp.json"), "w"))
        r = self.pin("prune")  # dry-run keeps it
        self.assertIn("orphaned", r.stdout)
        self.assertEqual(len(json.load(open(self.pins_file))), 1)
        self.pin("prune", "--yes")
        self.assertEqual(json.load(open(self.pins_file)), {})

    def test_unpin_name_collision_keeps_live_pin(self):
        # Regression (found dogfooding a wrapper→mcp-launch migration): after a
        # server's command changes and it's re-pinned under its new identity,
        # `unpin <name>` matched by NAME ONLY and deleted the fresh re-pin
        # along with the stale one. With multiple matches it must remove only
        # the pins that don't match the server as configured here.
        self.write_config()
        self.pin("pin")
        spec = {"command": sys.executable, "args": [FAKE, "--migrated"]}
        json.dump({"mcpServers": {"fake": spec}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))
        self.pin("pin")  # re-pin under the new identity
        self.assertEqual(len(json.load(open(self.pins_file))), 2)
        r = self.pin("unpin", "fake")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("kept the pin", r.stdout)
        remaining = json.load(open(self.pins_file))
        self.assertEqual([v["args"] for v in remaining.values()],
                         [[FAKE, "--migrated"]])
        # A second run is the explicit "remove the live one too" escape hatch.
        r = self.pin("unpin", "fake")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(json.load(open(self.pins_file)), {})

    def test_legacy_sse_server_skipped(self):
        # streamable-HTTP coverage lives in test_pin_http.py; only the legacy
        # SSE transport is still skipped (with an honest note).
        json.dump({"mcpServers": {"r": {"type": "sse", "url": "http://127.0.0.1:9/x"}}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0)
        self.assertIn("legacy SSE", r.stdout)

    def test_tools_subcommand_prints_json(self):
        r = self.pin("tools", "--", sys.executable, FAKE)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tools = json.loads(r.stdout)
        self.assertEqual([t["name"] for t in tools], ["hello"])

    def test_tools_subcommand_usage_and_failure(self):
        self.assertEqual(self.pin("tools").returncode, 2)
        r = self.pin("tools", "--", "/nonexistent-cmd-xyz")
        self.assertEqual(r.returncode, 1)

    def test_verify_records_last_verified(self):
        self.write_config()
        self.pin("pin")
        pins = json.load(open(self.pins_file))
        self.assertNotIn("lastVerified", list(pins.values())[0])
        self.pin("verify")
        pins = json.load(open(self.pins_file))
        self.assertIn("lastVerified", list(pins.values())[0])

    def test_crash_error_includes_server_stderr(self):
        self.write_config(env={"FAKE_DIE": "boom: missing FOO_TOKEN"})
        r = self.pin("verify")
        self.assertEqual(r.returncode, 1)
        self.assertIn("boom: missing FOO_TOKEN", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
