class TestGhLatest:
    def test_should_print_the_latest_tag(self, run, fake_bin, calls):
        fake_bin("curl", stdout='{"tag_name":"v2.101.0"}')
        result = run("gh-latest", "cli/cli")
        assert result.returncode == 0
        assert result.stdout == "v2.101.0\n"
        assert calls("curl") == [["-LfsS", "https://api.github.com/repos/cli/cli/releases/latest"]]

    class TestOnUnknownOption:
        def test_should_exit_2_and_name_the_option(self, run):
            result = run("gh-latest", "--nope")
            assert result.returncode == 2
            assert result.stderr == "gh-latest: unknown option: --nope\nSee 'gh-latest --help'\n"

    class TestOnMissingArgument:
        def test_should_print_the_help_to_stderr_and_exit_2(self, run):
            result = run("gh-latest")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")
            assert result.stdout == ""

    class TestOnMalformedRepository:
        def test_should_exit_2_and_say_what_was_expected(self, run):
            result = run("gh-latest", "nodash")
            assert result.returncode == 2
            assert "not an <owner>/<repo>: nodash" in result.stderr
