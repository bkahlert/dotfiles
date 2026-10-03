import os
import subprocess

import pytest


class TestOpAgent:
    class TestOnRead:
        def test_should_start_the_daemon_and_print_the_secret_byte_exact(self, run, fake_bin, calls, daemon):
            fake_bin("op", script=OP_SECRET)
            result = run("op-agent", "read", "op://Employee/item/password", timeout=30)
            assert result.returncode == 0
            assert result.stdout == " s3cr=t\n two\n"
            assert calls("op") == [["read", "--no-newline", "op://Employee/item/password"]]
            assert run("op-agent", "status").stdout.startswith("op-agent: running (pid ")

        def test_should_reuse_the_running_daemon(self, run, fake_bin, calls, daemon):
            fake_bin("op", script=OP_SECRET)
            run("op-agent", "read", "op://Employee/item/password", timeout=30)
            status = run("op-agent", "status").stdout
            run("op-agent", "read", "op://Employee/other/password", timeout=30)
            assert run("op-agent", "status").stdout == status
            assert [call[-1] for call in calls("op")] == ["op://Employee/item/password", "op://Employee/other/password"]

        def test_should_relay_an_op_error_and_exit_1(self, run, fake_bin, daemon):
            fake_bin("op", script='printf "[ERROR] no such item\\n" >&2\nexit 1\n')
            result = run("op-agent", "read", "op://Employee/missing/password", timeout=30)
            assert result.returncode == 1
            assert result.stderr == "op-agent: [ERROR] no such item\n"

        class TestOnAPidFileOfAForeignProcess:
            def test_should_give_up_after_the_write_timeout_and_drop_the_pid_file(self, run, sandbox):
                state = sandbox.home / "Library/Application Support/op-agent"
                state.mkdir(parents=True)
                os.mkfifo(state / "req", 0o600)
                with subprocess.Popen(["sleep", "60"]) as foreign:
                    (state / "pid").write_text(str(foreign.pid))
                    result = run("op-agent", "read", "op://Employee/item/password", timeout=30)
                    foreign.kill()
                assert result.returncode == 2
                assert result.stderr == "op-agent: daemon did not accept the request (stale pid file removed — retry)\n"
                assert not (state / "pid").exists()

    class TestOnStop:
        def test_should_end_the_daemon(self, run, fake_bin, daemon):
            fake_bin("op", script=OP_SECRET)
            run("op-agent", "read", "op://Employee/item/password", timeout=30)
            result = run("op-agent", "stop")
            assert result.returncode == 0
            status = run("op-agent", "status")
            assert (status.returncode, status.stdout) == (1, "op-agent: not running\n")

    class TestOnStatus:
        def test_should_exit_1_while_nothing_runs(self, run):
            result = run("op-agent", "status")
            assert (result.returncode, result.stdout) == (1, "op-agent: not running\n")

    class TestOnUnknownCommand:
        def test_should_exit_2(self, run):
            result = run("op-agent", "bogus")
            assert result.returncode == 2
            assert result.stderr == "op-agent: unknown command: bogus (see 'op-agent --help')\n"


OP_SECRET = '[[ $1 == read ]] && printf " s3cr=t\\n two\\n"\nexit 0\n'


@pytest.fixture
def daemon(run):
    yield
    run("op-agent", "stop")
