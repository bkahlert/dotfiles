import pytest

from repo import HOME_SOURCE

TEMPLATE = "private_dot_npmrc.tmpl"
TARGET = ".npmrc"


class TestNpmrc:
    def test_should_be_a_private_source_file_because_it_holds_registry_tokens(self):
        assert (HOME_SOURCE / TEMPLATE).is_file()
        assert not (HOME_SOURCE / "dot_npmrc.tmpl").exists()

    class TestOnIsta:
        def test_should_authenticate_both_registries_with_tokens_read_from_1password(self, chezmoi):
            assert chezmoi.render(TEMPLATE, company="ista").splitlines() == [
                "@express-service:registry=https://gitlab.com/api/v4/packages/npm/",
                "//gitlab.com/api/v4/packages/npm/:_authToken=fake:GitLab NPM Token/credential",
                "//ista.jfrog.io/artifactory/api/npm/npm/:_authToken=fake:jFrog NPM Token/credential",
            ]

        def test_should_be_applied(self, chezmoi):
            assert TARGET not in chezmoi.ignored("ista")

    @pytest.mark.parametrize("company", ("", "bkahlert"), ids=("none", "bkahlert"))
    class TestOnAnyOtherContext:
        def test_should_not_be_applied_because_the_registry_tokens_only_exist_in_the_work_vault(self, chezmoi, company):
            assert TARGET in chezmoi.ignored(company)
