import pytest


class TestInstallHomebrew:
    class TestOnDarwin:
        def test_should_not_install_when_brew_is_on_path(self, script, fake_bin, calls):
            fake_bin("brew")
            fake_bin("curl")
            result = script("install-homebrew")
            assert result.returncode == 0, result.stderr
            assert calls("curl") == []

        @pytest.mark.parametrize("prefix", ["/opt/homebrew", "/usr/local"])
        def test_should_not_reinstall_a_brew_off_path_in_the_standard_prefix(self, script, sandbox, fake_bin, homebrew_at, calls, prefix):
            sandbox.only_tools()
            fake_bin("curl")
            root = homebrew_at(prefix)
            result = script("install-homebrew", prefix_root=root)
            assert result.returncode == 0, result.stderr
            assert calls("curl") == []

        def test_should_install_when_brew_is_nowhere(self, script, sandbox, fake_bin, calls, tmp_path):
            sandbox.only_tools()
            (sandbox.fakes / "brew").unlink()
            fake_bin("curl", stdout="exit 0\n")
            result = script("install-homebrew", prefix_root=tmp_path)
            assert result.returncode == 0, result.stderr
            assert [call[-1] for call in calls("curl")] == ["https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"]

    class TestOnLinux:
        def test_should_do_nothing(self, script, fake_bin, calls):
            fake_bin("curl")
            result = script("install-homebrew", uname="Linux")
            assert result.returncode == 0, result.stderr
            assert calls("curl") == []
