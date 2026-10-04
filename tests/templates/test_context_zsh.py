import pytest

TEMPLATE = "private_dot_config/zsh/exact_conf.d/00-context.zsh.tmpl"


class TestContextZsh:
    @pytest.mark.parametrize("company", ("bkahlert", "ista"))
    def test_should_stamp_the_context_for_the_rest_of_the_modules(self, chezmoi, company):
        assert chezmoi.render(TEMPLATE, company=company) == f'export DOTFILES_CONTEXT="{company}"\n'

    class TestOnNoContext:
        def test_should_stamp_nothing_so_that_the_variable_stays_unset(self, chezmoi):
            assert chezmoi.render(TEMPLATE, company="") == ""
