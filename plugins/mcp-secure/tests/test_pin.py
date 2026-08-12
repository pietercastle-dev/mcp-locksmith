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


class PinFixture:
    """Fresh project dir + pins file + a redirected HOME, per test."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pin-test-")
        self.pins_file = os.path.join(self.root, "pins.json")

    def approve(self, *names, enable_all=False, disabled=(), trusted=False,
                record=True):
        """Write the fake HOME's ~/.claude.json record for this project, the way
        Claude Code does once the user has opened and approved it.
        record=False writes a config with no entry for this project at all."""
        projects = {}
        if record:
            projects[os.path.realpath(self.root)] = {
                "enabledMcpjsonServers": list(names),
                "disabledMcpjsonServers": list(disabled),
                "enableAllProjectMcpServers": enable_all,
                "hasTrustDialogAccepted": trusted,
            }
        json.dump({"projects": projects},
                  open(os.path.join(self.root, ".claude.json"), "w"))

    def write_config(self, env=None, name="fake", approved=True):
        spec = {"command": sys.executable, "args": [FAKE]}
        if env:
            spec["env"] = env
        json.dump({"mcpServers": {name: spec}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))
        if approved:
            self.approve(name)

    def pin(self, *args, home=None):
        e = dict(os.environ, MCP_PINS_FILE=self.pins_file, MCP_PIN_TIMEOUT="30")
        # Point HOME at an empty dir so the runner's real ~/.claude.json
        # servers don't leak into discovery.
        e["HOME"] = home or self.root
        return subprocess.run([sys.executable, PIN] + list(args),
                              capture_output=True, text=True, cwd=self.root, env=e)


class PinEnv(PinFixture, unittest.TestCase):
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
        # as "new, re-pin", the documented semantics /mcp-secure:update relies on.
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

    def test_repin_replace_supersedes_stale_pin(self):
        # After a version bump / migration the server hashes to a NEW identity;
        # `pin --replace` must drop the stale same-name pin so no orphan is left
        # (and a later verify can't match the wrong baseline). Fixes the orphan-
        # accumulation UX found dogfooding: the re-pin flows pass --replace.
        self.write_config()
        self.pin("pin")
        spec = {"command": sys.executable, "args": [FAKE, "--v2"]}
        json.dump({"mcpServers": {"fake": spec}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))
        r = self.pin("pin", "--replace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("superseded prior pin", r.stdout)
        remaining = json.load(open(self.pins_file))
        self.assertEqual([v["args"] for v in remaining.values()], [[FAKE, "--v2"]])

    def test_repin_without_replace_keeps_and_flags_stale_pin(self):
        # Conservative default: a bare re-pin leaves the stale pin (it MIGHT be
        # the same-named server in another repo, invisible from here) but flags
        # it and points at --replace, so orphans are never silent.
        self.write_config()
        self.pin("pin")
        spec = {"command": sys.executable, "args": [FAKE, "--v2"]}
        json.dump({"mcpServers": {"fake": spec}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("--replace", r.stdout)
        self.assertEqual(len(json.load(open(self.pins_file))), 2)  # both kept

    def test_repin_replace_leaves_other_servers_alone(self):
        # --replace only supersedes pins with the SAME name; a different server's
        # pin must survive a re-pin.
        self.write_config(name="fake")
        self.pin("pin")
        # add a second, differently-named server and pin it too
        json.dump({"mcpServers": {
            "fake": {"command": sys.executable, "args": [FAKE]},
            "other": {"command": sys.executable, "args": [FAKE]}}},
            open(os.path.join(self.root, ".mcp.json"), "w"))
        self.approve("fake", "other")
        self.pin("pin")
        # now bump only `fake` and re-pin --replace
        json.dump({"mcpServers": {
            "fake": {"command": sys.executable, "args": [FAKE, "--v2"]},
            "other": {"command": sys.executable, "args": [FAKE]}}},
            open(os.path.join(self.root, ".mcp.json"), "w"))
        self.pin("pin", "--replace", "fake")
        names = sorted(v["name"] for v in json.load(open(self.pins_file)).values())
        self.assertEqual(names, ["fake", "other"])  # other untouched, fake not doubled

    def test_legacy_sse_server_skipped(self):
        # streamable-HTTP coverage lives in test_pin_http.py; only the legacy
        # SSE transport is still skipped (with an honest note).
        json.dump({"mcpServers": {"r": {"type": "sse", "url": "http://127.0.0.1:9/x"}}},
                  open(os.path.join(self.root, ".mcp.json"), "w"))
        self.approve("r")
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


class ProjectApproval(PinFixture, unittest.TestCase):
    """A ./.mcp.json ships with a cloned repo, so a sweep must not spawn its
    servers (or run their headersHelper) before Claude Code has approval on
    record for this directory. Reads ~/.claude.json; HOME is redirected here,
    the real one is never touched."""

    def test_no_approval_record_is_skipped_with_a_note(self):
        self.write_config(approved=False)  # .mcp.json, no ~/.claude.json at all
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("not approved in Claude Code yet", r.stdout)
        self.assertNotIn("pinned 1 tool(s)", r.stdout)
        self.assertEqual(json.load(open(self.pins_file)), {})

    def test_project_entry_without_the_server_is_skipped(self):
        # The project HAS a record (other servers approved), this one isn't in it.
        self.write_config(approved=False)
        self.approve("somethingelse")
        r = self.pin("verify")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("not approved in Claude Code yet", r.stdout)
        self.assertNotIn("not pinned", r.stdout)  # never launched, so never judged

    def test_enabled_server_is_launched(self):
        self.write_config()  # write_config approves by name
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 1 tool(s)", r.stdout)

    def test_disabled_server_is_skipped(self):
        self.write_config(approved=False)
        self.approve(disabled=["fake"])
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("turned off for this project", r.stdout)
        self.assertEqual(json.load(open(self.pins_file)), {})

    def test_disable_beats_enable_all(self):
        # Contradictory config: the user said no to this one by name.
        self.write_config(approved=False)
        self.approve("fake", enable_all=True, disabled=["fake"])
        r = self.pin("pin")
        self.assertIn("turned off for this project", r.stdout)
        self.assertEqual(json.load(open(self.pins_file)), {})

    def test_enable_all_project_servers_launches(self):
        self.write_config(approved=False)
        self.approve(enable_all=True)
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 1 tool(s)", r.stdout)

    def test_trusted_folder_with_empty_lists_launches(self):
        # What a real, working repo looks like: the user accepted the folder
        # trust dialog and the per-server lists stayed empty. Gating on the
        # lists alone would skip every server people actually run.
        self.write_config(approved=False)
        self.approve(trusted=True)
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 1 tool(s)", r.stdout)

    def test_trusted_folder_still_honors_an_explicit_disable(self):
        self.write_config(approved=False)
        self.approve(trusted=True, disabled=["fake"])
        r = self.pin("pin")
        self.assertIn("turned off for this project", r.stdout)
        self.assertEqual(json.load(open(self.pins_file)), {})

    def test_explicitly_named_server_always_runs(self):
        # The escape hatch: naming it IS the user's consent.
        self.write_config(approved=False)
        r = self.pin("pin", "fake")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 1 tool(s)", r.stdout)
        r = self.pin("verify", "fake")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("unchanged", r.stdout)

    def test_user_scope_server_is_never_gated(self):
        # ~/.claude.json servers were added deliberately; only project scope,
        # which arrives with a repo, needs an approval record.
        json.dump({"mcpServers": {"user_srv": {"command": sys.executable, "args": [FAKE]}},
                   "projects": {}},
                  open(os.path.join(self.root, ".claude.json"), "w"))
        r = self.pin("pin")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pinned 1 tool(s)", r.stdout)

    def test_unpinned_project_server_keeps_its_pin_through_prune(self):
        # prune/unpin don't launch anything, so they must still SEE a skipped
        # server: otherwise its pin would look orphaned and get dropped.
        self.write_config()
        self.pin("pin")
        self.approve()  # approval revoked (e.g. a fresh machine / new clone)
        r = self.pin("prune", "--yes")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("no orphaned pins", r.stdout)
        self.assertEqual(len(json.load(open(self.pins_file))), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
