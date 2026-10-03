import signal
import subprocess


class TestKillport:
    def test_should_terminate_the_listener_and_report_the_freed_port(self, run, fake_bin, calls):
        with subprocess.Popen(["sleep", "100"]) as listener:
            try:
                fake_bin("sleep")
                fake_bin("lsof", script=listing_once(listener.pid))
                result = run("killport", "8080")
                assert listener.wait(timeout=5) == -signal.SIGTERM
            finally:
                listener.kill()
        assert result.returncode == 0
        assert result.stdout == f"ℹ Killing 1 process(es) on port 8080: {listener.pid}\n✔ Port 8080 freed.\n"
        assert calls("lsof") == [["-t", "-iTCP:8080", "-sTCP:LISTEN"]] * 2

    class TestOnAListenerThatIgnoresSigterm:
        def test_should_escalate_to_sigkill(self, run, fake_bin):
            with subprocess.Popen(["sleep", "100"], preexec_fn=ignore_sigterm) as listener:
                try:
                    fake_bin("sleep")
                    fake_bin("lsof", stdout=f"{listener.pid}\n")
                    result = run("killport", "8080")
                    assert listener.wait(timeout=5) == -signal.SIGKILL
                finally:
                    listener.kill()
            assert result.returncode == 0
            assert result.stdout == (f"ℹ Killing 1 process(es) on port 8080: {listener.pid}\n"
                                     f"! Forcing SIGKILL on: {listener.pid}\n✔ Port 8080 freed.\n")

    class TestOnNoListener:
        def test_should_exit_1(self, run, fake_bin):
            fake_bin("lsof")
            result = run("killport", "8080")
            assert result.returncode == 1
            assert result.stderr == "✘ No process listening on port 8080.\n"

    class TestOnBadArguments:
        def test_should_reject_a_port_that_is_not_a_number(self, run):
            result = run("killport", "abc")
            assert result.returncode == 2
            assert result.stderr == "killport: not a port number: abc\nSee 'killport --help'\n"

        def test_should_reject_more_than_one_port(self, run):
            result = run("killport", "1", "2")
            assert result.returncode == 2
            assert result.stderr == "killport: expected exactly one <port>\nSee 'killport --help'\n"

        def test_should_print_the_help_to_stderr_without_arguments(self, run):
            result = run("killport")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("killport", "--nope")
            assert result.returncode == 2
            assert result.stderr == "killport: unknown option: --nope\nSee 'killport --help'\n"


def listing_once(pid):
    return ('count=$(cat "$HOME/lsof.count" 2>/dev/null || echo 0)\n'
            'echo $((count + 1)) > "$HOME/lsof.count"\n'
            f'(( count == 0 )) && echo {pid}\n'
            'exit 0\n')


def ignore_sigterm():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
