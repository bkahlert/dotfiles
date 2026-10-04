import shlex

import pytest

from repo import HOME_SOURCE

ZSHENV = shlex.quote(str(HOME_SOURCE / "dot_zshenv"))
PRINT_PATH = 'print -r -- "$PATH"'


@pytest.fixture(autouse=True)
def bare(sandbox):
    """Only zsh is on the PATH: a fork of `ls`, `sort` or `tail` would fail instead of passing unnoticed."""
    sandbox.only_tools("zsh")


@pytest.fixture
def nvm(sandbox):
    """Builds ~/.nvm with the given installed versions, alias files and default alias; returns the versions directory."""
    def build(*versions, default=None, aliases=None):
        root = sandbox.home / ".nvm"
        for version in versions:
            (root / "versions" / "node" / version / "bin").mkdir(parents=True)
        for name, target in {"default": default, **(aliases or {})}.items():
            if target is not None:
                alias = root / "alias" / name
                alias.parent.mkdir(parents=True, exist_ok=True)
                alias.write_text(f"{target}\n")
        return root / "versions" / "node"
    return build


@pytest.fixture
def shell(sandbox):
    """Starts `zsh -f` with the snippet; by default it sources dot_zshenv and prints the PATH."""
    def start(snippet=f"source {ZSHENV}; {PRINT_PATH}"):
        return sandbox.run("zsh", "-f", "-c", snippet)
    return start


class TestZshenv:
    class TestOnNvmDefault:
        def test_should_put_an_exact_version_on_the_path(self, nvm, shell, sandbox):
            versions = nvm("v22.1.0", "v20.0.0", default="v22.1.0")
            result = shell()
            assert (result.stdout, result.stderr) == (f"{versions}/v22.1.0/bin:{sandbox.env['PATH']}\n", "")

        @pytest.mark.parametrize("default", ["22", "v22", "22.9", "v22.9", "22.9.0"])
        def test_should_resolve_a_partial_version_with_or_without_the_v(self, nvm, shell, sandbox, default):
            versions = nvm("v20.0.0", "v22.9.0", default=default)
            result = shell()
            assert (result.stdout, result.stderr) == (f"{versions}/v22.9.0/bin:{sandbox.env['PATH']}\n", "")

        def test_should_pick_the_numerically_highest_of_several_matches(self, nvm, shell, sandbox):
            versions = nvm("v22.9.0", "v22.10.0", "v22.2.1", "v220.0.0", default="22")
            assert shell().stdout == f"{versions}/v22.10.0/bin:{sandbox.env['PATH']}\n"

        def test_should_not_match_a_longer_number_for_a_partial_version(self, nvm, shell, sandbox):
            versions = nvm("v22.10.0", "v22.1.5", default="22.1")
            assert shell().stdout == f"{versions}/v22.1.5/bin:{sandbox.env['PATH']}\n"

        def test_should_follow_the_lts_alias_chain(self, nvm, shell, sandbox):
            versions = nvm("v20.1.0", "v22.3.0", default="lts/*",
                           aliases={"lts/*": "lts/jod", "lts/jod": "v22.3.0"})
            result = shell()
            assert (result.stdout, result.stderr) == (f"{versions}/v22.3.0/bin:{sandbox.env['PATH']}\n", "")

        def test_should_follow_a_named_lts_alias_to_a_partial_version(self, nvm, shell, sandbox):
            versions = nvm("v22.3.0", "v22.12.0", default="lts/jod", aliases={"lts/jod": "v22"})
            assert shell().stdout == f"{versions}/v22.12.0/bin:{sandbox.env['PATH']}\n"

        @pytest.mark.parametrize("default", ["node", "stable"])
        def test_should_take_the_newest_installed_version_for_node_and_stable(self, nvm, shell, sandbox, default):
            versions = nvm("v9.11.2", "v22.10.0", "v22.9.0", default=default)
            result = shell()
            assert (result.stdout, result.stderr) == (f"{versions}/v22.10.0/bin:{sandbox.env['PATH']}\n", "")

        def test_should_not_fork_for_the_lookup(self, nvm, shell, fake_bin, calls):
            nvm("v22.1.0", default="22")
            for tool in ("ls", "sort", "tail"):
                fake_bin(tool)
            shell()
            assert [calls(tool) for tool in ("ls", "sort", "tail")] == [[], [], []]

    class TestOnNothingResolving:
        @pytest.mark.parametrize("default, aliases", [
            ("lts/*", {}),
            ("lts/iron", {}),
            ("lts/*", {"lts/*": "lts/iron"}),
            ("23", {}),
            ("a", {"a": "b", "b": "a"}),
            ("../..", {}),
            ("", {}),
        ])
        def test_should_change_nothing_and_print_nothing(self, nvm, shell, sandbox, default, aliases):
            nvm("v22.1.0", default=default, aliases=aliases)
            result = shell()
            assert (result.stdout, result.stderr) == (f"{sandbox.env['PATH']}\n", "")

        def test_should_change_nothing_on_node_without_an_installed_version(self, nvm, shell, sandbox):
            nvm(default="node")
            result = shell()
            assert (result.stdout, result.stderr) == (f"{sandbox.env['PATH']}\n", "")

        def test_should_change_nothing_without_nvm(self, shell, sandbox):
            result = shell()
            assert (result.stdout, result.stderr) == (f"{sandbox.env['PATH']}\n", "")

        def test_should_change_nothing_on_a_version_without_a_bin_directory(self, nvm, shell, sandbox):
            versions = nvm("v22.1.0", default="22")
            (versions / "v22.1.0" / "bin").rmdir()
            result = shell()
            assert (result.stdout, result.stderr) == (f"{sandbox.env['PATH']}\n", "")

    class TestOnBinAlreadyOnPath:
        def test_should_not_add_it_again(self, nvm, shell, sandbox):
            versions = nvm("v22.1.0", default="22")
            sandbox.env["PATH"] = f"{versions}/v22.1.0/bin:{sandbox.env['PATH']}"
            assert shell().stdout == f"{sandbox.env['PATH']}\n"

        def test_should_not_add_it_twice_when_sourced_twice(self, nvm, shell, sandbox):
            versions = nvm("v22.1.0", default="22")
            result = shell(f"source {ZSHENV}; source {ZSHENV}; {PRINT_PATH}")
            assert result.stdout == f"{versions}/v22.1.0/bin:{sandbox.env['PATH']}\n"

    class TestOnZdotdir:
        def test_should_point_zdotdir_into_the_config_directory(self, shell, sandbox):
            result = shell(f'source {ZSHENV}; print -r -- "$ZDOTDIR"')
            assert result.stdout == f"{sandbox.home}/.config/zsh\n"
