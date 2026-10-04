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
            assert (calls("idp"), cache.read_text()) == ([["completion", "zsh"]], SCRIPT)

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
        def cached(self, sandbox, fake_bin, cache):
            fake_bin("idp", stdout="IDP_SCRIPT_SOURCED=regenerated\n")
            cache.parent.mkdir(parents=True)
            cache.write_text(SCRIPT)
            os.utime(sandbox.fakes / "idp", (LONG_AGO, LONG_AGO))

        def test_should_source_the_cache_without_running_idp(self, zsh, calls):
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"', modules=MODULES)
            assert (result.stdout, result.stderr, calls("idp")) == ("1\n", "", [])

    class TestOnIdpNewerThanCache:
        def test_should_regenerate_the_cache_and_source_it(self, zsh, sandbox, fake_bin, calls, cache):
            fake_bin("idp", stdout=SCRIPT)
            cache.parent.mkdir(parents=True)
            cache.write_text("IDP_SCRIPT_SOURCED=stale\n")
            os.utime(cache, (LONG_AGO, LONG_AGO))
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"', modules=MODULES)
            assert (result.stdout, calls("idp"), cache.read_text()) == ("1\n", [["completion", "zsh"]], SCRIPT)

        def test_should_keep_the_old_cache_when_idp_fails(self, zsh, sandbox, fake_bin, cache):
            fake_bin("idp", stderr="idp: not logged in\n", exit_code=1)
            cache.parent.mkdir(parents=True)
            cache.write_text("IDP_SCRIPT_SOURCED=stale\n")
            os.utime(cache, (LONG_AGO, LONG_AGO))
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"', modules=MODULES)
            assert (result.stdout, cache.read_text()) == ("stale\n", "IDP_SCRIPT_SOURCED=stale\n")

    class TestOnCacheDirectory:
        def test_should_follow_xdg_cache_home(self, zsh, sandbox, fake_bin):
            fake_bin("idp", stdout=SCRIPT)
            sandbox.env["XDG_CACHE_HOME"] = str(sandbox.home / "elsewhere")
            zsh("true", modules=MODULES)
            assert (sandbox.home / "elsewhere" / "zsh" / "idp-completion.zsh").read_text() == SCRIPT
