import contextlib
import os
import signal
import subprocess
import time

import pytest


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

        def test_should_leave_nothing_behind_on_failure(self, run, fake_bin, sandbox):
            fake_bin("openssl", script=OPENSSL_FAILING)
            result = run("cert-get", "--download", "example.test")
            assert (result.returncode, result.stdout) == (1, "")
            assert list(sandbox.home.glob("example.test*")) == []

        def test_should_keep_an_existing_file_on_failure(self, run, fake_bin, sandbox):
            existing = sandbox.home / "example.test.pem"
            existing.write_text("OLD\n")
            fake_bin("openssl", script=OPENSSL_FAILING)
            result = run("cert-get", "--download", "example.test")
            assert result.returncode == 1
            assert [existing.read_text(), sorted(path.name for path in sandbox.home.glob("example.test*"))] == [
                "OLD\n", ["example.test.pem"]]

        def test_should_leave_no_temporary_file_on_success(self, run, fake_bin, sandbox):
            fake_bin("openssl", script=OPENSSL)
            run("cert-get", "--download", "example.test")
            assert sorted(path.name for path in sandbox.home.glob("example.test*")) == ["example.test.pem"]

        def test_should_leave_nothing_behind_on_failure_for_a_domain_that_looks_like_an_option(self, run, fake_bin, sandbox):
            fake_bin("openssl", script=OPENSSL_FAILING)
            result = run("cert-get", "--download", "--", "-example.test")
            assert (result.returncode, result.stderr, list(sandbox.home.glob("*example.test*"))) == (1, "", [])

        def test_should_leave_nothing_behind_on_ctrl_c(self, fake_bin, sandbox):
            fake_bin("openssl", script=OPENSSL_HANGING)
            # Its own session, so the SIGINT goes to cert-get and its children the way Ctrl-C does, not to pytest.
            with subprocess.Popen(["cert-get", "--download", "example.test"], env=sandbox.env, cwd=sandbox.home,
                                  stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  start_new_session=True) as cert_get:
                try:
                    deadline = time.monotonic() + 5
                    while not list(sandbox.home.glob("example.test.pem.*")) and time.monotonic() < deadline:
                        time.sleep(0.05)
                    os.killpg(cert_get.pid, signal.SIGINT)
                    cert_get.wait(timeout=5)
                finally:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(cert_get.pid, signal.SIGKILL)
            assert list(sandbox.home.glob("example.test*")) == []

    class TestOnBadArguments:
        @pytest.mark.parametrize("flags", [(), ("--download",)], ids=["print", "download"])
        def test_should_reject_a_domain_with_a_slash(self, run, fake_bin, calls, sandbox, flags):
            fake_bin("openssl", script=OPENSSL)
            result = run("cert-get", *flags, "../evil")
            assert result.returncode == 2
            assert result.stderr == "cert-get: domain must not contain '/': ../evil\nSee 'cert-get --help'\n"
            assert calls("openssl") == []
            assert not (sandbox.home.parent / "evil.pem").exists()

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
# Blocks mid-download, as a slow handshake does.
OPENSSL_HANGING = 'case $1 in s_client) printf "CERT\\n"; exec sleep 30 ;; x509) cat; exec sleep 30 ;; esac\n'
OPENSSL_FAILING = 'case $1 in s_client) exit 1 ;; x509) printf "PEM:"; cat; exit 1 ;; esac\n'
