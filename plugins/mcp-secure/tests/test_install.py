#!/usr/bin/env python3
"""install.sh must succeed on a machine with no vault CLI (a supported state:
"you only need a vault if a tool requires a key") and on a config missing its
backend line. Regression for the pipefail-killed grep found in the v1.0
fresh-machine dogfood: the no-vault path exited 2 after linking, and a config
without MCP_SECRET_BACKEND would have died instead of warning.
Run: python3 test_install.py
"""
import os
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
INSTALL = os.path.join(REPO, "install.sh")

# System dirs only: excludes Homebrew/user paths, so op/sops/bw are absent no
# matter what the host has installed.
BARE_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
HELPERS = ("mcp-secret", "mcp-launch", "mcp-bundles", "mcp-doctor", "mcp-pin")

# The keychain backend is offered only on macOS, so the OS has to be a testable
# input: shim `uname` (and `security`) rather than branching on the host. That
# also keeps a real Mac out of the picture, so both CI runners see one behavior.
UNAME_SHIM = "#!/bin/sh\nprintf '%s\\n' '{os}'\n"
SECURITY_SHIM = "#!/bin/sh\nexit 0\n"   # presence is all install.sh checks


def _shim_dir(root, os_name, with_security, with_clis=()):
    d = os.path.join(root, "shims")
    os.makedirs(d, exist_ok=True)
    files = {"uname": UNAME_SHIM.format(os=os_name)}
    if with_security:
        files["security"] = SECURITY_SHIM
    for cli in with_clis:  # fake vault CLIs; presence is all detection checks
        files[cli] = SECURITY_SHIM
    for name, body in files.items():
        p = os.path.join(d, name)
        with open(p, "w") as fh:
            fh.write(body)
        os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
    return d


def run_install(home, os_name="Linux", with_security=False, with_clis=()):
    shims = _shim_dir(home, os_name, with_security, with_clis)
    return subprocess.run(
        ["bash", INSTALL, "--non-interactive"],
        env={"HOME": home, "PATH": shims + os.pathsep + BARE_PATH},
        capture_output=True,
        text=True,
    )


class TestInstall(unittest.TestCase):
    def test_no_vault_cli_still_succeeds(self):
        with tempfile.TemporaryDirectory() as home:
            r = run_install(home)
            self.assertEqual(
                r.returncode, 0,
                "no-vault install must exit 0\nstdout: %s\nstderr: %s"
                % (r.stdout, r.stderr),
            )
            self.assertIn("no secret backend CLI found", r.stderr)
            for b in HELPERS:
                link = os.path.join(home, ".local", "bin", b)
                self.assertTrue(os.path.islink(link), "%s not linked" % b)
            self.assertFalse(
                os.path.exists(os.path.join(home, ".config", "mcp-secret", "config")),
                "no config should be written without a backend",
            )

    def test_config_without_backend_warns_not_dies(self):
        with tempfile.TemporaryDirectory() as home:
            cfg_dir = os.path.join(home, ".config", "mcp-secret")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "config"), "w") as fh:
                fh.write("# hand-rolled config with no backend line\n")
            r = run_install(home)
            self.assertEqual(
                r.returncode, 0,
                "backend-less config must warn, not abort\nstdout: %s\nstderr: %s"
                % (r.stdout, r.stderr),
            )
            self.assertIn("no MCP_SECRET_BACKEND", r.stderr)

    def test_macos_offers_keychain_with_no_vault_cli(self):
        # macOS ships `security`, so a Mac always has a backend available even
        # with no vault CLI installed: the zero-install path.
        with tempfile.TemporaryDirectory() as home:
            r = run_install(home, os_name="Darwin", with_security=True)
            self.assertEqual(
                r.returncode, 0,
                "keychain install must exit 0\nstdout: %s\nstderr: %s"
                % (r.stdout, r.stderr),
            )
            self.assertNotIn("no secret backend CLI found", r.stderr)
            cfg = os.path.join(home, ".config", "mcp-secret", "config")
            self.assertTrue(os.path.exists(cfg), "config should be written")
            with open(cfg) as fh:
                body = fh.read()
            self.assertIn("MCP_SECRET_BACKEND=keychain", body)
            self.assertIn("add-generic-password", r.stdout)  # the store recipe

    def test_keychain_not_offered_off_macos(self):
        # `security` present but not a Mac (or a Linux box that has some other
        # binary by that name): keychain must not be selected.
        with tempfile.TemporaryDirectory() as home:
            r = run_install(home, os_name="Linux", with_security=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("no secret backend CLI found", r.stderr)
            self.assertFalse(
                os.path.exists(os.path.join(home, ".config", "mcp-secret", "config")))

    def _default_backend(self, home):
        cfg = os.path.join(home, ".config", "mcp-secret", "config")
        self.assertTrue(os.path.exists(cfg), "config should be written")
        with open(cfg) as fh:
            for line in fh:
                if line.startswith("MCP_SECRET_BACKEND="):
                    return line.strip().split("=", 1)[1]
        self.fail("no MCP_SECRET_BACKEND line in config")

    def test_backend_ranking_keychain_beats_sops(self):
        # sops installed on a Mac: keychain is still the suggestion. SOPS's
        # root of trust is a plaintext age key on disk; it must be chosen
        # deliberately, never suggested over the Keychain.
        with tempfile.TemporaryDirectory() as home:
            r = run_install(home, os_name="Darwin", with_security=True,
                            with_clis=("sops",))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self._default_backend(home), "keychain")

    def test_backend_ranking_vault_beats_keychain(self):
        # A vault CLI (op) is a statement of intent and has the sync/team
        # story: it outranks the Keychain when present.
        with tempfile.TemporaryDirectory() as home:
            r = run_install(home, os_name="Darwin", with_security=True,
                            with_clis=("op", "sops"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self._default_backend(home), "op")

    def test_backend_ranking_sops_last_off_macos(self):
        # No keychain off macOS: a vault CLI still outranks sops.
        with tempfile.TemporaryDirectory() as home:
            r = run_install(home, os_name="Linux", with_clis=("bw", "sops"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(self._default_backend(home), "bw")

    def test_kept_keychain_config_is_valid_not_warned(self):
        with tempfile.TemporaryDirectory() as home:
            cfg_dir = os.path.join(home, ".config", "mcp-secret")
            os.makedirs(cfg_dir)
            with open(os.path.join(cfg_dir, "config"), "w") as fh:
                fh.write("MCP_SECRET_BACKEND=keychain\n")
            r = run_install(home, os_name="Darwin", with_security=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("not a valid backend", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
