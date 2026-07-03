#!/usr/bin/env python3
"""Tests for mcp-nudge.py (SessionStart). Run: python test_nudge.py"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

NUDGE = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "mcp-nudge.py")
GHP = "ghp_EXAMPLEONLYnotarealtoken00"


def identity(name, command, args):
    raw = name + "\0" + command + "\0" + json.dumps(args, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class Env:
    def __init__(self, git=True, servers=None, bundles=(), pins=None):
        self.root = tempfile.mkdtemp(prefix="nudge-test-")
        self.home = os.path.join(self.root, "home")
        self.proj = os.path.join(self.root, "proj")
        os.makedirs(self.home)
        os.makedirs(self.proj)
        if git:
            os.makedirs(os.path.join(self.proj, ".git"))
        if servers is not None:
            json.dump({"mcpServers": servers}, open(os.path.join(self.proj, ".mcp.json"), "w"))
        bdir = os.path.join(self.home, ".config", "mcp-secret", "bundles")
        os.makedirs(bdir)
        for b in bundles:
            json.dump({"mcpServers": {}}, open(os.path.join(bdir, b + ".json"), "w"))
        if pins:
            pdir = os.path.join(self.home, ".config", "mcp-secret")
            json.dump(pins, open(os.path.join(pdir, "pins.json"), "w"))

    def run(self):
        env = dict(os.environ, HOME=self.home)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        env.pop("MCP_USER_BUNDLES", None)
        env["MCP_ORG_CONFIG"] = os.path.join(self.root, "no-org.json")
        p = subprocess.run([sys.executable, NUDGE], input=json.dumps({"cwd": self.proj}),
                           capture_output=True, text=True, env=env)
        out = p.stdout.strip()
        if not out:
            return None
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]


class Nudge(unittest.TestCase):
    def test_silent_outside_git_repo(self):
        self.assertIsNone(Env(git=False, bundles=("frontend",)).run())

    def test_no_servers_suggests_bundles(self):
        msg = Env(servers=None, bundles=("frontend", "team")).run()
        self.assertIn("no MCP servers", msg)
        self.assertIn("frontend", msg)
        self.assertIn("team", msg)

    def test_no_servers_no_bundles_is_silent(self):
        self.assertIsNone(Env(servers=None).run())

    def test_inline_env_secret_nudges_audit_once(self):
        e = Env(servers={"s": {"command": "srv", "env": {"T": GHP}}})
        msg = e.run()
        self.assertIn("plain text", msg)
        self.assertIn("audit", msg)
        self.assertIsNone(e.run())  # marker: at most once per project

    def test_inline_header_secret_nudges(self):
        e = Env(servers={"s": {"type": "http", "url": "https://x.example",
                               "headers": {"Authorization": f"Bearer {GHP}"}}})
        self.assertIn("plain text", e.run())

    def test_unpinned_server_nudges(self):
        e = Env(servers={"s": {"command": "srv", "args": ["--x"]}})
        msg = e.run()
        self.assertIn("pinned", msg)

    def test_clean_and_freshly_pinned_is_silent(self):
        import time
        fresh = time.strftime("%Y-%m-%dT%H:%M:%S")
        pins = {identity("s", "srv", ["--x"]): {"name": "s", "pinnedAt": fresh}}
        e = Env(servers={"s": {"command": "srv", "args": ["--x"]}}, pins=pins)
        self.assertIsNone(e.run())

    def test_stale_pin_nudges_check(self):
        pins = {identity("s", "srv", ["--x"]):
                {"name": "s", "pinnedAt": "2026-01-01T00:00:00"}}
        e = Env(servers={"s": {"command": "srv", "args": ["--x"]}}, pins=pins)
        msg = e.run()
        self.assertIn("drift-checked", msg)
        self.assertIn("check", msg)
        self.assertIsNone(e.run())  # marker gates the re-nudge

    def test_fresh_verify_beats_old_pin(self):
        import time
        fresh = time.strftime("%Y-%m-%dT%H:%M:%S")
        pins = {identity("s", "srv", ["--x"]):
                {"name": "s", "pinnedAt": "2026-01-01T00:00:00", "lastVerified": fresh}}
        e = Env(servers={"s": {"command": "srv", "args": ["--x"]}}, pins=pins)
        self.assertIsNone(e.run())

    def test_oauth_style_remote_not_counted_unpinned(self):
        # no headers/headersHelper → likely Claude Code OAuth, which mcp-pin
        # can't baseline, stay silent rather than nag about the impossible
        e = Env(servers={"r": {"type": "http", "url": "https://x.example"}})
        self.assertIsNone(e.run())

    def test_unpinned_remote_with_headers_nudges(self):
        e = Env(servers={"r": {"type": "http", "url": "https://x.example",
                               "headers": {"X-Api-Key": "${KEY}"}}})
        self.assertIn("pinned", e.run())

    def test_pinned_remote_stale_nudges_check(self):
        pins = {identity("r", "https://x.example", []):
                {"name": "r", "pinnedAt": "2026-01-01T00:00:00"}}
        e = Env(servers={"r": {"type": "http", "url": "https://x.example",
                               "headers": {"X-Api-Key": "${KEY}"}}}, pins=pins)
        self.assertIn("drift-checked", e.run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
