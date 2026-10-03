from repo import BIN_SOURCE


class TestTimeout:
    def test_should_forward_everything_to_gtimeout(self, run, fake_bin, calls):
        fake_bin("gtimeout", stdout="ran", exit_code=124)
        result = run("timeout", "-k", "5", "60", "./serve")
        assert (result.stdout, result.returncode) == ("ran", 124)
        assert calls("gtimeout") == [["-k", "5", "60", "./serve"]]

    class TestOnMissingGtimeout:
        def test_should_exit_127_and_name_the_package(self, run):
            result = run("env", "PATH=/usr/bin:/bin", str(BIN_SOURCE / "executable_timeout"), "1", "true")
            assert result.returncode == 127
            assert result.stderr == "timeout: gtimeout not found; install it with: brew install coreutils\n"
