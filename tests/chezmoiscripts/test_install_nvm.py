import re

import pytest

from repo import chezmoiscripts

SOURCE = dict(chezmoiscripts())["install-nvm"].read_text()
INSTALLER_URL = re.compile(r"https://raw\.githubusercontent\.com/nvm-sh/nvm/v\d+\.\d+\.\d+/install\.sh")
# What nvm's installer leaves behind: an nvm.sh whose nvm records its arguments and which, like the real one, does
# not survive set -u. The installer itself records the PROFILE it was given.
INSTALLER = """\
echo "PROFILE=${PROFILE-unset}" >> "$HOME/installer-calls"
mkdir -p "$NVM_DIR"
cat > "$NVM_DIR/nvm.sh" <<'NVM'
: "$NVM_SH_NEEDS_UNSET_VARIABLES"
nvm() { echo "$*" >> "$HOME/nvm-calls"; [[ $1 != version ]] || echo v24.21.0; }
NVM
"""


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("mkdir", "mktemp", "rm", "cat")


def fake_curl(sandbox, *, exit_code=0):
    """Writes INSTALLER to the ``--output`` file; a failing download leaves a partial file behind."""
    sandbox.fake_bin("curl", script=f"""\
while (( $# )); do
  case $1 in -o|--output) out=$2; shift 2 ;; *) shift ;; esac
done
cat > "$out" <<'INSTALLER'
{INSTALLER if exit_code == 0 else 'echo partial >> "$HOME/installer-calls"'}
INSTALLER
exit {exit_code}
""")


def lines(path):
    return path.read_text().splitlines() if path.exists() else []


class TestInstallNvm:
    class TestOnFreshMachine:
        def test_should_download_the_pinned_installer_over_tls(self, script, sandbox, calls):
            fake_curl(sandbox)
            result = script("install-nvm")
            assert result.returncode == 0, result.stderr
            [call] = calls("curl")
            assert "=https" in call and any(INSTALLER_URL.fullmatch(arg) for arg in call)

        def test_should_keep_the_installer_out_of_the_shell_profiles(self, script, sandbox):
            fake_curl(sandbox)
            script("install-nvm")
            assert lines(sandbox.home / "installer-calls") == ["PROFILE=/dev/null"]

        def test_should_install_the_latest_lts_node_and_make_its_major_the_default(self, script, sandbox):
            """A default of lts/* resolves through an alias nvm rewrites to the newest remote release, which may not be
            installed; the major stays resolvable to the newest installed one."""
            fake_curl(sandbox)
            script("install-nvm")
            assert lines(sandbox.home / "nvm-calls") == ["install --no-progress --lts", "version lts/*", "alias default 24"]

        def test_should_install_into_home_nvm(self, script, sandbox):
            fake_curl(sandbox)
            script("install-nvm")
            assert (sandbox.home / ".nvm" / "nvm.sh").is_file()

        def test_should_leave_no_installer_behind(self, script, sandbox):
            fake_curl(sandbox)
            script("install-nvm")
            assert list((sandbox.home / "tmp").iterdir()) == []

    class TestOnInstalledNvm:
        @pytest.fixture(autouse=True)
        def installed(self, sandbox):
            nvm_dir = sandbox.home / ".nvm"
            nvm_dir.mkdir()
            (nvm_dir / "nvm.sh").write_text(INSTALLER.split("<<'NVM'\n")[1].split("NVM\n")[0])
            return nvm_dir

        def test_should_not_download_the_installer_again(self, script, sandbox, calls):
            fake_curl(sandbox)
            result = script("install-nvm")
            assert (result.returncode, calls("curl")) == (0, [])

        def test_should_install_the_chosen_default_and_keep_it(self, script, sandbox, installed):
            (installed / "alias").mkdir()
            (installed / "alias" / "default").write_text("22\n")
            script("install-nvm")
            assert lines(sandbox.home / "nvm-calls") == ["install --no-progress 22"]

        def test_should_leave_a_system_default_alone(self, script, sandbox, installed):
            (installed / "alias").mkdir()
            (installed / "alias" / "default").write_text("system\n")
            result = script("install-nvm")
            assert (result.returncode, lines(sandbox.home / "nvm-calls")) == (0, [])

    class TestOnFailedDownload:
        def test_should_fail_without_running_the_partial_installer(self, script, sandbox):
            fake_curl(sandbox, exit_code=22)
            result = script("install-nvm")
            assert result.returncode != 0
            assert lines(sandbox.home / "installer-calls") == []
            assert lines(sandbox.home / "nvm-calls") == []

    class TestPinning:
        def test_should_name_one_nvm_release(self):
            assert re.search(r"^nvm_version=v\d+\.\d+\.\d+$", SOURCE, re.MULTILINE)
