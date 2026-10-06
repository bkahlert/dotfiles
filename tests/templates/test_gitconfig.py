import configparser
import shutil
import subprocess

import pytest

TEMPLATE = "dot_gitconfig.tmpl"

# The sandbox guards `git`, so the real one is resolved at import, before any sandbox PATH exists.
GIT = shutil.which("git")


class TestGitconfig:
    def test_should_identify_the_user_from_the_template_data(self, chezmoi):
        config = parse(chezmoi.render(TEMPLATE))
        assert dict(config["user"]) == {"name": "Test User", "email": "test@example.com"}

    def test_should_leave_the_editor_to_visual_and_editor(self, chezmoi, tmp_path):
        config = write_rendered(chezmoi, tmp_path)
        assert git_config(config, "--get", "core.editor").returncode == 1

    class TestGitDefaults:
        def test_should_use_main_as_the_default_branch(self, chezmoi, tmp_path):
            config = write_rendered(chezmoi, tmp_path)
            result = git_config(config, "--get", "init.defaultBranch")
            assert result.stdout.strip() == "main"

        def test_should_not_define_git_aliases(self, chezmoi, tmp_path):
            config = write_rendered(chezmoi, tmp_path)
            assert git_config(config, "--list").stdout.count("alias.") == 0

        def test_should_not_configure_an_external_diff_tool(self, chezmoi, tmp_path):
            config = write_rendered(chezmoi, tmp_path)
            result = git_config(config, "--list")
            assert "diff.tool=" not in result.stdout
            assert "difftool." not in result.stdout

        def test_should_not_configure_external_merge_or_web_tools(self, chezmoi, tmp_path):
            config = write_rendered(chezmoi, tmp_path)
            result = git_config(config, "--list")
            assert "merge.tool=" not in result.stdout
            assert "web.browser=" not in result.stdout

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
