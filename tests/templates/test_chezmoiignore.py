import pytest

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
        def test_should_leave_installer_owned_binaries_alone_so_exact_bin_does_not_remove_them(self, chezmoi):
            assert set(INSTALLER_OWNED) <= set(patterns(chezmoi))

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
        def test_should_never_deploy_work_only_targets(self, chezmoi, os):
            assert set(WORK_TARGETS) <= set(patterns(chezmoi, os=os))

    class TestMacosLibrary:
        def test_should_be_dropped_on_linux_where_there_is_no_library_directory(self, chezmoi):
            assert MACOS_LIBRARY in chezmoi.ignored(os="linux")

        def test_should_be_applied_on_macos(self, chezmoi):
            assert MACOS_LIBRARY not in chezmoi.ignored(os="darwin")
