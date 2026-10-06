TEMPLATE = "dot_local/share/private_secrets/private_context7_api_key.tmpl"
TARGET = ".local/share/secrets/context7_api_key"


class TestContext7ApiKey:
    def test_should_hold_the_key_from_the_keepassxc_vault_and_nothing_else(self, chezmoi):
        assert chezmoi.render(TEMPLATE) == "fake:CONTEXT7_API_KEY"

    def test_should_be_applied_without_extra_data(self, chezmoi):
        assert TARGET not in chezmoi.ignored()
