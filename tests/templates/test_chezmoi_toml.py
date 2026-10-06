import tomllib

import pytest

from repo import HOME_SOURCE

TEMPLATE = ".chezmoi.toml.tmpl"


class TestChezmoiToml:
    @pytest.mark.parametrize("company", ("", "bkahlert", "ista"), ids=("none", "bkahlert", "ista"))
    def test_should_record_the_answers_as_template_data(self, chezmoi, company):
        data = tomllib.loads(chezmoi.config(company).read_text())["data"]
        assert data == {"email": "test@example.com", "name": "Test User", "company": company}

    class TestScriptEnvironment:
        @pytest.mark.parametrize("company", ("", "bkahlert", "ista"), ids=("none", "bkahlert", "ista"))
        def test_should_not_export_profile_data_to_scripts(self, chezmoi, company):
            config = tomllib.loads(chezmoi.config(company).read_text())
            assert "scriptEnv" not in config

    class TestOnAnySourceLocation:
        @pytest.fixture(params=("in the default location", "in a clone elsewhere"))
        def source(self, request, tmp_path):
            """A source directory as `chezmoi init --source` takes it, and where the source state is read from."""
            if request.param == "in the default location":
                return HOME_SOURCE, HOME_SOURCE
            clone = tmp_path / "clone" / "dotfiles"
            (clone / "home").mkdir(parents=True)
            (clone / ".chezmoiroot").write_text("home\n")
            return clone, clone / "home"

        def test_should_keep_reading_the_source_state_where_init_found_it(self, chezmoi, source):
            init_source, source_state = source
            config = tomllib.loads(chezmoi.config("", source=init_source).read_text())
            assert config["sourceDir"] == str(source_state.resolve())

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
