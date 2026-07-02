#!/usr/bin/env python3
"""Tests for mcp-launch with a stubbed resolver. Run: python test_launch.py"""
import os
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
LAUNCH = os.path.join(os.path.dirname(HERE), "bin", "mcp-launch")

RESOLVER = """#!/bin/sh
case "$1" in
  fail://*) echo "no such secret" >&2; exit 1 ;;
  *) printf 'SEC+%s' "$1" ;;
esac
"""


class LaunchEnv(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="launch-test-")
        self.resolver = os.path.join(self.root, "fake-secret")
        open(self.resolver, "w").write(RESOLVER)
        os.chmod(self.resolver, os.stat(self.resolver).st_mode | stat.S_IEXEC)

    def launch(self, *args):
        env = dict(os.environ, MCP_SECRET_BIN=self.resolver)
        return subprocess.run([LAUNCH] + list(args), capture_output=True, text=True, env=env)

    def test_secret_injected_as_env(self):
        r = self.launch("--secret", "MY_TOKEN=op://V/i/f",
                        "--", "sh", "-c", 'printf %s "$MY_TOKEN"')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "SEC+op://V/i/f")

    def test_secret_equals_form(self):
        r = self.launch("--secret=T=ref1", "--", "sh", "-c", 'printf %s "$T"')
        self.assertEqual(r.stdout, "SEC+ref1")

    def test_arg_appended_to_argv(self):
        r = self.launch("--arg", "--api-key=ref2", "--", "echo", "base")
        self.assertEqual(r.stdout, "base --api-key SEC+ref2\n")

    def test_failed_resolve_exits_1(self):
        r = self.launch("--secret", "T=fail://x", "--", "echo", "never")
        self.assertEqual(r.returncode, 1)
        self.assertIn("failed to resolve", r.stderr)
        self.assertNotIn("never", r.stdout)  # server must not spawn

    def test_bad_pair_exits_2(self):
        self.assertEqual(self.launch("--secret", "noequals", "--", "echo").returncode, 2)

    def test_missing_separator_or_command_exits_2(self):
        self.assertEqual(self.launch("--secret", "T=r", "echo").returncode, 2)
        self.assertEqual(self.launch("--secret", "T=r", "--").returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
