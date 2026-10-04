import tomllib

import pytest

TEMPLATE = ".chezmoi.toml.tmpl"


class TestChezmoiToml:
    @pytest.mark.parametrize("company", ("", "bkahlert", "ista"), ids=("none", "bkahlert", "ista"))
    def test_should_record_the_answers_as_template_data(self, chezmoi, company):
        data = tomllib.loads(chezmoi.config(company).read_text())["data"]
        assert data == {"email": "test@example.com", "name": "Test User", "company": company}

    class TestOnIsta:
        def test_should_read_secrets_from_1password_without_signing_in_before_each_read(self, chezmoi):
            config = tomllib.loads(chezmoi.config("ista").read_text())
            assert config["onepassword"] == {"prompt": False}
            assert "keepassxc" not in config

    class TestOnAPersonalContext:
        def test_should_read_secrets_from_the_icloud_vault(self, chezmoi, sandbox):
            config = tomllib.loads(chezmoi.config("bkahlert").read_text())
            assert config["keepassxc"] == {"database": f"{sandbox.home}/Library/Mobile Documents/com~apple~CloudDocs/Vault/choam.kdbx"}
            assert "onepassword" not in config

    class TestOnNoContext:
        def test_should_configure_no_password_manager(self, chezmoi):
            config = tomllib.loads(chezmoi.config("").read_text())
            assert not {"onepassword", "keepassxc"} & set(config)
