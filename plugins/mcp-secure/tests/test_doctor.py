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

    def doctor(self, servers, *flags, backend=None):
        cfg = os.path.join(self.root, "cfg.json")
        json.dump({"mcpServers": servers}, open(cfg, "w"))
        secret_cfg = os.path.join(self.root, "none")
        if backend:
            secret_cfg = os.path.join(self.root, "mcp-secret-config")
            open(secret_cfg, "w").write("MCP_SECRET_BACKEND=%s\n" % backend)
        env = dict(os.environ, MCP_SECRET_BIN=self.resolver, HOME=self.root,
                   MCP_SECRET_CONFIG=secret_cfg,
                   MCP_ORG_CONFIG=os.path.join(self.root, "none"))
        return subprocess.run([sys.executable, DOCTOR, *flags, cfg],
                              capture_output=True, text=True, env=env)

    def project_doctor(self, servers, *flags, approved=None, enable_all=False,
                       disabled=(), trusted=False):
        """Point mcp-doctor at a real project `.mcp.json`, with (or without)
        Claude Code's approval record for that directory in a redirected HOME.
        approved=None means no record at all, i.e. a freshly cloned repo."""
        proj = os.path.join(self.root, "proj")
        os.makedirs(proj, exist_ok=True)
        cfg = os.path.join(proj, ".mcp.json")
        json.dump({"mcpServers": servers}, open(cfg, "w"))
        record = {}
        if approved is not None or enable_all or disabled or trusted:
            record[os.path.realpath(proj)] = {
                "enabledMcpjsonServers": list(approved or []),
                "disabledMcpjsonServers": list(disabled),
                "enableAllProjectMcpServers": enable_all,
                "hasTrustDialogAccepted": trusted,
            }
        json.dump({"projects": record}, open(os.path.join(self.root, ".claude.json"), "w"))
        env = dict(os.environ, MCP_SECRET_BIN=self.resolver, HOME=self.root,
                   MCP_SECRET_CONFIG=os.path.join(self.root, "none"),
                   MCP_ORG_CONFIG=os.path.join(self.root, "none"))
        return subprocess.run([sys.executable, DOCTOR, *flags, cfg],
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

    def test_launch_check_passes_working_server(self):
        fake = os.path.join(HERE, "fake_mcp_server.py")
        r = self.doctor({"f": {"command": sys.executable, "args": [fake],
                               "env": {"FAKE_TOOLS": "a,b"}}}, "--launch")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("launches and speaks MCP (2 tools)", r.stdout)

    def test_launch_check_reports_crash_with_stderr(self):
        fake = os.path.join(HERE, "fake_mcp_server.py")
        r = self.doctor({"f": {"command": sys.executable, "args": [fake],
                               "env": {"FAKE_DIE": "config file missing"}},
                         "remote": {"type": "http", "url": "https://x.example"}},
                        "--launch")
        self.assertEqual(r.returncode, 1)
        self.assertIn("config file missing", r.stdout)
        self.assertIn("no local launch", r.stdout)  # remote noted, not failed

    def test_launch_check_missing_command(self):
        r = self.doctor({"f": {"command": "/nonexistent-cmd-xyz", "args": []}}, "--launch")
        self.assertEqual(r.returncode, 1)

    def test_keychain_backend_is_recognized(self):
        # keychain is a known backend, so it must be reported, never treated as
        # missing/unknown. On macOS that's "reachable"; elsewhere a warning that
        # the refs won't resolve here (a warning, so Linux CI stays green).
        r = self.doctor({}, backend="keychain")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("default backend: keychain", r.stdout)
        if sys.platform == "darwin":
            self.assertIn("macOS Keychain reachable", r.stdout)
        else:
            self.assertIn("isn't macOS", r.stdout)

    def test_keychain_reference_is_collected_and_not_flagged(self):
        r = self.doctor({
            "a": {"command": "mcp-launch",
                  "args": ["--secret", "T=keychain://cloudflare/mcp", "--", "srv"]},
            "b": {"command": "srv", "env": {"API_TOKEN": "keychain://svc/acct"}},
        })
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no literal secrets in config", r.stdout)
        self.assertIn("keychain://cloudflare/mcp", r.stdout)
        self.assertIn("keychain://svc/acct", r.stdout)

    def test_unapproved_project_server_is_not_launched(self):
        # A .mcp.json arrives with a cloned repo: until Claude Code has the
        # user's approval on record, running mcp-doctor must not be what
        # spawns its command.
        fake = os.path.join(HERE, "fake_mcp_server.py")
        r = self.project_doctor({"f": {"command": sys.executable, "args": [fake]}},
                                "--launch")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("not approved in Claude Code yet", r.stdout)
        self.assertNotIn("launches and speaks MCP", r.stdout)

    def test_unapproved_project_server_still_gets_static_checks(self):
        # Skipping the launch must not skip the config review: the inline-secret
        # finding is exactly what an audit of a new repo is for.
        r = self.project_doctor({"f": {"command": "srv", "env": {"GITHUB_TOKEN": GHP}}})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("env.GITHUB_TOKEN", r.stdout)
        self.assertIn("not approved in Claude Code yet", r.stdout)

    def test_unapproved_project_server_references_are_not_resolved(self):
        # Resolving a reference runs the vault CLI on a string from that
        # untrusted config, so it waits for approval too.
        r = self.project_doctor({"a": {"command": "mcp-launch",
                                       "args": ["--secret", "T=op://W/i/f", "--", "srv"]}})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no secret references found", r.stdout)
        self.assertNotIn("op://W/i/f", r.stdout)

    def test_approved_project_server_launches(self):
        fake = os.path.join(HERE, "fake_mcp_server.py")
        spec = {"f": {"command": sys.executable, "args": [fake], "env": {"FAKE_TOOLS": "a,b"}}}
        r = self.project_doctor(spec, "--launch", approved=["f"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("launches and speaks MCP (2 tools)", r.stdout)
        # enableAllProjectMcpServers is the other way to say yes…
        r = self.project_doctor(spec, "--launch", enable_all=True)
        self.assertIn("launches and speaks MCP (2 tools)", r.stdout)
        # …as is an accepted folder trust dialog, which is what a real working
        # repo has (its per-server lists stay empty).
        r = self.project_doctor(spec, "--launch", trusted=True)
        self.assertIn("launches and speaks MCP (2 tools)", r.stdout)
        # …unless the server is turned off by name.
        r = self.project_doctor(spec, "--launch", enable_all=True, disabled=["f"])
        self.assertIn("turned off for this project", r.stdout)
        self.assertNotIn("launches and speaks MCP", r.stdout)

    def test_unresolvable_reference_fails(self):
        open(self.resolver, "w").write("#!/bin/sh\necho 'nope' >&2\nexit 1\n")
        r = self.doctor({"a": {"command": "mcp-launch",
                               "args": ["--secret", "T=op://W/i/f", "--", "srv"]}})
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
