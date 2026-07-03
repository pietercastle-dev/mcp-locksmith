#!/usr/bin/env python3
"""Tests for mcp-secret with stubbed backend CLIs. Run: python test_secret.py"""
import os
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
SECRET = os.path.join(os.path.dirname(HERE), "bin", "mcp-secret")

OP_SHIM = """#!/bin/sh
# fake 1Password CLI: `op read --no-newline <ref>` echoes the ref back
case "$1" in
  read) printf 'op-val:%s' "$3" ;;
  whoami) exit 0 ;;
  *) exit 1 ;;
esac
"""
SOPS_SHIM = """#!/bin/sh
# fake sops: `sops -d --extract <extract> <file>` echoes both back
printf 'sops-val:%s:%s' "$3" "$4"
"""


class SecretEnv(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="secret-test-")
        self.bin = os.path.join(self.root, "shims")
        os.makedirs(self.bin)
        for name, body in (("op", OP_SHIM), ("sops", SOPS_SHIM)):
            p = os.path.join(self.bin, name)
            open(p, "w").write(body)
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        self.cfg = os.path.join(self.root, "config")

    def run_secret(self, ref, config_lines=None):
        if config_lines is not None:
            open(self.cfg, "w").write("\n".join(config_lines) + "\n")
        env = dict(os.environ,
                   PATH=self.bin + os.pathsep + os.environ.get("PATH", ""),
                   MCP_SECRET_CONFIG=self.cfg, HOME=self.root)
        env.pop("MCP_SECRET_BACKEND", None)
        env.pop("MCP_OP_VAULT", None)
        env.pop("MCP_SOPS_FILE", None)
        return subprocess.run([SECRET, ref], capture_output=True, text=True, env=env)

    def test_full_op_ref(self):
        r = self.run_secret("op://Work/cloudflare/token")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "op-val:op://Work/cloudflare/token")

    def test_short_ref_expands_via_config(self):
        r = self.run_secret("cloudflare/token",
                            ["MCP_SECRET_BACKEND=op", "MCP_OP_VAULT=Work"])
        self.assertEqual(r.stdout, "op-val:op://Work/cloudflare/token")

    def test_short_ref_default_field_is_password(self):
        r = self.run_secret("cloudflare", ["MCP_SECRET_BACKEND=op", "MCP_OP_VAULT=W"])
        self.assertEqual(r.stdout, "op-val:op://W/cloudflare/password")

    def test_short_ref_without_backend_errors(self):
        r = self.run_secret("cloudflare/token")
        self.assertEqual(r.returncode, 1)
        self.assertIn("MCP_SECRET_BACKEND not set", r.stderr)

    def test_unknown_scheme_errors(self):
        r = self.run_secret("vault://x/y")
        self.assertEqual(r.returncode, 1)
        self.assertIn("unknown backend scheme", r.stderr)

    def test_sops_extract(self):
        f = os.path.join(self.root, "s.sops.yaml")
        open(f, "w").write("x")
        r = self.run_secret(f"sops://{f}#/cloudflare/token")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, f'sops-val:["cloudflare"]["token"]:{f}')

    def test_sops_path_traversal_rejected(self):
        # regression: shipped security fix (v0.1.1), an untrusted ref must not
        # read outside the intended location
        r = self.run_secret("sops://~/../../etc/passwd#/k")
        self.assertEqual(r.returncode, 1)
        self.assertIn("may not contain '..'", r.stderr)

    def test_sops_ref_needs_fragment(self):
        f = os.path.join(self.root, "s.sops.yaml")
        open(f, "w").write("x")
        r = self.run_secret(f"sops://{f}")
        self.assertEqual(r.returncode, 1)
        self.assertIn("needs a key fragment", r.stderr)

    def test_config_is_parsed_not_executed(self):
        # regression: shipped security fix (v0.1.1), config must never be
        # source'd; a command substitution in a value stays a literal string
        marker = os.path.join(self.root, "pwned")
        r = self.run_secret("item/field",
                            ["MCP_SECRET_BACKEND=op",
                             f"MCP_OP_VAULT=$(touch {marker})",
                             "IGNORED_KEY=whatever"])
        self.assertFalse(os.path.exists(marker), "config value was executed!")
        self.assertEqual(r.stdout, f"op-val:op://$(touch {marker})/item/field")


if __name__ == "__main__":
    unittest.main(verbosity=2)
