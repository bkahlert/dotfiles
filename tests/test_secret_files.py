import shlex

import pytest

from repo import HOME_SOURCE, module_path

MODULE = "10-context7.zsh"
VARIABLE = "CONTEXT7_API_KEY"
NAME = "context7_api_key"
RENDERED_SECRETS = HOME_SOURCE / "dot_local" / "share" / "private_secrets"


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


@pytest.fixture
def secret(sandbox):
    secrets = sandbox.home / ".local" / "share" / "secrets"
    secrets.mkdir(parents=True)

    def source(zsh):
        """Both views of the variable after the module ran: the shell's own and a child process's."""
        return zsh("\n".join([
            f"source {shlex.quote(str(module_path(MODULE)))}",
            f'print -r -- "${{{VARIABLE}-unset}}"',
            f"zsh -fc 'print -r -- \"${{{VARIABLE}-unset}}\"'"]))

    return source, secrets / NAME


class TestSecretFiles:
    class TestOnSecretFile:
        def test_should_export_its_content_to_child_processes(self, zsh, secret):
            source, file = secret
            file.write_text("s3cret-value")
            result = source(zsh)
            assert (result.stdout, result.stderr) == ("s3cret-value\ns3cret-value\n", "")

        def test_should_drop_the_trailing_newline_but_nothing_else(self, zsh, secret):
            source, file = secret
            file.write_text('  a "b" $HOME `c` \\d  \n')
            result = source(zsh)
            assert result.stdout == '  a "b" $HOME `c` \\d  \n' * 2

        def test_should_replace_a_value_inherited_from_an_older_shell(self, zsh, secret, sandbox):
            source, file = secret
            file.write_text("rotated")
            sandbox.env[VARIABLE] = "before-rotation"
            assert source(zsh).stdout == "rotated\nrotated\n"

        def test_should_not_leave_its_helper_variable_behind(self, zsh, secret):
            source, file = secret
            file.write_text("x")
            result = zsh(f"source {shlex.quote(str(module_path(MODULE)))}\nprint -r -- ${{(M)${{(k)parameters}}:#*_file}}")
            assert (result.stdout, result.stderr) == ("\n", "")

    class TestOnNoSecretFile:
        def test_should_export_nothing_and_stay_silent(self, zsh, secret):
            source, _ = secret
            result = source(zsh)
            assert (result.stdout, result.stderr) == ("unset\nunset\n", "")

        def test_should_leave_an_inherited_value_alone(self, zsh, secret, sandbox):
            source, _ = secret
            sandbox.env[VARIABLE] = "inherited"
            assert source(zsh).stdout == "inherited\ninherited\n"


def test_should_have_a_chezmoi_template_that_renders_the_secret_file_the_module_reads():
    assert (RENDERED_SECRETS / f"private_{NAME}.tmpl").is_file()
