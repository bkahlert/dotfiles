import configparser

import pytest

TEMPLATE = "dot_gitconfig.tmpl"


class TestGitconfig:
    @pytest.mark.parametrize("company", ("", "bkahlert", "ista"), ids=("none", "bkahlert", "ista"))
    def test_should_identify_the_user_from_the_template_data(self, chezmoi, company):
        config = parse(chezmoi.render(TEMPLATE, company=company))
        assert dict(config["user"]) == {"name": "Test User", "email": "test@example.com"}

    class TestOnMacOS:
        def test_should_use_the_keychain_as_credential_helper(self, chezmoi):
            assert parse(chezmoi.render(TEMPLATE, os="darwin"))["credential"]["helper"] == "osxkeychain"

    class TestOnLinux:
        def test_should_configure_no_credential_helper(self, chezmoi):
            assert "credential" not in parse(chezmoi.render(TEMPLATE, os="linux"))


def parse(text):
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    parser.read_string(text)
    return parser
