class TestCertPrint:
    def test_should_print_the_leaf_certificate_as_text(self, run, fake_bin, calls):
        fake_bin("openssl", script=OPENSSL)
        result = run("cert-print", "example.test")
        assert (result.returncode, result.stdout) == (0, "TEXT:CERT\n")
        assert sorted(calls("openssl")) == [
            ["s_client", "-showcerts", "-servername", "example.test", "-connect", "example.test:443"],
            ["x509", "-inform", "pem", "-noout", "-text"]]

    def test_should_connect_to_the_given_port(self, run, fake_bin, calls):
        fake_bin("openssl", script=OPENSSL)
        run("cert-print", "example.test", "8443")
        assert ["s_client", "-showcerts", "-servername", "example.test",
                "-connect", "example.test:8443"] in calls("openssl")

    class TestOnBadArguments:
        def test_should_print_the_help_to_stderr_without_arguments(self, run):
            result = run("cert-print")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")

        def test_should_reject_a_third_argument(self, run):
            result = run("cert-print", "a", "1", "x")
            assert result.returncode == 2
            assert result.stderr == "cert-print: too many arguments\nSee 'cert-print --help'\n"

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("cert-print", "--nope")
            assert result.returncode == 2
            assert result.stderr == "cert-print: unknown option: --nope\nSee 'cert-print --help'\n"


OPENSSL = 'case $1 in s_client) printf "CERT\\n" ;; x509) printf "TEXT:"; cat ;; esac\nexit 0\n'
