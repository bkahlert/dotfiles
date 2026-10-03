import contextlib
import socket


class TestPickPort:
    def test_should_print_a_port_that_can_be_bound(self, run):
        result = run("pick-port")
        assert result.returncode == 0
        port = int(result.stdout)
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("0.0.0.0", port))

    class TestOnTaken8080:
        def test_should_pick_another_port(self, run):
            with socket.socket() as holder:
                holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                with contextlib.suppress(OSError):
                    holder.bind(("0.0.0.0", 8080))
                    holder.listen()
                result = run("pick-port")
            assert result.returncode == 0
            assert int(result.stdout) != 8080

    class TestOnAnyArgument:
        def test_should_exit_2(self, run):
            result = run("pick-port", "x")
            assert result.returncode == 2
            assert result.stderr == "pick-port: unknown argument: x\nSee 'pick-port --help'\n"
