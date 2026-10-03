import pytest

from repo import CONF_D_SOURCE

PLUGINS = "07-plugins.zsh"
COMPLETIONS = next(CONF_D_SOURCE.glob("*-completions.zsh")).name


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh", "mkdir", "touch", "mv", "rm", "cat", "sed", "grep", "uname")
    zdotdir = sandbox.home / ".config" / "zsh"
    zdotdir.mkdir(parents=True)
    sandbox.env["ZDOTDIR"] = str(zdotdir)


@pytest.fixture
def plugin_completion(sandbox, fake_bin):
    """What `sheldon source` emits for a plugin with `apply = ["fpath"]`: its directory put on $fpath."""
    plugin = sandbox.home / "plugin-src"
    plugin.mkdir()
    (plugin / "_plugincmd").write_text("#compdef plugincmd\n_plugincmd() { :; }\n")
    fake_bin("sheldon", stdout=f"fpath=({plugin} $fpath)\n")


def conf_d_order(zsh, snippet):
    return zsh(snippet, modules=sorted([PLUGINS, COMPLETIONS]))


class TestCompletions:
    class TestOnPluginWithCompletions:
        def test_should_register_them(self, zsh, plugin_completion):
            result = conf_d_order(zsh, 'print -r -- "${_comps[plugincmd]}"')
            assert (result.stdout, result.stderr) == ("_plugincmd\n", "")
