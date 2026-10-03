import sys

import pytest


class TestPrintPort:
    class TestOnNoArguments:
        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS lists listeners through lsof")
        def test_should_list_every_listener_through_lsof(self, run, fake_bin, calls):
            fake_bin("lsof", stdout="COMMAND PID\nnode 1\n")
            result = run("print-port")
            assert (result.returncode, result.stdout) == (0, "COMMAND PID\nnode 1\n")
            assert calls("lsof") == [["-nP", "-iTCP", "-sTCP:LISTEN"]]

        @pytest.mark.skipif(sys.platform == "darwin", reason="Linux lists listeners through ss")
        def test_should_list_every_listener_through_ss(self, run, fake_bin, calls):
            fake_bin("ss", stdout="Netid State\n")
            result = run("print-port")
            assert (result.returncode, result.stdout) == (0, "Netid State\n")
            assert calls("ss") == [["-tulnp"]]

    class TestOnPorts:
        def test_should_query_lsof_for_all_of_them(self, run, fake_bin, calls):
            fake_bin("lsof", stdout="COMMAND PID\nnode 1\n")
            result = run("print-port", "3000", "8080")
            assert (result.returncode, result.stdout) == (0, "COMMAND PID\nnode 1\n")
            assert calls("lsof") == [["-nP", "-iTCP:3000", "-iTCP:8080"]]

        def test_should_exit_1_when_nothing_is_bound(self, run, fake_bin):
            fake_bin("lsof", exit_code=1)
            result = run("print-port", "3000")
            assert result.returncode == 1
            assert result.stderr == "print-port: nothing bound to port 3000\n"

        def test_should_reject_a_port_that_is_not_a_number(self, run, fake_bin):
            fake_bin("lsof")
            result = run("print-port", "abc")
            assert result.returncode == 2
            assert result.stderr == "print-port: not a port number: abc\nSee 'print-port --help'\n"

    class TestOnUnknownOption:
        def test_should_exit_2_and_name_the_option(self, run):
            result = run("print-port", "--nope")
            assert result.returncode == 2
            assert result.stderr == "print-port: unknown option: --nope\nSee 'print-port --help'\n"
