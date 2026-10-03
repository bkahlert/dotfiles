class TestGcloudLoginBrowser:
    class TestOnUrl:
        def test_should_record_the_url_without_a_newline(self, run, sandbox):
            sandbox.env["GCLOUD_LOGIN_URL_FILE"] = str(sandbox.home / "url")
            result = run("gcloud-login-browser", "https://accounts.google.com/o/oauth2/auth?a=1&b=2")
            assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
            assert (sandbox.home / "url").read_bytes() == b"https://accounts.google.com/o/oauth2/auth?a=1&b=2"

        def test_should_replace_the_url_of_an_earlier_call(self, run, sandbox):
            sandbox.env["GCLOUD_LOGIN_URL_FILE"] = str(sandbox.home / "url")
            run("gcloud-login-browser", "https://first.example/a-much-longer-url")
            run("gcloud-login-browser", "https://second.example")
            assert (sandbox.home / "url").read_text() == "https://second.example"

    class TestOnBadInput:
        def test_should_print_the_header_to_stderr_and_exit_2_without_a_url(self, run, sandbox):
            sandbox.env["GCLOUD_LOGIN_URL_FILE"] = str(sandbox.home / "url")
            result = run("gcloud-login-browser")
            assert result.returncode == 2
            assert result.stdout == ""
            assert result.stderr.startswith("Purpose: Browser hook for gcloud-login.")
            assert not (sandbox.home / "url").exists()

        def test_should_exit_2_with_a_one_line_hint_without_the_url_file_variable(self, run, sandbox):
            result = run("gcloud-login-browser", "https://example.com")
            assert result.returncode == 2
            assert result.stderr == "gcloud-login-browser: GCLOUD_LOGIN_URL_FILE not set\nSee 'gcloud-login-browser --help'\n"

        def test_should_exit_2_on_an_unknown_option(self, run, sandbox):
            sandbox.env["GCLOUD_LOGIN_URL_FILE"] = str(sandbox.home / "url")
            result = run("gcloud-login-browser", "--nope")
            assert result.returncode == 2
            assert result.stderr == "gcloud-login-browser: unknown option: --nope\nSee 'gcloud-login-browser --help'\n"

        def test_should_exit_2_on_more_than_one_url(self, run, sandbox):
            sandbox.env["GCLOUD_LOGIN_URL_FILE"] = str(sandbox.home / "url")
            result = run("gcloud-login-browser", "https://a.example", "https://b.example")
            assert result.returncode == 2
            assert result.stderr == "gcloud-login-browser: too many arguments\nSee 'gcloud-login-browser --help'\n"
            assert not (sandbox.home / "url").exists()

    class TestOnHelp:
        def test_should_print_the_header_to_stdout(self, run):
            result = run("gcloud-login-browser", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: Browser hook for gcloud-login.")
