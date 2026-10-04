class TestServe:
    def test_should_serve_on_the_picked_port_with_caching_disabled(self, run, fake_bin, calls):
        fake_bin("pick-port", stdout="4321")
        fake_bin("npx")
        result = run("serve")
        assert result.returncode == 0
        assert calls("npx") == [["http-server", "-c-1", "-p", "4321"]]

    def test_should_announce_the_url_on_stderr(self, run, fake_bin):
        fake_bin("pick-port", stdout="4321")
        fake_bin("npx")
        result = run("serve")
        assert (result.stdout, result.stderr) == ("", "serve: http://localhost:4321\n")

    def test_should_pass_extra_options_to_http_server(self, run, fake_bin, calls):
        fake_bin("pick-port", stdout="4321")
        fake_bin("npx")
        run("serve", "--cors", "-a", "127.0.0.1")
        assert calls("npx") == [["http-server", "-c-1", "-p", "4321", "--cors", "-a", "127.0.0.1"]]

    class TestOnNoFreePort:
        def test_should_exit_1_with_a_message_and_start_no_server(self, run, fake_bin, calls):
            fake_bin("pick-port", exit_code=1)
            fake_bin("npx")
            result = run("serve")
            assert (result.returncode, result.stderr) == (1, "serve: no port available\n")
            assert calls("npx") == []
