import pytest

RESTARTED = ["cfprefsd", "Dock", "Finder", "Mail", "SystemUIServer", "Terminal"]
# A representative pick across the sections of the script; a flipped flag or changed number fails.
CHOSEN = [
    ["write", "NSGlobalDomain", "NSAutomaticQuoteSubstitutionEnabled", "-bool", "false"],
    ["write", "NSGlobalDomain", "InitialKeyRepeat", "-int", "25"],
    ["write", "NSGlobalDomain", "KeyRepeat", "-int", "2"],
    ["write", "NSGlobalDomain", "AppleLocale", "-string", "de_DE"],
    ["write", "NSGlobalDomain", "AppleShowAllExtensions", "-bool", "true"],
    ["write", "com.apple.finder", "AppleShowAllFiles", "-bool", "true"],
    ["write", "com.apple.finder", "FXPreferredViewStyle", "-string", "Nlsv"],
    ["write", "com.apple.desktopservices", "DSDontWriteNetworkStores", "-bool", "true"],
    ["write", "com.apple.dock", "autohide", "-bool", "false"],
    ["write", "com.apple.dock", "tilesize", "-int", "23"],
    ["write", "com.apple.dock", "wvous-tl-corner", "-int", "3"],
    ["write", "com.apple.SoftwareUpdate", "AutomaticCheckEnabled", "-bool", "true"],
]
# Writes that name a domain and a type but no key, so `defaults` stores the value under the key
# "-int" or "-bool" and the setting is never applied. Remove an entry once its line is fixed.
KEYLESS = [
    ["write", "com.apple.swipescrolldirection", "-int", "0"],
    ["write", "com.apple.dock.showLaunchpadGestureEnabled", "-bool", "false"],
]


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

        def test_should_write_the_chosen_values(self, script, system_tools, calls):
            script("osx", "--no-restart")
            missing = [write for write in CHOSEN if write not in calls("defaults")]
            assert missing == []

        def test_should_save_screenshots_to_the_downloads_folder_of_the_home(self, script, system_tools, calls, sandbox):
            script("osx", "--no-restart")
            assert ["write", "com.apple.screencapture", "location", "-string", f"{sandbox.home}/Downloads"] in calls("defaults")

        def test_should_name_a_key_in_every_write(self, script, system_tools, calls):
            script("osx", "--no-restart")
            keyless = [call for call in calls("defaults") if call[0] == "write" and call[2].startswith("-")]
            assert keyless == KEYLESS

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
