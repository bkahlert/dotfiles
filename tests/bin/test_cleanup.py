import sys

import pytest

darwin = pytest.mark.skipif(sys.platform != "darwin", reason="cleanup is macOS only")


class TestCleanup:
    @darwin
    class TestOnDryRun:
        def test_should_delete_nothing_and_report_both_totals(self, run, fake_bin, calls, sandbox):
            safe, risky = xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", timeout=30)
            assert result.returncode == 0
            assert safe.exists() and risky.exists()
            assert "▪ DerivedData (dry-run)\n" in result.stdout
            assert "▪ Xcode Archives: would ask\n" in result.stdout
            assert "↗ Would reclaim: ~" in result.stdout
            assert calls("sudo") == []

        def test_should_delete_nothing_even_with_yes(self, run, fake_bin, sandbox):
            safe, risky = xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", "--yes", timeout=30)
            assert result.returncode == 0
            assert safe.exists() and risky.exists()

    @darwin
    class TestOnDryRunWithEveryToolPresent:
        @pytest.mark.parametrize("args", [(), ("--yes",)], ids=["plain", "with --yes"])
        def test_should_announce_each_tool_command_and_run_none_of_them(self, run, fake_bin, calls, sandbox, args):
            busy_tools(fake_bin, sandbox)
            result = run("cleanup", *args, timeout=30)
            assert result.returncode == 0
            for announced in ("composer clearcache", "brew cleanup --prune=all -s", "gem cleanup",
                              "npm cache clean --force", "yarn cache clean --force", "uv cache clean",
                              "xcrun simctl delete unavailable"):
                assert f"ℹ would run: {announced}\n" in result.stdout
            for asked in ("Trash: would ask", "Containers: would ask", "Volumes: would ask"):
                assert f"▪ {asked}\n" in result.stdout
            assert "would run: docker" not in result.stdout
            assert "would run: empty_trash" not in result.stdout
            for tool in ("composer", "gem", "npm", "yarn", "uv"):
                assert calls(tool) == [], tool
            assert calls("brew") == [["--cache"]]
            assert calls("docker") == [["info"], ["system", "df"]]
            assert calls("xcrun") == [["simctl", "list", "devices", "-j"], ["simctl", "runtime", "list", "-j"]]
            assert calls("osascript") == [["-e", "tell application \"Finder\" to count items of trash"]]
            assert calls("sudo") == []

    @darwin
    class TestOnApply:
        def test_should_remove_safe_items_and_keep_risky_ones_without_a_terminal(self, run, fake_bin, sandbox):
            safe, risky = xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", "--apply", timeout=30)
            assert result.returncode == 0
            assert not safe.exists() and risky.exists()
            assert "✔ DerivedData cleaned\n" in result.stdout
            assert "ℹ non-interactive: keeping\n▪ Xcode Archives kept\n" in result.stdout

        def test_should_remove_risky_items_with_yes(self, run, fake_bin, sandbox):
            safe, risky = xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", "--apply", "--yes", timeout=30)
            assert result.returncode == 0
            assert not safe.exists() and not risky.exists()
            assert "ℹ auto-yes\n✔ Xcode Archives cleaned\n" in result.stdout

        def test_should_skip_the_system_steps_when_sudo_is_denied(self, run, fake_bin, calls, sandbox):
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", "--apply", "--yes", timeout=30)
            assert calls("sudo") == [["-v"]]
            assert result.stdout.count("sudo not granted") == 1

        def test_should_clean_the_dropbox_cache_without_sudo(self, run, fake_bin, calls, sandbox):
            blob = sandbox.home / "Dropbox/.dropbox.cache/blob"
            blob.parent.mkdir(parents=True)
            blob.write_bytes(b"x")
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", "--apply", "--yes", timeout=30)
            assert not blob.exists()
            assert "✔ Dropbox cache cleaned\n" in result.stdout
            assert "Dropbox cache: needs sudo" not in result.stdout
            assert not any(str(blob.parent) in arg for call in calls("sudo") for arg in call)

        def test_should_only_hand_system_logs_to_sudo(self, run, fake_bin, calls, sandbox):
            xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            fake_bin("sudo")
            run("cleanup", "--apply", "--yes", timeout=30)
            elevated = [call for call in calls("sudo") if call[:2] == ["-n", "rm"]]
            paths = [path for call in elevated for path in call[3:]]
            allowed = ("/private/var/log/", "/Library/Logs/")
            assert calls("sudo")[0] == ["-v"]
            assert all(call[:3] == ["-n", "rm", "-rf"] for call in elevated)
            assert [path for path in paths if not path.startswith(allowed)] == []

    @darwin
    class TestOnApplyWithContainersAndTrash:
        def test_should_not_prune_or_empty_the_trash_without_confirmation(self, run, fake_bin, calls, sandbox):
            busy_tools(fake_bin, sandbox)
            result = run("cleanup", "--apply", timeout=30)
            assert result.returncode == 0
            assert calls("docker") == [["info"], ["system", "df"]]
            assert emptied_trash(calls) == []
            assert result.stdout.count("ℹ non-interactive: keeping\n") >= 3
            for kept in ("Trash kept", "Containers kept", "Volumes kept"):
                assert f"▪ {kept}\n" in result.stdout

        def test_should_prune_and_empty_the_trash_with_yes(self, run, fake_bin, calls, sandbox):
            busy_tools(fake_bin, sandbox)
            result = run("cleanup", "--apply", "--yes", timeout=30)
            assert result.returncode == 0
            assert calls("docker") == [["info"], ["system", "df"], ["system", "prune", "-f"], ["volume", "prune", "-f"]]
            assert len(emptied_trash(calls)) == 1
            assert "ℹ auto-yes\n✔ Trash emptied\n" in result.stdout

    @darwin
    class TestOnBadArguments:
        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("cleanup", "--nope")
            assert result.returncode == 2
            assert result.stderr == "cleanup: unknown option: --nope\nSee 'cleanup --help'\n"

        def test_should_reject_a_positional_argument(self, run):
            result = run("cleanup", "x")
            assert result.returncode == 2
            assert result.stderr == "cleanup: unexpected argument: x\nSee 'cleanup --help'\n"

        def test_should_reject_a_missing_sim_unused_value(self, run):
            result = run("cleanup", "--sim-unused")
            assert result.returncode == 2
            assert result.stderr == "cleanup: --sim-unused: missing value\nSee 'cleanup --help'\n"

        def test_should_reject_a_non_numeric_sim_unused(self, run):
            result = run("cleanup", "--sim-unused", "abc")
            assert result.returncode == 2
            assert result.stderr == "cleanup: --sim-unused: expected a number of days, got 'abc'\nSee 'cleanup --help'\n"

    @pytest.mark.skipif(sys.platform == "darwin", reason="the guard fires on other systems")
    class TestOnLinux:
        def test_should_refuse_to_run(self, run):
            result = run("cleanup")
            assert result.returncode == 1
            assert result.stderr == "cleanup: macOS only\n"


def xcode_leftovers(sandbox):
    safe = sandbox.home / "Library/Developer/Xcode/DerivedData/Foo"
    risky = sandbox.home / "Library/Developer/Xcode/Archives/Bar.xcarchive"
    for path in (safe, risky):
        path.mkdir(parents=True)
        (path / "blob").write_bytes(b"x" * 4096)
    return safe, risky


def emptied_trash(calls):
    return [call for call in calls("osascript") if "empty trash" in call[-1]]


def quiet_tools(fake_bin, sandbox):
    fake_bin("osascript", stdout="0")
    fake_bin("sudo", exit_code=1)
    fake_bin("getconf", stdout=str(sandbox.home / "tmp/T"))
    fake_bin("xcrun", script=SIMCTL_EMPTY)
    fake_bin("brew", script='[[ $1 == --cache ]] && exit 1\nexit 0\n')
    for tool in ("composer", "gem", "npm", "yarn", "uv", "docker", "plutil"):
        fake_bin(tool, exit_code=1)


def busy_tools(fake_bin, sandbox):
    """Every tool cleanup drives is installed and has something to clean: a dry run must still not call them."""
    fake_bin("osascript", stdout="3")
    fake_bin("sudo", exit_code=1)
    fake_bin("getconf", stdout=str(sandbox.home / "tmp/T"))
    fake_bin("xcrun", script=SIMCTL_UNAVAILABLE)
    fake_bin("brew", script='[[ $1 == --cache ]] && exit 1\nexit 0\n')
    fake_bin("docker", script='[[ $1 == system && $2 == df ]] && echo "Images 1 1 1GB"\nexit 0\n')
    for tool in ("composer", "gem", "npm", "yarn", "uv", "plutil"):
        fake_bin(tool)


SIMCTL_UNAVAILABLE = "\n".join([
    'case "$*" in',
    '  "simctl list devices -j") printf \'{"devices":{"r":[{"isAvailable":false,"dataPathSize":4096}]}}\' ;;',
    '  "simctl runtime list -j") printf "[]" ;;',
    "esac", "exit 0", ""])

SIMCTL_EMPTY = "\n".join([
    'case "$*" in',
    '  "simctl list devices -j") printf \'{"devices":{}}\' ;;',
    '  "simctl runtime list -j") printf "[]" ;;',
    "esac", "exit 0", ""])
