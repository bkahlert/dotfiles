import subprocess

from repo import SHIMS


class TestOp:
    def test_should_report_a_version(self):
        result = op("--version")
        assert result.stdout == "2.30.0\n"

    class TestRead:
        def test_should_print_a_placeholder_for_the_item_and_field(self):
            result = op("read", "op://Employee/GitLab Token/credential")
            assert result.stdout == "fake:GitLab Token/credential\n"

        def test_should_omit_the_newline_on_request(self):
            result = op("read", "--no-newline", "op://Employee/GitLab Token/credential")
            assert result.stdout == "fake:GitLab Token/credential"

    class TestOnAnythingElse:
        def test_should_exit_1_and_say_so(self):
            result = op("item", "get", "x")
            assert result.returncode == 1
            assert result.stderr == "op: unsupported in tests: item get x\n"


class TestKeepassxcCli:
    def test_should_report_a_version(self):
        result = keepassxc_cli("--version")
        assert result.stdout == "2.7.9\n"

    class TestShow:
        def test_should_print_the_entry_with_a_placeholder_password(self):
            result = keepassxc_cli("show", "/vault.kdbx", "--quiet", "--show-protected", "CONTEXT7_API_KEY",
                                   stdin="dummy-password\n")
            assert result.stdout == ("Title: CONTEXT7_API_KEY\nUserName: fake-user\n"
                                     "Password: fake:CONTEXT7_API_KEY\nURL: \nNotes: \n")

        def test_should_print_a_placeholder_for_a_requested_attribute(self):
            result = keepassxc_cli("show", "--key-file", "/k", "/vault.kdbx", "example.com",
                                   "--attributes", "host-name", "--quiet", "--show-protected")
            assert result.stdout == "fake:example.com/host-name\n"

        def test_should_not_block_without_a_password_on_stdin(self):
            result = keepassxc_cli("show", "/vault.kdbx", "--quiet", "--show-protected", "x")
            assert result.returncode == 0

    class TestOnAnythingElse:
        def test_should_exit_1_and_say_so(self):
            result = keepassxc_cli("db-info", "/vault.kdbx")
            assert result.returncode == 1
            assert result.stderr == "keepassxc-cli: unsupported in tests: db-info /vault.kdbx\n"


def op(*args, stdin=None):
    return shim("op", *args, stdin=stdin)


def keepassxc_cli(*args, stdin=None):
    return shim("keepassxc-cli", *args, stdin=stdin)


def shim(name, *args, stdin):
    options = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
    return subprocess.run([str(SHIMS / name), *args], capture_output=True, text=True, timeout=5, **options)
