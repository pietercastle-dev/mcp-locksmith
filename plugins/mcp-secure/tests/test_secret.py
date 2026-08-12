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
# fake macOS security(1). NEVER let the tests reach the real login keychain: the
# shim shadows /usr/bin/security on a mac and supplies it on Linux CI.
#
# Faithful to the real `security find-generic-password` (behavior verified
# against macOS 15 with a throwaway keychain, never the login one):
#   -w   prints the value + ONE trailing newline, BUT silently LOWERCASE-HEX
#        encodes any value containing a byte outside printable ASCII
#        (0x20-0x7e) — a newline, a tab, an é. Nothing marks it as encoded.
#   -g   prints the item's attributes on STDOUT and the password on STDERR, as
#        `password: "plain"` or `password: 0xHEX  "escaped"`. The 0x form is a
#        superset of -w's: it also kicks in for a backslash, which -w prints raw.
#   not found (unknown service, or an EMPTY -a account) exits 44.
SECURITY_SHIM = '''#!/usr/bin/env python3
import sys

# service -> stored value. Obviously-fake test data only.
VALUES = {
    "multiline": "-----BEGIN KEY-----\\nkc-line2\\n-----END KEY-----",
    "nonascii": "kc-caf\\u00e9",
    "hexlike": "636166c3a9",        # a plain value that merely LOOKS hex-encoded
    "backslash": "kc\\\\val",         # plain for -w, 0x form for -g
    "gquiet": "deadbeef",           # hex-shaped, and -g answers nothing (below)
}

argv = sys.argv[1:]
if not argv or argv[0] != "find-generic-password":
    sys.exit("fake security: unsupported command %r" % (argv[:1],))
svc = acct = None
mode = None
i = 1
while i < len(argv):
    a = argv[i]
    if a == "-s":
        svc = argv[i + 1]; i += 2
    elif a == "-a":
        acct = argv[i + 1]; i += 2
    elif a in ("-w", "-g"):
        mode = a; i += 1
    else:
        i += 1

# "The specified item could not be found in the keychain." -- also what real
# `security` says for an empty account, so `-a ""` is NOT the same as no -a.
if svc in (None, "", "missing") or acct == "":
    sys.stderr.write(
        "security: SecKeychainSearchCopyNext: "
        "The specified item could not be found in the keychain.\\n")
    sys.exit(44)

val = VALUES.get(svc, "kc-val:%s:%s" % (svc, acct or ""))
raw = val.encode("utf-8")

if mode == "-w":
    if all(0x20 <= b <= 0x7e for b in raw):
        out = raw
    else:
        out = raw.hex().encode("ascii")
    sys.stdout.buffer.write(out + b"\\n")
elif mode == "-g":
    sys.stdout.write('keychain: "fake.keychain"\\nclass: "genp"\\nattributes:\\n'
                     '    "acct"<blob>="%s"\\n    "svce"<blob>="%s"\\n'
                     % (acct or "", svc))
    if svc == "gquiet":
        pass                        # a -g that answers nothing: verdict unknown
    elif all(0x20 <= b <= 0x7e and b != 0x5c for b in raw):
        sys.stderr.write('password: "%s"\\n' % val)
    else:
        sys.stderr.write('password: 0x%s  "..."\\n' % raw.hex().upper())
sys.exit(0)
'''
# fake uname: the keychain backend is macOS-only, so the platform check needs a
# testable seam that works on ubuntu CI (and doesn't depend on the host's OS).
UNAME_SHIM = """#!/bin/sh
printf '%s\\n' "${FAKE_UNAME:-Darwin}"
"""


class SecretEnv(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="secret-test-")
        self.bin = os.path.join(self.root, "shims")
        os.makedirs(self.bin)
        for name, body in (("op", OP_SHIM), ("sops", SOPS_SHIM),
                           ("security", SECURITY_SHIM), ("uname", UNAME_SHIM)):
            p = os.path.join(self.bin, name)
            open(p, "w").write(body)
            os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
        self.cfg = os.path.join(self.root, "config")

    def run_secret(self, ref, config_lines=None, **extra_env):
        if config_lines is not None:
            open(self.cfg, "w").write("\n".join(config_lines) + "\n")
        env = dict(os.environ,
                   PATH=self.bin + os.pathsep + os.environ.get("PATH", ""),
                   MCP_SECRET_CONFIG=self.cfg, HOME=self.root)
        env.pop("MCP_SECRET_BACKEND", None)
        env.pop("MCP_OP_VAULT", None)
        env.pop("MCP_SOPS_FILE", None)
        env.update(extra_env)
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

    def test_keychain_full_ref_service_and_account(self):
        r = self.run_secret("keychain://cloudflare/token")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "kc-val:cloudflare:token")

    def test_keychain_full_ref_service_only(self):
        # no /<account> -> `security` is called without -a at all
        r = self.run_secret("keychain://cloudflare")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "kc-val:cloudflare:")

    def test_keychain_short_ref_expands_via_config(self):
        r = self.run_secret("cloudflare/token", ["MCP_SECRET_BACKEND=keychain"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "kc-val:cloudflare:token")

    def test_keychain_short_ref_item_only_has_no_account(self):
        r = self.run_secret("cloudflare", ["MCP_SECRET_BACKEND=keychain"])
        self.assertEqual(r.stdout, "kc-val:cloudflare:")

    def test_keychain_missing_item_errors_without_leaking(self):
        r = self.run_secret("keychain://missing/token")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("keychain item not found", r.stderr)
        self.assertIn("missing", r.stderr)         # names the service
        self.assertIn("token", r.stderr)           # names the account
        self.assertIn("add-generic-password", r.stderr)   # and the fix
        self.assertNotIn("kc-val", r.stderr)       # never echoes a value

    def test_keychain_plain_value_loses_only_securitys_own_newline(self):
        # `security -w` appends one newline of its own; that one goes, and
        # nothing else is added (callers inject the value verbatim).
        r = self.run_secret("keychain://cloudflare/token")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "kc-val:cloudflare:token")   # no trailing \n

    def test_keychain_hex_encoded_value_errors_without_leaking(self):
        # A multi-line value (a PEM key, a JSON blob) comes back hex-encoded
        # from `security -w`. Injecting that would be a silently WRONG secret,
        # so refuse — and say why in plain language.
        r = self.run_secret("keychain://multiline/mcp")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("not plain text", r.stderr)
        self.assertIn("multi-line or non-ASCII", r.stderr)
        self.assertIn("multiline", r.stderr)       # names the service
        self.assertIn("mcp", r.stderr)             # names the account
        self.assertNotIn("BEGIN KEY", r.stderr)    # never echoes the value
        self.assertNotIn("2d2d2d", r.stderr)       # nor its hex encoding

    def test_keychain_non_ascii_value_errors_without_leaking(self):
        r = self.run_secret("keychain://nonascii/mcp")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("not plain text", r.stderr)
        self.assertNotIn("caf", r.stderr)          # never echoes the value
        self.assertNotIn("6b63", r.stderr)         # nor its hex encoding

    def test_keychain_plain_value_that_looks_hex_still_resolves(self):
        # The false-positive guard: plenty of real API keys are lowercase hex.
        # `security -g` distinguishes a stored "636166c3a9" from an encoding of
        # "café", and the plain one must come through untouched.
        r = self.run_secret("keychain://hexlike/mcp")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "636166c3a9")

    def test_keychain_backslash_value_resolves(self):
        # `security -g` shows a backslash-bearing value in its 0x form even
        # though `-w` prints it raw; that must not be mistaken for an encoding.
        r = self.run_secret("keychain://backslash/mcp")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "kc\\val")

    def test_keychain_unverifiable_value_fails_closed(self):
        # if the -g probe can't settle "plain or encoded?", refuse: emitting a
        # maybe-encoded value is exactly the silent wrong-secret bug.
        r = self.run_secret("keychain://gquiet/mcp")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("could not confirm", r.stderr)
        self.assertNotIn("deadbeef", r.stderr)

    def test_keychain_empty_ref_errors(self):
        r = self.run_secret("keychain://")
        self.assertEqual(r.returncode, 1)
        self.assertIn("keychain ref needs a service", r.stderr)

    def test_keychain_empty_service_errors(self):
        r = self.run_secret("keychain:///mcp")
        self.assertEqual(r.returncode, 1)
        self.assertIn("keychain ref needs a service", r.stderr)

    def test_keychain_account_may_contain_slashes(self):
        # only the FIRST slash splits: everything after it is the account
        r = self.run_secret("keychain://cloudflare/a/b")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "kc-val:cloudflare:a/b")

    def test_keychain_requires_macos(self):
        r = self.run_secret("keychain://cloudflare/token", FAKE_UNAME="Linux")
        self.assertEqual(r.returncode, 1)
        self.assertIn("requires macOS", r.stderr)

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
