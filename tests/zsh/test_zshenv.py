import shlex

import pytest

from repo import HOME_SOURCE

ZSHENV = shlex.quote(str(HOME_SOURCE / "dot_zshenv"))
PRINT_PATH = 'print -r -- "$PATH"'


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


class TestZshenv:
    class TestOnZdotdir:
        def test_should_point_zdotdir_into_the_config_directory(self, shell, sandbox):
            result = shell(f'source {ZSHENV}; print -r -- "$ZDOTDIR"')
            assert (result.stdout, result.stderr) == (f"{sandbox.home}/.config/zsh\n", "")

        def test_should_follow_xdg_config_home(self, shell, sandbox):
            sandbox.env["XDG_CONFIG_HOME"] = str(sandbox.home / "xdg")
            result = shell(f'source {ZSHENV}; print -r -- "$ZDOTDIR"')
            assert result.stdout == f"{sandbox.home}/xdg/zsh\n"

    class TestOnFnmDefault:
        def test_should_put_its_bin_first_on_path(self, shell, fnm_default, sandbox):
            bin_dir = fnm_default(sandbox.home / ".local" / "share" / "fnm")
            result = shell()
            assert (result.stdout, result.stderr) == (f"{bin_dir}:{sandbox.env['PATH']}\n", "")

        @pytest.mark.parametrize("variable", ["FNM_DIR", "XDG_DATA_HOME"])
        def test_should_find_it_where_fnm_dir_or_xdg_data_home_point(self, shell, fnm_default, sandbox, variable):
            root = sandbox.home / "elsewhere"
            sandbox.env[variable] = str(root)
            bin_dir = fnm_default(root if variable == "FNM_DIR" else root / "fnm")
            assert shell().stdout == f"{bin_dir}:{sandbox.env['PATH']}\n"

        def test_should_not_add_it_twice_when_sourced_twice(self, shell, fnm_default, sandbox):
            bin_dir = fnm_default(sandbox.home / ".local" / "share" / "fnm")
            result = shell(f"source {ZSHENV}; source {ZSHENV}; {PRINT_PATH}")
            assert result.stdout == f"{bin_dir}:{sandbox.env['PATH']}\n"

    class TestOnNoFnmDefault:
        def test_should_change_nothing_and_print_nothing(self, shell, sandbox):
            result = shell()
            assert (result.stdout, result.stderr, result.returncode) == (f"{sandbox.env['PATH']}\n", "", 0)


@pytest.fixture
def shell(sandbox):
    """Starts `zsh -f` with the snippet; by default it sources dot_zshenv and prints the PATH."""
    def start(snippet=f"source {ZSHENV}; {PRINT_PATH}"):
        return sandbox.run("zsh", "-f", "-c", snippet)
    return start


@pytest.fixture
def fnm_default(sandbox):
    """Lays out an fnm dir whose default alias links to an installed version, as fnm does; returns its bin."""
    def build(fnm_dir):
        installation = fnm_dir / "node-versions" / "v22.23.3" / "installation"
        (installation / "bin").mkdir(parents=True)
        (fnm_dir / "aliases").mkdir()
        (fnm_dir / "aliases" / "default").symlink_to(installation)
        return fnm_dir / "aliases" / "default" / "bin"
    return build
