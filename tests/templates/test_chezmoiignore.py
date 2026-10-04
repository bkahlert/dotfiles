import pytest

SOURCE = ".chezmoiignore"
GCLOUD_SKILLS = [".agents/skills/gcloud-auth", ".agents/skills/gcloud-login-automation",
                 ".claude/skills/gcloud-auth", ".claude/skills/gcloud-login-automation"]
INSTALLER_OWNED = [".local/bin/claude", ".local/bin/browser-harness", ".local/bin/browser-harness-mcp", ".local/bin/fnm"]
MACOS_LIBRARY = "Library"
ISTA_MODULES = ".config/zsh/conf.d/ista"
NEVER_COMMITTED = [".aws/credentials", ".aws/sso/", ".aws/cli/cache/"]


def patterns(chezmoi, *, company="", os="darwin"):
    """The ignore patterns the template renders to, without comments and blank lines."""
    lines = (line.strip() for line in chezmoi.render(SOURCE, company=company, os=os).splitlines())
    return [line for line in lines if line and not line.startswith("#")]


CONTEXTS = pytest.mark.parametrize("company", ("", "bkahlert", "ista"), ids=("none", "bkahlert", "ista"))


class TestChezmoiignore:
    @CONTEXTS
    class TestInEveryContext:
        def test_should_leave_installer_owned_binaries_alone_so_exact_bin_does_not_remove_them(self, chezmoi, company):
            assert set(INSTALLER_OWNED) <= set(patterns(chezmoi, company=company))

        def test_should_never_apply_aws_credentials_or_the_sso_cache(self, chezmoi, company):
            assert set(NEVER_COMMITTED) <= set(patterns(chezmoi, company=company))

    class TestTimeoutWrapper:
        def test_should_be_dropped_on_linux_where_the_system_timeout_is_the_real_one(self, chezmoi):
            assert ".local/bin/timeout" in patterns(chezmoi, os="linux")

        def test_should_be_applied_on_macos_which_ships_none(self, chezmoi):
            assert ".local/bin/timeout" not in patterns(chezmoi, os="darwin")

    class TestGcloudSkills:
        def test_should_be_applied_on_ista(self, chezmoi):
            assert not set(GCLOUD_SKILLS) & set(patterns(chezmoi, company="ista"))

        @pytest.mark.parametrize("company", ("", "bkahlert"), ids=("none", "bkahlert"))
        def test_should_be_dropped_elsewhere_because_they_describe_the_ista_accounts_only(self, chezmoi, company):
            assert set(GCLOUD_SKILLS) <= set(patterns(chezmoi, company=company))

    class TestMacosLibrary:
        def test_should_be_dropped_on_linux_where_there_is_no_library_directory(self, chezmoi):
            assert MACOS_LIBRARY in chezmoi.ignored("bkahlert", os="linux")

        def test_should_be_applied_on_macos(self, chezmoi):
            assert MACOS_LIBRARY not in chezmoi.ignored("bkahlert", os="darwin")

    class TestIstaModules:
        def test_should_be_applied_on_ista_where_the_loader_sources_them(self, chezmoi):
            assert ISTA_MODULES not in chezmoi.ignored("ista")

        @pytest.mark.parametrize("company", ("", "bkahlert"), ids=("none", "bkahlert"))
        def test_should_be_dropped_elsewhere_because_nothing_sources_them(self, chezmoi, company):
            assert ISTA_MODULES in chezmoi.ignored(company)
