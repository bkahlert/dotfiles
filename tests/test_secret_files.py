import shlex

import pytest

from repo import HOME_SOURCE, module_path

# (module, environment variable, file under ~/.local/share/secrets that chezmoi renders)
SECRETS = [
    ("10-context7.zsh", "CONTEXT7_API_KEY", "context7_api_key"),
    ("ista/10-gitlab.zsh", "GITLAB_PRIVATE_TOKEN", "gitlab_token"),
]
RENDERED_SECRETS = HOME_SOURCE / "dot_local" / "share" / "private_secrets"


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


@pytest.fixture(params=SECRETS, ids=[variable for _, variable, _ in SECRETS])
def secret(request, sandbox):
    module, variable, name = request.param
    secrets = sandbox.home / ".local" / "share" / "secrets"
    secrets.mkdir(parents=True)

    def source(zsh):
        """Both views of the variable after the module ran: the shell's own and a child process's."""
        return zsh("\n".join([
            f"source {shlex.quote(str(module_path(module)))}",
            f'print -r -- "${{{variable}-unset}}"',
            f"zsh -fc 'print -r -- \"${{{variable}-unset}}\"'"]))

    source.module = module
    return source, variable, name, secrets / name


class TestSecretFiles:
    class TestOnSecretFile:
        def test_should_export_its_content_to_child_processes(self, zsh, secret):
            source, _, _, file = secret
            file.write_text("s3cret-value")
            result = source(zsh)
            assert (result.stdout, result.stderr) == ("s3cret-value\ns3cret-value\n", "")

        def test_should_drop_the_trailing_newline_but_nothing_else(self, zsh, secret):
            source, _, _, file = secret
            file.write_text('  a "b" $HOME `c` \\d  \n')
            result = source(zsh)
            assert result.stdout == '  a "b" $HOME `c` \\d  \n' * 2

        def test_should_replace_a_value_inherited_from_an_older_shell(self, zsh, secret, sandbox):
            source, variable, _, file = secret
            file.write_text("rotated")
            sandbox.env[variable] = "before-rotation"
            assert source(zsh).stdout == "rotated\nrotated\n"

        def test_should_not_leave_its_helper_variable_behind(self, zsh, secret):
            source, _, _, file = secret
            file.write_text("x")
            result = zsh(f"source {shlex.quote(str(module_path(source.module)))}\nprint -r -- ${{(M)${{(k)parameters}}:#*_file}}")
            assert (result.stdout, result.stderr) == ("\n", "")

    class TestOnNoSecretFile:
        def test_should_export_nothing_and_stay_silent(self, zsh, secret):
            source, *_ = secret
            result = source(zsh)
            assert (result.stdout, result.stderr) == ("unset\nunset\n", "")

        def test_should_leave_an_inherited_value_alone(self, zsh, secret, sandbox):
            source, variable, *_ = secret
            sandbox.env[variable] = "inherited"
            assert source(zsh).stdout == "inherited\ninherited\n"


@pytest.mark.parametrize("name", [name for _, _, name in SECRETS])
def test_should_have_a_chezmoi_template_that_renders_each_secret_file_a_module_reads(name):
    assert (RENDERED_SECRETS / f"private_{name}.tmpl").is_file()
