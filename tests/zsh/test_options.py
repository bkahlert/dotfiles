import pytest

MODULES = ["01-options.zsh"]


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


def env_of_child(zsh, name):
    """What a process started from the shell sees of the variable."""
    return zsh(f"zsh -fc 'print -r -- \"${{{name}-unset}}\"'", modules=MODULES)


class TestOptions:
    class TestOnWordSplitting:
        def test_should_pass_an_array_element_with_spaces_as_one_argument(self, zsh):
            result = zsh('count() { print -r -- $#; }\nfiles=("My File.txt" "b.txt")\ncount $files', modules=MODULES)
            assert (result.stdout, result.stderr) == ("2\n", "")

        def test_should_not_split_a_string_variable(self, zsh):
            result = zsh('count() { print -r -- $#; }\nopts="-a -b"\ncount $opts', modules=MODULES)
            assert result.stdout == "1\n"

    class TestOnGlobs:
        def test_should_pass_a_pattern_that_matches_nothing_through_unchanged(self, zsh):
            result = zsh("print -r -- no-such-file-*.xyz", modules=MODULES)
            assert (result.stdout, result.stderr) == ("no-such-file-*.xyz\n", "")

    class TestOnLocale:
        def test_should_export_an_english_utf8_lang(self, zsh, sandbox):
            del sandbox.env["LANG"]
            assert env_of_child(zsh, "LANG").stdout == "en_US.UTF-8\n"

        def test_should_drop_the_lc_ctype_a_terminal_injected(self, zsh, sandbox):
            sandbox.env["LC_CTYPE"] = "UTF-8"
            assert env_of_child(zsh, "LC_CTYPE").stdout == "unset\n"

    def test_should_export_clicolor(self, zsh):
        assert env_of_child(zsh, "CLICOLOR").stdout == "1\n"

    def test_should_load_the_color_arrays(self, zsh):
        result = zsh('[[ -n ${fg[red]} && -n ${color[bold]} ]] && print loaded', modules=MODULES)
        assert (result.stdout, result.stderr) == ("loaded\n", "")
