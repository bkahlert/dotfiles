import plistlib


class TestSetupStartupLaunchagent:
    class TestOnDarwin:
        def test_should_write_a_plist_running_startup_at_login(self, script, fake_bin, sandbox):
            startup = installed_startup(sandbox)
            fake_bin("launchctl")
            result = script("setup-startup-launchagent")
            plist = plistlib.loads(plist_path(sandbox).read_bytes())
            assert result.returncode == 0, result.stderr
            assert plist == {
                "Label": "com.user.startup",
                "ProgramArguments": [str(startup)],
                "RunAtLoad": True,
                "StandardOutPath": f"{sandbox.home}/.startup.log",
                "StandardErrorPath": f"{sandbox.home}/.startup.log",
            }

        def test_should_reload_the_agent(self, script, fake_bin, calls, sandbox):
            installed_startup(sandbox)
            fake_bin("launchctl")
            script("setup-startup-launchagent")
            assert calls("launchctl") == [["unload", str(plist_path(sandbox))], ["load", str(plist_path(sandbox))]]

        def test_should_load_the_agent_even_if_it_was_not_loaded_before(self, script, fake_bin, calls, sandbox):
            installed_startup(sandbox)
            fake_bin("launchctl", script='[[ $1 == unload ]] && exit 113\nexit 0\n')
            result = script("setup-startup-launchagent")
            assert result.returncode == 0
            assert [call[0] for call in calls("launchctl")] == ["unload", "load"]

        def test_should_fail_when_the_agent_does_not_load(self, script, fake_bin, sandbox):
            installed_startup(sandbox)
            fake_bin("launchctl", script='[[ $1 == load ]] && exit 5\nexit 0\n')
            assert script("setup-startup-launchagent").returncode == 5

    class TestOnMissingStartupScript:
        def test_should_skip_with_a_message(self, script, fake_bin, calls, sandbox):
            fake_bin("launchctl")
            result = script("setup-startup-launchagent")
            assert result.returncode == 0
            assert result.stdout == f"Skipping LaunchAgent setup: {sandbox.home}/.startup not found\n"
            assert not plist_path(sandbox).exists()
            assert calls("launchctl") == []

    class TestOnLinux:
        def test_should_do_nothing(self, script, fake_bin, calls, sandbox):
            installed_startup(sandbox)
            fake_bin("launchctl")
            result = script("setup-startup-launchagent", uname="Linux")
            assert result.returncode == 0
            assert not plist_path(sandbox).exists()
            assert calls("launchctl") == []


def installed_startup(sandbox):
    startup = sandbox.home / ".startup"
    startup.write_text("#!/bin/sh\n")
    return startup


def plist_path(sandbox):
    return sandbox.home / "Library/LaunchAgents/com.user.startup.plist"
