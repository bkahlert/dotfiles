import pytest

TEMPLATE = "dot_local/share/private_secrets/private_gitlab_token.tmpl"
TARGET = ".local/share/secrets/gitlab_token"


class TestGitlabToken:
    class TestOnIsta:
        def test_should_hold_the_token_from_1password_and_nothing_else(self, chezmoi):
            assert chezmoi.render(TEMPLATE, company="ista") == "fake:GitLab Token/credential"

        def test_should_be_applied(self, chezmoi):
            assert TARGET not in chezmoi.ignored("ista")

    @pytest.mark.parametrize("company", ("", "bkahlert"), ids=("none", "bkahlert"))
    class TestOnAnyOtherContext:
        def test_should_not_be_applied_because_the_work_vault_is_the_only_place_it_exists(self, chezmoi, company):
            assert TARGET in chezmoi.ignored(company)
