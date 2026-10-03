class TestFlushdns:
    class TestOnMacOS:
        def test_should_flush_the_cache_and_then_signal_mdnsresponder_through_sudo(self, run, fake_bin, calls):
            fake_bin("uname", stdout="Darwin\n")
            fake_bin("sudo")
            result = run("flushdns")
            assert result.returncode == 0
            assert calls("sudo") == [["dscacheutil", "-flushcache"], ["killall", "-HUP", "mDNSResponder"]]

        def test_should_stop_without_signalling_when_the_flush_fails(self, run, fake_bin, calls):
            fake_bin("uname", stdout="Darwin\n")
            fake_bin("sudo", exit_code=1)
            result = run("flushdns")
            assert result.returncode == 1
            assert calls("sudo") == [["dscacheutil", "-flushcache"]]

    class TestOnLinux:
        def test_should_exit_1_without_calling_sudo(self, run, fake_bin, calls):
            fake_bin("uname", stdout="Linux\n")
            fake_bin("sudo")
            result = run("flushdns")
            assert (result.returncode, result.stderr) == (1, "flushdns: macOS only\n")
            assert calls("sudo") == []

    class TestOnBadArguments:
        def test_should_exit_2_on_an_unknown_argument(self, run, fake_bin, calls):
            fake_bin("sudo")
            result = run("flushdns", "now")
            assert result.returncode == 2
            assert result.stderr == "flushdns: unknown argument: now\nSee 'flushdns --help'\n"
            assert calls("sudo") == []

    class TestOnHelp:
        def test_should_print_the_header_to_stdout(self, run, calls):
            result = run("flushdns", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose: Flush the macOS DNS cache.\nUsage:   flushdns\n")
            assert calls("sudo") == []
