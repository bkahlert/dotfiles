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

        def test_should_only_ever_hand_system_paths_to_sudo(self, run, fake_bin, calls, sandbox):
            quiet_tools(fake_bin, sandbox)
            run("cleanup", "--apply", timeout=30)
            assert calls("sudo")[0] == ["-v"]
            assert all(call[:3] == ["-n", "rm", "-rf"] for call in calls("sudo")[1:])

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


def quiet_tools(fake_bin, sandbox):
    fake_bin("osascript", stdout="0")
    fake_bin("sudo", exit_code=1)
    fake_bin("getconf", stdout=str(sandbox.home / "tmp/T"))
    fake_bin("xcrun", script=SIMCTL_EMPTY)
    fake_bin("brew", script='[[ $1 == --cache ]] && exit 1\nexit 0\n')
    for tool in ("composer", "gem", "npm", "yarn", "uv", "docker", "plutil"):
        fake_bin(tool, exit_code=1)


SIMCTL_EMPTY = "\n".join([
    'case "$*" in',
    '  "simctl list devices -j") printf \'{"devices":{}}\' ;;',
    '  "simctl runtime list -j") printf "[]" ;;',
    "esac", "exit 0", ""])
