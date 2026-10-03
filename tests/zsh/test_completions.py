import pytest

from repo import CONF_D_SOURCE

PLUGINS = "07-plugins.zsh"
COMPLETIONS = next(CONF_D_SOURCE.glob("*-completions.zsh")).name


def secure(*dirs):
    """compinit aborts on a group-writable $fpath directory or parent, which a umask of 002 creates."""
    for path in dirs:
        path.chmod(0o755)


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh", "mkdir", "touch", "mv", "rm", "cat", "sed", "grep", "uname")
    zdotdir = sandbox.home / ".config" / "zsh"
    zdotdir.mkdir(parents=True)
    sandbox.env["ZDOTDIR"] = str(zdotdir)
    # The module prefers $HOMEBREW_PREFIX, so a Homebrew on the machine (group-writable on GitHub's
    # runners) never reaches $fpath.
    prefix = sandbox.home / "brew"
    (prefix / "share" / "zsh" / "site-functions").mkdir(parents=True)
    secure(prefix, prefix / "share", prefix / "share" / "zsh", prefix / "share" / "zsh" / "site-functions")
    sandbox.env["HOMEBREW_PREFIX"] = str(prefix)


@pytest.fixture
def plugin_completion(sandbox, fake_bin):
    """What `sheldon source` emits for a plugin with `apply = ["fpath"]`: its directory put on $fpath."""
    plugin = sandbox.home / "plugin-src"
    plugin.mkdir()
    (plugin / "_plugincmd").write_text("#compdef plugincmd\n_plugincmd() { :; }\n")
    (plugin / "_plugincmd").chmod(0o644)
    secure(plugin, sandbox.home)
    fake_bin("sheldon", stdout=f"fpath=({plugin} $fpath)\n")


def conf_d_order(zsh, snippet):
    return zsh(snippet, modules=sorted([PLUGINS, COMPLETIONS]))


class TestCompletions:
    class TestOnPluginWithCompletions:
        def test_should_register_them(self, zsh, plugin_completion):
            result = conf_d_order(zsh, 'print -r -- "${_comps[plugincmd]}"')
            assert (result.stdout, result.stderr) == ("_plugincmd\n", "")
