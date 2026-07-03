#!/usr/bin/env python3
"""Keep-in-sync guard: the credential regexes and the server identity() hash are
duplicated across five standalone scripts by design (no shared lib). This test
freezes that duplication so a change to one copy that isn't mirrored to the
others fails CI. See CLAUDE.md "Keep-in-sync". Run: python test_keep_in_sync.py

The scripts sys.exit()/read stdin at import, so we can't import them. Instead we
AST-parse each file, pull out only the named definitions, and exec those nodes in
an isolated namespace with re/json/hashlib available.
"""
import ast
import hashlib
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
MCP = os.path.dirname(HERE)
HOOKS = os.path.join(MCP, "hooks")
BIN = os.path.join(MCP, "bin")

GUARD = os.path.join(HOOKS, "mcp-guard.py")
CALL_GUARD = os.path.join(HOOKS, "mcp-call-guard.py")
NUDGE = os.path.join(HOOKS, "mcp-nudge.py")
DOCTOR = os.path.join(BIN, "mcp-doctor")
PIN = os.path.join(BIN, "mcp-pin")


def load(path, names):
    """Exec only the module-level Assign/FunctionDef nodes in `names`, in source
    order, in a fresh namespace. Returns that namespace."""
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    picked = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
                picked.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in names:
                picked.append(node)
    ns = {"re": re, "json": json, "hashlib": hashlib}
    exec(compile(ast.Module(body=picked, type_ignores=[]), path, "exec"), ns)
    return ns


# Obviously-fake samples, one per SECRET_VAL shape, built by concatenation so no
# contiguous token literal sits in the source. Each MUST match its shape's
# quantifiers. (label, value)
SECRET_SAMPLES = [
    ("github-classic", "ghp_" + "EXAMPLEONLYnotarealtok"),
    ("github-pat", "github_pat_" + "EXAMPLEONLYnotarealtok"),
    ("slack", "xoxb-" + "EXAMPLE0000000"),
    ("openai-style", "sk-" + "EXAMPLEONLYnotarealkey0"),
    ("aws", "AKIA" + "EXAMPLEACCESS000"),
    ("jwt", "eyJ" + "EXAMPLEONLY" + "." + "notarealpayload"),
    ("google", "AIza" + "EXAMPLEONLYnotarealgooglekey0000"),
    ("pem", "-----BEGIN RSA PRIVATE KEY-----"),
    ("url-creds", "postgres://user:examplepass@dbhost"),
]

# Must match none of the SECRET_VAL shapes; the ref forms must match SAFE_VAL.
SAFE_SAMPLES = [
    "${GITHUB_TOKEN}", "$MYVAR", "op://Vault/item/field",
    "sops://secrets.yaml#/key", "bw://item/field", "Bearer ${TOKEN}",
]
# Not secret-shaped and not a ref (git SHA is a deliberate SECRET_VAL exclusion).
NEUTRAL_SAMPLES = ["a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", "hello-world", "8080"]

# Key names: those that read as credential-bearing vs plainly not.
SECRET_KEYS = ["TOKEN", "SECRET", "PASSWORD", "API_KEY", "ACCESS_KEY",
               "CLIENT_SECRET", "AUTHORIZATION", "AUTH", "BEARER", "COOKIE",
               "KEY", "PAT"]
SAFE_KEYS = ["USERNAME", "HOST", "PORT", "REGION", "URL", "ENDPOINT"]

# (name, command, args) inputs for the identity() hash.
IDENTITY_INPUTS = [
    ("github", "npx", ["-y", "github-mcp@1.2.3"]),
    ("db", "mcp-launch", ["--secret", "X=op://v/i/f", "--", "psql"]),
    ("remote", "https://mcp.example.com", []),
    ("edge", "cmd", ["b", "a", {"k": 1}]),
]


class SecretVal(unittest.TestCase):
    """SECRET_VAL: identical across guard, nudge, doctor (doctor names it _SECRET_VAL)."""

    def setUp(self):
        self.copies = {
            "guard": load(GUARD, {"SECRET_VAL"})["SECRET_VAL"],
            "nudge": load(NUDGE, {"SECRET_VAL"})["SECRET_VAL"],
            "doctor": load(DOCTOR, {"_SECRET_VAL"})["_SECRET_VAL"],
        }

    def test_patterns_identical(self):
        patterns = {name: rx.pattern for name, rx in self.copies.items()}
        self.assertEqual(len(set(patterns.values())), 1,
                         "SECRET_VAL drifted between copies: %r" % patterns)

    def test_matches_every_secret_shape(self):
        for name, rx in self.copies.items():
            for label, val in SECRET_SAMPLES:
                self.assertTrue(rx.search(val), "%s missed %s" % (name, label))

    def test_ignores_safe_and_neutral(self):
        for name, rx in self.copies.items():
            for val in SAFE_SAMPLES + NEUTRAL_SAMPLES:
                self.assertFalse(rx.search(val),
                                 "%s false-matched %r" % (name, val))


class CallGuardShapes(unittest.TestCase):
    """call-guard decomposes SECRET_VAL into labeled SHAPES; it must cover the
    same corpus so the runtime ask stays in step with the write guard."""

    def setUp(self):
        self.ns = load(CALL_GUARD, {"SHAPES", "SAFE_REF", "find_credential"})

    def test_covers_every_secret_shape(self):
        find = self.ns["find_credential"]
        for label, val in SECRET_SAMPLES:
            self.assertIsNotNone(find(val), "SHAPES missed %s" % label)

    def test_ignores_safe_and_neutral(self):
        find = self.ns["find_credential"]
        for val in SAFE_SAMPLES + NEUTRAL_SAMPLES:
            self.assertIsNone(find(val), "SHAPES false-matched %r" % val)


class SafeVal(unittest.TestCase):
    """SAFE_VAL: identical across guard and doctor (doctor names it _SAFE_VAL)."""

    def setUp(self):
        self.copies = {
            "guard": load(GUARD, {"SAFE_VAL"})["SAFE_VAL"],
            "doctor": load(DOCTOR, {"_SAFE_VAL"})["_SAFE_VAL"],
        }

    def test_patterns_identical(self):
        patterns = {name: rx.pattern for name, rx in self.copies.items()}
        self.assertEqual(len(set(patterns.values())), 1,
                         "SAFE_VAL drifted: %r" % patterns)

    def test_accepts_refs_rejects_secrets(self):
        for name, rx in self.copies.items():
            for val in SAFE_SAMPLES:
                self.assertTrue(rx.search(val), "%s rejected ref %r" % (name, val))
            for label, val in SECRET_SAMPLES:
                self.assertFalse(rx.search(val),
                                 "%s accepted secret %s" % (name, label))


class SecretKey(unittest.TestCase):
    """SECRET_KEY: identical across guard and doctor (doctor names it _SECRET_KEY).
    Reconciled to the union of both lists (AUTH|BEARER|COOKIE) 2026-07-03."""

    def setUp(self):
        self.copies = {
            "guard": load(GUARD, {"SECRET_KEY"})["SECRET_KEY"],
            "doctor": load(DOCTOR, {"_SECRET_KEY"})["_SECRET_KEY"],
        }

    def test_patterns_identical(self):
        patterns = {name: rx.pattern for name, rx in self.copies.items()}
        self.assertEqual(len(set(patterns.values())), 1,
                         "SECRET_KEY drifted: %r" % patterns)

    def test_flags_credential_keys(self):
        for name, rx in self.copies.items():
            for key in SECRET_KEYS:
                self.assertTrue(rx.search(key), "%s missed key %s" % (name, key))
            for key in SAFE_KEYS:
                self.assertFalse(rx.search(key),
                                 "%s false-matched key %s" % (name, key))


class Identity(unittest.TestCase):
    """identity(): same hash across pin, call-guard, nudge (call-guard names the
    first param `n`, so compare behavior, not source)."""

    def setUp(self):
        self.funcs = {
            "pin": load(PIN, {"identity"})["identity"],
            "call_guard": load(CALL_GUARD, {"identity"})["identity"],
            "nudge": load(NUDGE, {"identity"})["identity"],
        }

    def test_same_hash_for_every_input(self):
        for name, command, args in IDENTITY_INPUTS:
            hashes = {who: fn(name, command, args)
                      for who, fn in self.funcs.items()}
            self.assertEqual(len(set(hashes.values())), 1,
                             "identity() diverged on %r: %r" % (name, hashes))

    def test_hash_shape(self):
        h = self.funcs["pin"]("x", "y", [])
        self.assertEqual(len(h), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))


if __name__ == "__main__":
    unittest.main(verbosity=2)
