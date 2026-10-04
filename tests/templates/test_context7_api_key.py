TEMPLATE = "dot_local/share/private_secrets/private_context7_api_key.tmpl"
TARGET = ".local/share/secrets/context7_api_key"


class TestContext7ApiKey:
    class TestOnIsta:
        def test_should_hold_the_key_from_1password_and_nothing_else(self, chezmoi):
            assert chezmoi.render(TEMPLATE, company="ista") == "fake:CONTEXT7_API_KEY/credential"

    class TestOnAPersonalContext:
        def test_should_hold_the_key_from_the_keepassxc_vault_and_nothing_else(self, chezmoi):
            assert chezmoi.render(TEMPLATE, company="bkahlert") == "fake:CONTEXT7_API_KEY"

    class TestOnNoContext:
        def test_should_not_be_applied_because_there_is_no_vault_to_read_it_from(self, chezmoi):
            assert TARGET in chezmoi.ignored("")

    def test_should_be_applied_wherever_a_vault_exists(self, chezmoi):
        assert [TARGET in chezmoi.ignored(company) for company in ("bkahlert", "ista")] == [False, False]
