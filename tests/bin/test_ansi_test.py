import pytest

SECTIONS = [
    "1. SGR attributes x 16 colors",
    "2. 256-color palette",
    "3. 24-bit truecolor gradient",
    "4. Underline styles & colors",
    "5. OSC 8 hyperlinks",
    "6. Box-drawing & Unicode",
    "7. Nerd Font glyph ranges",
    "8. Reported terminal info",
]


class TestAnsiTest:
    @pytest.mark.parametrize("term", ["dumb", None])
    def test_should_print_every_section_and_stay_quiet_on_stderr(self, run, sandbox, term):
        if term is None:
            del sandbox.env["TERM"]
        else:
            sandbox.env["TERM"] = term
        result = run("ansi-test")
        assert (result.returncode, result.stderr) == (0, "")
        assert [s for s in SECTIONS if s not in result.stdout] == []

    def test_should_report_the_terminal_it_runs_in(self, run, sandbox):
        sandbox.env["TERM"] = "dumb"
        sandbox.env["COLORTERM"] = "truecolor"
        result = run("ansi-test")
        assert "  TERM         = dumb\n" in result.stdout
        assert "  COLORTERM    = truecolor\n" in result.stdout

    def test_should_print_usage_on_help(self, run):
        result = run("ansi-test", "--help")
        assert (result.returncode, result.stdout) == (0, (
            "Purpose: Visual terminal capability reference card (SGR, color, underline\n"
            "         styles, OSC 8, Unicode, Nerd Fonts).\n"
            "Usage:   ansi-test\n"))

    class TestOnUnknownArgument:
        def test_should_exit_2_with_a_hint(self, run):
            result = run("ansi-test", "--nope")
            assert (result.returncode, result.stderr) == (
                2, "ansi-test: unknown argument: --nope\nSee 'ansi-test --help'\n")
