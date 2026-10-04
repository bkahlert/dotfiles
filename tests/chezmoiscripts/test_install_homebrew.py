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

        class TestOnBrewNowhere:
            @pytest.fixture(autouse=True)
            def bare(self, sandbox):
                sandbox.only_tools("mktemp", "rm", "cat")
                (sandbox.fakes / "brew").unlink()

            def test_should_run_the_installer_downloaded_over_tls(self, script, sandbox, calls, tmp_path):
                fake_curl(sandbox)
                result = script("install-homebrew", prefix_root=tmp_path)
                assert result.returncode == 0, result.stderr
                [call] = calls("curl")
                assert INSTALLER_URL in call and "=https" in call and "-fsSL" in call
                assert (sandbox.home / "installer-calls").read_text() == "ran\n"

            def test_should_leave_no_installer_behind(self, script, sandbox, tmp_path):
                fake_curl(sandbox)
                script("install-homebrew", prefix_root=tmp_path)
                assert list((sandbox.home / "tmp").iterdir()) == []

            class TestOnFailedDownload:
                def test_should_fail_without_running_the_partial_installer(self, script, sandbox, tmp_path):
                    fake_curl(sandbox, exit_code=22)
                    result = script("install-homebrew", prefix_root=tmp_path)
                    assert result.returncode == 22
                    assert not (sandbox.home / "installer-calls").exists()

    class TestOnLinux:
        def test_should_do_nothing(self, script, fake_bin, calls):
            fake_bin("curl")
            result = script("install-homebrew", uname="Linux")
            assert result.returncode == 0, result.stderr
            assert calls("curl") == []


INSTALLER_URL = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"


def fake_curl(sandbox, *, exit_code=0):
    sandbox.fake_bin("curl", script=f"""\
while (( $# )); do
  case $1 in -o|--output) out=$2; shift 2 ;; *) shift ;; esac
done
cat > "$out" <<'INSTALLER'
{'echo ran >> "$HOME/installer-calls"' if exit_code == 0 else 'echo partial >> "$HOME/installer-calls"'}
INSTALLER
exit {exit_code}
""")
