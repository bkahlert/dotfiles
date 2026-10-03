class TestKnownHostsFix:
    class TestOnHost:
        def test_should_hand_ssh_keygen_the_known_hosts_under_home(self, run, fake_bin, calls, sandbox):
            fake_bin("ssh-keygen")
            result = run("known-hosts-fix", "a.test")
            assert result.returncode == 0
            assert calls("ssh-keygen") == [["-R", "a.test", "-f", str(sandbox.home / ".ssh/known_hosts")]]

        def test_should_remove_every_entry_of_the_host(self, run, fake_bin, sandbox):
            known_hosts = write_known_hosts(sandbox)
            fake_bin("ssh-keygen", script=REAL_SSH_KEYGEN)
            result = run("known-hosts-fix", "b.test")
            assert result.returncode == 0
            assert known_hosts.read_text() == PLAIN_A + HASHED

    class TestOnLineNumber:
        def test_should_resolve_the_line_to_its_host(self, run, fake_bin, calls, sandbox):
            write_known_hosts(sandbox)
            fake_bin("ssh-keygen")
            result = run("known-hosts-fix", "2")
            assert result.returncode == 0
            assert result.stderr == "Line 2 → host b.test\n"
            assert calls("ssh-keygen") == [["-R", "b.test", "-f", str(sandbox.home / ".ssh/known_hosts")]]

        def test_should_delete_a_hashed_line_directly(self, run, fake_bin, calls, sandbox):
            known_hosts = write_known_hosts(sandbox)
            fake_bin("ssh-keygen")
            result = run("known-hosts-fix", "3")
            assert result.returncode == 0
            assert result.stderr == ("Hashed entry; deleting line 3 directly "
                                     "(twin entries, if any, will need separate handling).\n")
            assert known_hosts.read_text() == PLAIN_A + PLAIN_B
            assert calls("ssh-keygen") == []

        def test_should_reject_a_line_out_of_range(self, run, sandbox):
            write_known_hosts(sandbox)
            result = run("known-hosts-fix", "9")
            assert result.returncode == 1
            assert result.stderr == "known-hosts-fix: line 9 is out of range (1..3)\n"

        def test_should_fail_without_a_known_hosts_file(self, run, sandbox):
            result = run("known-hosts-fix", "1")
            assert result.returncode == 1
            assert result.stderr == f"known-hosts-fix: {sandbox.home}/.ssh/known_hosts does not exist\n"

    class TestOnBadArguments:
        def test_should_print_the_help_to_stderr_without_arguments(self, run):
            result = run("known-hosts-fix")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")

        def test_should_reject_two_arguments(self, run):
            result = run("known-hosts-fix", "a.test", "b.test")
            assert result.returncode == 2
            assert result.stderr == "known-hosts-fix: expected exactly one <host> or <line>\nSee 'known-hosts-fix --help'\n"

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("known-hosts-fix", "--nope")
            assert result.returncode == 2
            assert result.stderr == "known-hosts-fix: unknown option: --nope\nSee 'known-hosts-fix --help'\n"


KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGRfYjWZcOhPaLmjKH3bTz3uY1H6Yk+3fBtYBgqd+8sW"
PLAIN_A = f"a.test {KEY}\n"
PLAIN_B = f"b.test,10.0.0.2 {KEY}\n"
HASHED = f"|1|abcdefghijklmnopqrstuvwxyz0=|abcdefghijklmnopqrstuvwxyz0= {KEY}\n"
REAL_SSH_KEYGEN = 'exec "$(command -pv ssh-keygen)" "$@"\n'


def write_known_hosts(sandbox):
    ssh = sandbox.home / ".ssh"
    ssh.mkdir(mode=0o700)
    known_hosts = ssh / "known_hosts"
    known_hosts.write_text(PLAIN_A + PLAIN_B + HASHED)
    return known_hosts
