import pytest

TEMPLATE = "dot_npmrc.tmpl"


class TestNpmrc:
    class TestOnIsta:
        def test_should_authenticate_both_registries_with_tokens_read_from_1password(self, chezmoi):
            assert chezmoi.render(TEMPLATE, company="ista").splitlines() == [
                "@express-service:registry=https://gitlab.com/api/v4/packages/npm/",
                "//gitlab.com/api/v4/packages/npm/:_authToken=fake:GitLab NPM Token/credential",
                "//ista.jfrog.io/artifactory/api/npm/npm/:_authToken=fake:jFrog NPM Token/credential",
            ]

    @pytest.mark.parametrize("company", ("", "bkahlert"), ids=("none", "bkahlert"))
    class TestOnAnyOtherContext:
        def test_should_render_nothing_and_ask_no_vault(self, chezmoi, company):
            assert chezmoi.render(TEMPLATE, company=company).strip() == ""
