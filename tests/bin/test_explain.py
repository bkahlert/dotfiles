import shutil

from repo import BIN_SOURCE

EXPLAIN = str(BIN_SOURCE / "executable_explain")
URL = "https://explainshell.com/explain?cmd="


class TestExplain:
    class TestOnCommand:
        def test_should_open_the_command_joined_with_plus_signs(self, run, fake_bin, calls):
            fake_bin("open")
            result = run("explain", "tar", "-xzvf", "foo.tgz")
            assert result.returncode == 0
            assert calls("open") == [[URL + "tar+-xzvf+foo.tgz"]]

        def test_should_keep_the_options_of_the_command_unescaped(self, run, fake_bin, calls):
            fake_bin("open")
            run("explain", "ls", "-la", "--color")
            assert calls("open") == [[URL + "ls+-la+--color"]]

        def test_should_percent_encode_characters_with_meaning_in_a_url(self, run, fake_bin, calls):
            fake_bin("open")
            run("explain", "find", ".", "-name", "*.log", "-mtime", "+7", "-delete")
            assert calls("open") == [[URL + "find+.+-name+%2A.log+-mtime+%2B7+-delete"]]

        def test_should_not_let_ampersands_hashes_and_percents_end_the_query(self, run, fake_bin, calls):
            fake_bin("open")
            run("explain", "echo", "a&b", "#c", "50%")
            assert calls("open") == [[URL + "echo+a%26b+%23c+50%25"]]

        def test_should_encode_quotes_and_non_ascii_bytes(self, run, fake_bin, calls):
            fake_bin("open")
            run("explain", "echo", "it's", "grüße")
            assert calls("open") == [[URL + "echo+it%27s+gr%C3%BC%C3%9Fe"]]

        def test_should_take_a_dashed_command_after_a_double_dash(self, run, fake_bin, calls):
            fake_bin("open")
            run("explain", "--", "-weird", "arg")
            assert calls("open") == [[URL + "-weird+arg"]]

    class TestOnOpener:
        def test_should_prefer_open_over_xdg_open(self, run, fake_bin, calls, sandbox):
            fake_bin("open")
            fake_bin("xdg-open")
            path = path_with(sandbox, "open", "xdg-open")
            result = run("env", f"PATH={path}", EXPLAIN, "ls")
            assert result.returncode == 0
            assert (calls("open"), calls("xdg-open")) == ([[URL + "ls"]], [])

        def test_should_fall_back_to_xdg_open(self, run, fake_bin, calls, sandbox):
            fake_bin("xdg-open")
            path = path_with(sandbox, "xdg-open")
            result = run("env", f"PATH={path}", EXPLAIN, "ls")
            assert result.returncode == 0
            assert calls("xdg-open") == [[URL + "ls"]]

        def test_should_exit_1_and_name_the_openers_without_any(self, run, sandbox):
            path = path_with(sandbox)
            result = run("env", f"PATH={path}", EXPLAIN, "ls")
            assert result.returncode == 1
            assert result.stderr == "executable_explain: no browser opener found (open, xdg-open)\n"

    class TestOnBadArguments:
        def test_should_print_the_header_to_stderr_and_exit_2_without_a_command(self, run, fake_bin, calls):
            fake_bin("open")
            result = run("explain")
            assert result.returncode == 2
            assert result.stdout == ""
            assert result.stderr.startswith("Purpose: Open explainshell.com for a command line.\n")
            assert calls("open") == []

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("explain", "--nope")
            assert result.returncode == 2
            assert result.stderr == "explain: unknown option: --nope\nSee 'explain --help'\n"

    class TestOnHelp:
        def test_should_print_the_header_to_stdout(self, run):
            result = run("explain", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: Open explainshell.com for a command line.\n")


def path_with(sandbox, *fakes):
    only = sandbox.home / "only-bin"
    only.mkdir()
    (only / "bash").symlink_to(shutil.which("bash"))
    for name in fakes:
        (only / name).symlink_to(sandbox.fakes / name)
    return only
