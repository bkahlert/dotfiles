import configparser
import shutil
import subprocess

import pytest

TEMPLATE = "dot_gitconfig.tmpl"

# The sandbox guards `git`, so the real one is resolved at import, before any sandbox PATH exists.
GIT = shutil.which("git")


class TestGitconfig:
    @pytest.mark.parametrize("company", ("", "bkahlert", "ista"), ids=("none", "bkahlert", "ista"))
    def test_should_identify_the_user_from_the_template_data(self, chezmoi, company):
        config = parse(chezmoi.render(TEMPLATE, company=company))
        assert dict(config["user"]) == {"name": "Test User", "email": "test@example.com"}

    def test_should_leave_the_editor_to_visual_and_editor(self, chezmoi, tmp_path):
        config = write_rendered(chezmoi, tmp_path)
        assert git_config(config, "--get", "core.editor").returncode == 1

    class TestOnSettingsGitWouldIgnore:
        """Git skips an alias named like a built-in command and reads a key only in the section that owns it."""

        def test_should_define_no_alias_shadowing_a_builtin_command(self, chezmoi, tmp_path):
            config = write_rendered(chezmoi, tmp_path)
            assert git_config(config, "--get", "alias.push").returncode == 1

        def test_should_trust_the_exit_code_of_the_diff_tool(self, chezmoi, tmp_path):
            config = write_rendered(chezmoi, tmp_path)
            result = git_config(config, "--type=bool", "--get", "difftool.trustExitCode")
            assert result.stdout.strip() == "true"

        def test_should_not_set_trust_exit_code_for_pull(self, chezmoi, tmp_path):
            config = write_rendered(chezmoi, tmp_path)
            assert git_config(config, "--get", "pull.trustExitCode").returncode == 1

    class TestOnMacOS:
        def test_should_use_the_keychain_as_credential_helper(self, chezmoi):
            assert parse(chezmoi.render(TEMPLATE, os="darwin"))["credential"]["helper"] == "osxkeychain"

    class TestOnLinux:
        def test_should_configure_no_credential_helper(self, chezmoi):
            assert "credential" not in parse(chezmoi.render(TEMPLATE, os="linux"))


def write_rendered(chezmoi, tmp_path):
    path = tmp_path / "gitconfig"
    path.write_text(chezmoi.render(TEMPLATE))
    return path


def git_config(path, *args):
    """`git config -f` reads the file alone: no system or global config leaks in."""
    return subprocess.run([GIT, "config", "-f", str(path), *args], capture_output=True, text=True, check=False)


def parse(text):
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    parser.read_string(text)
    return parser
