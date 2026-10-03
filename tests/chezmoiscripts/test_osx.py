import pytest

RESTARTED = ["cfprefsd", "Dock", "Finder", "Mail", "SystemUIServer", "Terminal"]


class TestOsx:
    class TestOnDarwin:
        def test_should_apply_defaults_without_restarting_on_no_restart(self, script, system_tools, calls, sandbox):
            result = script("osx", "--no-restart")
            verbs = {next(arg for arg in call if arg in ("write", "import")) for call in calls("defaults")}
            assert result.returncode == 0, result.stderr
            assert result.stdout == "Please log out and log back in to make all settings take effect.\n"
            assert len(calls("defaults")) > 50
            assert verbs == {"write", "import"}
            assert calls("osascript")[0] == ["-e", 'tell application "System Preferences" to quit']
            assert calls("chflags") == [["nohidden", str(sandbox.home / "Library")]]
            assert calls("killall") == []

        def test_should_restart_the_affected_apps(self, script, system_tools, calls):
            script("osx")
            assert [call[0] for call in calls("killall")] == RESTARTED

        def test_should_stop_at_the_first_failing_default(self, script, system_tools, fake_bin, calls):
            fake_bin("defaults", exit_code=1)
            result = script("osx", "--no-restart")
            assert result.returncode == 1
            assert len(calls("defaults")) == 1

    class TestOnLinux:
        def test_should_do_nothing(self, script, system_tools, calls):
            result = script("osx", uname="Linux")
            assert result.returncode == 0
            assert calls("defaults") == []
            assert calls("osascript") == []


@pytest.fixture
def system_tools(fake_bin, sandbox):
    for name in ("osascript", "chflags", "killall"):
        fake_bin(name)
    fake_bin("defaults", script='[[ $1 == import ]] && cat > /dev/null\nexit 0\n')
    fake_bin("plutil", stdout="<plist/>")
    fake_bin("mktemp", script='f="$TMPDIR/man-shortcuts-off.json"\n: > "$f"\nprintf "%s" "$f"\n')
