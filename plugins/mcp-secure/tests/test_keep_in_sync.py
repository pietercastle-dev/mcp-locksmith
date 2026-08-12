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
    "keychain://cloudflare/token", "keychain://cloudflare",
    "Bearer keychain://svc/acct",
    # an expansion followed by a path is a real config shape (SSH_AUTH_SOCK,
    # credential files), and must stay safe now that SAFE_VAL is end-anchored
    "${HOME}/.config/gcloud/x.json", "${TMPDIR}/ssh-x/agent.1", "$HOME/.aws/config",
]

# SAFE_VAL must NOT accept these: a safe-looking PREFIX with something else
# glued on. The trailing token is opaque (no SECRET_VAL shape), so SAFE_VAL is
# the only thing standing between it and the key-name heuristic. Built by
# concatenation, obviously fake.
NTN = "ntn_" + "EXAMPLEONLYnotarealtoken00"
UNSAFE_PREFIX_SAMPLES = [
    "${EMPTY}" + NTN,               # empty expansion, then the real value
    "${NOPE:-" + NTN + "}",         # default-value expansion holding the secret
    "op://v/i/f " + NTN,            # a reference, then the real value
    "Bearer ${TOKEN} " + NTN,
    "${HOME}/x " + NTN,             # …including after the allowed path tail
]
# (`$VAR` + token with no separator is deliberately absent: `$VARntn_…` is a
# single variable name to the shell too, so reading it as one is correct.)
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

    def test_rejects_safe_prefix_with_a_value_glued_on(self):
        # SAFE_VAL is a whitelist of WHOLE values, not of prefixes: an opaque
        # token behind `${EMPTY}` / a vault ref must not read as a reference.
        for name, rx in self.copies.items():
            for val in UNSAFE_PREFIX_SAMPLES:
                self.assertFalse(rx.search(val),
                                 "%s accepted %r as safe" % (name, val))

    def test_scheme_set_matches_call_guards_safe_ref(self):
        # The write guard's SAFE_VAL and the runtime guard's SAFE_REF must know
        # the same vault backends, or a fifth backend silently gets treated as a
        # reference on one path and as an unknown value on the other.
        ref = load(CALL_GUARD, {"SAFE_REF"})["SAFE_REF"]
        want = set(re.findall(r"(\w+)://", ref.pattern))
        self.assertTrue(want, "SAFE_REF lists no schemes")
        for name, rx in self.copies.items():
            self.assertEqual(set(re.findall(r"(\w+)://", rx.pattern)), want,
                             "%s SAFE_VAL schemes differ from SAFE_REF" % name)


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


class ProjectApprovalSync(unittest.TestCase):
    """The Claude Code approval read (project_approval/approval_state) is the
    second thing duplicated between mcp-pin and mcp-doctor: both decide whether
    a ./.mcp.json server may be spawned, so they must decide it identically."""

    def test_source_identical(self):
        for name in ("project_approval", "approval_state"):
            dumps = set()
            for path in (PIN, DOCTOR):
                tree = ast.parse(open(path).read())
                node = next(n for n in tree.body
                            if isinstance(n, ast.FunctionDef) and n.name == name)
                dumps.add(ast.dump(node))
            self.assertEqual(len(dumps), 1, "%s drifted between mcp-pin and mcp-doctor" % name)

    def test_states_agree(self):
        funcs = {"pin": load(PIN, {"approval_state"})["approval_state"],
                 "doctor": load(DOCTOR, {"approval_state"})["approval_state"]}
        # (enable_all, enabled, disabled, trusted) → the decision both must make.
        cases = [
            ((False, set(), set(), False), "unapproved"),   # never opened here
            ((False, {"srv"}, set(), False), "approved"),   # approved by name
            ((False, set(), {"srv"}, False), "disabled"),
            ((True, set(), set(), False), "approved"),      # enableAllProjectMcpServers
            ((False, set(), set(), True), "approved"),      # folder trust accepted
            ((True, set(), {"srv"}, True), "disabled"),     # a by-name no wins
            ((False, {"other"}, set(), False), "unapproved"),
        ]
        for approval, want in cases:
            for who, fn in funcs.items():
                self.assertEqual(fn("srv", approval), want,
                                 "%s: %r → expected %s" % (who, approval, want))


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
