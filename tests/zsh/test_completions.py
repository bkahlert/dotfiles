import os
import shlex
import time
from pathlib import Path

import pytest

from repo import CONF_D_SOURCE, module_path

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
    secure(zdotdir)
    # The module prefers $HOMEBREW_PREFIX, so a Homebrew on the machine (group-writable on GitHub's
    # runners) never reaches $fpath.
    prefix = sandbox.home / "brew"
    (prefix / "share" / "zsh" / "site-functions").mkdir(parents=True)
    secure(prefix, prefix / "share", prefix / "share" / "zsh", prefix / "share" / "zsh" / "site-functions")
    sandbox.env["HOMEBREW_PREFIX"] = str(prefix)


@pytest.fixture
def plugin_completion(sandbox, fake_bin):
    """What `sheldon source` emits for a plugin with `apply = ["fpath"]`: its directory put on $fpath.

    $fpath is cut down to the plugin and the directory holding compinit, so a host directory that
    compinit deems insecure (GitHub's runners have one) cannot make it abort.
    """
    plugin = sandbox.home / "plugin-src"
    plugin.mkdir()
    (plugin / "_plugincmd").write_text("#compdef plugincmd\n_plugincmd() { :; }\n")
    (plugin / "_plugincmd").chmod(0o644)
    secure(plugin, sandbox.home)
    fake_bin("sheldon", stdout=f"fpath=({plugin} ${{^fpath}}/compinit(N:h))\n")


def conf_d_order(zsh, snippet):
    return zsh(snippet, modules=sorted([PLUGINS, COMPLETIONS]))


class TestCompletions:
    class TestOnPluginWithCompletions:
        def test_should_register_them(self, zsh, plugin_completion):
            result = conf_d_order(zsh, 'print -r -- "${_comps[plugincmd]}"')
            assert (result.stdout, result.stderr) == ("_plugincmd\n", "")


HOUR = 3600


@pytest.fixture
def zdotdir(sandbox):
    return Path(sandbox.env["ZDOTDIR"])


@pytest.fixture
def hand_written(zdotdir):
    """completions/ next to .zshrc, the directory the module watches for changes."""
    directory = zdotdir / "completions"
    directory.mkdir()
    secure(zdotdir, directory)

    def add(command, hours_old=0):
        file = directory / f"_{command}"
        file.write_text(f"#compdef {command}\n_{command}() {{ :; }}\n")
        file.chmod(0o644)
        age(file, hours_old)
        return file
    return add


def shell(zsh, zdotdir, snippet=""):
    """A new shell: $fpath is the completions directory plus the one holding compinit, then the module runs."""
    return zsh("\n".join([f"fpath=({zdotdir}/completions ${{^fpath}}/compinit(N:h))",
                          f"source {shlex.quote(str(module_path(COMPLETIONS)))}", snippet]))


def registered(zsh, zdotdir, *commands):
    result = shell(zsh, zdotdir, "\n".join(f'print -r -- "${{_comps[{c}]-none}}"' for c in commands))
    assert result.stderr == ""
    return result.stdout.split()


def age(path, hours):
    stamp = time.time() - hours * HOUR
    os.utime(path, (stamp, stamp))


class TestCompletionsDump:
    def test_should_register_the_hand_written_completions_and_write_the_dump(self, zsh, zdotdir, hand_written):
        hand_written("first")
        assert registered(zsh, zdotdir, "first") == ["_first"]
        assert (zdotdir / ".zcompdump").is_file()

    def test_should_reuse_a_dump_younger_than_a_day(self, zsh, zdotdir, hand_written):
        hand_written("first", hours_old=3)
        registered(zsh, zdotdir, "first")
        age(zdotdir / ".zcompdump", 2)
        before = (zdotdir / ".zcompdump").stat().st_mtime_ns
        registered(zsh, zdotdir, "first")
        assert (zdotdir / ".zcompdump").stat().st_mtime_ns == before

    def test_should_rebuild_a_dump_older_than_a_day(self, zsh, zdotdir, hand_written):
        hand_written("first", hours_old=30)
        registered(zsh, zdotdir, "first")
        age(zdotdir / ".zcompdump", 25)
        before = (zdotdir / ".zcompdump").stat().st_mtime_ns
        registered(zsh, zdotdir, "first")
        assert (zdotdir / ".zcompdump").stat().st_mtime_ns > before

    def test_should_not_rescan_fpath_while_the_dump_is_fresh(self, zsh, zdotdir, hand_written, sandbox):
        hand_written("first", hours_old=3)
        registered(zsh, zdotdir, "first")
        age(zdotdir / ".zcompdump", 2)
        late = Path(sandbox.env["HOMEBREW_PREFIX"]) / "share" / "zsh" / "site-functions" / "_late"
        late.write_text("#compdef late\n_late() { :; }\n")
        late.chmod(0o644)
        assert registered(zsh, zdotdir, "late") == ["none"]
        age(zdotdir / ".zcompdump", 25)
        assert registered(zsh, zdotdir, "late") == ["_late"]

    def test_should_see_a_new_completion_although_the_dump_is_still_fresh(self, zsh, zdotdir, hand_written):
        hand_written("first", hours_old=3)
        registered(zsh, zdotdir, "first")
        age(zdotdir / ".zcompdump", 2)
        hand_written("second")
        assert registered(zsh, zdotdir, "first", "second") == ["_first", "_second"]

    def test_should_go_back_to_reusing_the_dump_after_picking_up_a_new_completion(self, zsh, zdotdir, hand_written):
        hand_written("first", hours_old=3)
        registered(zsh, zdotdir, "first")
        age(zdotdir / ".zcompdump", 2)
        hand_written("second")
        registered(zsh, zdotdir, "second")
        settled = (zdotdir / ".zcompdump").stat().st_mtime_ns
        registered(zsh, zdotdir, "second")
        assert (zdotdir / ".zcompdump").stat().st_mtime_ns == settled

    def test_should_not_rebuild_in_every_shell_after_a_known_completion_was_edited(self, zsh, zdotdir, hand_written):
        completion = hand_written("first", hours_old=3)
        registered(zsh, zdotdir, "first")
        age(zdotdir / ".zcompdump", 2)
        hand_written("first")  # same content, but newer than the dump
        registered(zsh, zdotdir, "first")
        settled = (zdotdir / ".zcompdump").stat().st_mtime_ns
        assert settled >= completion.stat().st_mtime_ns
        registered(zsh, zdotdir, "first")
        assert (zdotdir / ".zcompdump").stat().st_mtime_ns == settled


class TestCompletionsOfHomebrew:
    def test_should_register_them_although_brew_shellenv_did_not_run(self, zsh, zdotdir, sandbox):
        site_functions = Path(sandbox.env["HOMEBREW_PREFIX"]) / "share" / "zsh" / "site-functions"
        (site_functions / "_brewcmd").write_text("#compdef brewcmd\n_brewcmd() { :; }\n")
        (site_functions / "_brewcmd").chmod(0o644)
        assert registered(zsh, zdotdir, "brewcmd") == ["_brewcmd"]


class TestCompletionMenu:
    def test_should_offer_the_matches_as_a_menu_that_arrow_keys_walk_through(self, zsh, zdotdir):
        result = shell(zsh, zdotdir, "zstyle -L ':completion:*' menu\nzmodload -e zsh/complist && print complist")
        assert (result.stdout, result.stderr) == ("zstyle ':completion:*' menu select\ncomplist\n", "")
