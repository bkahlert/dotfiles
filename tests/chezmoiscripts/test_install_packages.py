import re
import shlex

import pytest

from repo import brewfile_lines

ENTRY = re.compile(r'(brew|cask) "[a-z0-9@._+-]+" +# \S.*')
LINUX_INSTALLERS = {
    "sheldon": "https://rossmacarthur.github.io/install/crate.sh",
    "starship": "https://starship.rs/install.sh",
    "zoxide": "https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh",
}


class TestInstallPackages:
    class TestOnDarwin:
        def test_should_hand_the_brewfile_to_brew_bundle_on_stdin(self, script, fake_bin, calls, sandbox):
            fake_bin("brew", script='cat > "$(dirname "$0")/brewfile"\n')
            result = script("install-packages")
            assert result.returncode == 0, result.stderr
            assert calls("brew") == [["bundle", "--file=/dev/stdin"]]
            assert (sandbox.fakes / "brewfile").read_text().splitlines() == brewfile_lines()

        def test_should_fail_when_brew_bundle_fails(self, script, fake_bin):
            fake_bin("brew", exit_code=1)
            assert script("install-packages").returncode == 1

        class TestOnBrewOffPath:
            @pytest.mark.parametrize("prefix", ["/opt/homebrew", "/usr/local"])
            def test_should_load_brew_from_the_standard_prefix(self, script, sandbox, homebrew_at, calls, prefix):
                sandbox.only_tools()
                root = homebrew_at(prefix)
                result = script("install-packages", prefix_root=root)
                assert result.returncode == 0, result.stderr
                assert calls("brew") == [["bundle", "--file=/dev/stdin"]]

    class TestBrewfile:
        @pytest.mark.parametrize("line", brewfile_lines(), ids=lambda line: line.split("#")[0].strip())
        def test_should_be_one_entry_with_a_comment_saying_why(self, line):
            assert ENTRY.fullmatch(line), f"not a `brew|cask \"name\"  # why` line: {line!r}"

        def test_should_list_every_package_once(self):
            names = [line.split('"')[1] for line in brewfile_lines()]
            assert sorted(names) == sorted(set(names))

    class TestOnLinux:
        def test_should_run_each_installer_for_a_missing_tool(self, script, linux, calls):
            result = script("install-packages", uname="Linux")
            assert result.returncode == 0, result.stderr
            assert [urls(call) for call in calls("curl")] == [[url] for url in LINUX_INSTALLERS.values()]

        @pytest.mark.parametrize("installed", LINUX_INSTALLERS)
        def test_should_skip_an_installed_tool(self, script, linux, fake_bin, calls, installed):
            fake_bin(installed)
            result = script("install-packages", uname="Linux")
            assert result.returncode == 0, result.stderr
            assert [urls(call) for call in calls("curl")] == [
                [url] for tool, url in LINUX_INSTALLERS.items() if tool != installed]

        def test_should_not_call_brew(self, script, linux, fake_bin, calls):
            fake_bin("brew")
            script("install-packages", uname="Linux")
            assert calls("brew") == []

        def test_should_download_over_tls_and_fail_on_http_errors(self, script, linux, calls):
            script("install-packages", uname="Linux")
            for call in calls("curl"):
                assert call[:4] == ["--proto", "=https", "--tlsv1.2", "-fsSL"], call

        def test_should_hand_starship_and_sheldon_their_options(self, script, linux, sandbox):
            script("install-packages", uname="Linux")
            ran = (sandbox.home / "ran").read_text().splitlines()
            assert ran == [
                f"{LINUX_INSTALLERS['sheldon']} --repo rossmacarthur/sheldon --to {sandbox.home}/.local/bin",
                f"{LINUX_INSTALLERS['starship']} --yes",
                f"{LINUX_INSTALLERS['zoxide']} ",
            ]

        class TestOnFailedDownload:
            @pytest.mark.parametrize("failing", LINUX_INSTALLERS)
            def test_should_fail_without_running_the_partial_script(self, script, linux, sandbox, failing):
                fake_curl(sandbox, fail_for=LINUX_INSTALLERS[failing])
                result = script("install-packages", uname="Linux")
                assert result.returncode == 22
                assert not (sandbox.home / "partial").exists()

        def test_should_fail_when_an_installer_fails(self, script, linux, sandbox):
            fake_curl(sandbox, body="exit 3")
            assert script("install-packages", uname="Linux").returncode == 3

        def test_should_remove_the_downloaded_installers(self, script, linux, sandbox):
            script("install-packages", uname="Linux")
            assert list((sandbox.home / "tmp").iterdir()) == []


@pytest.fixture
def linux(sandbox):
    sandbox.only_tools("sh", "mktemp", "rm")
    fake_curl(sandbox)


def fake_curl(sandbox, body=None, fail_for=None):
    """Writes the installer to the ``--output`` file. ``body`` defaults to one that records its URL and arguments in ``~/ran``; a download of ``fail_for`` leaves a partial script and exits 22."""
    installer = (f"printf '%s\\n' {shlex.quote(body)} > \"$out\"" if body
                 else "printf 'echo \"%s $*\" >> \"$HOME/ran\"\\n' \"$url\" > \"$out\"")
    sandbox.fake_bin("curl", script=f"""\
out=/dev/stdout
while (( $# )); do
  case $1 in -o|--output) out=$2; shift 2 ;; *) url=$1; shift ;; esac
done
if [[ $url == {shlex.quote(fail_for or "")} ]]; then
  echo 'echo > "$HOME/partial"' > "$out"
  exit 22
fi
{installer}
""")


def urls(call):
    return [arg for arg in call if arg.startswith("https://")]
