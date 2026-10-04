import re


class TestServeLive:
    def test_should_serve_on_the_picked_port_without_opening_a_browser(self, run, fake_bin, calls):
        fake_bin("pick-port", stdout="4321")
        fake_bin("npx")
        result = run("serve-live")
        assert result.returncode == 0
        assert unpinned(calls("npx")) == [["live-server", "--port=4321", "--no-browser"]]

    def test_should_announce_the_url_on_stderr(self, run, fake_bin):
        fake_bin("pick-port", stdout="4321")
        fake_bin("npx")
        result = run("serve-live")
        assert (result.stdout, result.stderr) == ("", "serve-live: http://localhost:4321\n")

    def test_should_pass_extra_options_to_live_server(self, run, fake_bin, calls):
        fake_bin("pick-port", stdout="4321")
        fake_bin("npx")
        run("serve-live", "--wait=200", "--open=/docs")
        assert unpinned(calls("npx")) == [["live-server", "--port=4321", "--no-browser", "--wait=200", "--open=/docs"]]

    class TestPinning:
        def test_should_run_an_exact_version(self, run, fake_bin, calls):
            fake_bin("pick-port", stdout="4321")
            fake_bin("npx")
            run("serve-live")
            assert re.fullmatch(r"live-server@\d+\.\d+\.\d+", calls("npx")[0][0])

    class TestOnNoFreePort:
        def test_should_exit_1_with_a_message_and_start_no_server(self, run, fake_bin, calls):
            fake_bin("pick-port", exit_code=1)
            fake_bin("npx")
            result = run("serve-live")
            assert (result.returncode, result.stderr) == (1, "serve-live: no port available\n")
            assert calls("npx") == []


def unpinned(npx_calls):
    return [[call[0].rsplit("@", 1)[0], *call[1:]] for call in npx_calls]
