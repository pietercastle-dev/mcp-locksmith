#!/usr/bin/env python3
"""Shipped exemplars must stay exemplary: parseable, exact-pinned, and free of
literal credentials (references only). This is what keeps "exemplar" from
regressing to "placeholder". Run: python3 test_bundles.py

SECRET_VAL/SAFE_VAL are borrowed from hooks/mcp-guard.py with the same
AST-extraction trick as test_keep_in_sync.py (the hook exits at import).
"""
import ast
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
MCP = os.path.dirname(HERE)
BUNDLES = os.path.join(MCP, "bundles")
GUARD = os.path.join(MCP, "hooks", "mcp-guard.py")

# Launchers that fetch a package named in their args: the package must carry an
# exact @x.y.z pin. `npx -y pkg` refetches latest on every spawn.
FETCHING_LAUNCHERS = {"npx", "uvx", "pipx"}
EXACT_PIN = re.compile(r"@\d+\.\d+\.\d+([-.+][0-9A-Za-z.]+)?$")


def load_guard_regexes():
    with open(GUARD) as fh:
        tree = ast.parse(fh.read(), filename=GUARD)
    picked = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id in ("SECRET_VAL", "SAFE_VAL")
            for t in node.targets
        )
    ]
    ns = {"re": re}
    exec(compile(ast.Module(body=picked, type_ignores=[]), GUARD, "exec"), ns)
    return ns["SECRET_VAL"], ns["SAFE_VAL"]


SECRET_VAL, SAFE_VAL = load_guard_regexes()


def bundle_files():
    return sorted(
        os.path.join(BUNDLES, f)
        for f in os.listdir(BUNDLES)
        if f.endswith(".json")
    )


def all_strings(obj):
    """Yield every string value anywhere in a parsed JSON object."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            for s in all_strings(v):
                yield s
    elif isinstance(obj, list):
        for v in obj:
            for s in all_strings(v):
                yield s


def launched_argv(server):
    """The argv that actually runs: unwrap mcp-launch's `--` passthrough."""
    argv = [server.get("command", "")] + list(server.get("args", []))
    if os.path.basename(argv[0]) == "mcp-launch" and "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    return argv


class TestBundles(unittest.TestCase):
    def setUp(self):
        self.parsed = {}
        for path in bundle_files():
            with open(path) as fh:
                self.parsed[os.path.basename(path)] = json.load(fh)

    def test_ship_set_is_nonempty(self):
        self.assertTrue(self.parsed, "no bundle JSON shipped in bundles/")

    def test_shape(self):
        for name, doc in self.parsed.items():
            servers = doc.get("mcpServers")
            self.assertIsInstance(servers, dict, "%s: no mcpServers object" % name)
            self.assertTrue(servers, "%s: mcpServers is empty" % name)

    def test_no_placeholders(self):
        for name, doc in self.parsed.items():
            for server_name, server in doc["mcpServers"].items():
                blob = server_name + " " + json.dumps(server)
                self.assertNotIn(
                    "example-", blob,
                    "%s/%s: placeholder content shipped" % (name, server_name),
                )

    def test_fetched_packages_are_exact_pinned(self):
        for name, doc in self.parsed.items():
            for server_name, server in doc["mcpServers"].items():
                argv = launched_argv(server)
                if os.path.basename(argv[0]) not in FETCHING_LAUNCHERS:
                    continue
                pkgs = [a for a in argv[1:] if not a.startswith("-")]
                self.assertTrue(
                    pkgs, "%s/%s: fetching launcher with no package"
                    % (name, server_name),
                )
                pkg = pkgs[0]
                self.assertNotIn(
                    "@latest", pkg,
                    "%s/%s: floating tag" % (name, server_name),
                )
                self.assertRegex(
                    pkg, EXACT_PIN,
                    "%s/%s: %r is not exact-pinned (want pkg@x.y.z)"
                    % (name, server_name, pkg),
                )

    def test_no_literal_credentials(self):
        for name, doc in self.parsed.items():
            for s in all_strings(doc):
                for m in SECRET_VAL.finditer(s):
                    self.assertTrue(
                        SAFE_VAL.search(m.group(0)),
                        "%s: credential-shaped literal %r"
                        % (name, m.group(0)[:12] + "..."),
                    )

    def test_secret_backed_servers_use_references(self):
        """mcp-launch --secret/--arg values must be NAME=ref, never NAME=<literal
        credential>; HTTP servers must carry auth via headersHelper, not headers."""
        for name, doc in self.parsed.items():
            for server_name, server in doc["mcpServers"].items():
                args = list(server.get("args", []))
                for flag in ("--secret", "--arg"):
                    for i, a in enumerate(args):
                        if a == flag and i + 1 < len(args):
                            pair = args[i + 1]
                            self.assertIn(
                                "=", pair,
                                "%s/%s: %s wants NAME=ref"
                                % (name, server_name, flag),
                            )
                            ref = pair.split("=", 1)[1]
                            self.assertFalse(
                                SECRET_VAL.search(ref)
                                and not SAFE_VAL.search(ref),
                                "%s/%s: literal after %s"
                                % (name, server_name, flag),
                            )
                if server.get("type") == "http" or "url" in server:
                    headers = server.get("headers", {})
                    for k in headers:
                        self.assertNotIn(
                            k.lower(), ("authorization", "cookie"),
                            "%s/%s: auth header inline; use headersHelper"
                            % (name, server_name),
                        )

    def test_vet_comment_on_secret_backed(self):
        """Every exemplar that resolves a secret records provenance + vet date."""
        for name, doc in self.parsed.items():
            uses_secret = any(
                "--secret" in server.get("args", [])
                or "headersHelper" in server
                for server in doc["mcpServers"].values()
            )
            if uses_secret:
                comment = doc.get("_comment", "")
                self.assertRegex(
                    comment, r"[Vv]etted \d{4}-\d{2}-\d{2}",
                    "%s: secret-backed exemplar without a vet date" % name,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
