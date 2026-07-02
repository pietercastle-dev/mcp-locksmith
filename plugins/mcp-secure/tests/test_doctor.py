#!/usr/bin/env python3
"""Tests for mcp-doctor's config scanning (inline secrets + reference collection),
with a stubbed resolver so no real backend is needed. Run: python test_doctor.py"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
DOCTOR = os.path.join(os.path.dirname(HERE), "bin", "mcp-doctor")
GHP = "ghp_EXAMPLEONLYnotarealtoken00"


class DoctorEnv(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="doctor-test-")
        self.resolver = os.path.join(self.root, "fake-secret")
        open(self.resolver, "w").write("#!/bin/sh\nprintf 'v'\n")
        os.chmod(self.resolver, os.stat(self.resolver).st_mode | stat.S_IEXEC)

    def doctor(self, servers):
        cfg = os.path.join(self.root, "cfg.json")
        json.dump({"mcpServers": servers}, open(cfg, "w"))
        env = dict(os.environ, MCP_SECRET_BIN=self.resolver, HOME=self.root,
                   MCP_SECRET_CONFIG=os.path.join(self.root, "none"),
                   MCP_ORG_CONFIG=os.path.join(self.root, "none"))
        return subprocess.run([sys.executable, DOCTOR, cfg],
                              capture_output=True, text=True, env=env)

    def test_flags_inline_secrets_in_env_headers_and_args(self):
        r = self.doctor({
            "a": {"command": "srv", "env": {"GITHUB_TOKEN": GHP}},
            "b": {"type": "http", "url": "https://x.example",
                  "headers": {"Authorization": "Bearer notarealopaquetokenvalue00"}},
            "c": {"command": "srv", "args": ["--key", "sk-EXAMPLEONLYnotarealkey000"]},
        })
        self.assertEqual(r.returncode, 1)
        self.assertIn("env.GITHUB_TOKEN", r.stdout)
        self.assertIn("headers.Authorization", r.stdout)
        self.assertIn("args[1]", r.stdout)

    def test_clean_config_with_references_passes(self):
        r = self.doctor({
            "a": {"command": "mcp-launch",
                  "args": ["--secret", "T=op://W/i/f", "--", "srv"]},
            "b": {"type": "http", "url": "https://x.example",
                  "headers": {"Authorization": "Bearer ${API_TOKEN}"}},
        })
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no literal secrets in config", r.stdout)
        self.assertIn("op://W/i/f", r.stdout)  # the reference was collected + resolved

    def test_unresolvable_reference_fails(self):
        open(self.resolver, "w").write("#!/bin/sh\necho 'nope' >&2\nexit 1\n")
        r = self.doctor({"a": {"command": "mcp-launch",
                               "args": ["--secret", "T=op://W/i/f", "--", "srv"]}})
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
