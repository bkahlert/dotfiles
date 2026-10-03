import re

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

    class TestBrewfile:
        @pytest.mark.parametrize("line", brewfile_lines(), ids=lambda line: line.split("#")[0].strip())
        def test_should_be_one_entry_with_a_comment_saying_why(self, line):
            assert ENTRY.fullmatch(line), f"not a `brew|cask \"name\"  # why` line: {line!r}"

        def test_should_list_every_package_once(self):
            names = [line.split('"')[1] for line in brewfile_lines()]
            assert sorted(names) == sorted(set(names))

    class TestOnLinux:
        def test_should_run_each_installer_for_a_missing_tool(self, script, sandbox, fake_bin, calls):
            sandbox.only_tools("sh")
            fake_bin("curl", stdout="exit 0\n")
            result = script("install-packages", uname="Linux")
            assert result.returncode == 0, result.stderr
            assert [urls(call) for call in calls("curl")] == [[url] for url in LINUX_INSTALLERS.values()]

        @pytest.mark.parametrize("installed", LINUX_INSTALLERS)
        def test_should_skip_an_installed_tool(self, script, sandbox, fake_bin, calls, installed):
            sandbox.only_tools("sh")
            fake_bin("curl", stdout="exit 0\n")
            fake_bin(installed)
            result = script("install-packages", uname="Linux")
            assert result.returncode == 0, result.stderr
            assert [urls(call) for call in calls("curl")] == [
                [url] for tool, url in LINUX_INSTALLERS.items() if tool != installed]

        def test_should_not_call_brew(self, script, sandbox, fake_bin, calls):
            sandbox.only_tools("sh")
            fake_bin("curl", stdout="exit 0\n")
            fake_bin("brew")
            script("install-packages", uname="Linux")
            assert calls("brew") == []


def urls(call):
    return [arg for arg in call if arg.startswith("https://")]
