import shutil

import pytest

from repo import HOME_SOURCE

SOURCE = ".chezmoiignore"
INSTALLER_OWNED = [".local/bin/browser-harness", ".local/bin/browser-harness-mcp",
                   ".local/bin/fnm"]
MACOS_LIBRARY = "Library"
WORK_TARGETS = [
    ".local/bin/gcloud-login",
    ".config/zsh/conf.d/ista/",
    ".local/share/secrets/gitlab_token",
    ".npmrc",
]
NEVER_COMMITTED = [".aws/credentials", ".aws/sso/", ".aws/cli/cache/"]


def patterns(chezmoi, *, os="darwin"):
    """The ignore patterns the template renders to, without comments and blank lines."""
    lines = (line.strip() for line in chezmoi.render(SOURCE, os=os).splitlines())
    return [line for line in lines if line and not line.startswith("#")]


class TestChezmoiignore:
    class TestShared:
        def test_should_not_ignore_installer_owned_binaries(self, chezmoi):
            assert not set(INSTALLER_OWNED) & set(patterns(chezmoi))

        def test_should_ignore_python_bytecode_caches(self, chezmoi, tmp_path):
            source = tmp_path / "source"
            source.mkdir()
            shutil.copy(HOME_SOURCE / SOURCE, source / SOURCE)
            bytecode = source / "dot_local/share/__pycache__/agent_statusline.cpython-314.pyc"
            bytecode.parent.mkdir(parents=True)
            bytecode.touch()

            result = chezmoi.run(
                "ignored", source=source, config=chezmoi.config(source=source), stdin=None)

            assert result.returncode == 0, result.stderr
            assert ".local/share/__pycache__" in result.stdout.split()

        def test_should_never_apply_aws_credentials_or_the_sso_cache(self, chezmoi):
            assert set(NEVER_COMMITTED) <= set(patterns(chezmoi))

    class TestTimeoutWrapper:
        def test_should_be_dropped_on_linux_where_the_system_timeout_is_the_real_one(self, chezmoi):
            assert ".local/bin/timeout" in patterns(chezmoi, os="linux")

        def test_should_be_applied_on_macos_which_ships_none(self, chezmoi):
            assert ".local/bin/timeout" not in patterns(chezmoi, os="darwin")

    class TestClaudeInstaller:
        @pytest.mark.parametrize("os", ["darwin", "linux"])
        def test_should_not_preserve_the_retired_native_installer_binary(self, chezmoi, os):
            assert ".local/bin/claude" not in patterns(chezmoi, os=os)

    class TestWorkOnlyTargets:
        @pytest.mark.parametrize("os", ["darwin", "linux"])
        def test_should_not_preserve_work_only_targets_on_personal_checkout(self, chezmoi, os):
            assert not set(WORK_TARGETS) & set(patterns(chezmoi, os=os))

    class TestMacosLibrary:
        def test_should_be_dropped_on_linux_where_there_is_no_library_directory(self, chezmoi):
            assert MACOS_LIBRARY in chezmoi.ignored(os="linux")

        def test_should_be_applied_on_macos(self, chezmoi):
            assert MACOS_LIBRARY not in chezmoi.ignored(os="darwin")
