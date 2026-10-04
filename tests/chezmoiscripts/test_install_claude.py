import pytest

INSTALLER_URL = "https://claude.ai/install.sh"
# What Anthropic's installer does, as far as this script cares: put claude into ~/.local/bin.
INSTALLER = 'mkdir -p "$HOME/.local/bin"\nprintf "#!/bin/sh\\n" > "$HOME/.local/bin/claude"\nchmod +x "$HOME/.local/bin/claude"\necho ran >> "$HOME/installer-calls"\n'


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("mkdir", "mktemp", "rm", "cat", "chmod")


def fake_curl(sandbox, *, exit_code=0):
    sandbox.fake_bin("curl", script=f"""\
while (( $# )); do
  case $1 in -o|--output) out=$2; shift 2 ;; *) shift ;; esac
done
cat > "$out" <<'INSTALLER'
{INSTALLER if exit_code == 0 else 'echo partial >> "$HOME/installer-calls"'}
INSTALLER
exit {exit_code}
""")


class TestInstallClaude:
    class TestOnFreshMachine:
        def test_should_run_anthropic_s_installer_downloaded_over_tls(self, script, sandbox, calls):
            fake_curl(sandbox)
            result = script("install-claude")
            assert result.returncode == 0, result.stderr
            [call] = calls("curl")
            assert INSTALLER_URL in call and "=https" in call
            assert (sandbox.home / "installer-calls").read_text() == "ran\n"
            assert (sandbox.home / ".local" / "bin" / "claude").is_file()

        def test_should_leave_no_installer_behind(self, script, sandbox):
            fake_curl(sandbox)
            script("install-claude")
            assert list((sandbox.home / "tmp").iterdir()) == []

    class TestOnInstalledClaude:
        def test_should_leave_it_to_update_itself(self, script, sandbox, calls):
            fake_curl(sandbox)
            local_bin = sandbox.home / ".local" / "bin"
            local_bin.mkdir(parents=True)
            (local_bin / "claude").write_text("#!/bin/sh\n")
            (local_bin / "claude").chmod(0o755)
            result = script("install-claude")
            assert (result.returncode, calls("curl")) == (0, [])

    class TestOnFailedDownload:
        def test_should_fail_without_running_the_partial_installer(self, script, sandbox):
            fake_curl(sandbox, exit_code=22)
            result = script("install-claude")
            assert result.returncode != 0
            assert (sandbox.home / "installer-calls").exists() is False
