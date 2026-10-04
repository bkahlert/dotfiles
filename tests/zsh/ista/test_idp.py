import os

import pytest

MODULES = ["ista/10-idp.zsh"]
# What `idp completion zsh` prints: a wrapper function and its completion setup, to be sourced by the shell.
SCRIPT = "IDP_SCRIPT_SOURCED=1\nidp() { print wrapper \"$@\"; }\n"
LONG_AGO = 1_000_000_000


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


@pytest.fixture
def cache(sandbox):
    return sandbox.home / ".cache" / "zsh" / "idp-completion.zsh"


class TestIdp:
    class TestOnNoIdp:
        def test_should_stay_silent_and_define_nothing(self, zsh, sandbox):
            (sandbox.fakes / "idp").unlink()
            result = zsh('print -r -- "${IDP_SCRIPT_SOURCED-unset} ${+functions[idp]}"', modules=MODULES)
            assert (result.returncode, result.stdout, result.stderr) == (0, "unset 0\n", "")

        def test_should_not_leave_a_cache_behind(self, zsh, sandbox, cache):
            (sandbox.fakes / "idp").unlink()
            zsh("true", modules=MODULES)
            assert not cache.exists()

    class TestOnIdp:
        def test_should_ask_it_for_the_zsh_completion_script_and_cache_the_answer(self, zsh, fake_bin, calls, cache):
            fake_bin("idp", stdout=SCRIPT)
            zsh("true", modules=MODULES)
            assert (calls("idp"), body(cache)) == ([["completion", "zsh"]], SCRIPT)

        def test_should_source_the_script_into_the_current_shell(self, zsh, fake_bin):
            fake_bin("idp", stdout=SCRIPT)
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"\nidp use staging', modules=MODULES)
            assert (result.stdout, result.stderr) == ("1\nwrapper use staging\n", "")

        def test_should_let_the_shell_start_when_idp_fails(self, zsh, fake_bin):
            fake_bin("idp", stderr="idp: not logged in\n", exit_code=1)
            result = zsh("print still-running", modules=MODULES)
            assert (result.returncode, result.stdout) == (0, "still-running\n")

        def test_should_not_cache_a_failed_run(self, zsh, fake_bin, cache):
            fake_bin("idp", stderr="idp: not logged in\n", exit_code=1)
            zsh("true", modules=MODULES)
            assert not cache.exists()

    class TestOnFreshCache:
        @pytest.fixture(autouse=True)
        def cached(self, zsh, sandbox, fake_bin):
            fake_bin("idp", stdout=SCRIPT)
            zsh("true", modules=MODULES)
            fake_bin("idp", stdout="IDP_SCRIPT_SOURCED=regenerated\n")
            os.utime(sandbox.fakes / "idp", (LONG_AGO, LONG_AGO))

        def test_should_source_the_cache_without_running_idp(self, zsh, calls):
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"', modules=MODULES)
            # The one call is the fixture's, which wrote the cache.
            assert (result.stdout, result.stderr, calls("idp")) == ("1\n", "", [["completion", "zsh"]])

    class TestOnIdpNewerThanCache:
        def test_should_regenerate_the_cache_and_source_it(self, zsh, sandbox, fake_bin, calls, cache):
            fake_bin("idp", stdout=SCRIPT)
            stale(sandbox, cache)
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"', modules=MODULES)
            assert (result.stdout, calls("idp"), body(cache)) == ("1\n", [["completion", "zsh"]], SCRIPT)

        def test_should_keep_the_old_cache_when_idp_fails(self, zsh, sandbox, fake_bin, cache):
            fake_bin("idp", stderr="idp: not logged in\n", exit_code=1)
            stale(sandbox, cache)
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"', modules=MODULES)
            assert (result.stdout, body(cache)) == ("stale\n", "IDP_SCRIPT_SOURCED=stale\n")

    class TestOnUpgradeToAnOlderBuild:
        def test_should_regenerate_the_cache_for_the_new_binary(self, zsh, sandbox):
            """Homebrew links a new version from a new Cellar path and keeps the build's mtime, which can predate the cache."""
            (sandbox.fakes / "idp").unlink()
            (sandbox.fakes / "idp").symlink_to(installed_idp(sandbox, "1.0", "IDP_SCRIPT_SOURCED=v1"))
            zsh("true", modules=MODULES)
            (sandbox.fakes / "idp").unlink()
            (sandbox.fakes / "idp").symlink_to(installed_idp(sandbox, "2.0", "IDP_SCRIPT_SOURCED=v2"))
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"', modules=MODULES)
            assert (result.stdout, result.stderr) == ("v2\n", "")


    class TestOnCacheDirectory:
        def test_should_follow_xdg_cache_home(self, zsh, sandbox, fake_bin):
            fake_bin("idp", stdout=SCRIPT)
            sandbox.env["XDG_CACHE_HOME"] = str(sandbox.home / "elsewhere")
            zsh("true", modules=MODULES)
            assert body(sandbox.home / "elsewhere" / "zsh" / "idp-completion.zsh") == SCRIPT


def installed_idp(sandbox, version, script):
    """An idp under a versioned Cellar path whose mtime is long ago."""
    binary = sandbox.home / "Cellar" / "idp" / version / "bin" / "idp"
    binary.parent.mkdir(parents=True)
    binary.write_text(f"#!/bin/sh\nprintf '%s\\n' '{script}'\n")
    binary.chmod(0o755)
    os.utime(binary, (LONG_AGO, LONG_AGO))
    return binary


def body(cache):
    """The cached script without its first line, which names the binary it came from."""
    return cache.read_text().split("\n", 1)[1]


def stale(sandbox, cache):
    """A cache written for the idp on the PATH, older than that binary: only the mtime says to regenerate it."""
    cache.parent.mkdir(parents=True)
    cache.write_text(f"# idp: {(sandbox.fakes / 'idp').resolve()}\nIDP_SCRIPT_SOURCED=stale\n")
    os.utime(cache, (LONG_AGO, LONG_AGO))
