class TestCertGet:
    def test_should_print_the_leaf_certificate_as_pem(self, run, fake_bin, calls):
        fake_bin("openssl", script=OPENSSL)
        result = run("cert-get", "example.test")
        assert (result.returncode, result.stdout) == (0, "PEM:CERT\n")
        assert sorted(calls("openssl")) == [
            ["s_client", "-showcerts", "-servername", "example.test", "-connect", "example.test:443"],
            ["x509", "-outform", "PEM"]]

    def test_should_connect_to_the_given_port(self, run, fake_bin, calls):
        fake_bin("openssl", script=OPENSSL)
        run("cert-get", "mail.example.test", "993")
        assert ["s_client", "-showcerts", "-servername", "mail.example.test",
                "-connect", "mail.example.test:993"] in calls("openssl")

    class TestOnDownload:
        def test_should_write_domain_pem_and_print_its_name(self, run, fake_bin, sandbox):
            fake_bin("openssl", script=OPENSSL)
            result = run("cert-get", "--download", "example.test")
            assert (result.returncode, result.stdout) == (0, "example.test.pem\n")
            assert (sandbox.home / "example.test.pem").read_text() == "PEM:CERT\n"

    class TestOnBadArguments:
        def test_should_print_the_help_to_stderr_without_arguments(self, run):
            result = run("cert-get")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")

        def test_should_reject_a_third_argument(self, run):
            result = run("cert-get", "a", "1", "x")
            assert result.returncode == 2
            assert result.stderr == "cert-get: too many arguments\nSee 'cert-get --help'\n"

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("cert-get", "--nope")
            assert result.returncode == 2
            assert result.stderr == "cert-get: unknown option: --nope\nSee 'cert-get --help'\n"


OPENSSL = 'case $1 in s_client) printf "CERT\\n" ;; x509) printf "PEM:"; cat ;; esac\nexit 0\n'
